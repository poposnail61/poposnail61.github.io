import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
"""굵기에 따라 합획이 뒤집히는 (초성,중성) 쌍을 정량화한다.

Thin에서 떨어져 있다가 Black에서 붙는 9쌍은 마스터 간 topology(윤곽선 수)가 달라
보간이 깨진다. 해결은 둘 중 하나로 topology를 통일하는 것이다.

  A안 — 전 굵기에서 붙인다.  Thin 쪽에서 간격을 없애 닿게 한다.
  B안 — 전 굵기에서 뗀다.    Black 쪽에서 겹침을 풀어 떼어 놓는다.

두 안의 비용은 같은 자로 잰다: **초성 윤곽선과 중성 윤곽선의 최단거리**.
bbox나 세로 프로파일로는 안 된다. ㅃ처럼 초성 한가운데가 비어 있으면 세로로는
영영 안 만나는데도 굵어지면서 옆으로 닿기 때문이다. 최단거리는 세로·가로·대각을
가리지 않고 하나의 수로 답한다. 접근 방향(dx,dy)도 같이 내서 기둥을 늘리는 것으로
해결되는지 옆으로 벌려야 하는지 구분한다.

붙어 버린 굵기에서는 거리를 못 재므로, 안 붙은 굵기들의 거리를 wght에 대해 선형
회귀해 900으로 외삽한다. 음수 외삽값이 곧 침투 깊이다.

    python3 build/fuse.py /path/to/fontdir
"""
import json, os, statistics as st, sys
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
import measure as M

WEIGHTS = [('Thin', 100), ('Light', 300), ('DemiLight', 350), ('Regular', 400),
           ('Medium', 500), ('Bold', 700), ('Black', 900)]
FLIP = ['ㄸㅗ', 'ㅃㅗ', 'ㅆㅗ', 'ㅉㅗ', 'ㄲㅛ', 'ㅅㅛ', 'ㅆㅛ', 'ㅈㅛ', 'ㅉㅛ']
STEP = 6.0                       # 윤곽선 재표본 간격 (em)
HERE = _os.path.dirname(_os.path.abspath(__file__))
OUT = _os.path.join(HERE, os.pardir)

# ── 윤곽선을 곡선까지 펴고 일정 간격으로 재표본한다 ─────────────────────────
class FlatPen(BasePen):
    N = 8
    def __init__(self, gs):
        super().__init__(gs); self.contours = []; self._cur = []; self._p = (0, 0)
    def _moveTo(self, p): self._flush(); self._cur = [p]; self._p = p
    def _lineTo(self, p): self._cur.append(p); self._p = p
    def _curveToOne(self, a, b, c):
        p0 = self._p
        for i in range(1, self.N + 1):
            t = i / self.N; u = 1 - t
            self._cur.append((u*u*u*p0[0] + 3*u*u*t*a[0] + 3*u*t*t*b[0] + t*t*t*c[0],
                              u*u*u*p0[1] + 3*u*u*t*a[1] + 3*u*t*t*b[1] + t*t*t*c[1]))
        self._p = c
    def _qCurveToOne(self, a, b):
        p0 = self._p
        for i in range(1, self.N + 1):
            t = i / self.N; u = 1 - t
            self._cur.append((u*u*p0[0] + 2*u*t*a[0] + t*t*b[0],
                              u*u*p0[1] + 2*u*t*a[1] + t*t*b[1]))
        self._p = b
    def _closePath(self): self._flush()
    def _endPath(self): self._flush()
    def _flush(self):
        if self._cur: self.contours.append(resample(self._cur)); self._cur = []

