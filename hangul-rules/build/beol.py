import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""초성·종성이 몇 벌 필요한가 — 중성 그룹 수를 데이터로 정한다.

초성×중성 상호작용을 '초성 변형체를 중성 그룹으로 고른다'로 읽으면, 그룹 수 k 가
곧 벌 수다. k 를 늘려가며 홀드아웃 오차를 재고 무릎을 찾는다.
"""
import pickle
import numpy as np
from collections import defaultdict
from tree import CHO, JUNG, JONG, COMPOUND_TRAILINGS
RIGHT,LEFT,HORZ='ㅏㅐㅑㅒㅣ','ㅓㅔㅕㅖ','ㅗㅛㅜㅠㅡ'
def fam(v): return 'VR' if v in RIGHT else 'VL' if v in LEFT else 'H' if v in HORZ else 'M'
def tkind(t): return 'none' if t==0 else ('compound' if t in COMPOUND_TRAILINGS else 'simple')
HERE=_os.path.dirname(_os.path.abspath(__file__))
part=pickle.load(open(_os.path.join(HERE,'partial.pkl'),'rb'))
DATA=defaultdict(list)
for k,bx in part.items():
    for p,b in bx.items(): DATA[p].append(k+tuple(b))
PATHS=sorted(DATA,key=lambda p:-len(DATA[p]))
rng=np.random.default_rng(20260730)
mask={k:(rng.random()<0.8) for k in sorted(part)}
FAMS=['VR','VL','H','M']; TKS=['none','simple','compound']
def oh(v,n):
    M=np.zeros((len(v),n)); M[np.arange(len(v)),v]=1; return M

def build(rows, cho_grp, jong_grp):
    """cho_grp/jong_grp: 중성 21개 -> 그룹 id 배열"""
    li=np.array([r[0] for r in rows]); vi=np.array([r[1] for r in rows]); ti=np.array([r[2] for r in rows])
    f=np.array([FAMS.index(fam(JUNG[v])) for v in vi]); t=np.array([TKS.index(tkind(x)) for x in ti])
    kc=cho_grp[vi]; kj=jong_grp[vi]
    nc=int(cho_grp.max())+1; nj=int(jong_grp.max())+1
    return np.hstack([np.ones((len(rows),1)), oh(f*3+t,12), oh(li,19), oh(vi,21), oh(ti,28),
                      oh(li*nc+kc,19*nc), oh(ti*nj+kj,28*nj)])
def ev(cho_grp,jong_grp):
    tr=[];te=[];pr=0
    for p in PATHS:
        rows=DATA[p]; X=build(rows,cho_grp,jong_grp)
        Y=np.array([r[3:] for r in rows],dtype=float)
        m=np.array([mask[(r[0],r[1],r[2])] for r in rows])
        if m.sum()<10 or (~m).sum()<3: continue
        W=np.linalg.solve(X[m].T@X[m]+np.eye(X.shape[1]), X[m].T@Y[m])
        pr+=int((np.abs(W).max(axis=1)>1e-6).sum())*4
        for sel,acc in ((m,tr),(~m,te)): acc.append(np.abs(X[sel]@W-Y[sel]).max(axis=1))
    return pr,np.median(np.concatenate(tr)),np.median(np.concatenate(te)),np.percentile(np.concatenate(te),95)

# 1) 중성별 효과 벡터를 뽑아 계층 군집
def effect_vectors(role):
    """role='cho'면 초성 상자, 'jong'이면 종성 상자에서 중성별 평균 효과"""
    paths=(['Leading','LeadingMedial','LeadingMedialBase'] if role=='cho'
           else ['Trailing','TrailingFirst','TrailingSecond'])
    acc=defaultdict(list)
    for p in paths:
        if p not in DATA: continue
        rows=DATA[p]; B=np.array([r[3:] for r in rows],dtype=float)
        base=B.mean(axis=0)
        for r,b in zip(rows,B): acc[r[1]].append(b-base)
    V=np.zeros((21,4))
    for v in range(21):
        V[v]=np.mean(acc[v],axis=0) if acc[v] else 0
    return V
def cluster(V,k):
    """단순 계층 군집 (Ward 유사, 완전연결)"""
    groups=[[i] for i in range(21)]
    def cen(g): return V[g].mean(axis=0)
    while len(groups)>k:
        best=None
        for a in range(len(groups)):
            for b in range(a+1,len(groups)):
                d=np.linalg.norm(cen(groups[a])-cen(groups[b]))
                n=len(groups[a])*len(groups[b])/(len(groups[a])+len(groups[b]))
                if best is None or n*d<best[0]: best=(n*d,a,b)
        _,a,b=best; groups[a]=groups[a]+groups[b]; groups.pop(b)
    out=np.zeros(21,dtype=int)
    for gi,g in enumerate(groups):
        for v in g: out[v]=gi
    return out,groups
Vc=effect_vectors('cho'); Vj=effect_vectors('jong')
print('%-6s %-6s %9s %9s %9s %9s'%('초성벌','종성벌','파라미터','학습','검증','검증p95'))
best=None
for kc in (1,2,3,4,6,8,11,21):
    gc,_=cluster(Vc,kc)
    for kj in (1,2,4,8,21):
        gj,_=cluster(Vj,kj)
        pr,a,b,c=ev(gc,gj)
        print('%-6d %-6d %9d %9.1f %9.1f %9.1f'%(kc,kj,pr,a,b,c))
        if best is None or b<best[0]: best=(b,kc,kj,pr,c)
print()
print('최소 검증오차: 초성 %d벌 × 종성 %d벌 -> %.1f em (파라미터 %d, p95 %.1f)'%(
    best[1],best[2],best[0],best[3],best[4]))
for k in (2,3,4,6):
    g,groups=cluster(Vc,k)
    print('초성 %d벌 중성 그룹:'%k, ' | '.join(''.join(JUNG[v] for v in sorted(gg)) for gg in groups))
print()
for k in (2,4,8):
    g,groups=cluster(Vj,k)
    print('종성 %d벌 중성 그룹:'%k, ' | '.join(''.join(JUNG[v] for v in sorted(gg)) for gg in groups))
