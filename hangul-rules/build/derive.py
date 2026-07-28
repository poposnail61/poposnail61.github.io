import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""리프 잉크 박스 -> hangul-font-studio LayoutNodeValue (padding/gap/spaceWeight)."""
import json, pickle, statistics as st, sys
from collections import defaultdict
from tree import tree, CHO, JUNG, JONG, COMPOUND_MEDIALS, COMPOUND_TRAILINGS
RIGHT,LEFT,HORZ,MIX='ㅏㅐㅑㅒㅣ','ㅓㅔㅕㅖ','ㅗㅛㅜㅠㅡ','ㅘㅙㅚㅝㅞㅟㅢ'
def fam(v): return 'VR' if v in RIGHT else 'VL' if v in LEFT else 'H' if v in HORZ else 'M'
def tkind(ti): return 'none' if ti==0 else ('compound' if ti in COMPOUND_TRAILINGS else 'simple')
leaves,_=pickle.load(open('leaves.pkl','rb'))

def union(a,b): return (min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3]))

def node_boxes(nodes, root, lb):
    box=[None]*len(nodes)
    for i,(path,kind) in enumerate(nodes):
        if kind[0]=='leaf':
            if path not in lb: return None
            box[i]=lb[path]
        else:
            a,b=kind[2]
            if box[a] is None or box[b] is None: return None
            box[i]=union(box[a],box[b])
    return box

def derive(k, lb, cell):
    li,vi,ti=k
    nodes,root=tree(li,vi,ti)
    box=node_boxes(nodes,root,lb)
    if box is None: return None
    out={}
    cw=cell[2]-cell[0]; chh=cell[3]-cell[1]
    r=box[root]
    out[nodes[root][0]]={'padding':{'left':100*(r[0]-cell[0])/cw,'right':100*(cell[2]-r[2])/cw,
                                   'bottom':100*(r[1]-cell[1])/chh,'top':100*(cell[3]-r[3])/chh}}
    stack=[root]
    while stack:
        i=stack.pop(); path,kind=nodes[i]
        if kind[0]=='leaf': continue
        axis,(a,b)=kind[1],kind[2]
        R=box[i]; A=box[a]; B=box[b]
        if axis=='Vertical':
            mA,mB=A[3]-A[1],B[3]-B[1]; sep=A[1]-B[3]; Mn=R[3]-R[1]; cross=R[2]-R[0]
        else:
            mA,mB=A[2]-A[0],B[2]-B[0]; sep=B[0]-A[2]; Mn=R[2]-R[0]; cross=R[3]-R[1]
        if Mn<=0 or cross<=0 or mA<=0 or mB<=0: return None
        out[path]=dict(out.get(path,{}))
        out[path]['gap']=100*sep/Mn if sep>0 else 0.0
        out[path]['overlap']=100*(-sep)/Mn if sep<0 else 0.0
        out[path]['axis']=axis
        tot=mA+mB
        for child,m in ((a,mA),(b,mB)):
            cpath=nodes[child][0]; C=box[child]
            pad={'left':0.0,'right':0.0,'top':0.0,'bottom':0.0}
            if axis=='Vertical':
                pad['left']=100*(C[0]-R[0])/cross; pad['right']=100*(R[2]-C[2])/cross
            else:
                pad['bottom']=100*(C[1]-R[1])/cross; pad['top']=100*(R[3]-C[3])/cross
            d=out.setdefault(cpath,{}); d['padding']=pad; d['spaceWeight']=m/tot
            stack.append(child)
    return out

# 기준 프레임: 전 음절 루트 잉크 봉투
env=None
for k,lb in leaves.items():
    nodes,root=tree(*k); box=node_boxes(nodes,root,lb)
    if box: env = box[root] if env is None else union(env,box[root])
print('전 음절 잉크 봉투:', env)
CELL=(round(env[0]),round(env[1]),round(env[2]),round(env[3]))
print('기준 셀:', CELL, 'w=%d h=%d'%(CELL[2]-CELL[0],CELL[3]-CELL[1]))

acc=defaultdict(lambda: defaultdict(list)); nsyl=defaultdict(int)
rootw=defaultdict(lambda: defaultdict(list))
for k,lb in leaves.items():
    d=derive(k,lb,CELL)
    if d is None: continue
    key='%s-%s'%(fam(JUNG[k[1]]),tkind(k[2])); nsyl[key]+=1
    for path,v in d.items():
        for f in ('gap','overlap','spaceWeight'):
            if f in v: acc[(key,path)][f].append(v[f])
        for s,val in v['padding'].items(): acc[(key,path)]['pad.'+s].append(val)
        if 'axis' in v: acc[(key,path)]['axis']=v['axis']
    # 종성별 Root spaceWeight (사다리를 가중치로)
    if k[2] and 'Trailing' in d and 'spaceWeight' in d['Trailing']:
        rootw[JONG[k[2]]]['w'].append(d['Trailing']['spaceWeight'])
print()
print('토폴로지별 표본:', dict(sorted(nsyl.items())))
acc={k:dict(v) for k,v in acc.items()}
rootw={k:dict(v) for k,v in rootw.items()}
pickle.dump((CELL,acc,dict(nsyl),rootw),open('derived.pkl','wb'))

def med(x): return round(st.median(x),2)
print()
ORDER=['Root','LeadingMedial','LeadingMedialBase','Leading','Medial','MedialBase',
       'MedialExtension','Trailing','TrailingFirst','TrailingSecond']
for key in sorted(nsyl):
    print('=== %s  (n=%d) ==='%(key,nsyl[key]))
    paths=[p for p in ORDER if (key,p) in acc]
    for p in paths:
        a=acc[(key,p)]
        bits=[]
        if 'axis' in a: bits.append('axis=%s'%a['axis'][0])
        if 'spaceWeight' in a: bits.append('w=%.3f'%st.median(a['spaceWeight']))
        if 'gap' in a: bits.append('gap=%.2f'%st.median(a['gap']))
        if 'overlap' in a and st.median(a['overlap'])>0: bits.append('ovl=%.2f'%st.median(a['overlap']))
        pad=tuple(med(a['pad.'+s]) for s in ('top','right','bottom','left'))
        bits.append('pad(t/r/b/l)=%5.2f %5.2f %5.2f %5.2f'%pad)
        print('   %-18s %s'%(p,'  '.join(bits)))