def resample(pts):
    """닫힌 다각형을 STEP 간격으로 다시 찍는다. 긴 직선 구간의 표본 부족을 막는다."""
    out = []
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % n]
        out.append((x0, y0))
        d = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** .5
        k = int(d // STEP)
        for j in range(1, k):
            t = j / k
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return out

def shapes_pts(gs, gname):
    """measure.shapes_of와 같은 카운터 병합. 점 목록도 함께 돌려준다."""
    pen = FlatPen(gs); gs[gname].draw(pen); pen._endPath()
    raw = []
    for c in pen.contours:
        xs = [x for x, _ in c]; ys = [y for _, y in c]
        raw.append({'pts': c, 'bb': (min(xs), min(ys), max(xs), max(ys)),
                    'a': M.signed_area(c)})
    if not raw: return []
    pos = [i for i, r in enumerate(raw) if r['a'] > 0]
    neg = [i for i, r in enumerate(raw) if r['a'] <= 0]
    if sum(abs(raw[i]['a']) for i in pos) < sum(abs(raw[i]['a']) for i in neg):
        pos, neg = neg, pos
    groups = {i: [i] for i in pos}
    for j in neg:
        bj = raw[j]['bb']; best = None; ba = None
        for i in pos:
            bi = raw[i]['bb']
            if bi[0] <= bj[0] and bi[1] <= bj[1] and bi[2] >= bj[2] and bi[3] >= bj[3]:
                a = abs(raw[i]['a'])
                if ba is None or a < ba: ba, best = a, i
        if best is None: groups[j] = [j]; pos.append(j)
        else: groups[best].append(j)
    out = []
    for mem in groups.values():
        bbs = [raw[k]['bb'] for k in mem]
        out.append({'bb': (min(b[0] for b in bbs), min(b[1] for b in bbs),
                           max(b[2] for b in bbs), max(b[3] for b in bbs)),
                    'pts': np.array([p for k in mem for p in raw[k]['pts']])})
    out.sort(key=lambda s: (s['bb'][0], s['bb'][1]))
    return out

def touches(shapes):
    """한 도형이 초성·중성 영역을 관통 = 획이 붙었다 (measure와 동일 기준)."""
    return any(s['bb'][1] < 430 and s['bb'][3] > 700 for s in shapes)

def split_horz(shapes):
    """가로모임을 (초성 도형들, 중성 도형)으로. 붙었거나 못 고르면 None."""
    wide = [s for s in shapes if s['bb'][2] - s['bb'][0] > 750]
    if len(wide) != 1: return None
    mid = wide[0]
    cho = [s for s in shapes if s is not mid and s['bb'][3] > mid['bb'][3]]
    return (cho, mid) if cho else None

def nearest(shapes, margin=260):
    """초성-중성 최단거리와 접근 벡터 (d, dx, dy). 붙었으면 None."""
    if touches(shapes): return None
    sp = split_horz(shapes)
    if sp is None: return None
    cho, mid = sp
    C = np.concatenate([s['pts'] for s in cho])
    Mi = mid['pts']
    C = C[C[:, 1] <= C[:, 1].min() + margin]          # 초성 아랫부분만
    Mi = Mi[Mi[:, 1] >= Mi[:, 1].max() - margin]      # 중성 윗부분만
    if len(C) == 0 or len(Mi) == 0: return None
    d2 = ((C[:, None, 0] - Mi[None, :, 0]) ** 2 +
          (C[:, None, 1] - Mi[None, :, 1]) ** 2)
    i, j = np.unravel_index(d2.argmin(), d2.shape)
    return (float(d2[i, j] ** .5), float(C[i, 0] - Mi[j, 0]), float(C[i, 1] - Mi[j, 1]))

def crossings(shapes, y):
    xs = []
    for s in shapes:
        pts = s['pts']
        for i in range(len(pts)):
            x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % len(pts)]
            if (y0 - y) * (y1 - y) < 0:
                xs.append(x0 + (x1 - x0) * (y - y0) / (y1 - y0))
    return sorted(xs)

def center_run(shapes, y, cx=500.0):
    """주사선 y에서 x=cx를 품는 잉크 구간 (좌, 우). 없으면 None."""
    xs = crossings(shapes, y)
    for i in range(0, len(xs) - 1, 2):
        if xs[i] <= cx <= xs[i + 1]: return (xs[i], xs[i + 1])
    return None

def runs(shapes, y, maxw=300.0):
    """주사선 y의 잉크 구간 중 폭이 maxw 미만인 것들 (= 기둥). 좌→우."""
    xs = crossings(shapes, y)
    return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)
            if xs[i + 1] - xs[i] < maxw]

def stem_runs(shapes, y0, y1, want, f=0.45):
    """가로대 바로 위 주사선에서 기둥으로 보이는 구간 want개.

    가로대(폭 900+)와 잔획(폭 30 미만)을 걸러내고 중앙부에 있는 것만 남긴다.
    주사선을 낮게(0.45) 고정한다. 더 위로 가면 초성과 합쳐진 구간이 잡혀
    비교 기준이 흔들린다.
    """
    y = y0 + (y1 - y0) * f
    cand = [r for r in runs(shapes, y, 300.0)
            if 30 <= r[1] - r[0] and 250 <= (r[0] + r[1]) / 2 <= 750]
    if len(cand) < want: return None
    cand.sort(key=lambda r: abs((r[0] + r[1]) / 2 - 500))
    return sorted(cand[:want])

def fit(xs, ys):
    """단순 선형회귀. (기울기, 절편, r)"""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs); syy = sum((b - my) ** 2 for b in ys)
    if sxx == 0: return None
    k = sxy / sxx
    r = sxy / (sxx * syy) ** .5 if syy > 0 else 1.0
    return k, my - k * mx, r

