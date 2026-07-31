import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""상자가 그 노드가 차지할 수 없을 만큼 커졌는지로 분해 오류를 잡는다.

같은 (노드, 토폴로지)의 중앙값 대비 지나치게 큰 상자는 다른 자모의 획을 삼킨 것이다.
bbox 겹침으로는 못 잡는다 — 종성 상자가 가로로 넓어 중성 기둥이 옆을 지나가도 겹치기 때문.
"""
import pickle
import numpy as np
from collections import Counter, defaultdict
from tree import CHO, JUNG, JONG, COMPOUND_TRAILINGS
RIGHT,LEFT,HORZ='ㅏㅐㅑㅒㅣ','ㅓㅔㅕㅖ','ㅗㅛㅜㅠㅡ'
def fam(v): return 'VR' if v in RIGHT else 'VL' if v in LEFT else 'H' if v in HORZ else 'M'
def tk(t): return 'none' if t==0 else ('compound' if t in COMPOUND_TRAILINGS else 'simple')
HERE=_os.path.dirname(_os.path.abspath(__file__))
part=pickle.load(open(_os.path.join(HERE,'partial.pkl'),'rb'))
def gkey(k,p):
    """상자 크기를 비교할 때는 그 노드가 담는 자모 정체성까지 키에 넣어야 한다.
    ㅝ의 확장부(ㅓ, 가로획 있음)와 ㅚ의 확장부(ㅣ)를 같이 묶으면 오탐이 난다."""
    li,vi,ti=k; g=(fam(JUNG[vi]),tk(ti))
    if p=='Leading': return (p,g,CHO[li])
    if 'Medial' in p and p!='LeadingMedial' and p!='LeadingMedialBase': return (p,g,JUNG[vi])
    if p in ('Trailing','TrailingFirst','TrailingSecond'): return (p,g,JONG[ti])
    return (p,g,CHO[li],JUNG[vi])
dims=defaultdict(list)
for k,bx in part.items():
    for p,b in bx.items(): dims[gkey(k,p)].append((b[2]-b[0],b[3]-b[1]))
med={key:(float(np.median([d[0] for d in v])),float(np.median([d[1] for d in v])))
     for key,v in dims.items() if len(v)>=12}
FACTOR=1.5
flag=[]; per=Counter()
for k,bx in part.items():
    for p,b in bx.items():
        key=gkey(k,p)
        if key not in med: continue
        w,h=b[2]-b[0],b[3]-b[1]; mw,mh=med[key]
        r=max(w/mw if mw>0 else 0, h/mh if mh>0 else 0)
        if r>FACTOR: flag.append((r,k,p,round(w),round(h),round(mw),round(mh))); per[p]+=1
flag.sort(reverse=True)
tot=sum(len(v) for v in part.values())
print('상자 %d개 중 과대 상자 %d개 (%.1f%%)  — 같은 (노드,토폴로지) 중앙값의 %.1f배 초과'%(
    tot,len(flag),100*len(flag)/tot,FACTOR))
print('노드별:',dict(per.most_common()))
syl=len({f[1] for f in flag})
print('해당 음절 %d자 (%.1f%%)'%(syl,100*syl/len(part)))
print()
print('가장 심한 15개:')
print('  %-4s %-18s %6s %6s   %s'%('글자','노드','폭','높이','기대(폭x높이)'))
for r,k,p,w,h,mw,mh in flag[:15]:
    ch=chr(0xAC00+(k[0]*21+k[1])*28+k[2])
    print('  %-4s %-18s %6d %6d   %d x %d  (%.1f배)'%(ch,p,w,h,mw,mh,r))
print()
c=Counter((fam(JUNG[k[1]]),tk(k[2])) for _,k,_,_,_,_,_ in flag)
print('토폴로지별:',dict(c.most_common()))
pickle.dump({f[1] for f in flag},open(_os.path.join(HERE,'flagged.pkl'),'wb'))
