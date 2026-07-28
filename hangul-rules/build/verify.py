import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""hangul-resolver의 사각형 평가를 그대로 재구현해 역산값을 되돌려 본다."""
import json, os, statistics as st, sys
STUDIO_JSON=os.path.join(os.path.dirname(os.path.abspath(__file__)),os.pardir,'studio-rules.json')
from tree import tree, CHO, JUNG, JONG
from derive import derive, node_boxes, fam, tkind, CELL, leaves

def inset(rect, pad):
    x,y,w,h=rect
    l=w*pad['left']/100; r=w*pad['right']/100
    t=h*pad['top']/100;  b=h*pad['bottom']/100
    return (x+l, y+b, w-l-r, h-t-b)

def evaluate(nodes, root, values):
    """values: path -> {padding,gap,overlap,spaceWeight}. 반환: index -> (x,y,w,h) inner rect"""
    rects={}
    stack=[(root,(0.0,0.0,1.0,1.0))]
    while stack:
        i,alloc=stack.pop()
        path,kind=nodes[i]
        v=values[path]
        rect=inset(alloc, v['padding'])
        rects[i]=rect
        if kind[0]=='leaf': continue
        axis,(a,b)=kind[1],kind[2]
        x,y,w,h=rect
        main = w if axis=='Horizontal' else h
        sep = main*(v.get('gap',0.0)-v.get('overlap',0.0))/100
        avail = main - sep
        wa=values[nodes[a][0]]['spaceWeight']; wb=values[nodes[b][0]]['spaceWeight']
        tot=wa+wb
        ma=avail*wa/tot; mb=avail*wb/tot
        if axis=='Horizontal':
            stack.append((a,(x,y,ma,h)))
            stack.append((b,(x+ma+sep,y,mb,h)))
        else:
            stack.append((a,(x,y+h-ma,w,ma)))          # 첫 자식이 위
            stack.append((b,(x,y+h-ma-sep-mb,w,mb)))
    return rects

def to_em(rect):
    cx0,cy0,cx1,cy1=CELL; cw=cx1-cx0; ch=cy1-cy0
    x,y,w,h=rect
    return (cx0+x*cw, cy0+y*ch, cx0+(x+w)*cw, cy0+(y+h)*ch)

R=json.load(open(STUDIO_JSON))

bad=[]
def check(mode, limit=None):
    errs=[]; worst=(0,None)
    for n,(k,lb) in enumerate(leaves.items()):
        if limit and n>=limit: break
        d=derive(k,lb,CELL)
        if d is None: continue
        li,vi,ti=k; top='%s-%s'%(fam(JUNG[vi]),tkind(ti))
        nodes,root=tree(li,vi,ti)
        if mode=='exact':
            vals=d
        else:
            tn=R['topologies'][top]['nodes']; f=fam(JUNG[vi])
            vals={p:{'padding':tn[p]['padding'],'gap':tn[p].get('gap',0.0),
                     'overlap':tn[p].get('overlap',0.0),
                     'spaceWeight':tn[p].get('spaceWeight',1.0)} for p,_ in nodes}
            if mode=='median+ctx':
                def look(tbl,jamo):
                    e=R['contextTables'].get(tbl,{}).get('entries',{})
                    return e.get(f+'|'+jamo,{}).get('value')
                # 종성 정체성 -> Trailing 가중치와 Root gap
                if ti and 'Trailing' in vals:
                    w=look('Trailing.spaceWeight',JONG[ti])
                    if w is not None:
                        vals['Trailing']['spaceWeight']=w
                        vals['LeadingMedial']['spaceWeight']=1-w
                    g=look('Root.gap',JONG[ti])
                    if g is not None: vals['Root']['gap']=g
                # 중성 정체성 -> Medial 가중치
                for p,sib in (('Medial','Leading'),('MedialExtension','LeadingMedialBase')):
                    if p in vals:
                        w=look(p+'.spaceWeight',JUNG[vi])
                        if w is not None:
                            vals[p]['spaceWeight']=w; vals[sib]['spaceWeight']=1-w
                # 패딩도 같은 키로 보정한다
                for p,jamo in (('Leading',CHO[li]),('Trailing',JONG[ti] if ti else None),
                               ('Medial',JUNG[vi]),('MedialExtension',JUNG[vi])):
                    if p not in vals or jamo is None: continue
                    pad=dict(vals[p]['padding'])
                    for side in ('top','right','bottom','left'):
                        x=look(p+'.padding.'+side,jamo)
                        if x is not None: pad[side]=x
                    vals[p]['padding']=pad
                # 초성 정체성 -> Leading 가중치 (형제는 보존 비율로 재정규화)
                if 'Leading' in vals and f!='M':
                    w=look('Leading.spaceWeight',CHO[li])
                    if w is not None:
                        sib='Medial' if 'Medial' in vals else 'MedialBase'
                        if sib in vals:
                            vals['Leading']['spaceWeight']=w; vals[sib]['spaceWeight']=1-w
        try: rects=evaluate(nodes,root,vals)
        except Exception: continue
        box=node_boxes(nodes,root,lb)
        for i,(path,kind) in enumerate(nodes):
            if kind[0]!='leaf': continue
            got=to_em(rects[i]); want=box[i]
            e=max(abs(g-w_) for g,w_ in zip(got,want))
            errs.append(e)
            if e>worst[0]: worst=(e,(chr(0xAC00+(li*21+vi)*28+ti),path,tuple(round(x) for x in got),want))
            if mode=='exact' and e>1.0: bad.append((round(e),chr(0xAC00+(li*21+vi)*28+ti),path,top))
    return errs, worst

fid={}
for mode in ('exact','median','median+ctx'):
    errs,worst=check(mode)
    print('%-7s  리프 %d개  최대오차 %.2f  중앙값 %.3f  p95 %.1f em'%(
        mode,len(errs),max(errs),st.median(errs),sorted(errs)[int(len(errs)*.95)]))
    fid[mode]={'leaves':len(errs),'medianEm':round(st.median(errs),2),
               'p95Em':round(sorted(errs)[int(len(errs)*.95)],2),'maxEm':round(max(errs),2)}
    if mode.startswith('median'): print('   최악:',worst[1])
    if mode=='exact':
        print('   1em 초과 리프 %d개 (%.2f%%)'%(len(bad),100*len(bad)/len(errs)))
        from collections import Counter
        print('   토폴로지:',Counter(b[3] for b in bad).most_common())
        print('   path:',Counter(b[2] for b in bad).most_common())
        print('   예:',bad[:6])
        fid['exact']['over1EmLeaves']=len(bad)

P=STUDIO_JSON
R2=json.load(open(P))
R2['fidelity']={
 'metric':'리프 박스 최대 코너 편차, em 단위 (셀 %d×%d)'%(CELL[2]-CELL[0],CELL[3]-CELL[1]),
 'exact':fid['exact'],'topologyMedianOnly':fid['median'],'withContextTables':fid['median+ctx'],
 'note':('exact는 음절별 역산값을 그대로 되돌린 것으로 알고리즘 재현이 맞는지 확인하는 용도다. '
         '실제 규칙 적용 충실도는 withContextTables 쪽을 봐야 한다. Noto가 11,172자를 개별 '
         '최적화한 폰트이므로 완전 일치는 원리적으로 불가능하다.')}
json.dump(R2,open(P,'w'),ensure_ascii=False,indent=1)
print('fidelity 기록 완료')