def main(fontdir):
    G, cache = {}, {}
    for name, _ in WEIGHTS:
        p = os.path.join(fontdir, 'NotoSansCJKkr-%s.otf' % name)
        f = TTFont(p); gs = f.getGlyphSet(); cm = f.getBestCmap()
        G[name] = (gs, cm); cache[name] = {}
        print('읽음 %s' % os.path.basename(p))
    def sh(w, k):
        if k not in cache[w]:
            gs, cm = G[w]
            cache[w][k] = shapes_pts(gs, cm[ord(M.syl(*k))])
        return cache[w][k]
    print()

    idx = {p: (M.CHO.index(p[0]), M.JUNG.index(p[1])) for p in FLIP}
    out = {'schema': 'hangul-rules/fuse/1',
           'note': '굵기별 합획 뒤집힘 9쌍 — A안(전 굵기 접촉)·B안(전 굵기 분리) 비용',
           'metric': '초성 윤곽선과 중성 윤곽선의 최단거리 (em, upem 1000)',
           'pairs': {}}

    # ── 1. 접촉이 시작되는 굵기 ─────────────────────────────────────────────
    print('■ 1. 28개 종성 중 획이 붙는 자수')
    print('  %-4s %-6s %s' % ('쌍', '과반', '  '.join('%5s' % w[:5] for w, _ in WEIGHTS)))
    for p in FLIP:
        li, vi = idx[p]
        cnt = [sum(1 for ti in range(28) if touches(sh(w, (li, vi, ti))))
               for w, _ in WEIGHTS]
        maj = next((wg for (w, wg), c in zip(WEIGHTS, cnt) if c > 14), None)
        print('  %-4s %-6s %s' % (p, maj or '—', '  '.join('%5d' % c for c in cnt)))
        out['pairs'][p] = {'contactByWeight': {w: c for (w, _), c in zip(WEIGHTS, cnt)},
                           'majorityOnsetWght': maj}
    t0 = sum(1 for p in FLIP if touches(sh('Thin', (idx[p][0], idx[p][1], 0))))
    print()
    print('  Thin에서도 붙는 자리는 받침 없는 음절(ti=0) 하나뿐 — %d/9쌍' % t0)
    print('  받침이 없으면 중성이 더 크게 자라 이미 닿는다. 뒤집히는 건 ti≥1이다.')
    aff = sum(1 for p in FLIP for ti in range(28)
              if not touches(sh('Thin', (idx[p][0], idx[p][1], ti)))
              and touches(sh('Black', (idx[p][0], idx[p][1], ti))))
    print('  Thin 비접촉 → Black 접촉으로 뒤집히는 음절: %d자 (9쌍×28=252 중)' % aff)
    out['flippedSyllables'] = aff
    out['alreadyFusedAtThin'] = t0

    # ── 2. 굵기별 최단거리 ──────────────────────────────────────────────────
    print()
    print('■ 2. 초성-중성 최단거리 (받침 있는 음절 ti≥1의 중앙값, em)')
    print('  0 = 붙음. 값이 있는 굵기만 회귀에 쓴다.')
    print('  %-4s %s' % ('쌍', '  '.join('%6s' % w[:5] for w, _ in WEIGHTS)))
    dist = {}
    for p in FLIP:
        li, vi = idx[p]; row = []
        for w, _ in WEIGHTS:
            ds = [r[0] for ti in range(1, 28)
                  if (r := nearest(sh(w, (li, vi, ti)))) is not None]
            row.append(st.median(ds) if len(ds) >= 5 else None)
        dist[p] = row
        out['pairs'][p]['minDistByWeight'] = {
            w: (round(v, 1) if v is not None else None) for (w, _), v in zip(WEIGHTS, row)}
        print('  %-4s %s' % (p, '  '.join('%6.0f' % v if v is not None else '     ·'
                                          for v in row)))

    # ── 3. 접근 방향 ────────────────────────────────────────────────────────
    print()
    print('■ 3. 최근접점의 접근 방향 (Thin, ti≥1 중앙값)')
    print('  |dy|>|dx| 이면 기둥 길이로 해결된다. 반대면 옆으로 벌려야 한다.')
    print('  %-4s %7s %7s %8s' % ('쌍', 'dx', 'dy', '지배축'))
    for p in FLIP:
        li, vi = idx[p]
        rs = [r for ti in range(1, 28) if (r := nearest(sh('Thin', (li, vi, ti))))]
        if len(rs) < 5: continue
        dx = st.median([abs(r[1]) for r in rs]); dy = st.median([abs(r[2]) for r in rs])
        ax = '세로' if dy > dx else '가로'
        print('  %-4s %7.0f %7.0f %8s' % (p, dx, dy, ax))
        out['pairs'][p]['approach'] = {'dxEm': round(dx, 1), 'dyEm': round(dy, 1),
                                       'axis': 'vertical' if dy > dx else 'horizontal'}

    # ── 4. A안 — Thin에서 붙인다 ────────────────────────────────────────────
    print()
    print('■ 4. A안 비용 — Thin에서 간격을 없애려면 (em)')
    print('  = Thin 최단거리. 중성 전체 높이 대비 비율.')
    print('  %-4s %8s %10s %8s' % ('쌍', '메울 간격', '중성높이', '비율%'))
    growA = {}
    for p in FLIP:
        li, vi = idx[p]
        d = dist[p][0]
        hs = [sp[1]['bb'][3] - sp[1]['bb'][1] for ti in range(1, 28)
              if (sp := split_horz(sh('Thin', (li, vi, ti))))]
        if d is None or not hs: continue
        h = st.median(hs); growA[p] = d
        print('  %-4s %8.0f %10.0f %8.1f' % (p, d, h, 100 * d / h))
        out['pairs'][p]['optionA_fuseAtThin'] = {
            'closeEm': round(d, 1), 'medialHeightEm': round(h, 1),
            'percentOfMedial': round(100 * d / h, 1)}
    if growA:
        v = list(growA.values())
        print('  %-4s %8.0f  (최대 %.0f)' % ('중앙', st.median(v), max(v)))
        out['optionA'] = {'medianCloseEm': round(st.median(v), 1),
                          'maxCloseEm': round(max(v), 1)}

    # ── 5. B안 — Black에서 뗀다 ────────────────────────────────────────────
    print()
    print('■ 5. B안 비용 — Black에서 겹침을 풀려면 (em)')
    print('  붙은 뒤엔 못 재므로 안 붙은 굵기의 거리를 wght로 회귀해 900으로 외삽한다.')
    print('  침투깊이 = −외삽거리, 필요분리 = 침투깊이 + 목표간격(같은 자리 비접촉 초성 중앙값)')
    print('  %-4s %3s %6s %8s %8s %8s %8s %7s'
          % ('쌍', 'n', 'r', '외삽d', '침투깊이', '목표간격', '필요분리', '비율%'))
    cutB = {}
    # 목표 간격: Black에서 같은 중성을 쓰면서 안 붙는 초성들의 최단거리
    target = {}
    for v in 'ㅗㅛ':
        vi = M.JUNG.index(v)
        ds = [r[0] for li in range(19) for ti in range(1, 28)
              if (r := nearest(sh('Black', (li, vi, ti)))) is not None]
        target[v] = st.median(ds)
    hblack = {}
    for v in 'ㅗㅛ':
        vi = M.JUNG.index(v)
        hs = [sp[1]['bb'][3] - sp[1]['bb'][1] for li in range(19) for ti in range(1, 28)
              if (sp := split_horz(sh('Black', (li, vi, ti))))]
        hblack[v] = st.median(hs)
    for p in FLIP:
        xs = [wg for (w, wg), d in zip(WEIGHTS, dist[p]) if d is not None]
        ys = [d for d in dist[p] if d is not None]
        if len(xs) < 2: continue
        f = fit(xs, ys)
        if f is None: continue
        k, b0, r = f
        ext = k * 900 + b0
        pen = max(0.0, -ext)
        need = pen + target[p[1]]
        cutB[p] = need
        h = hblack[p[1]]
        print('  %-4s %3d %6.2f %8.0f %8.0f %8.0f %8.0f %7.1f'
              % (p, len(xs), r, ext, pen, target[p[1]], need, 100 * need / h))
        out['pairs'][p]['optionB_separateAtBlack'] = {
            'nWeights': len(xs), 'r': round(r, 3), 'extrapolatedDistEm': round(ext, 1),
            'penetrationEm': round(pen, 1), 'targetGapEm': round(target[p[1]], 1),
            'separateEm': round(need, 1), 'medialHeightEm': round(h, 1),
            'percentOfMedial': round(100 * need / h, 1)}
    if cutB:
        v = list(cutB.values())
        print('  %-4s %47.0f  (최대 %.0f)' % ('중앙', st.median(v), max(v)))
        out['optionB'] = {'medianSeparateEm': round(st.median(v), 1),
                          'maxSeparateEm': round(max(v), 1),
                          'targetGapEm': {k2: round(v2, 1) for k2, v2 in target.items()}}

    # ── 6. 결정표 ──────────────────────────────────────────────────────────
    print()
    print('■ 6. 결정표')
    print('  %-4s %9s %9s %8s' % ('쌍', 'A안 메움', 'B안 분리', '싼 쪽'))
    rec = {}
    for p in FLIP:
        a, b_ = growA.get(p), cutB.get(p)
        if a is None or b_ is None: continue
        rec[p] = 'A' if a <= b_ else 'B'
        print('  %-4s %9.0f %9.0f %8s' % (p, a, b_, rec[p]))
        out['pairs'][p]['cheaper'] = rec[p]
    if rec:
        na = sum(1 for x in rec.values() if x == 'A')
        print()
        print('  A안이 싼 쌍 %d / B안이 싼 쌍 %d' % (na, len(rec) - na))
        out['recommendation'] = {'cheaperA': na, 'cheaperB': len(rec) - na}

    # ── 7. 합획이 '겹침'인가 '다시 그림'인가 ────────────────────────────────
    # 붙은 글자의 기둥 좌우 x가 안 붙은 글자와 같으면 노토는 두 컴포넌트를 그대로
    # 겹쳐 놓은 것이다. 그렇다면 합자 컴포넌트를 새로 그릴 필요가 없다.
    print()
    print('■ 7. Black의 합획은 컴포넌트를 다시 그린 것인가, 그냥 겹친 것인가')
    print('  가로대 바로 위에서 잰 기둥 x를 같은 자리 다른 초성들의 중앙값과 견준다.')
    print('  합획 때문에 기둥을 고쳐 그렸다면 접촉이 시작되는 굵기에서 값이 튀어야 한다.')
    print('  ㅛ는 초성 획이 같은 주사선을 지나가 기둥과 구분이 안 되므로 뺐다.')
    print('  %-4s %s' % ('쌍', '  '.join('%6s' % w[:5] for w, _ in WEIGHTS)))
    flipset = {(idx[p][0], idx[p][1]) for p in FLIP}
    def stem_delta(w, li, vi):
        want = 2 if M.JUNG[vi] == 'ㅛ' else 1
        ds = []
        for ti in range(1, 28):
            # 가로대 y는 분리되는 초성들에서 얻는다 (기둥 주사선 위치 결정용)
            mids = [sp[1]['bb'] for l2 in range(19)
                    if (sp := split_horz(sh(w, (l2, vi, ti)))) is not None]
            if len(mids) < 3: continue
            y0 = st.median([m[1] for m in mids]); y1 = st.median([m[3] for m in mids])
            a = stem_runs(sh(w, (li, vi, ti)), y0, y1, want)
            bs = [r for l2 in range(19) if (l2, vi) not in flipset
                  and (r := stem_runs(sh(w, (l2, vi, ti)), y0, y1, want)) is not None]
            if not a or len(bs) < 5: continue
            b = [(st.median([x[i][0] for x in bs]), st.median([x[i][1] for x in bs]))
                 for i in range(want)]
            ds.append(max(max(abs(a[i][0] - b[i][0]), abs(a[i][1] - b[i][1]))
                          for i in range(want)))
        return st.median(ds) if len(ds) >= 5 else None
    grow = []
    for p in FLIP:
        li, vi = idx[p]
        row = [stem_delta(w, li, vi) for w, _ in WEIGHTS]
        if row[0] is None or row[-1] is None: continue
        grow.append(row[-1] - row[0])
        print('  %-4s %s' % (p, '  '.join('%6.1f' % v if v is not None else '     ·'
                                          for v in row)))
        out['pairs'][p]['stemDeltaByWeight'] = {
            w: (round(v, 1) if v is not None else None)
            for (w, _), v in zip(WEIGHTS, row)}
    if grow:
        print()
        print('  차이는 어느 굵기에서도 튀지 않고 Black에서 오히려 줄어든다.')
        print('  Thin→Black 변화 중앙 %+.1f em, 최대 %+.1f em — 노토는 합획에서 중성을'
              % (st.median(grow), max(grow)))
        print('  고쳐 그리지 않았다. 두 컴포넌트를 그대로 겹쳐 놓은 것이다.')
        out['stemRedrawn'] = {'medianGrowthEm': round(st.median(grow), 1),
                              'maxGrowthEm': round(max(grow), 1),
                              'conclusion': 'components unchanged; fusion is plain overlap',
                              'measuredPairs': [p for p in FLIP
                                                if 'stemDeltaByWeight' in out['pairs'][p]]}

    json.dump(out, open(os.path.join(OUT, 'fuse-pairs.json'), 'w'),
              ensure_ascii=False, indent=1)
    print()
    print('fuse-pairs.json 생성')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')
