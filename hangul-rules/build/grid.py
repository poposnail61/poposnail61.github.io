import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""레이아웃 키 × 패딩 키 조합별 재현 오차를 실측 비교한다.

모델: 레이아웃 키가 같은 음절은 split 값(gap/overlap/spaceWeight)과 슬롯을 공유한다.
슬롯은 그 키에서 관측된 잉크 전부를 담는 bbox로 잡아 패딩이 항상 >= 0이 되게 한다.
각 자모는 패딩 키 단위로 하나의 패딩을 갖고 슬롯 안으로 파고들어 자기 크기를 만든다.
"""
import contextlib, io as _io, statistics as st
from collections import defaultdict
from tree import tree, CHO, JUNG, JONG
with contextlib.redirect_stdout(_io.StringIO()):
    from derive import fam, tkind, CELL, leaves

CX0,CY0,CX1,CY1=CELL; CW=CX1-CX0; CH=CY1-CY0
def union(a,b): return (min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3]))

def build(layout_key, pad_key):
    # 1) 레이아웃 키별 공유 리프 박스
    grp=defaultdict(dict); members=defaultdict(list)
    for k,lb in leaves.items():
        nodes,root=tree(*k)
        if any(p not in lb for p,kind in nodes if kind[0]=='leaf'): continue
        g=layout_key(*k); sig=tuple(p for p,_ in nodes)
        if g in members and members[g][0][4]!=sig: continue
        members[g].append((k,lb,nodes,root,sig))
        for p,kind in nodes:
            if kind[0]!='leaf': continue
            grp[g][p]=lb[p] if p not in grp[g] else union(grp[g][p],lb[p])
    # 2) 키별 노드 박스와 split 값
    layout={}
    for g,ms in members.items():
        nodes,root=ms[0][2],ms[0][3]
        box=[None]*len(nodes)
        for i,(p,kind) in enumerate(nodes):
            box[i]=grp[g][p] if kind[0]=='leaf' else union(box[kind[2][0]],box[kind[2][1]])
        vals={nodes[root][0]:{'padding':{
            'left':100*(box[root][0]-CX0)/CW,'right':100*(CX1-box[root][2])/CW,
            'bottom':100*(box[root][1]-CY0)/CH,'top':100*(CY1-box[root][3])/CH}}}
        bad=False
        for i,(path,kind) in enumerate(nodes):
            if kind[0]!='leaf':
                axis,(a,b)=kind[1],kind[2]; R,A,B=box[i],box[a],box[b]
                if axis=='Vertical': mA,mB,sep,Mn=A[3]-A[1],B[3]-B[1],A[1]-B[3],R[3]-R[1]
                else:                mA,mB,sep,Mn=A[2]-A[0],B[2]-B[0],B[0]-A[2],R[2]-R[0]
                if Mn<=0 or mA<=0 or mB<=0: bad=True; break
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
        if bad: continue
        layout[g]=(nodes,root,vals)
    # 3) 슬롯 할당 계산 -> 자모 패딩 표본
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
            if axis=='Horizontal':
                stack += [(a,(x,y,ma,h)),(bb,(x+ma+sep,y,mb,h))]
            else:
                stack += [(a,(x,y+h-ma,w,ma)),(bb,(x,y+h-ma-sep-mb,w,mb))]
        return alloc
    def to_em(r): x,y,w,h=r; return (CX0+x*CW,CY0+y*CH,CX0+(x+w)*CW,CY0+(y+h)*CH)

    samples=defaultdict(list); recs=[]
    for g,ms in members.items():
        if g not in layout: continue
        nodes,root,vals=layout[g]
        alloc=allocate(nodes,root,vals)
        for k,lb,_,_,_ in ms:
            for i,(path,kind) in enumerate(nodes):
                if kind[0]!='leaf': continue
                A=to_em(alloc[i]); I=lb[path]; w=A[2]-A[0]; h=A[3]-A[1]
                if w<=0 or h<=0: continue
                pk=pad_key(k[0],k[1],k[2],path)
                pd={'left':100*(I[0]-A[0])/w,'right':100*(A[2]-I[2])/w,
                    'bottom':100*(I[1]-A[1])/h,'top':100*(A[3]-I[3])/h}
                samples[pk].append(pd); recs.append((pk,A,I))
    pads={pk:{s:st.median([d[s] for d in v]) for s in ('top','right','bottom','left')}
          for pk,v in samples.items()}
    errs=[]
    for pk,A,I in recs:
        p=pads[pk]; w=A[2]-A[0]; h=A[3]-A[1]
        got=(A[0]+w*p['left']/100, A[1]+h*p['bottom']/100,
             A[2]-w*p['right']/100, A[3]-h*p['top']/100)
        errs.append(max(abs(a-b) for a,b in zip(got,I)))
    return {'layouts':len(layout),'pads':len(pads),'leaves':len(recs),
            'median':round(st.median(errs),1),'p95':round(sorted(errs)[int(len(errs)*.95)],1),
            'params':len(layout)*9+len(pads)*4}

TOPO=lambda li,vi,ti: '%s-%s'%(fam(JUNG[vi]),tkind(ti))
CASES=[
 ('토폴로지 12 / 초성패딩 계열별',
  TOPO, lambda li,vi,ti,p: (p,fam(JUNG[vi]))),
 ('토폴로지 12 / 패딩 자모+계열별',
  TOPO, lambda li,vi,ti,p: (p,fam(JUNG[vi]),CHO[li] if p=='Leading' else JUNG[vi] if 'Medial' in p else JONG[ti])),
 ('중성×받침종류 / 패딩 자모+계열별',
  lambda li,vi,ti: (JUNG[vi], tkind(ti)),
  lambda li,vi,ti,p: (p,fam(JUNG[vi]),CHO[li] if p=='Leading' else JUNG[vi] if 'Medial' in p else JONG[ti])),
 ('계열×종성 / 패딩 자모+계열별',
  lambda li,vi,ti: (fam(JUNG[vi]), JONG[ti]),
  lambda li,vi,ti,p: (p,fam(JUNG[vi]),CHO[li] if p=='Leading' else JUNG[vi] if 'Medial' in p else JONG[ti])),
 ('중성×종성 588 / 초성패딩 계열별  ← 제안하신 구조',
  lambda li,vi,ti: (vi,ti), lambda li,vi,ti,p: (p,fam(JUNG[vi]))),
 ('중성×종성 588 / 패딩 자모+계열별',
  lambda li,vi,ti: (vi,ti),
  lambda li,vi,ti,p: (p,fam(JUNG[vi]),CHO[li] if p=='Leading' else JUNG[vi] if 'Medial' in p else JONG[ti])),
 ('중성×종성 588 / 패딩 자모+컬럼별 (상한)',
  lambda li,vi,ti: (vi,ti),
  lambda li,vi,ti,p: (p,vi,ti,CHO[li] if p=='Leading' else '')),
]
print('%-44s %7s %6s %8s %8s %8s'%('구조','레이아웃','패딩','파라미터','중앙값','p95'))
for name,lk,pk in CASES:
    r=build(lk,pk)
    print('%-44s %7d %6d %8d %8.1f %8.1f'%(name,r['layouts'],r['pads'],r['params'],r['median'],r['p95']))
