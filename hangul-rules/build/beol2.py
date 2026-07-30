import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""최종 벌식 스윕. 전통 벌식 그대로 세 슬롯의 변형체 키를 동시에 정한다.

  초성 벌 = 초성 x 중성그룹(kc) x 받침유무(선택)
  중성 벌 = 중성 x 초성그룹(kv)
  종성 벌 = 종성 x 중성그룹(kj)
"""
import itertools, pickle
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
def ward(V,k,n):
    groups=[[i] for i in range(n)]
    cen=lambda g: V[g].mean(axis=0)
    while len(groups)>k:
        best=None
        for a in range(len(groups)):
            for b in range(a+1,len(groups)):
                d=np.linalg.norm(cen(groups[a])-cen(groups[b]))
                w=len(groups[a])*len(groups[b])/(len(groups[a])+len(groups[b]))
                if best is None or w*d<best[0]: best=(w*d,a,b)
        _,a,b=best; groups[a]+=groups[b]; groups.pop(b)
    out=np.zeros(n,dtype=int)
    for gi,g in enumerate(groups):
        for v in g: out[v]=gi
    return out,groups
def eff(paths, by):
    acc=defaultdict(list); n=21 if by==1 else 19
    for p in paths:
        if p not in DATA: continue
        rows=DATA[p]; B=np.array([r[3:] for r in rows],dtype=float); base=B.mean(axis=0)
        for r,b in zip(rows,B): acc[r[by]].append(b-base)
    V=np.zeros((n,4))
    for i in range(n): V[i]=np.mean(acc[i],axis=0) if acc[i] else 0
    return V,n
Vc,_=eff(['Leading','LeadingMedial','LeadingMedialBase'],1)      # 초성 벌 <- 중성
Vj,_=eff(['Trailing','TrailingFirst','TrailingSecond'],1)        # 종성 벌 <- 중성
Vv,_=eff(['Medial','MedialBase','MedialExtension'],0)            # 중성 벌 <- 초성

def ev(gc,gj,gv,use_tk):
    tr=[];te=[];pr=0
    nc=int(gc.max())+1; nj=int(gj.max())+1; nv=int(gv.max())+1
    for p in PATHS:
        rows=DATA[p]
        li=np.array([r[0] for r in rows]); vi=np.array([r[1] for r in rows]); ti=np.array([r[2] for r in rows])
        f=np.array([FAMS.index(fam(JUNG[v])) for v in vi]); t=np.array([TKS.index(tkind(x)) for x in ti])
        ck = gc[vi]*2+(ti>0).astype(int) if use_tk else gc[vi]
        ncc = nc*2 if use_tk else nc
        X=np.hstack([np.ones((len(rows),1)), oh(f*3+t,12), oh(li,19), oh(vi,21), oh(ti,28),
                     oh(li*ncc+ck,19*ncc), oh(ti*nj+gj[vi],28*nj), oh(vi*nv+gv[li],21*nv)])
        Y=np.array([r[3:] for r in rows],dtype=float)
        m=np.array([mask[(r[0],r[1],r[2])] for r in rows])
        if m.sum()<10 or (~m).sum()<3: continue
        W=np.linalg.solve(X[m].T@X[m]+np.eye(X.shape[1]), X[m].T@Y[m])
        pr+=int((np.abs(W).max(axis=1)>1e-6).sum())*4
        for sel,acc in ((m,tr),(~m,te)): acc.append(np.abs(X[sel]@W-Y[sel]).max(axis=1))
    te=np.concatenate(te)
    return pr,np.median(np.concatenate(tr)),np.median(te),np.percentile(te,95)

print('%-30s %8s %7s %7s %7s'%('구성 (초성벌 x 중성벌 x 종성벌)','파라미터','학습','검증','p95'))
front=[]
for kc,kj,kv,tk in [(3,2,1,False),(3,2,2,False),(3,2,2,True),(4,4,2,True),(6,4,2,True),
                    (6,4,4,True),(8,8,4,True),(11,8,4,True),(11,8,8,True),(11,21,8,True),
                    (21,21,19,True),(6,4,4,False),(8,8,4,False),(11,8,4,False)]:
    gc,_=ward(Vc,kc,21); gj,_=ward(Vj,kj,21); gv,_=ward(Vv,kv,19)
    pr,a,b,c=ev(gc,gj,gv,tk)
    lab='%d%s x %d x %d'%(kc,'x받침' if tk else '',kv,kj)
    print('%-30s %8d %7.1f %7.1f %7.1f'%(lab,pr,a,b,c))
    front.append((pr,b,c,lab))
front.sort()
print()
print('파레토 전선 (파라미터 대비 최소 검증오차):')
best=1e9
for pr,b,c,lab in front:
    if b<best: print('  %-26s %7d  %6.1f em  p95 %5.1f'%(lab,pr,b,c)); best=b
