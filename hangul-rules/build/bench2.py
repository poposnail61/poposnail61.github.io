import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""2차 스윕: 상호작용을 계열 단위로 줄이고, 파라미터화도 비교한다."""
import pickle
import numpy as np
from collections import defaultdict
from tree import tree, CHO, JUNG, JONG, COMPOUND_TRAILINGS
RIGHT,LEFT,HORZ,MIX='ㅏㅐㅑㅒㅣ','ㅓㅔㅕㅖ','ㅗㅛㅜㅠㅡ','ㅘㅙㅚㅝㅞㅟㅢ'
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
def oh(v,n):
    M=np.zeros((len(v),n)); M[np.arange(len(v)),v]=1; return M
FAMS=['VR','VL','H','M']; TKS=['none','simple','compound']
def feats(rows):
    li=np.array([r[0] for r in rows]); vi=np.array([r[1] for r in rows]); ti=np.array([r[2] for r in rows])
    f=np.array([FAMS.index(fam(JUNG[v])) for v in vi]); t=np.array([TKS.index(tkind(x)) for x in ti])
    return dict(li=li,vi=vi,ti=ti,fam=f,tk=t,topo=f*3+t)
def design(rows,spec):
    F=feats(rows); n=len(rows); C=[np.ones((n,1))]
    add=lambda v,k: C.append(oh(v,k))
    if 'topo' in spec: add(F['topo'],12)
    if 'cho' in spec: add(F['li'],19)
    if 'jung' in spec: add(F['vi'],21)
    if 'jong' in spec: add(F['ti'],28)
    if 'cho*fam' in spec: add(F['li']*4+F['fam'],19*4)
    if 'cho*jung' in spec: add(F['li']*21+F['vi'],19*21)
    if 'jong*fam' in spec: add(F['ti']*4+F['fam'],28*4)
    if 'jong*topo' in spec: add(F['ti']*12+F['topo'],28*12)
    if 'jong*jung' in spec: add(F['ti']*21+F['vi'],28*21)
    if 'jung*tk' in spec: add(F['vi']*3+F['tk'],21*3)
    return np.hstack(C)
LAM=1.0
def ev(spec,param='corner'):
    tr=[];te=[];pr=0
    for p in PATHS:
        rows=DATA[p]; X=design(rows,spec)
        B=np.array([r[3:] for r in rows],dtype=float)
        Y=B if param=='corner' else np.stack([(B[:,0]+B[:,2])/2,(B[:,1]+B[:,3])/2,
                                              B[:,2]-B[:,0],B[:,3]-B[:,1]],axis=1)
        m=np.array([mask[(r[0],r[1],r[2])] for r in rows])
        if m.sum()<10 or (~m).sum()<3: continue
        W=np.linalg.solve(X[m].T@X[m]+LAM*np.eye(X.shape[1]), X[m].T@Y[m])
        pr+=int((np.abs(W).max(axis=1)>1e-6).sum())*4
        for sel,acc in ((m,tr),(~m,te)):
            P=X[sel]@W
            if param!='corner':
                P=np.stack([P[:,0]-P[:,2]/2,P[:,1]-P[:,3]/2,P[:,0]+P[:,2]/2,P[:,1]+P[:,3]/2],axis=1)
            acc.append(np.abs(P-B[sel]).max(axis=1))
    tr=np.concatenate(tr);te=np.concatenate(te)
    return pr,np.median(tr),np.median(te),np.percentile(te,95)
S=[('완전가산',{'topo','cho','jung','jong'}),
   ('+초성×계열',{'topo','cho','jung','jong','cho*fam'}),
   ('+초성×계열 +종성×계열',{'topo','cho','jung','jong','cho*fam','jong*fam'}),
   ('+초성×계열 +종성×토폴로지',{'topo','cho','jung','jong','cho*fam','jong*topo'}),
   ('+초성×중성 +종성×계열',{'topo','cho','jung','jong','cho*jung','jong*fam'}),
   ('+초성×중성 +종성×토폴로지',{'topo','cho','jung','jong','cho*jung','jong*topo'}),
   ('+초성×중성 +종성×중성',{'topo','cho','jung','jong','cho*jung','jong*jung'}),
   ('+초성×계열 +종성×중성',{'topo','cho','jung','jong','cho*fam','jong*jung'}),
   ('+초성×중성 +종성×중성 +중성×받침',{'topo','cho','jung','jong','cho*jung','jong*jung','jung*tk'}),
  ]
print('%-32s %9s %9s %9s %9s'%('모델','파라미터','학습','검증','검증p95'))
for nm,sp in S:
    pr,a,b,c=ev(sp); print('%-32s %9d %9.1f %9.1f %9.1f'%(nm,pr,a,b,c))
print()
print('파라미터화 비교 (모서리 직접 vs 중심+크기), 최적 모델 기준:')
best={'topo','cho','jung','jong','cho*jung','jong*jung'}
for pm in ('corner','centersize'):
    pr,a,b,c=ev(best,pm); print('  %-12s %9d %9.1f %9.1f %9.1f'%(pm,pr,a,b,c))
