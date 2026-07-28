#!/usr/bin/env python3
"""한글 폰트의 음절 조합 규칙을 전수 실측해 rules.json / glyphs.json을 만든다.

    pip install fonttools
    python3 measure.py /path/to/NotoSansCJKkr-Regular.otf

폰트 파일만 받으므로 다른 한글 폰트에도 그대로 적용된다.
자세한 방법과 한계는 ../SPEC.md 참고.
"""
import json, os, statistics as st, sys
from collections import Counter, defaultdict

from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.pens.svgPathPen import SVGPathPen

CHO = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
JUNG = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'
JONG = [''] + list('ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ')
RIGHT, LEFT, HORZ, MIX = 'ㅏㅐㅑㅒㅣ', 'ㅓㅔㅕㅖ', 'ㅗㅛㅜㅠㅡ', 'ㅘㅙㅚㅝㅞㅟㅢ'
FAMS = (('VR', RIGHT, ('초성', '중성', '종성')),
        ('VL', LEFT,  ('초성블록', '중성기둥', '종성')),
        ('H',  HORZ,  ('초성', '중성', '종성')),
        ('M',  MIX,   ('좌상블록', '중성기둥', '종성')))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, os.pardir)

def fam_of(v):
    for f, vs, _ in FAMS:
        if v in vs: return f

def syl(li, vi, ti): return chr(0xAC00 + (li * 21 + vi) * 28 + ti)
def med(xs): return round(st.median(xs))

# ── 1. 아웃라인 → 도형(shape) ────────────────────────────────────────────────
class ContourPen(BasePen):
    """윤곽선을 좌표 리스트로 수집한다."""
    def __init__(self, gs):
        super().__init__(gs); self.contours = []; self._cur = []
    def _moveTo(self, p): self._flush(); self._cur = [p]
    def _lineTo(self, p): self._cur.append(p)
    def _curveToOne(self, a, b, c): self._cur += [a, b, c]
    def _qCurveToOne(self, a, b): self._cur += [a, b]
    def _closePath(self): self._flush()
    def _endPath(self): self._flush()
    def _flush(self):
        if self._cur: self.contours.append(self._cur); self._cur = []

def signed_area(pts):
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] -
               pts[(i + 1) % len(pts)][0] * pts[i][1]
               for i in range(len(pts))) / 2

def shapes_of(gs, gname):
    """카운터(속빈 부분)를 부모에 병합해 도형 목록을 만든다.

    각 도형 = (점수, xmin, ymin, xmax, ymax, 윤곽선수)
    """
    pen = ContourPen(gs); gs[gname].draw(pen); pen._endPath()
    raw = []
    for c in pen.contours:
        xs = [x for x, _ in c]; ys = [y for _, y in c]
        raw.append({'n': len(c), 'bb': (min(xs), min(ys), max(xs), max(ys)),
                    'a': signed_area(c)})
    if not raw: return []
    pos = [i for i, r in enumerate(raw) if r['a'] > 0]
    neg = [i for i, r in enumerate(raw) if r['a'] <= 0]
    # 면적 합이 큰 쪽이 바깥 윤곽선
    if sum(abs(raw[i]['a']) for i in pos) < sum(abs(raw[i]['a']) for i in neg):
        pos, neg = neg, pos
    groups = {i: [i] for i in pos}
    for j in neg:
        bj = raw[j]['bb']; best = None; best_area = None
        for i in pos:
            bi = raw[i]['bb']
            if bi[0] <= bj[0] and bi[1] <= bj[1] and bi[2] >= bj[2] and bi[3] >= bj[3]:
                a = abs(raw[i]['a'])
                if best_area is None or a < best_area: best_area, best = a, i
        if best is None: groups[j] = [j]; pos.append(j)
        else: groups[best].append(j)
    out = []
    for members in groups.values():
        bbs = [raw[k]['bb'] for k in members]
        out.append((sum(raw[k]['n'] for k in members),
                    round(min(b[0] for b in bbs), 1), round(min(b[1] for b in bbs), 1),
                    round(max(b[2] for b in bbs), 1), round(max(b[3] for b in bbs), 1),
                    len(members)))
    out.sort(key=lambda s: (s[1], s[2]))
    return out

def extract(font):
    gs = font.getGlyphSet(); cmap = font.getBestCmap()
    return {(li, vi, ti): shapes_of(gs, cmap[ord(syl(li, vi, ti))])
            for li in range(19) for vi in range(21) for ti in range(28)}

