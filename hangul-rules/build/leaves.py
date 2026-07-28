import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""리프(자모) 단위 잉크 박스를 뽑는다. 겹중성/겹종성을 각각 둘로 쪼갠다."""
import sys, os, pickle
import measure as M
from fontTools.ttLib import TTFont
from tree import tree, CHO, JUNG, JONG, COMPOUND_MEDIALS, COMPOUND_TRAILINGS

FONT=(sys.argv[1] if len(sys.argv)>1 else None)

def slots_with_shapes(D, tol, usable):
    got=M.decompose(D,tol,usable)
    out={}
    for k,(c,m,j) in got.items():
        if not c or not m or (k[2] and not j): continue
        bc,bm,bj=M.bbox(c),M.bbox(m),M.bbox(j)
        if M.fam_of(JUNG[k[1]]) in ('VR','VL') and bc[2]>bm[0]+40: continue
        if k[2] and bj[3]>min(bc[3],bm[3])-30: continue
        out[k]=(c,m,j)
    return out

def run_validated(D,tol):
    usable={}
    for _ in range(3):
        got=M.decompose(D,tol,usable)
        nxt={k: bool(c) and bool(m) and (k[2]==0 or bool(j)) for k,(c,m,j) in got.items()}
        if nxt==usable: break
        usable=nxt
    return slots_with_shapes(D,tol,usable)

def split_x(shapes):
    """x 방향 최대 공백으로 두 덩이로 나눈다. 못 나누면 None."""
    if len(shapes)<2: return None
    iv=sorted((s[1],s[3]) for s in shapes); cur=iv[0][1]; gaps=[]
    for lo,hi in iv[1:]:
        if lo>cur: gaps.append((lo-cur,(cur+lo)/2))
        cur=max(cur,hi)
    if not gaps: return None
    cut=max(gaps)[1]
    a=[s for s in shapes if s[3]<=cut]; b=[s for s in shapes if s[1]>=cut]
    return (a,b) if len(a)+len(b)==len(shapes) and a and b else None

def pull_base(cs, ms):
    """겹중성의 MedialBase(ㅗ/ㅜ/ㅡ)를 찾는다.

    이 자모는 항상 단일 윤곽선이고 좌상 블록에서 가장 아래에 있으며 가장 넓다.
    Noto에서는 초성과 크기가 연동돼 초성 덩이에 섞여 들어오는 경우가 많다.
    """
    for pool, rest_of in ((ms, 'medial'), (cs, 'leading')):
        if not pool: continue
        yc = lambda s: (s[2] + s[4]) / 2
        low = min(pool, key=yc)
        if low[5] != 1: continue                      # 단일 윤곽선이어야 한다
        w = low[3] - low[1]
        if w < 400: continue
        if any(s is not low and s[3] - s[1] >= w for s in pool): continue
        return low, rest_of
    return None, None

def split_medial(vi, cs, ms):
    base, came_from = pull_base(cs, ms)
    if base is None: return None
    if came_from == 'medial':
        ext = [s for s in ms if s is not base]; lead = cs
    else:
        ext = ms; lead = [s for s in cs if s is not base]
    if not ext or not lead: return None
    return lead, [base], ext

def reunite_medial(vi, cs, ms):
    """세로모임에서 초성 덩이로 흘러간 중성 가로획을 되돌린다.

    ㅔ·ㅖ는 Noto에서 'ㅓ 가로획+기둥'과 'ㅣ'가 별개 도형이고, 가로획 쪽은 초성 폭에
    연동돼 초성축 불변량 판정에서 탈락한다. studio 트리는 ㅔ를 단일 Medial 리프로
    보므로 여기서 합쳐 준다. 오른쪽 40% 안에 있고 상단이 중성과 같은 높이인 도형만
    옮겨 초성 ㅊ·ㅎ처럼 위로 솟은 획을 잘못 가져가지 않는다.
    """
    if JUNG[vi] not in 'ㅏㅐㅑㅒㅓㅔㅕㅖㅣ' or not ms: return cs, ms
    x_min = 27 + 0.40 * (895 - 27)
    top = max(s[4] for s in cs + ms)
    move = [s for s in cs if s[1] > x_min and s[4] >= top - 40]
    if not move or len(move) == len(cs): return cs, ms
    return [s for s in cs if s not in move], ms + move

def leaf_boxes(k, cs, ms, js):
    """SemanticPath -> ink bbox. 못 쪼개면 해당 path 없음."""
    li,vi,ti=k
    if vi in COMPOUND_MEDIALS:
        sp=split_medial(vi,cs,ms)
        if sp is None: return None
        out={'Leading':M.bbox(sp[0]),'MedialBase':M.bbox(sp[1]),
             'MedialExtension':M.bbox(sp[2])}
    else:
        cs,ms=reunite_medial(vi,cs,ms)
        out={'Leading':M.bbox(cs),'Medial':M.bbox(ms)}
    if ti:
        if ti in COMPOUND_TRAILINGS:
            sp=split_x(js)
            if sp is None: return None
            out['TrailingFirst']=M.bbox(sp[0]); out['TrailingSecond']=M.bbox(sp[1])
        else:
            out['Trailing']=M.bbox(js)
    return out

def horz_shapes(D):
    """가로모임: 폭 750 이상 도형이 중성. shape 단위로 반환한다."""
    out={}
    for v in 'ㅗㅛㅜㅠㅡ':
        vi=JUNG.index(v)
        for ti in range(28):
            for li in range(19):
                sh=D[(li,vi,ti)]
                wide=[s for s in sh if s[3]-s[1]>750]
                if len(wide)!=1: continue
                mid=wide[0]; rest=[s for s in sh if s is not mid]
                cs=[s for s in rest if s[4]>mid[4]]
                js=[s for s in rest if s[4]<=mid[4]]
                if not cs or (ti and not js) or (ti==0 and js): continue
                out[(li,vi,ti)]=(cs,mid,js)
    return out

if __name__=='__main__':
    f=TTFont(FONT); D=M.extract(f)
    a=run_validated(D,60); b=run_validated(D,120)
    slots=dict(b); slots.update(a)
    print('세로/섞임 분해 %d자'%len(slots))
    ok=0; fail=0
    leaves={}
    for k,(cs,ms,js) in slots.items():
        lb=leaf_boxes(k,cs,ms,js)
        if lb: leaves[k]=lb; ok+=1
        else: fail+=1
    # 가로모임은 별도 경로 (초성/중성/종성 bbox만)
    for k,(cs,mid,js) in horz_shapes(D).items():
        if k in leaves: continue
        li,vi,ti=k
        lb={'Leading':M.bbox(cs),'Medial':(mid[1],mid[2],mid[3],mid[4])}
        if ti:
            if ti in COMPOUND_TRAILINGS:
                sp=split_x(js)
                if sp is None: continue
                lb['TrailingFirst']=M.bbox(sp[0]); lb['TrailingSecond']=M.bbox(sp[1])
            else:
                lb['Trailing']=M.bbox(js)
        leaves[k]=lb
    print('리프 단위 확보 %d자 (겹중성/겹종성 분리 실패 %d)'%(len(leaves),fail))
    pickle.dump((leaves,D),open('leaves.pkl','wb'))
    for ch in '괆과관각가고곡':
        i=ord(ch)-0xAC00; kk=(i//588,(i%588)//28,i%28)
        print(' ',ch, leaves.get(kk,'—'))
