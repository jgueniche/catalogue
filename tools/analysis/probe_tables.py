"""Phase-1 analysis probe v2 (NOT the parser).

Tables are found from their header LABELS (SemiBold 'Product Code' ... 'LIST PRICE'),
columns from label positions confirmed by vertical rules, rows from horizontal rules.
Outputs a JSON of rows + stats used to write the phase-1 analysis note.
"""
import collections
import json
import re

import pdfplumber

import os
import sys

# Usage: python tools/analysis/probe_tables.py [pdf] [out_dir]
PDF = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TARIF_PDF", "data/sources/Price_list-CISMEA-EURO_AUG2026_A0.pdf")
SP = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("ANALYSIS_OUT", "data/analysis")
os.makedirs(SP, exist_ok=True)
CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9\-]*[A-Z0-9]\*?$")
PRICE_RE = re.compile(r"^\d{1,3}(?: \d{3})*$")


def is_red(obj):
    col = obj.get("non_stroking_color")
    return isinstance(col, (list, tuple)) and len(col) == 3 and col[0] > 0.8 and col[1] < 0.1 and col[2] < 0.2


def text_lines(chars, ytol=2.0):
    chars = sorted(chars, key=lambda c: (c["top"], c["x0"]))
    lines = []
    for c in chars:
        for ln in lines:
            if abs(ln["top"] - c["top"]) <= ytol:
                ln["chars"].append(c)
                break
        else:
            lines.append({"top": c["top"], "chars": [c]})
    out = []
    for ln in sorted(lines, key=lambda l: l["top"]):
        cs = sorted(ln["chars"], key=lambda c: c["x0"])
        out.append({"text": "".join(c["text"] for c in cs).strip(), "top": ln["top"],
                    "bottom": max(c["bottom"] for c in cs), "x0": cs[0]["x0"], "x1": cs[-1]["x1"]})
    return [l for l in out if l["text"]]


def find_headers(page):
    """Return list of header dicts: {top,bottom,cols:[(name,x0,x1)]} using SemiBold labels."""
    words = page.extract_words(extra_attrs=["fontname", "size"])
    sb = [w for w in words if "SemiBold" in w["fontname"] and 7 < w["size"] < 8]
    rows = collections.defaultdict(list)
    for w in sb:
        rows[round(w["top"])].append(w)
    headers = []
    for top, ws in sorted(rows.items()):
        txt = " ".join(w["text"] for w in sorted(ws, key=lambda w: w["x0"]))
        if "Product" in txt and "Code" in txt and "PRICE" in txt:
            headers.append({"top": min(w["top"] for w in ws), "bottom": max(w["bottom"] for w in ws), "words": ws})
    # attach 2-line labels (Standard / Packaging Qty) within +-8pt
    for h in headers:
        extra = [w for w in sb if abs(w["top"] - h["top"]) <= 8 and w not in h["words"]]
        h["words"] += extra
        h["top"] = min(w["top"] for w in h["words"])
        h["bottom"] = max(w["bottom"] for w in h["words"])
    return headers


def rules(page):
    hs, vs = [], []
    for r in page.rects:
        w, h = r["x1"] - r["x0"], r["bottom"] - r["top"]
        if h <= 1.0 and w > 20:
            hs.append(((r["top"] + r["bottom"]) / 2, r["x0"], r["x1"]))
        elif w <= 1.0 and h > 5:
            vs.append(((r["x0"] + r["x1"]) / 2, r["top"], r["bottom"]))
    return hs, vs


