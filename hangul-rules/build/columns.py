import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""(중성,종성) 컬럼이 레이아웃을 공유하고 초성은 자기 패딩만 갖는 모델로 재적합.

컬럼의 슬롯은 그 컬럼에서 관측된 자모 전부를 담는 bbox로 잡는다. 패딩이 음수를
못 쓰므로 슬롯 ⊇ 잉크여야 하고, 각 자모는 안으로 패딩을 먹어 자기 크기를 만든다.
"""
import json, os, pickle, statistics as st, sys
from collections import defaultdict
from tree import tree, CHO, JUNG, JONG
from derive import node_boxes, fam, tkind, CELL, leaves

def union(a,b): return (min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3]))
def inset_pct(alloc, ink):
    """alloc -> ink 로 만드는 패딩 %. alloc ⊇ ink 이면 전부 >= 0."""
    x0,y0,x1,y1=alloc; w=x1-x0; h=y1-y0
    return {'left':100*(ink[0]-x0)/w, 'right':100*(x1-ink[2])/w,
            'bottom':100*(ink[1]-y0)/h, 'top':100*(y1-ink[3])/h}

# ── 1. 컬럼별 공유 슬롯 ────────────────────────────────────────────────────
col_syl=defaultdict(list)
for k,lb in leaves.items(): col_syl[(k[1],k[2])].append((k[0],lb))

columns={}
for (vi,ti),members in col_syl.items():
    nodes,root=tree(0,vi,ti)
    paths=[p for p,_ in nodes]
    shared={}
    ok=True
    for li,lb in members:
        for p,kind in nodes:
            if kind[0]!='leaf': continue
            if p not in lb: ok=False; break
            shared[p]=lb[p] if p not in shared else union(shared[p],lb[p])
        if not ok: break
    if not ok or len(members)<2: continue
    # 그룹 박스는 자식들의 합집합으로 다시 세워 트리 정합성을 유지한다
    box=[None]*len(nodes)
    for i,(p,kind) in enumerate(nodes):
        box[i]=shared[p] if kind[0]=='leaf' else union(box[kind[2][0]],box[kind[2][1]])
    columns[(vi,ti)]={'nodes':nodes,'root':root,'box':box,'members':members}
print('컬럼 %d개 (관측 초성 2자 이상)'%len(columns))
cnt=[len(c['members']) for c in columns.values()]
print('  컬럼당 초성 수: 중앙값 %d, 최소 %d, 최대 %d, 19자 완비 %d개'%(
    st.median(cnt),min(cnt),max(cnt),sum(1 for c in cnt if c==19)))

# ── 2. 컬럼 레이아웃 역산 (split 값) ───────────────────────────────────────
def column_layout(c):
    nodes,root,box=c['nodes'],c['root'],c['box']
    cx0,cy0,cx1,cy1=CELL; cw=cx1-cx0; ch=cy1-cy0
    vals={}
    r=box[root]
    vals[nodes[root][0]]={'padding':{'left':100*(r[0]-cx0)/cw,'right':100*(cx1-r[2])/cw,
                                     'bottom':100*(r[1]-cy0)/ch,'top':100*(cy1-r[3])/ch}}
    stack=[root]
    while stack:
        i=stack.pop(); path,kind=nodes[i]
        if kind[0]=='leaf': continue
        axis,(a,b)=kind[1],kind[2]
        R,A,B=box[i],box[a],box[b]
        if axis=='Vertical':
            mA,mB,sep,Mn = A[3]-A[1], B[3]-B[1], A[1]-B[3], R[3]-R[1]
        else:
            mA,mB,sep,Mn = A[2]-A[0], B[2]-B[0], B[0]-A[2], R[2]-R[0]
        if Mn<=0 or mA<=0 or mB<=0: return None
        d=vals.setdefault(path,{}); d['axis']=axis
        d['gap']=100*sep/Mn if sep>0 else 0.0
        d['overlap']=100*(-sep)/Mn if sep<0 else 0.0
        tot=mA+mB
        for child,m in ((a,mA),(b,mB)):
            e=vals.setdefault(nodes[child][0],{}); e['spaceWeight']=m/tot
        stack += [a,b]
    # 그룹 노드의 패딩은 부모 split이 정한다 (main 0, cross는 shared 박스 기준)
    stack=[root]
    while stack:
        i=stack.pop(); path,kind=nodes[i]
        if kind[0]=='leaf': continue
        axis,(a,b)=kind[1],kind[2]; R=box[i]
        for child in (a,b):
            C=box[child]; pad={'left':0.0,'right':0.0,'top':0.0,'bottom':0.0}
            if axis=='Vertical':
                cross=R[2]-R[0]
                pad['left']=100*(C[0]-R[0])/cross; pad['right']=100*(R[2]-C[2])/cross
            else:
                cross=R[3]-R[1]
                pad['bottom']=100*(C[1]-R[1])/cross; pad['top']=100*(R[3]-C[3])/cross
            vals.setdefault(nodes[child][0],{})['padding']=pad
            stack.append(child)
    return vals

layouts={}
for key,c in columns.items():
    v=column_layout(c)
    if v: layouts[key]=v
print('레이아웃 확보 %d컬럼'%len(layouts))
pickle.dump((columns,layouts),open(os.path.join(_os.path.dirname(_os.path.abspath(__file__)),'columns.pkl'),'wb'))
