#!/usr/bin/env python3
"""page.template.html + rules.json + glyphs.json -> 자립형 index.html.

Noto Sans CJK KR을 페이지에 등장하는 글자로만 서브셋해 data URI로 인라인한다.
필요: pip install fonttools brotli
사용: python3 build.py /path/to/NotoSansCJKkr-Regular.otf /path/to/NotoSansCJKkr-Bold.otf
"""
import base64, io, os, sys
from fontTools.ttLib import TTFont
from fontTools import subset

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, os.pardir, "index.html")

def subset_woff2(src, unicodes):
    f = TTFont(src)
    o = subset.Options()
    o.flavor = "woff2"; o.desubroutinize = True
    o.layout_features = []; o.name_IDs = []; o.name_legacy = False
    o.notdef_outline = False; o.recalc_bounds = True
    o.glyph_names = False; o.legacy_kern = False; o.hinting = False
    o.drop_tables += ["DSIG"]
    s = subset.Subsetter(options=o); s.populate(unicodes=unicodes); s.subset(f)
    buf = io.BytesIO(); f.flavor = "woff2"; f.save(buf)
    data = buf.getvalue()
    print("  %-34s %6d bytes" % (os.path.basename(src), len(data)))
    return "data:font/woff2;base64," + base64.b64encode(data).decode()

def main(reg_otf, bold_otf):
    tpl    = open(os.path.join(HERE, "page.template.html"), encoding="utf-8").read()
    rules  = open(os.path.join(HERE, os.pardir, "rules.json"),  encoding="utf-8").read()
    glyphs = open(os.path.join(HERE, os.pardir, "glyphs.json"), encoding="utf-8").read()

    chars  = set(tpl) | set(rules) | set(glyphs)
    chars |= {chr(c) for c in range(0x3131, 0x3164)}          # 호환 자모
    chars |= set("0123456789.,%×−–—·()[]:/+↓←→●")
    unicodes = sorted(ord(c) for c in chars if ord(c) > 0x1F)
    print("서브셋 문자 %d자" % len(unicodes))

    html = (tpl.replace("__FONT_REGULAR__", subset_woff2(reg_otf,  unicodes))
               .replace("__FONT_BOLD__",    subset_woff2(bold_otf, unicodes))
               .replace("__RULES_JSON__",   rules.replace("</", "<\\/"))
               .replace("__GLYPHS_JSON__",  glyphs.replace("</", "<\\/")))
    for ph in ("__FONT_REGULAR__", "__FONT_BOLD__", "__RULES_JSON__", "__GLYPHS_JSON__"):
        assert ph not in html, "미치환 플레이스홀더: " + ph
    open(OUT, "w", encoding="utf-8").write(html)
    print("index.html %d bytes" % os.path.getsize(OUT))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
