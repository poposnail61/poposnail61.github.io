import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""모델 구조 탐색 벤치마크.

목표는 각 노드 잉크 상자의 네 모서리(em)다. 예측자 집합을 바꿔가며 홀드아웃 오차를
잰다. 레이아웃 파라미터화(패딩 %)와 분리해 비교하려고 em 절대좌표를 직접 맞춘다.
승자를 나중에 엔진의 트리 형태로 옮긴다.
"""
import pickle, sys
import numpy as np
from collections import defaultdict
from tree import tree, CHO, JUNG, JONG, COMPOUND_MEDIALS, COMPOUND_TRAILINGS
RIGHT,LEFT,HORZ,MIX='ㅏㅐㅑㅒㅣ','ㅓㅔㅕㅖ','ㅗㅛㅜㅠㅡ','ㅘㅙㅚㅝㅞㅟㅢ'
def fam(v): return 'VR' if v in RIGHT else 'VL' if v in LEFT else 'H' if v in HORZ else 'M'
def tkind(t): return 'none' if t==0 else ('compound' if t in COMPOUND_TRAILINGS else 'simple')
HERE=_os.path.dirname(_os.path.abspath(__file__))
part=pickle.load(open(_os.path.join(HERE,'partial.pkl'),'rb'))

DATA=defaultdict(list)          # path -> [(li,vi,ti, x0,y0,x1,y1)]
for (li,vi,ti),bx in part.items():
    for p,b in bx.items(): DATA[p].append((li,vi,ti)+tuple(b))
PATHS=sorted(DATA, key=lambda p:-len(DATA[p]))
print('노드별 표본:', {p:len(DATA[p]) for p in PATHS})

rng=np.random.default_rng(20260730)
syls=sorted(part); mask={k:(rng.random()<0.8) for k in syls}   # 음절 단위 8:2 분할

def onehot(vals, n):
    M=np.zeros((len(vals),n)); M[np.arange(len(vals)),vals]=1; return M

def design(rows, spec):
    """spec: 사용할 인자 목록. 절편은 항상 포함."""
    li=np.array([r[0] for r in rows]); vi=np.array([r[1] for r in rows]); ti=np.array([r[2] for r in rows])
    famid=np.array([['VR','VL','H','M'].index(fam(JUNG[v])) for v in vi])
    tkid=np.array([['none','simple','compound'].index(tkind(t)) for t in ti])
    topo=famid*3+tkid
    cols=[np.ones((len(rows),1))]
    if 'topo' in spec: cols.append(onehot(topo,12))
    if 'fam'  in spec: cols.append(onehot(famid,4))
    if 'cho'  in spec: cols.append(onehot(li,19))
    if 'jung' in spec: cols.append(onehot(vi,21))
    if 'jong' in spec: cols.append(onehot(ti,28))
    if 'cho*topo' in spec: cols.append(onehot(li*12+topo,19*12))
    if 'jung*cho' in spec: cols.append(onehot(vi*19+li,21*19))
    if 'cho*jung' in spec: cols.append(onehot(li*21+vi,19*21))
    if 'jong*jung'in spec: cols.append(onehot(ti*21+vi,28*21))
    if 'jong*cho' in spec: cols.append(onehot(ti*19+li,28*19))
    if 'col'  in spec: cols.append(onehot(vi*28+ti,21*28))
    if 'syl'  in spec:
        u={};idx=[]
        for r in rows:
            key=(r[0],r[1],r[2]); u.setdefault(key,len(u)); idx.append(u[key])
        cols.append(onehot(np.array(idx),len(u)))
    return np.hstack(cols)

LAM=1.0
def evaluate(spec):
    tr_err=[]; te_err=[]; params=0
    for p in PATHS:
        rows=DATA[p]
        X=design(rows,spec); Y=np.array([r[3:] for r in rows],dtype=float)
        m=np.array([mask[(r[0],r[1],r[2])] for r in rows])
        if m.sum()<10 or (~m).sum()<3: continue
        Xtr,Ytr=X[m],Y[m]
        A=Xtr.T@Xtr+LAM*np.eye(X.shape[1]); B=Xtr.T@Ytr
        W=np.linalg.solve(A,B)
        used=int((np.abs(W).max(axis=1)>1e-6).sum())
        params+=used*4
        for sel,acc in ((m,tr_err),(~m,te_err)):
            R=np.abs(X[sel]@W-Y[sel]).max(axis=1)
            acc.append(R)
    tr=np.concatenate(tr_err); te=np.concatenate(te_err)
    return params, np.median(tr), np.median(te), np.percentile(te,95)

SPECS=[
 ('상수만',                     set()),
 ('토폴로지',                   {'topo'}),
 ('토폴로지+초성',               {'topo','cho'}),
 ('토폴로지+초성+중성',           {'topo','cho','jung'}),
 ('토폴로지+초성+중성+종성 (완전가산)',{'topo','cho','jung','jong'}),
 ('+ 초성×토폴로지',             {'topo','cho','jung','jong','cho*topo'}),
 ('+ 초성×중성',                {'topo','cho','jung','jong','cho*jung'}),
 ('+ 초성×중성 + 중성×초성(동일)',  {'topo','cho','jung','jong','cho*jung','jung*cho'}),
 ('+ 종성×중성',                {'topo','cho','jung','jong','cho*jung','jong*jung'}),
 ('+ 종성×초성',                {'topo','cho','jung','jong','cho*jung','jong*jung','jong*cho'}),
 ('컬럼 + 초성',                {'col','cho'}),
 ('컬럼 + 초성 + 초성×중성',       {'col','cho','cho*jung'}),
 ('컬럼 + 전부 + 상호작용',        {'col','cho','jung','jong','cho*jung','jong*cho'}),
 ('음절별 (포화)',               {'syl'}),
]
print()
print('%-34s %9s %9s %9s %9s'%('모델','파라미터','학습중앙','검증중앙','검증p95'))
res=[]
for name,spec in SPECS:
    pr,tr,te,p95=evaluate(spec)
    res.append((name,pr,tr,te,p95))
    print('%-34s %9d %9.1f %9.1f %9.1f'%(name,pr,tr,te,p95))
pickle.dump(res,open(_os.path.join(HERE,'bench.pkl'),'wb'))