def analyze_page(pno, page):
    headers = find_headers(page)
    hs, vs = rules(page)
    chars = page.chars
    words = page.extract_words(extra_attrs=["fontname", "size", "non_stroking_color"])
    family = " ".join(w["text"] for w in sorted([w for w in words if round(w["size"], 2) == 16.32], key=lambda w: w["x0"]))
    sections = []
    secw = collections.defaultdict(list)
    for w in words:
        if is_red(w) and round(w["size"], 2) in (8.88, 9.6):
            secw[round(w["top"], 1)].append(w)
    for t, ws in sorted(secw.items()):
        sections.append((t, " ".join(x["text"] for x in sorted(ws, key=lambda x: x["x0"]))))
    tables = []
    for hi, h in enumerate(headers):
        limit = headers[hi + 1]["top"] if hi + 1 < len(headers) else page.height
        # section title above this header (closest red title above, but below previous table)
        # table x-extent: horizontal rules just below header
        cand = [r for r in hs if h["bottom"] - 1 <= r[0] <= h["bottom"] + 12]
        tx0 = min(r[1] for r in cand) if cand else None
        tx1 = max(r[2] for r in cand) if cand else None
        # vertical rules crossing the body (any start)
        vx = sorted({round(x, 1) for x, t, b in vs if t < h["bottom"] + 15 and b > h["bottom"] + 5 and tx0 - 2 <= x <= tx1 + 2})
        # label centers
        labs = []
        for key, pat in (("code", "Code"), ("desc", "Description"), ("price", "PRICE"), ("pack", "Qty")):
            ws = [w for w in h["words"] if w["text"] == pat]
            if ws:
                labs.append((key, (ws[0]["x0"] + ws[0]["x1"]) / 2))
        cols = {}
        for key, cx in labs:
            left = max([x for x in vx if x < cx], default=None)
            right = min([x for x in vx if x > cx], default=None)
            cols[key] = (left, right)
        # row rules
        hy = sorted({round(y, 2) for y, x0, x1 in hs if h["bottom"] - 2 <= y < limit and x1 >= tx1 - 3 and x0 <= tx0 + 80})
        # keep contiguous run of rules (stop at a gap > 60pt => end of table)
        run = [hy[0]] if hy else []
        for y in hy[1:]:
            if y - run[-1] > 80:
                break
            run.append(y)
        rows = []
        inner = [x for x in vx if tx0 + 5 < x < tx1 - 5]
        def spanned(y0, y1):
            return all(any(abs(vx_ - x) < 0.6 and t <= y0 + 1 and b >= y1 - 1 for vx_, t, b in vs) for x in inner)
        for i in range(len(run) - 1):
            y0, y1 = run[i], run[i + 1]
            if y1 - y0 < 4 or not spanned(y0, y1):
                continue
            row = {"page": pno, "y0": y0, "y1": y1}
            for key, (cx0, cx1) in cols.items():
                cc = [c for c in chars if cx0 < (c["x0"] + c["x1"]) / 2 < cx1 and y0 < (c["top"] + c["bottom"]) / 2 < y1]
                row[key] = text_lines(cc)
            fl = [c for c in chars if is_red(c) and c["x1"] < (tx0 or 0) and y0 < (c["top"] + c["bottom"]) / 2 < y1]
            row["flag"] = "".join(c["text"] for c in fl)
            rows.append(row)
        table_bottom = run[-1] if run else None
        tables.append({"header_top": h["top"], "tx0": tx0, "tx1": tx1, "cols": cols, "rows": rows, "bottom": table_bottom})
    return {"page": pno, "family": family, "sections": sections, "tables": tables}


