import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""권장 모델(초성11 x 중성4 x 종성8)의 잔차를 축별로 분해해 가장 안 맞는 곳을 찾는다."""
import pickle, json
import numpy as np
from collections import defaultdict
from tree import CHO, JUNG, JONG, COMPOUND_TRAILINGS
RIGHT,LEFT,HORZ='ㅏㅐㅑㅒㅣ','ㅓㅔㅕㅖ','ㅗㅛㅜㅠㅡ'
def fam(v): return 'VR' if v in RIGHT else 'VL' if v in LEFT else 'H' if v in HORZ else 'M'
def tkind(t): return 'none' if t==0 else ('compound' if t in COMPOUND_TRAILINGS else 'simple')
HERE=_os.path.dirname(_os.path.abspath(__file__))
part=pickle.load(open(_os.path.join(HERE,'partial.pkl'),'rb'))
VG=json.load(open(_os.path.join(HERE,'..','variant_groups.json'),encoding='utf-8'))
gc=np.zeros(21,int); gj=np.zeros(21,int); gv=np.zeros(19,int)
for i,g in enumerate(VG['choVariantGroups']):
    for ch in g: gc[JUNG.index(ch)]=i
for i,g in enumerate(VG['trailingVariantGroups']):
    for ch in g: gj[JUNG.index(ch)]=i
for i,g in enumerate(VG['medialVariantGroups']):
    for ch in g: gv[CHO.index(ch)]=i
DATA=defaultdict(list)
for k,bx in part.items():
    for p,b in bx.items(): DATA[p].append(k+tuple(b))
PATHS=sorted(DATA,key=lambda p:-len(DATA[p]))
rng=np.random.default_rng(20260730)
mask={k:(rng.random()<0.8) for k in sorted(part)}
FAMS=['VR','VL','H','M']; TKS=['none','simple','compound']
def oh(v,n):
    M=np.zeros((len(v),n)); M[np.arange(len(v)),v]=1; return M
def X_of(rows):
    li=np.array([r[0] for r in rows]); vi=np.array([r[1] for r in rows]); ti=np.array([r[2] for r in rows])
    f=np.array([FAMS.index(fam(JUNG[v])) for v in vi]); t=np.array([TKS.index(tkind(x)) for x in ti])
    nc,nj,nv=11,8,4
    return np.hstack([np.ones((len(rows),1)), oh(f*3+t,12), oh(li,19), oh(vi,21), oh(ti,28),
                      oh(li*nc+gc[vi],19*nc), oh(ti*nj+gj[vi],28*nj), oh(vi*nv+gv[li],21*nv)])
recs=[]
for p in PATHS:
    rows=DATA[p]; X=X_of(rows); Y=np.array([r[3:] for r in rows],dtype=float)
    m=np.array([mask[(r[0],r[1],r[2])] for r in rows])
    if m.sum()<10: continue
    W=np.linalg.solve(X[m].T@X[m]+np.eye(X.shape[1]), X[m].T@Y[m])
    P=X@W; E=P-Y
    for r,e,tr in zip(rows,E,m):
        recs.append(dict(syl=r[:3],path=p,err=float(np.abs(e).max()),
                         signed=e,train=bool(tr),box=r[3:]))
te=[r for r in recs if not r['train']]
def rank(keyfn, title, top=10, minn=20):
    g=defaultdict(list)
    for r in te: g[keyfn(r)].append(r['err'])
    rows=[(np.median(v),np.percentile(v,90),len(v),k) for k,v in g.items() if len(v)>=minn]
    rows.sort(reverse=True)
    print('\n### %s (검증셋 중앙값 기준)'%title)
    print('   %-24s %7s %7s %6s'%('키','중앙값','p90','n'))
    for md,p90,n,k in rows[:top]: print('   %-24s %7.1f %7.1f %6d'%(k,md,p90,n))
    if len(rows)>top:
        print('   ... 가장 잘 맞는 쪽')
        for md,p90,n,k in rows[-3:]: print('   %-24s %7.1f %7.1f %6d'%(k,md,p90,n))
allerr=[r['err'] for r in te]
print('검증셋 %d상자  중앙값 %.1f  p90 %.1f  p99 %.1f em'%(
    len(te),np.median(allerr),np.percentile(allerr,90),np.percentile(allerr,99)))
rank(lambda r:r['path'],'노드별')
rank(lambda r:'%s / %s'%(fam(JUNG[r['syl'][1]]),tkind(r['syl'][2])),'토폴로지별')
rank(lambda r:JUNG[r['syl'][1]],'중성별',12)
rank(lambda r:CHO[r['syl'][0]],'초성별',8)
rank(lambda r:JONG[r['syl'][2]] or '(없음)','종성별',10)
print('\n### 가장 안 맞는 개별 상자 20개')
te.sort(key=lambda r:-r['err'])
print('   %-4s %-18s %7s   %s'%('글자','노드','오차','치우침 (x0,y0,x1,y1)'))
for r in te[:20]:
    li,vi,ti=r['syl']; ch=chr(0xAC00+(li*21+vi)*28+ti)
    print('   %-4s %-18s %7.0f   %s'%(ch,r['path'],r['err'],
        ' '.join('%+5.0f'%x for x in r['signed'])))
# 계통 오차인지 확인
print('\n### 치우침(bias) — 계통 오차가 남았는지')
print('   %-18s %s'%('노드','평균 부호 오차 (x0,y0,x1,y1)'))
g=defaultdict(list)
for r in te: g[r['path']].append(r['signed'])
for p in PATHS:
    if p in g and len(g[p])>=20:
        m=np.mean(g[p],axis=0)
        print('   %-18s %s'%(p,' '.join('%+6.1f'%x for x in m)))
pickle.dump(te,open(_os.path.join(HERE,'worst.pkl'),'wb'))
