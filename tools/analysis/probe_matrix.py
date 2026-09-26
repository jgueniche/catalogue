"""Phase-1 analysis probe for the compatibility matrix (pages 30-34). NOT the parser."""
import collections
import json
import re

import pdfplumber

import os
import sys

# Usage: python tools/analysis/probe_matrix.py [pdf] [out_dir]
PDF = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TARIF_PDF", "data/sources/Price_list-CISMEA-EURO_AUG2026_A0.pdf")
SP = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("ANALYSIS_OUT", "data/analysis")
os.makedirs(SP, exist_ok=True)
CHECK = ""


def col(o):
    c = o.get("non_stroking_color")
    return tuple(round(x, 3) for x in c) if isinstance(c, (list, tuple)) else c


def header_columns(words, htop, hbot, x_min):
    """Cluster SemiBold 5.88 header words right of x_min into printer columns."""
    hw = [w for w in words if htop - 1 <= w["top"] <= hbot + 1 and "SemiBold" in w["fontname"]
          and abs(w["size"] - 5.88) < 0.05 and w["x0"] > x_min]
    # group into lines, then line-segments separated by gaps > 8pt
    segs = []
    lines = collections.defaultdict(list)
    for w in hw:
        lines[round(w["top"], 0)].append(w)
    for t, ws in lines.items():
        ws.sort(key=lambda w: w["x0"])
        cur = [ws[0]]
        for w in ws[1:]:
            if w["x0"] - cur[-1]["x1"] > 4:
                segs.append(cur)
                cur = [w]
            else:
                cur.append(w)
        segs.append(cur)
    segs = [{"top": s[0]["top"], "x0": s[0]["x0"], "x1": s[-1]["x1"], "cx": (s[0]["x0"] + s[-1]["x1"]) / 2,
             "text": " ".join(w["text"] for w in s)} for s in segs]
    # cluster segments by center x (tol 10)
    clusters = []
    for s in sorted(segs, key=lambda s: s["cx"]):
        if clusters and abs(clusters[-1][-1]["cx"] - s["cx"]) < 10:
            clusters[-1].append(s)
        else:
            clusters.append([s])
    cols = []
    for c in clusters:
        c.sort(key=lambda s: s["top"])
        cols.append({"label": " ".join(s["text"] for s in c), "cx": sum(s["cx"] for s in c) / len(c)})
    return cols


