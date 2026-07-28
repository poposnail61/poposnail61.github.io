import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""중첩 4레이어 모델. 각 층이 오차를 얼마나 줄이는지 측정한다.

L1 Template   토폴로지 12종의 split 값 + 슬롯. 계열별 패딩 하나.
L2 Jamo       자모마다 자기 패딩 (초성 19×계열, 중성 21, 종성 27).
L3 Combination (중성,종성) 컬럼별 슬롯 delta. 앞 층 위에 가산.
L4 Glyph      음절별 잔차. 여기까지 가면 개별 보정이다.

L1이 CompositionTemplate, L2가 자모 기본값, L3이 combination CorrectionRule,
L4가 exact glyph rule에 대응한다.
"""
import contextlib, io as _io, json, statistics as st
from collections import defaultdict
from tree import tree, CHO, JUNG, JONG
with contextlib.redirect_stdout(_io.StringIO()):
    from derive import fam, tkind, CELL, leaves

CX0,CY0,CX1,CY1=CELL; CW=CX1-CX0; CH=CY1-CY0
def union(a,b): return (min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3]))
def to_em(r): x,y,w,h=r; return (CX0+x*CW,CY0+y*CH,CX0+(x+w)*CW,CY0+(y+h)*CH)

TOPO=lambda vi,ti: '%s-%s'%(fam(JUNG[vi]),tkind(ti))
usable=[]
for k,lb in leaves.items():
    nodes,root=tree(*k)
    if any(p not in lb for p,kind in nodes if kind[0]=='leaf'): continue
    usable.append((k,lb,nodes,root))
print('대상 %d자'%len(usable))

# ── L1: 토폴로지별 슬롯과 split 값 ─────────────────────────────────────────
slot=defaultdict(dict); mem=defaultdict(list)
for k,lb,nodes,root in usable:
    g=TOPO(k[1],k[2]); mem[g].append((k,lb,nodes,root))
    for p,kind in nodes:
        if kind[0]=='leaf':
            slot[g][p]=lb[p] if p not in slot[g] else union(slot[g][p],lb[p])
layout={}
for g,ms in mem.items():
    nodes,root=ms[0][2],ms[0][3]
    box=[None]*len(nodes)
    for i,(p,kind) in enumerate(nodes):
        box[i]=slot[g][p] if kind[0]=='leaf' else union(box[kind[2][0]],box[kind[2][1]])
    r=box[root]
    vals={nodes[root][0]:{'padding':{'left':100*(r[0]-CX0)/CW,'right':100*(CX1-r[2])/CW,
                                     'bottom':100*(r[1]-CY0)/CH,'top':100*(CY1-r[3])/CH}}}
    for i,(path,kind) in enumerate(nodes):
        if kind[0]=='leaf': continue
        axis,(a,b)=kind[1],kind[2]; R,A,B=box[i],box[a],box[b]
        if axis=='Vertical': mA,mB,sep,Mn=A[3]-A[1],B[3]-B[1],A[1]-B[3],R[3]-R[1]
        else:                mA,mB,sep,Mn=A[2]-A[0],B[2]-B[0],B[0]-A[2],R[2]-R[0]
        d=vals.setdefault(path,{}); d['axis']=axis
        d['gap']=100*sep/Mn if sep>0 else 0.0
        d['overlap']=100*(-sep)/Mn if sep<0 else 0.0
        for ch,m in ((a,mA),(b,mB)):
            vals.setdefault(nodes[ch][0],{})['spaceWeight']=m/(mA+mB)
        for ch in (a,b):
            C=box[ch]; pad={'left':0.0,'right':0.0,'top':0.0,'bottom':0.0}
            if axis=='Vertical':
                cr=R[2]-R[0]; pad['left']=100*(C[0]-R[0])/cr; pad['right']=100*(R[2]-C[2])/cr
            else:
                cr=R[3]-R[1]; pad['bottom']=100*(C[1]-R[1])/cr; pad['top']=100*(R[3]-C[3])/cr
            vals.setdefault(nodes[ch][0],{})['padding']=pad
    layout[g]=(nodes,root,vals)

def allocate(nodes,root,vals):
    alloc={}; stack=[(root,(0.0,0.0,1.0,1.0))]
    while stack:
        i,al=stack.pop(); path,kind=nodes[i]; v=vals[path]
        x,y,w,h=al; p=v['padding']
        l,r=w*p['left']/100,w*p['right']/100; t,b=h*p['top']/100,h*p['bottom']/100
        rect=(x+l,y+b,w-l-r,h-t-b); alloc[i]=rect
        if kind[0]=='leaf': continue
        axis,(a,bb)=kind[1],kind[2]; x,y,w,h=rect
        main=w if axis=='Horizontal' else h
        sep=main*(v.get('gap',0)-v.get('overlap',0))/100; av=main-sep
        wa=vals[nodes[a][0]]['spaceWeight']; wb=vals[nodes[bb][0]]['spaceWeight']
        ma,mb=av*wa/(wa+wb),av*wb/(wa+wb)
        if axis=='Horizontal': stack += [(a,(x,y,ma,h)),(bb,(x+ma+sep,y,mb,h))]
        else:                  stack += [(a,(x,y+h-ma,w,ma)),(bb,(x,y+h-ma-sep-mb,w,mb))]
    return alloc

# ── 슬롯 할당 -> 자모별 필요 패딩 표본 ────────────────────────────────────
def jamo_key(li,vi,ti,path):
    f=fam(JUNG[vi])
    if path=='Leading': return ('Leading',f,CHO[li])
    if 'Medial' in path: return (path,f,JUNG[vi])
    return (path,f,JONG[ti])
rows=[]
for g,ms in mem.items():
    nodes,root,vals=layout[g]; alloc=allocate(nodes,root,vals)
    for k,lb,_,_ in ms:
        for i,(path,kind) in enumerate(nodes):
            if kind[0]!='leaf': continue
            A=to_em(alloc[i]); I=lb[path]; w=A[2]-A[0]; h=A[3]-A[1]
            need={'left':100*(I[0]-A[0])/w,'right':100*(A[2]-I[2])/w,
                  'bottom':100*(I[1]-A[1])/h,'top':100*(A[3]-I[3])/h}
            rows.append({'syl':k,'path':path,'A':A,'I':I,'need':need,
                         'fam':fam(JUNG[k[1]]),'jk':jamo_key(*k,path),
                         'col':(k[1],k[2])})
SIDES=('top','right','bottom','left')
def fit(keyfn):
    acc=defaultdict(lambda: defaultdict(list))
    for r in rows:
        for s in SIDES: acc[keyfn(r)][s].append(r['need'][s])
    return {k:{s:st.median(v[s]) for s in SIDES} for k,v in acc.items()}, len(acc)
def err(pred):
    out=[]
    for r in rows:
        p=pred(r); A=r['A']; w=A[2]-A[0]; h=A[3]-A[1]
        got=(A[0]+w*p['left']/100, A[1]+h*p['bottom']/100,
             A[2]-w*p['right']/100, A[3]-h*p['top']/100)
        out.append(max(abs(a-b) for a,b in zip(got,r['I'])))
    return out
def stat(e): return round(st.median(e),1), round(sorted(e)[int(len(e)*.95)],1)

P1,n1=fit(lambda r:(r['path'],r['fam']))
P2,n2=fit(lambda r:r['jk'])
D3=defaultdict(lambda: defaultdict(list))
for r in rows:
    for s in SIDES: D3[(r['col'],r['path'])][s].append(r['need'][s]-P2[r['jk']][s])
D3={k:{s:st.median(v[s]) for s in SIDES} for k,v in D3.items()}
P4,n4=fit(lambda r:(r['syl'],r['path']))

nodes_params=sum(len(v[2])*9 for v in layout.values())
cases=[
 ('L1  Template only (토폴로지 12 + 계열별 패딩)', lambda r:P1[(r['path'],r['fam'])], nodes_params+n1*4),
 ('L2  + 자모별 패딩',                          lambda r:P2[r['jk']],              nodes_params+n2*4),
 ('L3  + (중성,종성) 컬럼 보정',
   lambda r:{s:P2[r['jk']][s]+D3[(r['col'],r['path'])][s] for s in SIDES},
   nodes_params+n2*4+len(D3)*4),
 ('L4  + 음절별 보정 (상한)',                    lambda r:P4[(r['syl'],r['path'])], nodes_params+n4*4),
]
print()
print('%-42s %9s %8s %8s'%('레이어','파라미터','중앙값','p95'))
prev=None
for name,pred,params in cases:
    m,p=stat(err(pred))
    gain='' if prev is None else '  (−%.0f%%)'%(100*(1-m/prev))
    print('%-42s %9d %8.1f %8.1f%s'%(name,params,m,p,gain)); prev=m
print()
print('셀 높이 %d 기준 상대오차: L1 %.1f%%  L2 %.1f%%  L3 %.1f%%  L4 %.1f%%'%(
    CH, *[100*stat(err(c[1]))[0]/CH for c in cases]))

# ── 산출 ──────────────────────────────────────────────────────────────────
import os
def rnd(d): return {s:round(d[s],3) for s in SIDES}
JAMO_LABEL={'Leading':'초성','Medial':'중성','MedialBase':'중성기저',
            'MedialExtension':'중성확장','Trailing':'종성',
            'TrailingFirst':'종성1','TrailingSecond':'종성2'}
out={
 'schema':'hangul-rules/studio-layered/1',
 'source':'Noto Sans CJK KR Regular (noto-cjk Sans2.004)',
 'frame':{'unitsPerEm':1000,'advanceWidth':1000,
          'cellEmBox':{'x0':CELL[0],'y0':CELL[1],'x1':CELL[2],'y1':CELL[3]}},
 'model':{'L1':'CompositionTemplate 12종. split 값과 슬롯.',
          'L2':'자모 기본 패딩. JamoVariant 단위.',
          'L3':'(중성,종성) 컬럼 보정. CorrectionRule level=combination, 패딩 가산 delta.',
          'L4':'음절별 보정. exact glyph rule. 필요할 때만.'},
 'L1_templates':{}, 'L2_jamoPadding':{}, 'L3_columnDelta':{},
}
for g,(nodes,root,vals) in sorted(layout.items()):
    ORDER=['Root','LeadingMedial','LeadingMedialBase','Leading','Medial','MedialBase',
           'MedialExtension','Trailing','TrailingFirst','TrailingSecond']
    nd={}
    for p in ORDER:
        if p not in vals: continue
        v=vals[p]; e={'padding':rnd(v['padding'])}
        for f in ('axis','gap','overlap','spaceWeight'):
            if f in v: e[f]=round(v[f],3) if isinstance(v[f],float) else v[f]
        nd[p]=e
    out['L1_templates'][g]={'nodes':nd,'syllables':len(mem[g])}
for (path,f,j),pad in sorted(P2.items()):
    out['L2_jamoPadding'].setdefault(path,{}).setdefault(f,{})[j]=rnd(pad)
cov=set()
for ((vi,ti),path),d in sorted(D3.items(), key=lambda kv:(kv[0][0],kv[0][1])):
    key='%s|%s'%(JUNG[vi], JONG[ti] or '-')
    out['L3_columnDelta'].setdefault(key,{})[path]=rnd(d)
    cov.add((vi,ti))
out['coverage']={'measuredSyllables':len(usable),'totalSyllables':11172,
                 'columnsCovered':len(cov),'columnsTotal':588,
                 'note':'리프 단위 분해가 된 음절만. 겹중성/겹종성을 쪼개야 하므로 전체보다 적다.'}
out['fidelity']={'metric':'리프 박스 최대 코너 편차 em (셀 %dx%d)'%(CW,CH),
    'layers':{c[0].split()[0]:{'params':c[2],'medianEm':stat(err(c[1]))[0],
                               'p95Em':stat(err(c[1]))[1],
                               'relPct':round(100*stat(err(c[1]))[0]/CH,2)} for c in cases}}
P=os.path.join(os.path.dirname(os.path.abspath(__file__)),os.pardir,'studio-rules-layered.json')
json.dump(out,open(P,'w'),ensure_ascii=False,indent=1)
print()
print('studio-rules-layered.json 생성')
print('  L1 템플릿 %d  L2 자모패딩 %d  L3 컬럼delta %d'%(
    len(out['L1_templates']),
    sum(len(v2) for v in out['L2_jamoPadding'].values() for v2 in v.values()),
    sum(len(v) for v in out['L3_columnDelta'].values())))
print('  컬럼 커버리지 %d/588, 음절 %d/11172'%(len(cov),len(usable)))