# ── 2. 초성축 근사 불변량으로 슬롯 귀속 (세로·섞임모임) ─────────────────────
def similar(a, b, tol):
    return (a[0] == b[0] and a[5] == b[5] and
            max(abs(a[1] - b[1]), abs(a[2] - b[2]),
                abs(a[3] - b[3]), abs(a[4] - b[4])) <= tol)

def decompose(D, tol, usable):
    """(중성,종성) 고정 후 초성 19자에 걸쳐 불변인 도형 = 중성 ∪ 종성.
    차집합이 초성. 중성/종성은 ymax 최대 간격으로 분리한다."""
    out = {}
    for vi in range(21):
        for ti in range(28):
            pool = [l for l in range(19) if usable.get((l, vi, ti), True)]
            thr = max(3, int(len(pool) * 0.68))
            for li in range(19):
                inv, cho = [], []
                for s in D[(li, vi, ti)]:
                    hits = sum(1 for l in pool
                               if any(similar(s, q, tol) for q in D[(l, vi, ti)]))
                    (inv if hits >= thr else cho).append(s)
                if ti == 0:
                    out[(li, vi, ti)] = (cho, inv, []); continue
                ys = sorted({s[4] for s in inv})
                if len(ys) < 2:
                    out[(li, vi, ti)] = (cho, inv, []); continue
                cut = max(((ys[i + 1] - ys[i], (ys[i] + ys[i + 1]) / 2)
                           for i in range(len(ys) - 1)))[1]
                out[(li, vi, ti)] = (cho, [s for s in inv if s[4] > cut],
                                          [s for s in inv if s[4] <= cut])
    return out

def bbox(shapes):
    if not shapes: return None
    return (min(s[1] for s in shapes), min(s[2] for s in shapes),
            max(s[3] for s in shapes), max(s[4] for s in shapes))

def validated(D, tol):
    usable = {}
    for _ in range(3):
        got = decompose(D, tol, usable)
        nxt = {k: bool(c) and bool(m) and (k[2] == 0 or bool(j))
               for k, (c, m, j) in got.items()}
        if nxt == usable: break
        usable = nxt
    good = {}
    for k, (c, m, j) in decompose(D, tol, usable).items():
        if not c or not m or (k[2] and not j): continue
        bc, bm, bj = bbox(c), bbox(m), bbox(j)
        if fam_of(JUNG[k[1]]) in ('VR', 'VL') and bc[2] > bm[0] + 40: continue
        if k[2] and bj[3] > min(bc[3], bm[3]) - 30: continue
        good[k] = (bc, bm, bj)
    return good

# ── 3. 가로모임: 중성은 폭 750 이상인 도형 ───────────────────────────────────
def decompose_horz(D):
    out = {}
    for v in HORZ:
        vi = JUNG.index(v)
        for ti in range(28):
            for li in range(19):
                sh = D[(li, vi, ti)]
                wide = [s for s in sh if s[3] - s[1] > 750]
                if len(wide) != 1: continue
                mid = wide[0]; rest = [s for s in sh if s is not mid]
                cho  = [s for s in rest if s[4] > mid[4]]
                jong = [s for s in rest if s[4] <= mid[4]]
                if not cho or (ti and not jong) or (ti == 0 and jong): continue
                out[(li, vi, ti)] = (bbox(cho), (mid[1], mid[2], mid[3], mid[4]),
                                     bbox(jong))
    return out

# ── 4. 규칙 집계 ────────────────────────────────────────────────────────────
def left_dependency(D):
    """중성 좌단 x = a + slope × 초성 우단 x  (세로모임, 분해 불필요)"""
    res = {}
    for v in 'ㅏㅑㅓㅕㅣ':
        vi = JUNG.index(v); pts = []; merged = tot = 0
        for ti in range(28):
            for li in range(19):
                sh = [s for s in D[(li, vi, ti)] if s[4] > 700]
                if not sh: continue
                tot += 1
                jung = max(sh, key=lambda s: s[3])
                others = [s for s in sh if s is not jung]
                if not others or jung[1] < 300: merged += 1; continue
                pts.append((max(s[3] for s in others), jung[1]))
        if len(pts) < 50: continue
        mx = st.mean([p[0] for p in pts]); my = st.mean([p[1] for p in pts])
        den = sum((p[0] - mx) ** 2 for p in pts)
        slope = sum((p[0] - mx) * (p[1] - my) for p in pts) / den
        sx = st.pstdev([p[0] for p in pts]); sy = st.pstdev([p[1] for p in pts])
        res[v] = {'slope': round(slope, 3), 'r': round(slope * sx / sy, 3) if sy else 0,
                  'gap': round(my - mx, 1), 'n': len(pts), 'merged': merged, 'tot': tot}
    return res

