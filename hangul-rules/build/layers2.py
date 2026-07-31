import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""부분 분해 데이터로 4레이어 규칙을 적합한다.

partial.pkl 은 음절마다 '측정 가능한 가장 깊은 노드'의 상자를 담는다. 붙어서 못 쪼갠
자리는 그룹 노드가 terminal 로 들어온다. 관측된 path 만 가지고 적합·평가한다.
"""
import contextlib, io as _io, json, os, pickle, statistics as st
import master as MA
from collections import defaultdict, Counter
from tree import tree, CHO, JUNG, JONG, COMPOUND_MEDIALS, COMPOUND_TRAILINGS
RIGHT,LEFT,HORZ,MIX='ㅏㅐㅑㅒㅣ','ㅓㅔㅕㅖ','ㅗㅛㅜㅠㅡ','ㅘㅙㅚㅝㅞㅟㅢ'
def fam(v): return 'VR' if v in RIGHT else 'VL' if v in LEFT else 'H' if v in HORZ else 'M'
def tkind(ti): return 'none' if ti==0 else ('compound' if ti in COMPOUND_TRAILINGS else 'simple')
HERE=_os.path.dirname(_os.path.abspath(__file__))
part=pickle.load(open(_os.path.join(HERE,MA.tmp('partial.pkl')),'rb'))
def union(a,b): return (min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3]))
SIDES=('top','right','bottom','left')
ORDER=['Root','LeadingMedial','LeadingMedialBase','Leading','Medial','MedialBase',
       'MedialExtension','Trailing','TrailingFirst','TrailingSecond']

# ── 기준 셀: 관측된 모든 상자의 봉투 ──────────────────────────────────────
env=None
for k,bx in part.items():
    for b in bx.values(): env=b if env is None else union(env,b)
CELL=MA.cell((round(env[0]),round(env[1]),round(env[2]),round(env[3])))
CX0,CY0,CX1,CY1=CELL; CW=CX1-CX0; CH=CY1-CY0
print('기준 셀 %s  %d x %d'%(CELL,CW,CH))

TOPO=lambda vi,ti: '%s-%s'%(fam(JUNG[vi]),tkind(ti))
mem=defaultdict(list); obs=defaultdict(lambda: defaultdict(list))
for k,bx in part.items():
    g=TOPO(k[1],k[2]); mem[g].append((k,bx))
    for p,b in bx.items(): obs[g][p].append(b)

# ── L1: 토폴로지별 노드 상자 (관측 합집합 + 트리 정합) ─────────────────────
def node_boxes(g):
    nodes,root=tree(*mem[g][0][0])
    U={p:None for p,_ in nodes}
    for p,bs in obs[g].items():
        if p not in U: continue
        for b in bs: U[p]=b if U[p] is None else union(U[p],b)
    box=[None]*len(nodes)
    for i,(p,kind) in enumerate(nodes):
        if kind[0]=='leaf': box[i]=U[p]
        else:
            a,b=kind[2]
            ch=None
            if box[a] is not None and box[b] is not None: ch=union(box[a],box[b])
            elif box[a] is not None: ch=box[a]
            elif box[b] is not None: ch=box[b]
            box[i]=ch if U[p] is None else (U[p] if ch is None else union(U[p],ch))
    return nodes,root,box

def split_vals(nodes,root,box):
    if box[root] is None: return None
    r=box[root]
    vals={nodes[root][0]:{'padding':{'left':100*(r[0]-CX0)/CW,'right':100*(CX1-r[2])/CW,
                                     'bottom':100*(r[1]-CY0)/CH,'top':100*(CY1-r[3])/CH}}}
    for i,(path,kind) in enumerate(nodes):
        if kind[0]=='leaf': continue
        axis,(a,b)=kind[1],kind[2]; R,A,B=box[i],box[a],box[b]
        if R is None or A is None or B is None: return None
        if axis=='Vertical': mA,mB,sep,Mn=A[3]-A[1],B[3]-B[1],A[1]-B[3],R[3]-R[1]
        else:                mA,mB,sep,Mn=A[2]-A[0],B[2]-B[0],B[0]-A[2],R[2]-R[0]
        if Mn<=0 or mA<=0 or mB<=0: return None
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
    return vals

layout={}
for g in mem:
    nodes,root,box=node_boxes(g); v=split_vals(nodes,root,box)
    if v: layout[g]=(nodes,root,v)
    else: print('  ! %s 레이아웃 실패'%g)
print('L1 템플릿 %d종'%len(layout))

def allocate(nodes,root,vals):
    alloc={}; stack=[(root,(0.0,0.0,1.0,1.0))]
    while stack:
        i,al=stack.pop(); path,kind=nodes[i]; v=vals[path]
        x,y,w,h=al; p=v['padding']
        l,r=w*p['left']/100,w*p['right']/100; t,b=h*p['top']/100,h*p['bottom']/100
        rect=(x+l,y+b,w-l-r,h-t-b); alloc[i]=rect
        if kind[0]=='leaf': continue
        axis,(a,bb2)=kind[1],kind[2]; x,y,w,h=rect
        main=w if axis=='Horizontal' else h
        sep=main*(v.get('gap',0)-v.get('overlap',0))/100; av=main-sep
        wa=vals[nodes[a][0]]['spaceWeight']; wb=vals[nodes[bb2][0]]['spaceWeight']
        ma,mb=av*wa/(wa+wb),av*wb/(wa+wb)
        if axis=='Horizontal': stack += [(a,(x,y,ma,h)),(bb2,(x+ma+sep,y,mb,h))]
        else:                  stack += [(a,(x,y+h-ma,w,ma)),(bb2,(x,y+h-ma-sep-mb,w,mb))]
    return alloc
def to_em(r): x,y,w,h=r; return (CX0+x*CW,CY0+y*CH,CX0+(x+w)*CW,CY0+(y+h)*CH)

def pad_key(li,vi,ti,path):
    """자모 패딩 키.

    초성은 중성까지, 중성은 초성까지 키에 넣는다. 전자는 전통 벌식의 문맥 변형체
    (초성 ㄱ 이 ㅏ 앞과 ㅗ 앞에서 다른 꼴)와 같은 개념이고, 후자는 중성이 초성과 상호 침투하는 계열(ㅓ계열의 가로획,
    가로모임·섞임모임의 기둥)에서 중성 상자가 초성에 따라 크게 달라지기 때문이다.
    실측에서 두 항이 p95 를 79 -> 36 em, Leading 잔차를 12.0 -> 8.1 em 으로 줄였다.
    명세 7.1 의 JamoVariant 문맥 태그에 그대로 대응한다.
    """
    f=fam(JUNG[vi])
    if path in ('LeadingMedial','LeadingMedialBase'): return (path,f,CHO[li],JUNG[vi])
    if path=='Leading': return (path,f,CHO[li],JUNG[vi])
    if 'Medial' in path: return (path,f,JUNG[vi],CHO[li])
    return (path,f,JONG[ti])

rows=[]
for g,ms in mem.items():
    if g not in layout: continue
    nodes,root,vals=layout[g]; alloc=allocate(nodes,root,vals)
    idx={p:i for i,(p,_) in enumerate(nodes)}
    for k,bx in ms:
        for p,I in bx.items():
            if p not in idx: continue
            A=to_em(alloc[idx[p]]); w=A[2]-A[0]; h=A[3]-A[1]
            if w<=0 or h<=0: continue
            rows.append({'syl':k,'path':p,'A':A,'I':I,'fam':fam(JUNG[k[1]]),
                         'pk':pad_key(*k,p),'col':(k[1],k[2])})
print('관측 상자 %d개'%len(rows))

def fit(keyfn):
    acc=defaultdict(lambda: defaultdict(list))
    for r in rows:
        A=r['A']; w=A[2]-A[0]; h=A[3]-A[1]; I=r['I']
        need={'left':100*(I[0]-A[0])/w,'right':100*(A[2]-I[2])/w,
              'bottom':100*(I[1]-A[1])/h,'top':100*(A[3]-I[3])/h}
        for s in SIDES: acc[keyfn(r)][s].append(need[s])
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
P2,n2=fit(lambda r:r['pk'])
D3=defaultdict(lambda: defaultdict(list))
for r in rows:
    A=r['A']; w=A[2]-A[0]; h=A[3]-A[1]; I=r['I']
    need={'left':100*(I[0]-A[0])/w,'right':100*(A[2]-I[2])/w,
          'bottom':100*(I[1]-A[1])/h,'top':100*(A[3]-I[3])/h}
    for s in SIDES: D3[(r['col'],r['path'])][s].append(need[s]-P2[r['pk']][s])
D3={k:{s:st.median(v[s]) for s in SIDES} for k,v in D3.items()}
P4,n4=fit(lambda r:(r['syl'],r['path']))
np_=sum(len(v[2])*9 for v in layout.values())
cases=[('L1',lambda r:P1[(r['path'],r['fam'])],np_+n1*4),
       ('L2',lambda r:P2[r['pk']],np_+n2*4),
       ('L3',lambda r:{s:P2[r['pk']][s]+D3[(r['col'],r['path'])][s] for s in SIDES},
        np_+n2*4+len(D3)*4),
       ('L4',lambda r:P4[(r['syl'],r['path'])],np_+n4*4)]
print()
print('%-4s %10s %9s %8s'%('레이어','파라미터','중앙값','p95'))
res={}
for nm,pred,pp in cases:
    m,p=stat(err(pred)); res[nm]={'params':pp,'medianEm':m,'p95Em':p,
                                  'relPct':round(100*m/CH,2)}
    print('%-4s %10d %9.1f %8.1f   (%.1f%% of cell)'%(nm,pp,m,p,100*m/CH))
pickle.dump((CELL,layout,P1,P2,D3,rows,res),open(_os.path.join(HERE,MA.tmp('layers2.pkl')),'wb'))
