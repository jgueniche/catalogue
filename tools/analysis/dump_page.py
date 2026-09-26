"""Usage: python tools/analysis/dump_page.py <out_dir> <page> [<page>...]

Dump pdfplumber words + chars (coords, fontname, size, colors) + graphics for given pages."""
import json, sys, collections
import pdfplumber

import os
PDF = os.environ.get("TARIF_PDF", "data/sources/Price_list-CISMEA-EURO_AUG2026_A0.pdf")
OUT = sys.argv[1]
pages = [int(p) for p in sys.argv[2:]]

def r(v): return round(v, 2) if isinstance(v, float) else v
def color(c):
    if c is None: return None
    if isinstance(c, (list, tuple)): return [round(x, 3) for x in c]
    return c

with pdfplumber.open(PDF) as pdf:
    for pno in pages:
        page = pdf.pages[pno - 1]
        words = page.extract_words(keep_blank_chars=False, use_text_flow=False,
                                   extra_attrs=["fontname", "size", "non_stroking_color"])
        chars = page.chars
        with open(f"{OUT}/p{pno:02d}_words.tsv", "w") as f:
            f.write("x0\tx1\ttop\tbottom\tfontname\tsize\tcolor\ttext\n")
            for w in words:
                f.write(f"{r(w['x0'])}\t{r(w['x1'])}\t{r(w['top'])}\t{r(w['bottom'])}\t{w['fontname']}\t{r(w['size'])}\t{color(w['non_stroking_color'])}\t{w['text']}\n")
        with open(f"{OUT}/p{pno:02d}_chars.tsv", "w") as f:
            f.write("x0\tx1\ttop\tbottom\tfontname\tsize\tncolor\tscolor\tcodepoint\ttext\n")
            for c in chars:
                f.write(f"{r(c['x0'])}\t{r(c['x1'])}\t{r(c['top'])}\t{r(c['bottom'])}\t{c['fontname']}\t{r(c['size'])}\t{color(c.get('non_stroking_color'))}\t{color(c.get('stroking_color'))}\tU+{ord(c['text'][0]):04X}\t{c['text']!r}\n")
        graphics = {
            "page": pno, "width": page.width, "height": page.height,
            "lines": [{k: r(l[k]) for k in ("x0","x1","top","bottom","linewidth")} | {"color": color(l.get("stroking_color"))} for l in page.lines],
            "rects": [{k: r(x[k]) for k in ("x0","x1","top","bottom")} | {"fill": color(x.get("non_stroking_color")), "stroke": color(x.get("stroking_color")), "filled": x.get("fill"), "stroked": x.get("stroke")} for x in page.rects],
            "curves": [{k: r(x[k]) for k in ("x0","x1","top","bottom")} | {"fill": color(x.get("non_stroking_color")), "npts": len(x.get("pts", []))} for x in page.curves],
            "images": [{k: r(x[k]) for k in ("x0","x1","top","bottom")} | {"name": x.get("name")} for x in page.images],
        }
        with open(f"{OUT}/p{pno:02d}_graphics.json", "w") as f:
            json.dump(graphics, f, indent=1)
        fonts = collections.Counter((c["fontname"], r(c["size"]), str(color(c.get("non_stroking_color")))) for c in chars)
        print(f"== page {pno}: {len(words)} words, {len(chars)} chars, {len(page.lines)} lines, {len(page.rects)} rects, {len(page.curves)} curves, {len(page.images)} images")
        for (fn, sz, col), n in fonts.most_common():
            print(f"   {n:5d}  {fn:40s} size={sz:<6} color={col}")
