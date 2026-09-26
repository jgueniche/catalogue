"""Render every page of a PDF to PNG (PyMuPDF) for visual review.

Usage: python tools/analysis/render_pages.py [pdf] [out_dir] [dpi]
"""
import os
import sys

import pymupdf

pdf = sys.argv[1] if len(sys.argv) > 1 else "data/sources/Price_list-CISMEA-EURO_AUG2026_A0.pdf"
out = sys.argv[2] if len(sys.argv) > 2 else "data/analysis/renders"
dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 150
os.makedirs(out, exist_ok=True)
doc = pymupdf.open(pdf)
for page in doc:
    page.get_pixmap(dpi=dpi).save(f"{out}/p{page.number + 1:02d}.png")
print(f"{doc.page_count} pages -> {out}")
