import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""마스터 100/900 효과 벡터를 이어 붙여 굵기에 안정적인 벌 구성을 찾는다.

한 마스터에서만 군집하면 다른 마스터에서 그룹이 재편된다(중성은 쌍 일치 72%).
두 끝점의 효과를 8차원으로 이어 붙여 군집하면 두 마스터 모두에서 성립하는
그룹만 남는다.
"""
import json, pickle, subprocess, sys
import numpy as np
from collections import defaultdict
from tree import CHO, JUNG, JONG, COMPOUND_TRAILINGS
RIGHT,LEFT,HORZ='ㅏㅐㅑㅒㅣ','ㅓㅔㅕㅖ','ㅗㅛㅜㅠㅡ'
def fam(v): return 'VR' if v in RIGHT else 'VL' if v in LEFT else 'H' if v in HORZ else 'M'
def tkind(t): return 'none' if t==0 else ('compound' if t in COMPOUND_TRAILINGS else 'simple')
HERE=_os.path.dirname(_os.path.abspath(__file__))
S='/tmp/claude-0/-home-user-poposnail61-github-io/727310cc-b2b3-5037-a683-997efa16057f/scratchpad'
def load(w):
    subprocess.run([sys.executable,_os.path.join(HERE,'partial.py'),
                    '%s/NotoSansCJKkr-%s.otf'%(S,w)],capture_output=True,check=True)
    part=pickle.load(open(_os.path.join(HERE,'partial.pkl'),'rb'))
    D=defaultdict(list)
    for k,bx in part.items():
        for p,b in bx.items(): D[p].append(k+tuple(b))
    return part,D
def eff(D,paths,by,n):
    acc=defaultdict(list)
    for p in paths:
        if p not in D: continue
        B=np.array([r[3:] for r in D[p]],dtype=float); base=B.mean(axis=0)
        for r,b in zip(D[p],B): acc[r[by]].append(b-base)
    V=np.zeros((n,4))
    for i in range(n): V[i]=np.mean(acc[i],axis=0) if acc[i] else 0
    return V/ (np.abs(V).max()+1e-9)          # 마스터 간 스케일 차이를 없앤다
def ward(V,k,n):
    g=[[i] for i in range(n)]; cen=lambda x:V[x].mean(axis=0)
    while len(g)>k:
        best=None
        for a in range(len(g)):
            for b in range(a+1,len(g)):
                d=np.linalg.norm(cen(g[a])-cen(g[b]))
                w=len(g[a])*len(g[b])/(len(g[a])+len(g[b]))
                if best is None or w*d<best[0]: best=(w*d,a,b)
        _,a,b=best; g[a]+=g[b]; g.pop(b)
    return sorted([sorted(x) for x in g],key=lambda x:x[0])
PT={},
parts={}; Ds={}
for w in ('Thin','Black'):
    parts[w],Ds[w]=load(w)
CHOP=['Leading','LeadingMedial','LeadingMedialBase']
JONGP=['Trailing','TrailingFirst','TrailingSecond']
MEDP=['Medial','MedialBase','MedialExtension']
Vc=np.hstack([eff(Ds[w],CHOP,1,21) for w in ('Thin','Black')])
Vj=np.hstack([eff(Ds[w],JONGP,1,21) for w in ('Thin','Black')])
Vv=np.hstack([eff(Ds[w],MEDP,0,19) for w in ('Thin','Black')])

def ev(gc,gj,gv,w):
    part,D=parts[w],Ds[w]
    rng=np.random.default_rng(20260730)
    mask={k:(rng.random()<0.8) for k in sorted(part)}
    FAMS=['VR','VL','H','M']; TKS=['none','simple','compound']
    def oh(v,n):
        M=np.zeros((len(v),n)); M[np.arange(len(v)),v]=1; return M
    te=[];pr=0
    nc,nj,nv=int(gc.max())+1,int(gj.max())+1,int(gv.max())+1
    for p in sorted(D,key=lambda x:-len(D[x])):
        rows=D[p]
        li=np.array([r[0] for r in rows]);vi=np.array([r[1] for r in rows]);ti=np.array([r[2] for r in rows])
        f=np.array([FAMS.index(fam(JUNG[v])) for v in vi]);t=np.array([TKS.index(tkind(x)) for x in ti])
        X=np.hstack([np.ones((len(rows),1)),oh(f*3+t,12),oh(li,19),oh(vi,21),oh(ti,28),
                     oh(li*nc+gc[vi],19*nc),oh(ti*nj+gj[vi],28*nj),oh(vi*nv+gv[li],21*nv)])
        Y=np.array([r[3:] for r in rows],dtype=float)
        m=np.array([mask[(r[0],r[1],r[2])] for r in rows])
        if m.sum()<10 or (~m).sum()<3: continue
        W=np.linalg.solve(X[m].T@X[m]+np.eye(X.shape[1]),X[m].T@Y[m])
        pr+=int((np.abs(W).max(axis=1)>1e-6).sum())*4
        te.append(np.abs(X[~m]@W-Y[~m]).max(axis=1))
    te=np.concatenate(te)
    return pr,np.median(te),np.percentile(te,95)
def gidx(groups,n):
    out=np.zeros(n,int)
    for gi,g in enumerate(groups):
        for i in g: out[i]=gi
    return out
print('공통 벌 구성 (두 마스터 효과를 이어 붙여 군집)')
for kc,kv,kj in [(11,4,8),(11,2,8),(8,2,8),(11,2,4)]:
    gc=gidx(ward(Vc,kc,21),21); gv=gidx(ward(Vv,kv,19),19); gj=gidx(ward(Vj,kj,21),21)
    r={w:ev(gc,gj,gv,w) for w in ('Thin','Black')}
    print('  %2d x %d x %d   Thin %5.1f/%5.1f   Black %5.1f/%5.1f   (파라미터 %d)'%(
        kc,kv,kj,r['Thin'][1],r['Thin'][2],r['Black'][1],r['Black'][2],r['Thin'][0]))
print()
for name,V,k,alph,n in (('초성',Vc,11,JUNG,21),('중성',Vv,4,CHO,19),('종성',Vj,8,JUNG,21)):
    gs=ward(V,k,n)
    print('%s %d벌 (공통): %s'%(name,k,' | '.join(''.join(alph[i] for i in g) for g in gs)))
print()
gs=ward(Vv,2,19)
print('중성 2벌 (공통): %s'%(' | '.join(''.join(CHO[i] for i in g) for g in gs)))
out={'note':'마스터 100/900 효과 벡터를 이어 붙여 군집한 굵기 안정 벌 구성',
     'cho11':[''.join(JUNG[i] for i in g) for g in ward(Vc,11,21)],
     'medial4':[''.join(CHO[i] for i in g) for g in ward(Vv,4,19)],
     'medial2':[''.join(CHO[i] for i in g) for g in ward(Vv,2,19)],
     'trailing8':[''.join(JUNG[i] for i in g) for g in ward(Vj,8,21)]}
json.dump(out,open(_os.path.join(HERE,_os.pardir,'variant-groups-stable.json'),'w'),
          ensure_ascii=False,indent=1)
print('\nvariant-groups-stable.json 생성')