def main():
    tariff = json.load(open(f"{SP}/contexts_v2.json"))
    tariff_codes = sorted({c["code"].rstrip("*") for c in tariff if not c.get("empty")})
    out_rows, cols_ref, groups_ref, footnotes = [], None, None, []
    anomalies = []
    with pdfplumber.open(PDF) as pdf:
        for pno in range(30, 35):
            page = pdf.pages[pno - 1]
            words = page.extract_words(extra_attrs=["fontname", "size", "non_stroking_color"])
            chars = page.chars
            grey = [r for r in page.rects if col(r) == (0.906, 0.902, 0.902)]
            bars = [r for r in page.rects if col(r) == (0.137, 0.255, 0.392) and r["bottom"] - r["top"] > 5]
            rules = sorted({round((r["top"] + r["bottom"]) / 2, 2) for r in page.rects
                            if col(r) in ((0.0,), 0.0, (0,)) and r["bottom"] - r["top"] < 1 and r["x1"] - r["x0"] > 500})
            for hb in sorted(grey, key=lambda r: r["top"]):
                prints_w = [w for w in words if w["text"] == "Roll" and hb["top"] <= w["top"] <= hb["bottom"]]
                x_min = prints_w[0]["x1"] + 5 if prints_w else 330
                cols = header_columns(words, hb["top"], hb["bottom"], x_min)
                grp = [w for w in words if abs(w["size"] - 5.28) < 0.05 and hb["top"] - 1 <= w["top"] <= hb["bottom"]]
                glines = collections.defaultdict(list)
                for w in grp:
                    glines[round(w["top"], 0)].append(w)
                gsegs = []
                for t, ws in glines.items():
                    ws.sort(key=lambda w: w["x0"])
                    cur = [ws[0]]
                    for w in ws[1:]:
                        if w["x0"] - cur[-1]["x1"] > 8:
                            gsegs.append(cur); cur = [w]
                        else:
                            cur.append(w)
                    gsegs.append(cur)
                groups = [(" ".join(w["text"] for w in s), (s[0]["x0"] + s[-1]["x1"]) / 2) for s in gsegs]
                labels = [c["label"] for c in cols]
                if cols_ref is None:
                    cols_ref, groups_ref = labels, groups
                elif labels != cols_ref:
                    anomalies.append(("header differs", pno, labels))
                # table body: from header bottom to next grey header (or page end)
                nxt = min([r["top"] for r in grey if r["top"] > hb["bottom"]], default=page.height)
                # section bars inside
                sec_bars = [b for b in bars if hb["bottom"] - 1 <= b["top"] < nxt]
                body_rules = [y for y in rules if hb["bottom"] < y < nxt]
                section = None
                # rows = intervals between consecutive rules (first interval starts at section bar bottom)
                starts = []
                if sec_bars:
                    b = sorted(sec_bars, key=lambda b: b["top"])[0]
                    section = " ".join(w["text"] for w in words if b["top"] - 1 <= w["top"] <= b["bottom"] and col(w) in ((1.0,), 1.0, (1,)))
                    edges = [b["bottom"]] + body_rules
                else:
                    edges = body_rules
                last_text = max([c["bottom"] for c in chars if edges and edges[-1] < c["top"] < nxt and c["x0"] < 70 and col(c) == (0.863, 0.0, 0.078)], default=None)
                if last_text:
                    edges = edges + [last_text + 1]
                for i in range(len(edges) - 1):
                    y0, y1 = edges[i], edges[i + 1]
                    inrow = [c for c in chars if y0 < (c["top"] + c["bottom"]) / 2 < y1]
                    code = "".join(c["text"] for c in sorted([c for c in inrow if col(c) == (0.863, 0.0, 0.078) and c["x0"] < 70], key=lambda c: c["x0"])).strip()
                    desc = "".join(c["text"] for c in sorted([c for c in inrow if 70 <= c["x0"] < 250 and c["fontname"].endswith("Regular") or (70 <= c["x0"] < 250 and "Italic" in c["fontname"])], key=lambda c: (round(c["top"]), c["x0"]))).strip()
                    prints = "".join(c["text"] for c in sorted([c for c in inrow if 250 <= c["x0"] < x_min - 5], key=lambda c: (round(c["top"]), c["x0"]))).strip()
                    checks = [c for c in inrow if c["text"] == CHECK]
                    marks = [c for c in inrow if abs(c["size"] - 3.96) < 0.05 or abs(c["size"] - 4.2) < 0.05]
                    cells = collections.defaultdict(dict)
                    for ck in checks:
                        cx = (ck["x0"] + ck["x1"]) / 2
                        best = min(cols, key=lambda c: abs(c["cx"] - cx))
                        d = abs(best["cx"] - cx)
                        cells[best["label"]]["check"] = True
                        cells[best["label"]]["dx"] = round(d, 1)
                    # small text: footnote markers '(n)' and 'From S/N:' serials
                    small = collections.defaultdict(list)
                    for m in marks:
                        small[round(m["top"], 0)].append(m)
                    smalltxt = []
                    # merge the 2 lines of 'From S/N:' + serial by column, markers by line
                    for t, ms in small.items():
                        ms.sort(key=lambda m: m["x0"])
                        cur = [ms[0]]
                        for m in ms[1:]:
                            if m["x0"] - cur[-1]["x1"] > 3:
                                smalltxt.append(cur); cur = [m]
                            else:
                                cur.append(m)
                        smalltxt.append(cur)
                    for s in smalltxt:
                        txt = "".join(m["text"] for m in s).strip()
                        cx = (s[0]["x0"] + s[-1]["x1"]) / 2
                        if re.fullmatch(r"\(\d\)", txt):
                            # footnote marker: attach to nearest check on its left
                            left = [c for c in checks if c["x1"] <= s[0]["x0"] + 1]
                            if left:
                                ck = max(left, key=lambda c: c["x1"])
                                lab = min(cols, key=lambda c: abs(c["cx"] - (ck["x0"] + ck["x1"]) / 2))["label"]
                                cells[lab].setdefault("notes", []).append(txt)
                            else:
                                anomalies.append(("orphan marker", pno, code, txt))
                        else:
                            lab = min(cols, key=lambda c: abs(c["cx"] - cx))["label"]
                            cells[lab].setdefault("text", []).append(txt)
                    if not code and not desc:
                        continue
                    out_rows.append({"page": pno, "section": section, "code": code, "desc": desc, "prints": prints,
                                     "cells": {k: v for k, v in cells.items()}})
            # footnotes (size 4.68, starting with '(n)')
            fl = collections.defaultdict(list)
            last_rule = max(rules) if rules else 0
            for c in chars:
                if c["top"] > last_rule + 2 and c["top"] < 760:
                    fl[round(c["top"], 0)].append(c)
            for t, cs in sorted(fl.items()):
                cs.sort(key=lambda c: c["x0"])
                txt = "".join(c["text"] for c in cs).strip()
                if re.match(r"^\(\d\)", txt):
                    footnotes.append((pno, txt))
    json.dump({"columns": cols_ref, "groups": groups_ref, "rows": out_rows, "footnotes": footnotes, "anomalies": anomalies},
              open(f"{SP}/matrix_probe.json", "w"), indent=1)
    print("columns:", len(cols_ref), cols_ref)
    print("groups:", [(g, round(x, 1)) for g, x in groups_ref])
    print("footnotes:", sorted(set(footnotes)))
    print("anomalies:", anomalies)
    print("rows:", len(out_rows), "sections:", dict(collections.Counter(r["section"] for r in out_rows)))
    ncheck = sum(1 for r in out_rows for v in r["cells"].values() if v.get("check"))
    print("checks mapped:", ncheck, " max dx:", max(v.get("dx", 0) for r in out_rows for v in r["cells"].values()))
    # resolution against tariff
    exact, wild, missing = [], [], []
    for r in out_rows:
        code = r["code"]
        m = re.fullmatch(r"([A-Z0-9]+?)(x+)", code)
        if m:
            pref, n = m.group(1), len(m.group(2))
            hits = [c for c in tariff_codes if c.startswith(pref) and len(c) == len(code)]
            wild.append((code, hits))
        elif code in tariff_codes:
            exact.append(code)
        else:
            missing.append((code, r["desc"], r["page"]))
    print(f"\nexact matches: {len(exact)}")
    print("wildcards:")
    for code, hits in wild:
        print(f"   {code:14s} -> {hits}")
    print("absent from tariff (hors tarif):")
    for code, d, p in missing:
        near = [c for c in tariff_codes if len(c) == len(code) and sum(a != b for a, b in zip(c, code)) == 1]
        print(f"   p{p} {code:12s} {d[:60]:60s} near={near}")
    # rows without any compat
    print("rows with no check/serial:", [(r["page"], r["code"]) for r in out_rows if not r["cells"]])
    print("cells with text (serials etc.):")
    for r in out_rows:
        for k, v in r["cells"].items():
            if v.get("text") or v.get("notes"):
                print(f"   p{r['page']} {r['code']:12s} {k:40s} {v}")
    # golden checks
    def compat(code):
        for r in out_rows:
            if r["code"] == code:
                return [k for k, v in r["cells"].items()]
    for c in ("R5F002xxx", "R5F202xxxx", "RT4F010xxx", "ACL004", "RTCT107NAAA", "S10277", "R4F226NAAA"):
        print("GOLDEN", c, "->", compat(c))


if __name__ == "__main__":
    main()
