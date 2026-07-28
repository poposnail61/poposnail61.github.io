import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""최종 4레이어 규칙을 studio-rules-layered.json 으로 낸다."""
import json, os, pickle, statistics as st
from collections import defaultdict, Counter
from tree import tree, CHO, JUNG, JONG, COMPOUND_MEDIALS, COMPOUND_TRAILINGS
HERE=_os.path.dirname(_os.path.abspath(__file__))
CELL,layout,P1,P2,D3,rows,res=pickle.load(open(_os.path.join(HERE,'layers2.pkl'),'rb'))
part=pickle.load(open(_os.path.join(HERE,'partial.pkl'),'rb'))
CX0,CY0,CX1,CY1=CELL; CW=CX1-CX0; CH=CY1-CY0
SIDES=('top','right','bottom','left')
ORDER=['Root','LeadingMedial','LeadingMedialBase','Leading','Medial','MedialBase',
       'MedialExtension','Trailing','TrailingFirst','TrailingSecond']
def rnd(d): return {s:round(d[s],3) for s in SIDES}

def e_of(r,pred):
    p=pred(r); A=r['A']; w=A[2]-A[0]; h=A[3]-A[1]
    got=(A[0]+w*p['left']/100,A[1]+h*p['bottom']/100,A[2]-w*p['right']/100,A[3]-h*p['top']/100)
    return max(abs(a-b) for a,b in zip(got,r['I']))
PRED3=lambda r:{s:P2[r['pk']][s]+D3[(r['col'],r['path'])][s] for s in SIDES}
PRED2=lambda r:P2[r['pk']]
bypath=defaultdict(list); bypath2=defaultdict(list)
for r in rows:
    bypath[r['path']].append(e_of(r,PRED3)); bypath2[r['path']].append(e_of(r,PRED2))
print('노드별 잔차 (L3 / L2), em:')
print('  %-18s %6s %8s %8s %8s'%('node','관측','L3중앙','L3p95','L2중앙'))
for p in ORDER:
    if p not in bypath: continue
    e3,e2=bypath[p],bypath2[p]
    print('  %-18s %6d %8.1f %8.1f %8.1f'%(p,len(e3),st.median(e3),
        sorted(e3)[int(len(e3)*.95)],st.median(e2)))

# 미측정 음절 분류
miss=[]
for li in range(19):
    for vi in range(21):
        for ti in range(28):
            if (li,vi,ti) not in part: miss.append((li,vi,ti))
print()
print('아무 상자도 못 얻은 음절 %d자'%len(miss))
print('  중성별:',dict(Counter(JUNG[v] for _,v,_ in miss).most_common()))
print('  초성별:',dict(Counter(CHO[l] for l,_,_ in miss).most_common(6)))
print('  예:',''.join(chr(0xAC00+(l*21+v)*28+t) for l,v,t in miss[:24]))

out={'schema':'hangul-rules/studio-layered/2',
 'source':'Noto Sans CJK KR Regular (noto-cjk Sans2.004)',
 'frame':{'unitsPerEm':1000,'advanceWidth':1000,
          'cellEmBox':{'x0':CELL[0],'y0':CELL[1],'x1':CELL[2],'y1':CELL[3]}},
 'model':{'L1':'CompositionTemplate 12종. split 값과 슬롯.',
          'L2':'자모 기본 패딩. JamoVariant 기본값.',
          'L3':'(중성,종성) 컬럼 보정. CorrectionRule level=combination, 패딩 가산 delta.',
          'L4':'음절별 보정. exact glyph rule. 필요할 때만.',
          'terminalGroups':('획이 붙어 리프까지 못 쪼갠 자리는 그룹 노드가 terminal 로 '
                            '관측된다. LeadingMedial·LeadingMedialBase 항목이 그것이다.')},
 'L1_templates':{}, 'L2_padding':{}, 'L3_columnDelta':{}}
for g,(nodes,root,vals) in sorted(layout.items()):
    nd={}
    for p in ORDER:
        if p not in vals: continue
        v=vals[p]; e={'padding':rnd(v['padding'])}
        for fl in ('axis','gap','overlap','spaceWeight'):
            if fl in v: e[fl]=round(v[fl],3) if isinstance(v[fl],float) else v[fl]
        nd[p]=e
    out['L1_templates'][g]={'nodes':nd}
for key,pad in sorted(P2.items(), key=lambda kv:str(kv[0])):
    path,f=key[0],key[1]; rest='|'.join(key[2:])
    out['L2_padding'].setdefault(path,{}).setdefault(f,{})[rest]=rnd(pad)
cov=set()
for ((vi,ti),path),d in sorted(D3.items(), key=lambda kv:(kv[0][0][0],kv[0][0][1],kv[0][1])):
    out['L3_columnDelta'].setdefault('%s|%s'%(JUNG[vi],JONG[ti] or '-'),{})[path]=rnd(d)
    cov.add((vi,ti))
pc=Counter(r['path'] for r in rows)
out['coverage']={'syllablesWithAnyBox':len(part),'totalSyllables':11172,
  'boxes':len(rows),'columnsCovered':len(cov),'columnsTotal':588,
  'perNode':{p:pc[p] for p in ORDER if p in pc},
  'unmeasured':len(miss)}
out['fidelity']={'metric':'관측 노드 상자의 최대 코너 편차 em (셀 %dx%d)'%(CW,CH),
  'layers':res,
  'perNodeL3':{p:{'n':len(bypath[p]),'medianEm':round(st.median(bypath[p]),1)}
               for p in ORDER if p in bypath}}
P=_os.path.join(HERE,os.pardir,'studio-rules-layered.json')
json.dump(out,open(P,'w'),ensure_ascii=False,indent=1)
print()
print('studio-rules-layered.json  L1 %d  L2 %d  L3 %d컬럼'%(
    len(out['L1_templates']),
    sum(len(v2) for v in out['L2_padding'].values() for v2 in v.values()),
    len(out['L3_columnDelta'])))
print('커버리지 %d/11172자 (%.1f%%), 상자 %d개, 컬럼 %d/588'%(
    len(part),100*len(part)/11172,len(rows),len(cov)))