def main():
    out = []
    with pdfplumber.open(PDF) as pdf:
        for pno in range(3, 30):
            out.append(analyze_page(pno, pdf.pages[pno - 1]))
    json.dump(out, open(f"{SP}/probe_v2.json", "w"), indent=1, default=str)

    # ---- flatten into contexts with family/section propagation
    fam, sec = None, None
    contexts, anomalies = [], []
    for pg in out:
        if pg["family"]:
            fam = pg["family"]
        for t in pg["tables"]:
            above = [s for s in pg["sections"] if s[0] < t["header_top"]]
            if above:
                sec = above[-1][1]
            for r in t["rows"]:
                code_lines = [l["text"] for l in r.get("code", [])]
                # join split codes: line ending with '-' => no space
                code = ""
                for l in code_lines:
                    code += l
                desc_lines = [l["text"] for l in r.get("desc", [])]
                price_txt = " ".join(l["text"] for l in r.get("price", []))
                pack_txt = " ".join(l["text"] for l in r.get("pack", []))
                if not code and not desc_lines and not price_txt:
                    contexts.append({"page": pg["page"], "empty": True})
                    continue
                contexts.append({"page": pg["page"], "family": fam, "section": sec, "code": code,
                                 "code_lines": code_lines, "desc": desc_lines, "price": price_txt,
                                 "pack": pack_txt, "flag": r["flag"], "y0": r["y0"], "y1": r["y1"]})
    json.dump(contexts, open(f"{SP}/contexts_v2.json", "w"), indent=1)

    rows = [c for c in contexts if not c.get("empty")]
    empties = [c for c in contexts if c.get("empty")]
    print(f"rows (contexts): {len(rows)}   empty separator rows: {len(empties)} on pages {sorted({c['page'] for c in empties})}")
    codes = collections.Counter(c["code"].rstrip("*") for c in rows)
    print(f"unique codes: {len(codes)}")
    print("per page rows:", dict(collections.Counter(c["page"] for c in rows)))
    bad_code = [c for c in rows if not CODE_RE.match(c["code"])]
    print("codes failing regex:", [(c["page"], c["code"]) for c in bad_code])
    split = [c for c in rows if len(c["code_lines"]) > 1]
    print("split codes:", [(c["page"], c["code_lines"], c["code"]) for c in split])
    star = [c for c in rows if c["code"].endswith("*")]
    print("codes with '*':", [(c["page"], c["code"]) for c in star])
    prices = collections.Counter("int" if PRICE_RE.match(c["price"]) else c["price"] for c in rows)
    print("price cell kinds:", dict(prices))
    packs = collections.Counter(c["pack"] for c in rows if c["pack"])
    print("packaging values:", dict(packs), " rows with pack col:", sum(1 for c in rows if c["pack"]))
    flags = collections.Counter(c["flag"] or "-" for c in rows)
    print("flags:", dict(flags))
    # duplicates with price divergence
    by = collections.defaultdict(list)
    for c in rows:
        by[c["code"].rstrip("*")].append(c)
    dup = {k: v for k, v in by.items() if len(v) > 1}
    print(f"codes appearing >1: {len(dup)}")
    div = {k: sorted({x['price'] for x in v}) for k, v in dup.items() if len({x['price'] for x in v}) > 1}
    print("PRICE DIVERGENCE:", div)
    fdiv = {k: [(x['page'], x['flag'] or '-') for x in v] for k, v in dup.items() if len({x['flag'] for x in v}) > 1}
    print(f"flag divergence ({len(fdiv)}):", fdiv)
    ddiv = {k: [(x['page'], ' / '.join(x['desc'])) for x in v] for k, v in dup.items() if len({' / '.join(x['desc']).replace('  ', ' ').strip() for x in v}) > 1}
    print(f"description divergence ({len(ddiv)}):")
    for k, v in ddiv.items():
        print("   ", k)
        for p, d in v:
            print("       p", p, ":", d[:160])
    fams = collections.Counter((c["family"]) for c in rows)
    print("families:", dict(fams))
    secs = collections.Counter((c["section"]) for c in rows)
    print("sections:", dict(secs))
    # notes inside descriptions
    pat = re.compile(r"(mounting plate: *(S\d+)|ref (A\d+)|minimum order quantity is (\d+)|contact us for availability|Not recommended for PVC|ERC|Supported on [^)]*only|order USB cable)", re.I)
    notes = collections.Counter()
    for c in rows:
        for l in c["desc"]:
            for m in pat.finditer(l):
                notes[m.group(1)[:40]] += 1
    print("embedded notes:", dict(notes))


if __name__ == "__main__":
    main()