def contact_matrices(D):
    """한 윤곽선이 두 슬롯 영역을 관통 ⇒ 획이 물리적으로 닿았다."""
    spans = lambda sh, lo, hi: any(s[2] < lo and s[4] > hi for s in sh)
    cj, jj = {}, {}
    for v in HORZ:
        vi = JUNG.index(v)
        for li in range(19):
            key = CHO[li] + v
            cj[key] = sum(1 for ti in range(28) if spans(D[(li, vi, ti)], 430, 700))
            jj[key] = sum(1 for ti in range(1, 28) if spans(D[(li, vi, ti)], 60, 330))
    return cj, jj

def build_rules(font, D, slots):
    upem = font['head'].unitsPerEm
    rules = {'unitsPerEm': upem, 'decomposed': len(slots), 'total': 11172}

    zones = {}
    for fam, vs, labels in FAMS:
        for bat in (0, 1):
            dat = [slots[k] for k in slots
                   if JUNG[k[1]] in vs and ((k[2] > 0) == bat)]
            if fam in ('VL', 'M'):
                # VL·M은 중성 가로부가 초성과 연동돼 귀속이 글자마다 달라진다.
                # 라벨이 흔들리지 않도록 초성·중성을 하나의 블록으로 합쳐 집계한다.
                labels = ('초·중성 블록', None, '종성')
                dat = [((min(c[0], m[0]), min(c[1], m[1]),
                         max(c[2], m[2]), max(c[3], m[3])), None, j)
                       for c, m, j in dat]
            if len(dat) < 20: continue
            z = {'n': len(dat), 'labels': labels}
            for name, i in (('a', 0), ('b', 1), ('c', 2)):
                if labels[i] is None: continue
                sel = [x[i] for x in dat if x[i]]
                if not sel: continue
                z[name] = {'x0': med([s[0] for s in sel]), 'y0': med([s[1] for s in sel]),
                           'x1': med([s[2] for s in sel]), 'y1': med([s[3] for s in sel]),
                           'w':  med([s[2] - s[0] for s in sel]),
                           'h':  med([s[3] - s[1] for s in sel])}
            zones['%s%d' % (fam, bat)] = z
    rules['zones'] = zones

    ladder = {}
    for ti in range(1, 28):
        dat = [slots[k] for k in slots if k[2] == ti]
        if len(dat) < 8: continue
        ladder[JONG[ti]] = {'h':  med([x[2][3] - x[2][1] for x in dat]),
                            'y0': med([x[2][1] for x in dat]),
                            'y1': med([x[2][3] for x in dat]),
                            'w':  med([x[2][2] - x[2][0] for x in dat]), 'n': len(dat)}
    rules['jongLadder'] = dict(sorted(ladder.items(), key=lambda kv: kv[1]['h']))

    widths = {}
    for vi in range(21):
        for bat in (0, 1):
            dat = [slots[k] for k in slots if k[1] == vi and ((k[2] > 0) == bat)]
            if len(dat) < 15: continue
            fam = fam_of(JUNG[vi])
            widths['%s%d' % (JUNG[vi], bat)] = {
                'choW':   med([x[0][2] - x[0][0] for x in dat]),
                'choX1':  med([x[0][2] for x in dat]),
                'jungX0': med([x[1][0] for x in dat]),
                'jungW':  med([x[1][2] - x[1][0] for x in dat]),
                'n': len(dat), 'fam': fam,
                # VL·M은 중성 가로부가 초성 쪽에 붙기도 해 폭 수치가 흔들린다
                'firm': fam in ('VR', 'H')}
    rules['jungWidth'] = widths

    # 초성 세로 점유 등급 + 종성 압축 상관
    grade, heights, pairs, slopes = defaultdict(list), defaultdict(list), [], []
    for vi in range(21):
        if JUNG[vi] in HORZ: continue
        for ti in range(1, 28):
            dat = [(slots[(li, vi, ti)], li) for li in range(19) if (li, vi, ti) in slots]
            if len(dat) < 12: continue
            ch = [c[3] - c[1] for (c, _, _), _ in dat]
            jh = [j[3] - j[1] for (_, _, j), _ in dat]
            mc, sc = st.mean(ch), (st.pstdev(ch) or 1)
            mj, sj = st.mean(jh), (st.pstdev(jh) or 1)
            for (c, _, j), li in dat:
                grade[CHO[li]].append(((c[3] - c[1]) - mc) / sc)
                heights[CHO[li]].append(c[3] - c[1])
            pairs += [((a - mc) / sc, (b - mj) / sj) for a, b in zip(ch, jh)]
            den = sum((a - mc) ** 2 for a in ch)
            if den: slopes.append(sum((a - mc) * (b - mj) for a, b in zip(ch, jh)) / den)
    rules['choGrade'] = {k: {'z': round(st.mean(v), 2), 'medH': med(heights[k]),
                             'n': len(v)}
                         for k, v in sorted(grade.items(), key=lambda kv: -st.mean(kv[1]))}
    rules['choJong'] = {'r': round(sum(a * b for a, b in pairs) / len(pairs), 3),
                        'coef': round(st.median(slopes), 3), 'n': len(pairs),
                        'columns': len(slopes)}

    rules['leftDep'] = left_dependency(D)
    cj, jj = contact_matrices(D)
    rules['contactCho'], rules['contactJong'] = cj, jj
    per_fam = Counter(fam_of(JUNG[k[1]]) for k in slots)
    totals = {'VR': 5 * 19 * 28, 'VL': 4 * 19 * 28, 'H': 5 * 19 * 28, 'M': 7 * 19 * 28}
    rules['coverage'] = {f: {'ok': per_fam[f], 'total': totals[f]} for f in totals}
    return rules

