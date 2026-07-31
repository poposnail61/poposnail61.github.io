import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""굵기(wght)에 따라 조합 규칙이 얼마나 변하는지 정리한다.

measure.py 를 7종 굵기에 돌린 rules-*.json 을 읽는다.
"""
import json, os
from collections import Counter
CHO='ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'; HORZ='ㅗㅛㅜㅠㅡ'
W=['Thin','Light','DemiLight','Regular','Medium','Bold','Black']
WGHT=dict(zip(W,[100,300,350,400,500,700,900]))
R={}
for w in W:
    p='/tmp/rules-%s.json'%w
    if os.path.exists(p): R[w]=json.load(open(p))
W=[w for w in W if w in R]
def row(label, fn):
    print('  %-26s'%label + ''.join('%8s'%fn(R[w]) for w in W))
print('굵기별 조합 규칙 (%s)'%' / '.join('%s %d'%(w,WGHT[w]) for w in W))
print('  %-26s'%'' + ''.join('%8d'%WGHT[w] for w in W))
row('분해율 %', lambda r:'%.0f'%(100*r['decomposed']/11172))
row('종성 ㄴ 높이', lambda r:r['jongLadder']['ㄴ']['h'])
row('종성 ㅎ 높이', lambda r:r['jongLadder']['ㅎ']['h'])
row('사다리 비 (최대/최소)', lambda r:'%.2f'%(max(v['h'] for v in r['jongLadder'].values())/
                                              min(v['h'] for v in r['jongLadder'].values())))
row('VR 초성 폭', lambda r:r['zones']['VR1']['a']['w'])
row('VR 초성 높이', lambda r:r['zones']['VR1']['a']['h'])
row('VR 중성 폭', lambda r:r['zones']['VR1']['b']['w'])
row('VR 종성 폭', lambda r:r['zones']['VR1']['c']['w'])
row('초성→종성 상관 r', lambda r:'%.3f'%r['choJong']['r'])
row('초성→종성 회귀계수', lambda r:'%.3f'%r['choJong']['coef'])
row('전부접촉 쌍 (>=20자)', lambda r:sum(1 for x in r['contactCho'].values() if x>=20))
row('무접촉 쌍 (<=2자)',   lambda r:sum(1 for x in r['contactCho'].values() if x<=2))
row('ㅜ 중성-종성 접촉 평균', lambda r:'%.1f'%(sum(r['contactJong'][c+'ㅜ'] for c in CHO)/19))
print()
print('종성 사다리 순위 안정성 (Thin 대비 일치 자수 / 27):')
o0=list(R[W[0]]['jongLadder'])
print('  '+'  '.join('%s %d'%(w,sum(1 for a,b in zip(o0,list(R[w]['jongLadder'])) if a==b)) for w in W))
print()
print('굵기에 따라 접촉이 뒤집히는 (초성,중성) 쌍 — Thin<=2 이고 Black>=20:')
flip=[c+v for v in HORZ for c in CHO
      if R['Thin']['contactCho'][c+v]<=2 and R['Black']['contactCho'][c+v]>=20]
print('  %d쌍: %s'%(len(flip),' '.join(flip)))
print()
print('반대로 Thin>=20 인데 Black<=2 인 쌍:')
flip2=[c+v for v in HORZ for c in CHO
       if R['Thin']['contactCho'][c+v]>=20 and R['Black']['contactCho'][c+v]<=2]
print('  %d쌍: %s'%(len(flip2),' '.join(flip2) or '없음'))
out={'weights':{w:WGHT[w] for w in W},
     'flipsThinToBlack':flip,
     'perWeight':{w:{'decomposedPct':round(100*R[w]['decomposed']/11172,1),
                     'jongLadder':{k:v['h'] for k,v in R[w]['jongLadder'].items()},
                     'zonesVR1':{s:R[w]['zones']['VR1'][s] for s in 'abc' if s in R[w]['zones']['VR1']},
                     'choJong':R[w]['choJong'],
                     'contactPairsAlways':sum(1 for x in R[w]['contactCho'].values() if x>=20),
                     'contactPairsNever':sum(1 for x in R[w]['contactCho'].values() if x<=2)}
                  for w in W}}
json.dump(out,open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),os.pardir,'weight-axis.json'),'w'),
          ensure_ascii=False,indent=1)
print('\nweight-axis.json 생성')
