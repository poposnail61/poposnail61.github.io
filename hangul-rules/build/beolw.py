import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""벌 구성(변형체 그룹)이 마스터 100/900에서 같은가.

다르면 JamoVariant 구조 자체가 굵기마다 달라져야 해서 곤란하다.
"""
import json, pickle, subprocess, sys
import numpy as np
from collections import defaultdict
from tree import CHO, JUNG, JONG, COMPOUND_TRAILINGS
HERE=_os.path.dirname(_os.path.abspath(__file__))
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
    return sorted([sorted(g) for g in groups], key=lambda g:g[0])
def eff(DATA, paths, by, n):
    acc=defaultdict(list)
    for p in paths:
        if p not in DATA: continue
        rows=DATA[p]; B=np.array([r[3:] for r in rows],dtype=float); base=B.mean(axis=0)
        for r,b in zip(rows,B): acc[r[by]].append(b-base)
    V=np.zeros((n,4))
    for i in range(n): V[i]=np.mean(acc[i],axis=0) if acc[i] else 0
    return V
def groups_for(font):
    subprocess.run([sys.executable,_os.path.join(HERE,'partial.py'),font],
                   capture_output=True,check=True)
    part=pickle.load(open(_os.path.join(HERE,'partial.pkl'),'rb'))
    DATA=defaultdict(list)
    for k,bx in part.items():
        for p,b in bx.items(): DATA[p].append(k+tuple(b))
    Vc=eff(DATA,['Leading','LeadingMedial','LeadingMedialBase'],1,21)
    Vj=eff(DATA,['Trailing','TrailingFirst','TrailingSecond'],1,21)
    Vv=eff(DATA,['Medial','MedialBase','MedialExtension'],0,19)
    return (ward(Vc,11,21), ward(Vv,4,19), ward(Vj,8,21), len(part))
S='/tmp/claude-0/-home-user-poposnail61-github-io/727310cc-b2b3-5037-a683-997efa16057f/scratchpad'
res={}
for w in ('Thin','Regular','Black'):
    res[w]=groups_for('%s/NotoSansCJKkr-%s.otf'%(S,w))
    print('%s 분해 %d자'%(w,res[w][3]))
def show(name,idx,alph):
    print('\n=== %s ==='%name)
    for w in ('Thin','Regular','Black'):
        gs=res[w][idx]
        print('  %-8s %s'%(w,' | '.join(''.join(alph[i] for i in g) for g in gs)))
    # 쌍별 일치율: 같은 그룹에 속하는지 여부가 마스터 간 같은가
    def pairset(gs,n):
        m={}
        for gi,g in enumerate(gs):
            for i in g: m[i]=gi
        return {(a,b):(m[a]==m[b]) for a in range(n) for b in range(a+1,n)}
    n=len(alph)
    pt,pb=pairset(res['Thin'][idx],n),pairset(res['Black'][idx],n)
    agree=sum(1 for k in pt if pt[k]==pb[k])
    print('  Thin vs Black 쌍 일치: %d / %d (%.1f%%)'%(agree,len(pt),100*agree/len(pt)))
show('초성 11벌 (중성 묶음)',0,JUNG)
show('중성 4벌 (초성 묶음)',1,CHO)
show('종성 8벌 (중성 묶음)',2,JUNG)
json.dump({w:{'cho':[''.join(JUNG[i] for i in g) for g in res[w][0]],
              'medial':[''.join(CHO[i] for i in g) for g in res[w][1]],
              'trailing':[''.join(JUNG[i] for i in g) for g in res[w][2]]}
           for w in res},
          open(_os.path.join(HERE,_os.pardir,'variant-groups-by-weight.json'),'w'),
          ensure_ascii=False,indent=1)
