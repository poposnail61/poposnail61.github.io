import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""2패스 분해. 1패스로 종성 고유 높이 표를 만들고, 2패스에서 그 표로 절단선을 고른다.

기존 '최대 ymax 간격' 규칙은 종성이 여러 도형일 때(ㅀ = ㄹ + ㅎ윗획 + ㅎ원) 종성 내부의
간격이 중성-종성 간격보다 커지면 잘못 자른다. 믏에서 ㄹ과 ㅎ윗획이 중성으로 갔다.
"""
import pickle, sys
import numpy as np
from collections import defaultdict
import measure as M
from fontTools.ttLib import TTFont
from tree import CHO, JUNG, JONG, COMPOUND_TRAILINGS
import leaves as L

def cut_candidates(shapes):
    ys=sorted({s[4] for s in shapes})
    return [(ys[i]+ys[i+1])/2 for i in range(len(ys)-1)]

def split_by_cut(inv, cut):
    return [s for s in inv if s[4]>cut],[s for s in inv if s[4]<=cut]

def decompose2(D, tol, usable, jong_h):
    """jong_h: 종성 index -> 기대 높이. None이면 1패스(최대 간격)."""
    out={}
    for vi in range(21):
        for ti in range(28):
            pool=[l for l in range(19) if usable.get((l,vi,ti),True)]
            thr=max(3,int(len(pool)*0.68))
            for li in range(19):
                inv=[];cho=[]
                for s in D[(li,vi,ti)]:
                    hits=sum(1 for l in pool if any(L.M.bbox and M_sim(s,q,tol) for q in D[(l,vi,ti)]))
                    (inv if hits>=thr else cho).append(s)
                if ti==0: out[(li,vi,ti)]=(cho,inv,[]); continue
                cands=cut_candidates(inv)
                if not cands: out[(li,vi,ti)]=(cho,inv,[]); continue
                if jong_h is None or ti not in jong_h:
                    ys=sorted({s[4] for s in inv})
                    cut=max(((ys[i+1]-ys[i],(ys[i]+ys[i+1])/2) for i in range(len(ys)-1)))[1]
                else:
                    want=jong_h[ti]
                    best=None
                    for c in cands:
                        up,low=split_by_cut(inv,c)
                        if not up or not low: continue
                        h=max(s[4] for s in low)-min(s[2] for s in low)
                        d=abs(h-want)
                        if best is None or d<best[0]: best=(d,c)
                    cut=best[1] if best else cands[0]
                up,low=split_by_cut(inv,cut)
                out[(li,vi,ti)]=(cho,up,low)
    return out
def M_sim(a,b,tol):
    return (a[0]==b[0] and a[5]==b[5] and
            max(abs(a[1]-b[1]),abs(a[2]-b[2]),abs(a[3]-b[3]),abs(a[4]-b[4]))<=tol)

def validated2(D,tol,jong_h):
    usable={}
    for _ in range(3):
        got=decompose2(D,tol,usable,jong_h)
        nxt={k: bool(c) and bool(m) and (k[2]==0 or bool(j)) for k,(c,m,j) in got.items()}
        if nxt==usable: break
        usable=nxt
    good={}
    for k,(c,m,j) in decompose2(D,tol,usable,jong_h).items():
        if not c or not m or (k[2] and not j): continue
        bc,bm,bj=M.bbox(c),M.bbox(m),M.bbox(j)
        if M.fam_of(JUNG[k[1]]) in ('VR','VL') and bc[2]>bm[0]+40: continue
        if k[2] and bj[3]>min(bc[3],bm[3])-30: continue
        good[k]=(c,m,j)
    return good

def jong_table(slots):
    h=defaultdict(list)
    for (li,vi,ti),(c,m,j) in slots.items():
        if ti and j:
            b=M.bbox(j); h[ti].append(b[3]-b[1])
    return {t:float(np.median(v)) for t,v in h.items() if len(v)>=8}

if __name__=='__main__':
    f=TTFont(sys.argv[1]); D=M.extract(f)
    s1=validated2(D,60,None); s1b=validated2(D,120,None)
    p1=dict(s1b); p1.update(s1)
    tbl=jong_table(p1)
    print('1패스 %d자, 종성 높이 표 %d종'%(len(p1),len(tbl)))
    print('  ', '  '.join('%s %.0f'%(JONG[t],v) for t,v in sorted(tbl.items())[:14]))
    s2=validated2(D,60,tbl); s2b=validated2(D,120,tbl)
    p2=dict(s2b); p2.update(s2)
    print('2패스 %d자'%len(p2))
    # 달라진 글자 수
    diff=sum(1 for k in p2 if k in p1 and M.bbox(p2[k][2] or [(0,0,0,0,0,0)])!=M.bbox(p1[k][2] or [(0,0,0,0,0,0)]))
    print('종성 상자가 바뀐 글자: %d'%diff)
    pickle.dump((p2,D,tbl),open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),'pass2.pkl'),'wb'))
