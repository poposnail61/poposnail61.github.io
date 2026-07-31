import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""마스터 100/900 선형 보간이 중간 굵기를 재현하는가.

studio 엔진은 마스터 둘을 보간한다. 중간 굵기는 실측 정답지로 쓰고, lerp(100,900)이
얼마나 벗어나는지 잰다. 벗어남이 모든 값에 공통이면 avar 하나로 고칠 수 있고,
값마다 다르면 중간 보정 source가 필요하다.
"""
import json, os
import numpy as np
W=['Thin','Light','DemiLight','Regular','Medium','Bold','Black']
G=dict(zip(W,[100,300,350,400,500,700,900]))
R={w:json.load(open('/tmp/rules-%s.json'%w)) for w in W}
MID=[w for w in W if w not in ('Thin','Black')]

def collect(r):
    """비교할 스칼라들을 하나의 이름->값 사전으로."""
    d={}
    for k,v in r['jongLadder'].items(): d['종성높이.'+k]=v['h']
    for zk in ('VR0','VR1','VL1','H1','M1'):
        z=r['zones'].get(zk)
        if not z: continue
        for s in 'abc':
            if s in z:
                d['존.%s.%s.w'%(zk,s)]=z[s]['w']; d['존.%s.%s.h'%(zk,s)]=z[s]['h']
                d['존.%s.%s.y0'%(zk,s)]=z[s]['y0']
    for k,v in r['choGrade'].items(): d['초성등급.'+k]=v['z']
    d['상관.r']=r['choJong']['r']; d['상관.coef']=r['choJong']['coef']
    return d
D={w:collect(R[w]) for w in W}
keys=sorted(set(D['Thin'])&set(D['Black'])&set.intersection(*[set(D[w]) for w in MID]))
print('비교 스칼라 %d개'%len(keys))

def lerp(a,b,t): return a+(b-a)*t
rows=[]
for k in keys:
    a,b=D['Thin'][k],D['Black'][k]
    if abs(b-a)<1e-9: continue
    errs=[]
    for w in MID:
        t=(G[w]-100)/800.0
        pred=lerp(a,b,t); act=D[w][k]
        errs.append((act-pred)/abs(b-a))          # 진폭 대비 상대 오차
    rows.append((max(abs(e) for e in errs),k,errs))
rows.sort(reverse=True)
allerr=np.array([e for _,_,es in rows for e in es])
print('선형 보간 오차 (끝점 간 진폭 대비): 중앙값 %.1f%%  p90 %.1f%%  최대 %.1f%%'%(
    100*np.median(np.abs(allerr)),100*np.percentile(np.abs(allerr),90),100*np.abs(allerr).max()))
print()
print('굵기별 평균 치우침 — 한 방향이면 avar 하나로 고칠 수 있다')
print('  %-10s'%'' + ''.join('%9s'%w for w in MID))
print('  %-10s'%'wght' + ''.join('%9d'%G[w] for w in MID))
means=[]
for i,w in enumerate(MID):
    e=[es[i] for _,_,es in rows]
    means.append(np.median(e))
print('  %-10s'%'중앙 편차' + ''.join('%8.1f%%'%(100*m) for m in means))
sd=[np.std([es[i] for _,_,es in rows]) for i in range(len(MID))]
print('  %-10s'%'편차 산포' + ''.join('%8.1f%%'%(100*s) for s in sd))
print()
print('선형에서 가장 많이 벗어나는 값 12개:')
print('  %-24s %8s   %s'%('값','최대편차',' '.join('%7s'%w for w in MID)))
for mx,k,es in rows[:12]:
    print('  %-24s %7.0f%%   %s'%(k,100*mx,' '.join('%6.0f%%'%(100*e) for e in es)))
print()
print('가장 선형에 가까운 값 5개:')
for mx,k,es in rows[-5:]:
    print('  %-24s %7.0f%%'%(k,100*mx))
# avar 후보: 모든 값이 같은 t 왜곡을 겪는가
print()
print('avar 적합성 검사 — 각 굵기에서 "실효 t"를 값마다 역산해 흩어짐을 본다')
print('  %-10s %8s %8s %8s'%('wght','실효t 중앙','산포','명목t'))
for i,w in enumerate(MID):
    ts=[]
    for _,k,_ in rows:
        a,b=D['Thin'][k],D['Black'][k]
        if abs(b-a)<1e-9: continue
        ts.append((D[w][k]-a)/(b-a))
    ts=np.array(ts); ts=ts[(ts>-1)&(ts<2)]
    print('  %-10d %8.3f %8.3f %8.3f'%(G[w],np.median(ts),np.std(ts),(G[w]-100)/800))
