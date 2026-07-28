import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""리프 단위 분해 실패를 원인별로 분류한다."""
import contextlib, io as _io, pickle, sys
from collections import Counter
import measure as M
from fontTools.ttLib import TTFont
from tree import tree, CHO, JUNG, JONG, COMPOUND_MEDIALS, COMPOUND_TRAILINGS
import leaves as L

f=TTFont(sys.argv[1]); D=M.extract(f)
a=L.run_validated(D,60); b=L.run_validated(D,120)
slots=dict(b); slots.update(a)
horz=L.horz_shapes(D)
why=Counter(); detail=Counter()
for li in range(19):
    for vi in range(21):
        for ti in range(28):
            k=(li,vi,ti)
            in_slot = k in slots; in_horz = k in horz
            if not in_slot and not in_horz:
                why['A 슬롯분해 실패']+=1
                detail['A %s'%M.fam_of(JUNG[vi])]+=1; continue
            if in_slot:
                cs,ms,js=slots[k]
                if vi in COMPOUND_MEDIALS and L.split_medial(vi,cs,ms) is None:
                    why['B 겹중성 base 못 찾음']+=1; detail['B %s'%JUNG[vi]]+=1; continue
                if ti in COMPOUND_TRAILINGS and L.split_x(js) is None:
                    why['C 겹종성 못 쪼갬']+=1; detail['C %s'%JONG[ti]]+=1; continue
            else:
                cs,mid,js=horz[k]
                if ti in COMPOUND_TRAILINGS and L.split_x(js) is None:
                    why['C 겹종성 못 쪼갬']+=1; detail['C %s'%JONG[ti]]+=1; continue
            why['OK']+=1
print('11,172자 분류:')
for k,v in sorted(why.items()): print('  %-22s %5d  %5.1f%%'%(k,v,100*v/11172))
print()
print('A 계열별:', dict(sorted((k[2:],v) for k,v in detail.items() if k[0]=='A')))
print('B 중성별:', dict(sorted((k[2:],v) for k,v in detail.items() if k[0]=='B')))
print('C 종성별:', dict(sorted((k[2:],v) for k,v in detail.items() if k[0]=='C')))
