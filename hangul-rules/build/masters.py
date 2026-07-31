import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""두 마스터(Thin 100 / Black 900)로 규칙을 뽑고 마스터 색인을 만든다.

    python3 build/masters.py /path/to/fontdir          # 전체 파이프라인 + 색인
    python3 build/masters.py --index-only              # 이미 뽑아 둔 산출물로 색인만

파이프라인은 마스터마다 네 단계다.
    partial.py <font>   부분 분해            -> partial-<tag>.pkl
    layers2.py          4레이어 적합          -> layers2-<tag>.pkl
    emit2.py            레이어 규칙           -> studio-rules-layered-<tag>.json
    leaves.py <font> + emit.py  토폴로지 기본값 -> studio-rules-<tag>.json

색인 studio-rules-masters.json 은 두 마스터를 한데 묶고, 마스터 사이에서 실제로
움직이는 값이 무엇인지 정리한다. 규칙 본문은 마스터별 파일에 그대로 둔다
(합치면 76만 바이트가 되는데 겹치는 부분이 없어 합칠 이득이 없다).
"""
import json, os, statistics as st, subprocess, sys
from collections import defaultdict

HERE = _os.path.dirname(_os.path.abspath(__file__))
ROOT = _os.path.join(HERE, os.pardir)
MASTERS = [('thin', 'Thin', 100), ('black', 'Black', 900)]
SIDES = ('top', 'right', 'bottom', 'left')

def step(tag, weight, args, cell=None):
    env = dict(os.environ, HFS_MASTER=tag, HFS_WGHT=str(weight),
               HFS_SOURCE='Noto Sans CJK KR %s (noto-cjk Sans2.004)' % weight)
    if cell: env['HFS_CELL'] = ','.join(str(v) for v in cell)
    print('  · %-12s %s' % (weight, args[0]))
    r = subprocess.run([sys.executable, os.path.join(HERE, args[0])] + args[1:],
                       env=env, cwd=ROOT, capture_output=True, text=True)
    if r.returncode: print(r.stdout[-3000:], r.stderr[-3000:]); sys.exit(1)

def envelope(tag):
    import pickle
    p = pickle.load(open(os.path.join(HERE, 'partial-%s.pkl' % tag), 'rb'))
    e = None
    for bx in p.values():
        for b in bx.values():
            e = b if e is None else (min(e[0], b[0]), min(e[1], b[1]),
                                     max(e[2], b[2]), max(e[3], b[3]))
    return e

def run_all(fontdir):
    """부분 분해 → 공통 셀 결정 → 나머지 단계.

    셀은 두 마스터 잉크 봉투의 합집합 하나로 통일한다. 마스터마다 봉투가 달라
    셀도 달라지면 정규화 좌표 (0,0,1,1)이 마스터마다 다른 em 상자를 가리켜
    보간이 어긋난다.
    """
    for tag, weight, _ in MASTERS:
        font = os.path.join(fontdir, 'NotoSansCJKkr-%s.otf' % weight)
        if not os.path.exists(font): sys.exit('폰트 없음: %s' % font)
        step(tag, weight, ['partial.py', font])
    es = [envelope(tag) for tag, _, _ in MASTERS]
    cell = (int(min(e[0] for e in es)), int(min(e[1] for e in es)),
            round(max(e[2] for e in es)), round(max(e[3] for e in es)))
    print('  공통 셀 %s  %d x %d' % (cell, cell[2] - cell[0], cell[3] - cell[1]))
    for tag, weight, _ in MASTERS:
        font = os.path.join(fontdir, 'NotoSansCJKkr-%s.otf' % weight)
        for a in (['layers2.py'], ['emit2.py'], ['leaves.py', font], ['emit.py']):
            step(tag, weight, a, cell)
    return cell

def load(tag):
    p = os.path.join(ROOT, 'studio-rules-layered-%s.json' % tag)
    q = os.path.join(ROOT, 'studio-rules-%s.json' % tag)
    return json.load(open(p)), json.load(open(q))

def main():
    args = sys.argv[1:]
    if args and args[0] != '--index-only':
        print('■ 두 마스터 파이프라인')
        run_all(args[0])
        print()

    L, T = {}, {}
    for tag, _, _ in MASTERS: L[tag], T[tag] = load(tag)

    idx = {'schema': 'hangul-rules/studio-masters/1',
           'note': ('마스터 두 벌(100/900)의 규칙 색인. 규칙 본문은 각 파일에 있고 '
                    '중간 굵기는 선형 보간으로 얻는다.'),
           'cellEmBox': L['thin']['frame']['cellEmBox'],
           'cellNote': ('두 마스터 잉크 봉투의 합집합. 마스터마다 셀이 다르면 정규화 '
                        '좌표가 서로 다른 em 상자를 가리켜 보간이 어긋난다.'),
           'masters': [], 'interpolation': {
               'kind': 'linear', 'avar': False,
               'evidence': ('중간 5종 실측 대비 중앙 3.2 em / 최대 32.5 em. '
                            '규칙 모델 자체의 오차(8.8 em)보다 작다. WEIGHT-AXIS.md §6')}}
    for tag, weight, wght in MASTERS:
        idx['masters'].append({
            'name': weight, 'wght': wght, 'tag': tag, 'source': L[tag]['source'],
            'frame': L[tag]['frame'], 'coverage': L[tag]['coverage'],
            'fidelity': L[tag]['fidelity']['layers'],
            'files': {'layered': 'studio-rules-layered-%s.json' % tag,
                      'topology': 'studio-rules-%s.json' % tag}})

    # ── 마스터 사이에서 무엇이 움직이나 ────────────────────────────────────
    a, b = L['thin'], L['black']
    print('■ 마스터 간 차이 — L1 템플릿 노드 값 (Black − Thin)')
    print('  %-14s %-18s %8s %8s %8s' % ('토폴로지', '노드', 'gap', 'overlap', 'space'))
    moves = defaultdict(list)
    for g in sorted(set(a['L1_templates']) & set(b['L1_templates'])):
        na, nb = a['L1_templates'][g]['nodes'], b['L1_templates'][g]['nodes']
        for p in sorted(set(na) & set(nb)):
            row = []
            for f in ('gap', 'overlap', 'spaceWeight'):
                if f in na[p] and f in nb[p]:
                    d = nb[p][f] - na[p][f]; row.append(d); moves[f].append(abs(d))
                else: row.append(None)
            for s in SIDES:
                moves['pad_' + s].append(abs(nb[p]['padding'][s] - na[p]['padding'][s]))
            if any(v is not None and abs(v) >= 1.0 for v in row):
                print('  %-14s %-18s %s' % (g, p, ' '.join(
                    '%8.2f' % v if v is not None else '       ·' for v in row)))
    print()
    print('  필드별 |Black−Thin| 중앙 / 최대')
    fm = {}
    for f in ('gap', 'overlap', 'spaceWeight') + tuple('pad_' + s for s in SIDES):
        if not moves[f]: continue
        fm[f] = {'medianDelta': round(st.median(moves[f]), 3),
                 'maxDelta': round(max(moves[f]), 3)}
        print('    %-12s %8.2f %8.2f' % (f, fm[f]['medianDelta'], fm[f]['maxDelta']))
    idx['L1delta'] = fm

    # ── L2 자모 패딩이 마스터 간에 얼마나 움직이나 ─────────────────────────
    def flat(d):
        o = {}
        for path, byfam in d['L2_padding'].items():
            for f, rest in byfam.items():
                for k, pad in rest.items(): o[(path, f, k)] = pad
        return o
    fa, fb = flat(a), flat(b)
    common = sorted(set(fa) & set(fb))
    dl = [max(abs(fb[k][s] - fa[k][s]) for s in SIDES) for k in common]
    print()
    print('■ L2 자모 패딩 %d개 공통 항목의 |Black−Thin| (부모 사각형 대비 %%)'
          % len(common))
    ds = sorted(dl)
    print('  중앙 %.2f  p90 %.2f  최대 %.2f' % (st.median(ds), ds[int(len(ds)*.9)], ds[-1]))
    bynode = defaultdict(list)
    for d, k in zip(dl, common): bynode[k[0]].append(d)
    print('  노드별 중앙 / p90')
    ORDER = ['Root', 'LeadingMedial', 'LeadingMedialBase', 'Leading', 'Medial',
             'MedialBase', 'MedialExtension', 'Trailing', 'TrailingFirst',
             'TrailingSecond']
    idx['L2byNode'] = {}
    for p in ORDER:
        if p not in bynode: continue
        v = sorted(bynode[p])
        idx['L2byNode'][p] = {'n': len(v), 'medianDelta': round(st.median(v), 2),
                              'p90Delta': round(v[int(len(v)*.9)], 2)}
        print('    %-18s %4d %8.2f %8.2f'
              % (p, len(v), st.median(v), v[int(len(v)*.9)]))
    top = sorted(zip(dl, common), reverse=True)[:12]
    print('  가장 많이 움직이는 항목')
    for d, k in top: print('    %-18s %-3s %-8s %8.2f' % (k[0], k[1], k[2], d))
    idx['L2delta'] = {'commonEntries': len(common),
                      'medianDelta': round(st.median(ds), 2),
                      'p90Delta': round(ds[int(len(ds)*.9)], 2),
                      'maxDelta': round(ds[-1], 2),
                      'largest': [{'path': k[0], 'family': k[1], 'key': k[2],
                                   'delta': round(d, 2)} for d, k in top]}
    onlyA = sorted(set(fa) - set(fb)); onlyB = sorted(set(fb) - set(fa))
    print('  Thin에만 있는 항목 %d, Black에만 있는 항목 %d' % (len(onlyA), len(onlyB)))
    idx['L2delta']['thinOnly'] = len(onlyA)
    idx['L2delta']['blackOnly'] = len(onlyB)

    # ── 변형체(벌) 구성과 합획 결정 ────────────────────────────────────────
    vg = json.load(open(os.path.join(ROOT, 'variant-groups-stable.json')))
    idx['variantGroups'] = {'note': vg['note'],
                            'leading': vg['cho11'], 'medial': vg['medial2'],
                            'trailing': vg['trailing8'],
                            'counts': {'leading': len(vg['cho11']),
                                       'medial': len(vg['medial2']),
                                       'trailing': len(vg['trailing8'])}}
    fp = os.path.join(ROOT, 'fuse-pairs.json')
    if os.path.exists(fp):
        f = json.load(open(fp))
        idx['fusion'] = {
            'flippedPairs': sorted(f['pairs']),
            'flippedSyllables': f['flippedSyllables'],
            'stemRedrawn': f.get('stemRedrawn'),
            'decision': ('컴포넌트를 겹친 채로 두고 윤곽선을 합치지 않는다. '
                         '마스터마다 컴포넌트 수와 윤곽선 수가 같으므로 보간이 성립한다. '
                         'FUSION.md 참고')}

    # ── 두 마스터 사이를 선형 보간하면 중간 굵기가 나오는가 ─────────────────
    mid = os.path.join(ROOT, 'studio-rules-layered-regular.json')
    if os.path.exists(mid):
        R = json.load(open(mid)); fr = flat(R)
        t = (400 - 100) / 800.0
        keys = sorted(set(fa) & set(fb) & set(fr))
        e = [max(abs(fa[k][s] + (fb[k][s] - fa[k][s]) * t - fr[k][s]) for s in SIDES)
             for k in keys]
        base = [max(abs(fr[k][s] - fa[k][s]) for s in SIDES) for k in keys]
        es = sorted(e)
        print()
        print('■ 선형 보간 검증 — Thin·Black에서 wght 400을 예측해 실측 Regular와 비교')
        print('  공통 항목 %d개, 패딩 %%포인트' % len(keys))
        print('  보간 오차   중앙 %.2f  p90 %.2f  최대 %.2f'
              % (st.median(es), es[int(len(es)*.9)], es[-1]))
        print('  보간 안 하고 Thin을 그대로 썼을 때  중앙 %.2f' % st.median(sorted(base)))
        idx['interpolation']['checkAtRegular'] = {
            'entries': len(keys), 'unit': 'padding % points',
            'medianError': round(st.median(es), 2),
            'p90Error': round(es[int(len(es)*.9)], 2),
            'maxError': round(es[-1], 2),
            'baselineThinOnly': round(st.median(sorted(base)), 2)}

    P = os.path.join(ROOT, 'studio-rules-masters.json')
    json.dump(idx, open(P, 'w'), ensure_ascii=False, indent=1)
    print()
    print('studio-rules-masters.json 생성 — 마스터 %d벌' % len(idx['masters']))
    for m in idx['masters']:
        print('  %-6s wght %3d  커버리지 %d자  L3 중앙 %.1f em  (%s)'
              % (m['name'], m['wght'], m['coverage']['syllablesWithAnyBox'],
                 m['fidelity']['L3']['medianEm'], m['files']['layered']))

if __name__ == '__main__':
    main()
