import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""토폴로지 기본값 + 컨텍스트 보정표를 studio-rules.json으로 낸다."""
import json, os, pickle, statistics as st, sys
from collections import defaultdict
STUDIO_JSON=os.path.join(os.path.dirname(os.path.abspath(__file__)),os.pardir,'studio-rules.json')
from tree import tree, CHO, JUNG, JONG, COMPOUND_MEDIALS, COMPOUND_TRAILINGS
from derive import derive, node_boxes, fam, tkind, CELL, leaves

def q(x): return round(st.median(x),3)
def iqr(x):
    s=sorted(x); n=len(s)
    return round(s[int(n*.75)]-s[int(n*.25)],3) if n>3 else None

per={}   # (topology, path) -> field -> [values]
ctx=defaultdict(lambda: defaultdict(list))
for k,lb in leaves.items():
    d=derive(k,lb,CELL)
    if d is None: continue
    li,vi,ti=k; f=fam(JUNG[vi]); top='%s-%s'%(f,tkind(ti))
    for path,v in d.items():
        e=per.setdefault((top,path),{'axis':v.get('axis')})
        for fld in ('gap','overlap','spaceWeight'):
            if fld in v: e.setdefault(fld,[]).append(v[fld])
        for s_,val in v['padding'].items(): e.setdefault('pad_'+s_,[]).append(val)
    # 컨텍스트 보정 표본
    if ti and 'Trailing' in d and 'spaceWeight' in d['Trailing']:
        ctx['Trailing.spaceWeight'][f+'|'+JONG[ti]].append(d['Trailing']['spaceWeight'])
        ctx['Root.gap'][f+'|'+JONG[ti]].append(d['Root']['gap'])
    for p in ('Medial','MedialExtension'):
        if p in d and 'spaceWeight' in d[p]:
            ctx[p+'.spaceWeight'][f+'|'+JUNG[vi]].append(d[p]['spaceWeight'])
    if 'Leading' in d and 'spaceWeight' in d['Leading']:
        ctx['Leading.spaceWeight'][f+'|'+CHO[li]].append(d['Leading']['spaceWeight'])
    for side in ('top','right','bottom','left'):
        if 'Leading' in d:
            ctx['Leading.padding.'+side][f+'|'+CHO[li]].append(d['Leading']['padding'][side])
        if ti and 'Trailing' in d:
            ctx['Trailing.padding.'+side][f+'|'+JONG[ti]].append(d['Trailing']['padding'][side])
        for p in ('Medial','MedialExtension'):
            if p in d:
                ctx[p+'.padding.'+side][f+'|'+JUNG[vi]].append(d[p]['padding'][side])

ORDER=['Root','LeadingMedial','LeadingMedialBase','Leading','Medial','MedialBase',
       'MedialExtension','Trailing','TrailingFirst','TrailingSecond']
tops=defaultdict(dict)
counts=defaultdict(int)
for (top,path),e in per.items():
    node={}
    if e.get('axis'): node['axis']=e['axis']
    if 'spaceWeight' in e:
        node['spaceWeight']=q(e['spaceWeight']); node['spaceWeightIqr']=iqr(e['spaceWeight'])
    if 'gap' in e: node['gap']=q(e['gap'])
    if 'overlap' in e: node['overlap']=q(e['overlap'])
    node['padding']={s_:q(e['pad_'+s_]) for s_ in ('top','right','bottom','left')}
    node['n']=len(e.get('pad_top',[]))
    tops[top][path]=node
    counts[top]=max(counts[top],node['n'])
out={
 'schema':'hangul-rules/studio-layout/1',
 'source':'Noto Sans CJK KR Regular (noto-cjk Sans2.004)',
 'frame':{'unitsPerEm':1000,'advanceWidth':1000,
          'cellEmBox':{'x0':CELL[0],'y0':CELL[1],'x1':CELL[2],'y1':CELL[3]},
          'note':'정규화 (0,0,1,1)이 이 em 박스에 대응한다. 전 음절 잉크 봉투에서 얻었다.'},
 'units':{'padding':'부모 사각형 대비 %','gap':'노드 inner main 대비 %',
          'overlap':'노드 inner main 대비 %','spaceWeight':'형제 합=1로 정규화'},
 'topologies':{},
 'contextTables':{},
}
for top in sorted(tops):
    ex={'VR-none':'가','VR-simple':'각','VR-compound':'갃','VL-none':'거','VL-simple':'걱',
        'VL-compound':'걳','H-none':'고','H-simple':'곡','H-compound':'곿',
        'M-none':'과','M-simple':'관','M-compound':'괆'}.get(top)
    out['topologies'][top]={'example':ex,'syllables':counts[top],
        'nodes':{p:tops[top][p] for p in ORDER if p in tops[top]}}
for name,tbl in ctx.items():
    out['contextTables'][name]={'keyedBy':'family|jamo',
        'entries':{k:{'value':q(v),'n':len(v)} for k,v in tbl.items() if len(v)>=6}}
json.dump(out,open(STUDIO_JSON,'w'),
          ensure_ascii=False,indent=1)
print('studio-rules.json 생성. 토폴로지 %d종'%len(out['topologies']))
print()
for name in out['contextTables']:
    e=out['contextTables'][name]['entries']
    print('%s : %d개 항목'%(name,len(e)))
t={k:v for k,v in out['contextTables']['Trailing.spaceWeight']['entries'].items() if k.startswith('VR|')}
print(' VR 종성별 Trailing spaceWeight:',
      '  '.join('%s %.3f'%(k.split('|')[1],v['value']) for k,v in sorted(t.items(),key=lambda kv:kv[1]['value'])))
