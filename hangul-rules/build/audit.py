import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""분해 라벨의 구조적 모순을 감사한다.

받침이 있는 글자에서 종성이 아닌 노드의 박스가 종성 위쪽 경계보다 한참 아래로
내려가면, 그 박스는 종성 일부를 삼켰거나 라벨이 잘못된 것이다.
"""
import pickle
import numpy as np
from collections import Counter, defaultdict
from tree import tree, CHO, JUNG, JONG, COMPOUND_TRAILINGS
HERE=_os.path.dirname(_os.path.abspath(__file__))
part=pickle.load(open(_os.path.join(HERE,'partial.pkl'),'rb'))
TRAIL={'Trailing','TrailingFirst','TrailingSecond'}
TOL=50
bad=defaultdict(list); ok=0; noT=0
for k,bx in part.items():
    li,vi,ti=k
    tb=[b for p,b in bx.items() if p in TRAIL]
    ub=[(p,b) for p,b in bx.items() if p not in TRAIL]
    if ti==0:
        if tb: bad['받침 없는데 종성 박스 있음'].append((k,'')); continue
        ok+=1; continue
    if not tb: noT+=1; continue
    def inter(a,b):
        w=min(a[2],b[2])-max(a[0],b[0]); h=min(a[3],b[3])-max(a[1],b[1])
        return max(0,w)*max(0,h)
    hit=None
    for p,b in ub:
        area=(b[2]-b[0])*(b[3]-b[1])
        ov=max(inter(b,t) for t in tb)
        # 상위 노드가 종성 상자와 실제로 겹치면 삼킨 것이다
        if area>0 and ov/area > 0.10: hit=p; break
    if hit: bad['상위 노드가 종성 상자와 겹침'].append((k,hit))
    else: ok+=1
print('분해 %d자 중'%len(part))
print('  구조적으로 온전:        %5d'%ok)
print('  종성 박스가 아예 없음:   %5d  (받침 있는 글자)'%noT)
for kind,v in bad.items(): print('  %-22s %5d'%(kind,len(v)))
print()
c=Counter()
for k,p in bad['상위 노드가 종성 상자와 겹침']:
    c[p]+=1
print('침범한 노드:', dict(c.most_common()))
c2=Counter(JONG[k[2]] for k,_ in bad['상위 노드가 종성 상자와 겹침'])
print('종성별:', dict(c2.most_common(12)))
c3=Counter('겹받침' if k[2] in COMPOUND_TRAILINGS else '홑받침' for k,_ in bad['상위 노드가 종성 상자와 겹침'])
print('받침 종류:', dict(c3))
# 종성 없는 케이스
c4=Counter(JONG[k[2]] for k in part if k[2] and not [p for p in part[k] if p in TRAIL])
print()
print('종성 박스를 못 얻은 글자의 종성별:', dict(c4.most_common(10)))
print('예:', ''.join(chr(0xAC00+(k[0]*21+k[1])*28+k[2]) for k in list(part)[:0]) or
      ''.join(chr(0xAC00+(k[0]*21+k[1])*28+k[2]) for k in part if k[2] and not [p for p in part[k] if p in TRAIL])[:30])