# ── 5. 시각화용 글리프 SVG 추출 ─────────────────────────────────────────────
def build_glyphs(font, slots):
    gs = font.getGlyphSet(); cmap = font.getBestCmap()
    s = lambda l, v, t: syl(CHO.index(l), JUNG.index(v), JONG.index(t))
    sets = {
        'classes':    ['가', '각', '거', '걱', '고', '곡', '과', '관'],
        'choSeries':  [s(l, 'ㅏ', 'ㄼ') for l in CHO],
        'choSeriesH': [s(l, 'ㅏ', 'ㅎ') for l in CHO],
        'jongLadder': [s('ㄹ', 'ㅏ', t) for t in JONG],
        'jungSeries': [s('ㄹ', v, 'ㄱ') for v in JUNG],
        'contact':    ['노', '오', '도', '고', '구', '그', '기', '로', '모', '소', '자', '츄'],
        'leftVowel':  ['나', '너', '다', '더', '라', '러', '사', '서', '자', '저', '파', '퍼'],
        'demo':       ['낣', '랇'],
    }
    out = {}
    for ch in sorted({c for v in sets.values() for c in v}):
        pen = SVGPathPen(gs); gs[cmap[ord(ch)]].draw(pen)
        i = ord(ch) - 0xAC00; k = (i // 588, (i % 588) // 28, i % 28)
        e = {'p': pen.getCommands(), 'j': [CHO[k[0]], JUNG[k[1]], JONG[k[2]]]}
        if k in slots:
            c, m, j = slots[k]
            e['cho'] = [round(x) for x in c]; e['jung'] = [round(x) for x in m]
            if j: e['jong'] = [round(x) for x in j]
        out[ch] = e
    return {'sets': sets, 'glyphs': out}

def main(path):
    font = TTFont(path)
    print('폰트: %s  unitsPerEm=%d' % (os.path.basename(path), font['head'].unitsPerEm))
    D = extract(font); print('아웃라인 추출 %d자' % len(D))

    tight, loose = validated(D, 60), validated(D, 120)
    slots = dict(loose); slots.update(tight)          # 허용오차 60 우선, 실패분만 120
    print('분해 성공: 60→%d, 120→%d, 합집합 %d (%.1f%%)'
          % (len(tight), len(loose), len(slots), 100 * len(slots) / 11172))
    horz = decompose_horz(D)
    for k, v in horz.items(): slots.setdefault(k, v)
    print('가로모임 포함 총 %d자 (%.1f%%)' % (len(slots), 100 * len(slots) / 11172))

    rules = build_rules(font, D, slots)
    rules['font'] = os.path.basename(path)
    json.dump(rules, open(os.path.join(OUT, 'rules.json'), 'w'),
              ensure_ascii=False, indent=1)
    json.dump(build_glyphs(font, slots), open(os.path.join(OUT, 'glyphs.json'), 'w'),
              ensure_ascii=False, separators=(',', ':'))
    print('rules.json / glyphs.json 생성 완료')
    print('  종성 사다리: ' + '  '.join('%s %d' % (k, v['h'])
                                        for k, v in rules['jongLadder'].items()))
    print('  초성↔종성 상관 r=%(r)s  회귀계수 %(coef)s  n=%(n)d' % rules['choJong'])

if __name__ == '__main__':
    if len(sys.argv) != 2: sys.exit(__doc__)
    main(sys.argv[1])
