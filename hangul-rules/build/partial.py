import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""측정 가능한 가장 깊은 노드까지만 내려가는 부분 분해.

획이 붙어 분리가 안 되는 자리는 리프 대신 그 부모 그룹 노드를 하나의 상자로 남긴다.
음절 전체를 버리지 않으므로 커버리지가 크게 올라간다.
"""
import pickle, sys
from collections import Counter, defaultdict
import measure as M
from fontTools.ttLib import TTFont
from tree import tree, CHO, JUNG, JONG, COMPOUND_MEDIALS, COMPOUND_TRAILINGS
import leaves as L

def union(a,b): return (min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3]))
def bb(sl): return M.bbox(sl)

def peel_trailing(shapes):
    """종성을 y 공백으로 떼어낸다. 모든 후보 절단선을 시험해 타당한 것을 고른다."""
    iv=sorted((s[2],s[4]) for s in shapes); cur=iv[0][1]; cuts=[]
    for lo,hi in iv[1:]:
        if lo>cur: cuts.append((cur+lo)/2)
        cur=max(cur,hi)
    for cut in cuts:                                  # 아래쪽 절단선부터
        low=[s for s in shapes if s[4]<=cut]; up=[s for s in shapes if s[2]>=cut]
        if len(low)+len(up)!=len(shapes) or not low or not up: continue
        bl,bu=bb(low),bb(up)
        if bl[3]<500 and bu[3]>700: return low,up     # 종성은 아래, 초·중성은 위
    return None

def right_extension(shapes, xmin=600):
    """섞임/세로모임에서 오른쪽 기둥(중성 확장부)만 떼어낸다."""
    r=[s for s in shapes if s[1]>xmin]; rest=[s for s in shapes if s[1]<=xmin]
    return (r,rest) if r and rest else None

def boxes_for(k, slots, horz, D):
    """path -> box. 리프까지 못 가면 그룹 노드로 남긴다."""
    li,vi,ti=k
    out={}; compound_v = vi in COMPOUND_MEDIALS; compound_t = ti in COMPOUND_TRAILINGS

    def put_trailing(js):
        if not ti: return
        if compound_t:
            sp=L.split_x(js)
            if sp: out['TrailingFirst']=bb(sp[0]); out['TrailingSecond']=bb(sp[1])
            else:  out['Trailing']=bb(js)
        else: out['Trailing']=bb(js)

    if k in slots:
        cs,ms,js=slots[k]
        put_trailing(js)
        if compound_v:
            sp=L.split_medial(vi,cs,ms)
            if sp:
                out['Leading']=bb(sp[0]); out['MedialBase']=bb(sp[1])
                out['MedialExtension']=bb(sp[2])
            else:
                # 초성과 중성기저가 붙었다. 확장부만 떼고 나머지는 그룹으로 남긴다
                ext=right_extension(cs+ms)
                if ext:
                    out['MedialExtension']=bb(ext[0]); out['LeadingMedialBase']=bb(ext[1])
                else:
                    out['LeadingMedial']=bb(cs+ms)
        else:
            cs2,ms2=L.reunite_medial(vi,cs,ms)
            out['Leading']=bb(cs2); out['Medial']=bb(ms2)
        return out

    if k in horz:
        cs,mid,js=horz[k]
        put_trailing(js)
        out['Leading']=bb(cs); out['Medial']=(mid[1],mid[2],mid[3],mid[4])
        return out

    # 슬롯분해 자체가 실패: 종성만이라도 떼어 본다
    sh=D[k]
    if ti:
        pl=peel_trailing(sh)
        if pl:
            low,up=pl; put_trailing(low)
            if compound_v:
                ext=right_extension(up)
                if ext: out['MedialExtension']=bb(ext[0]); out['LeadingMedialBase']=bb(ext[1])
                else:   out['LeadingMedial']=bb(up)
            else:
                ext=right_extension(up)
                if ext and JUNG[vi] not in 'ㅗㅛㅜㅠㅡ':
                    out['Medial']=bb(ext[0]); out['Leading']=bb(ext[1])
                else:
                    out['LeadingMedial']=bb(up)
            return out
    # 받침 없거나 못 떼면 오른쪽 기둥만이라도
    if not compound_v and JUNG[vi] not in 'ㅗㅛㅜㅠㅡ':
        ext=right_extension(sh)
        if ext: return {'Medial':bb(ext[0]),'Leading':bb(ext[1])}
    if compound_v:
        ext=right_extension(sh)
        if ext: return {'MedialExtension':bb(ext[0]),'LeadingMedialBase':bb(ext[1])}
    return {}

def main(font_path):
    f=TTFont(font_path); D=M.extract(f)
    a=L.run_validated(D,60); b=L.run_validated(D,120)
    slots=dict(b); slots.update(a); horz=L.horz_shapes(D)
    res={}; pathcnt=Counter(); depth=Counter()
    for li in range(19):
        for vi in range(21):
            for ti in range(28):
                k=(li,vi,ti)
                bx=boxes_for(k,slots,horz,D)
                if not bx: depth['0 아무것도 못 얻음']+=1; continue
                nodes,root=tree(*k)
                leafpaths={p for p,kind in nodes if kind[0]=='leaf'}
                # 트리에 없는 path 제거 (안전)
                bx={p:v for p,v in bx.items() if p in {q for q,_ in nodes}}
                if not bx: depth['0 아무것도 못 얻음']+=1; continue
                res[k]=bx
                for p in bx: pathcnt[p]+=1
                depth['리프 전부' if leafpaths<=set(bx) else '부분']+=1
    print('부분 분해 결과 (11,172자):')
    for kk,v in sorted(depth.items()): print('  %-18s %5d  %5.1f%%'%(kk,v,100*v/11172))
    print()
    print('노드별 관측 자수:')
    for p,c in sorted(pathcnt.items(),key=lambda kv:-kv[1]):
        print('  %-18s %5d'%(p,c))
    pickle.dump(res,open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),'partial.pkl'),'wb'))
    print()
    print('총 상자 %d개 / %d자'%(sum(pathcnt.values()),len(res)))

if __name__=='__main__': main(sys.argv[1])
