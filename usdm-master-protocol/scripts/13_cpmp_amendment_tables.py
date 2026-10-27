"""CPMP: the Protocol Amendment Summary of Changes tables, cell by cell.

Every amended CPMP document (master + 10 ISAs) has a summary-of-changes table
before its TOC; NP03 also has the table of its earlier amendment (a) in
Appendix 5 "Protocol Amendment History". This script reads those tables into
cells and change rows. It types nothing: text comes from the PDF text layer,
with word boundaries from output_cpmp/step2/page_text.csv (script 10), and is
checked cell by cell against OCR of the rendered page.

Table pages: pages whose text has both the column header "Section # and Name"
and "Brief Rationale" (letters only, spaces ignored).

Geometry (page rendered at SCALE x 72 dpi, dark = gray < DARK):
- Column starts from the header line: x of "Section", "Description", "Brief".
- Table body: from the first horizontal rule below the header line to the
  lowest horizontal rule of at least half the table width.
- Horizontal rules per column: a run of dark pixel rows covering >= 95% of the
  column width, at most RULE_MAX pt high. Taller dark runs are redaction bars.
- Style: "grid" if a vertical rule is found at the Description column start,
  else "open" (newer template: rules between section groups only).
- Cells: per column, the text between two rules of that column.
- Change rows: within a section group (column 1 cell), split at every rule of
  column 2 or 3. In the open style a group has no inner rules; it is split at
  each rationale paragraph start (a column 3 line with a gap above it of more
  than PARA_GAP x line height, or the group's first column 3 line).
- Table bottom: the lowest rule, or the last text line above the page footer
  (page number, "Approved on ...", "CCI" stamp) when the table runs on.
- Continuation page, first row at the top of the body:
  - section text only (description and rationale empty): continues the section
    name of the previous page's last row (`section_continued_on_pN`);
  - empty section, description and rationale both starting with a capital
    letter: a new row in the previous page's last section group
    (`section_from_previous_page`);
  - empty section otherwise: continues the previous page's last row
    (`continued_on_pN`).
- Redaction bars: their top and bottom are rules of the columns they cover; a
  row with no text inside a bar is `empty_row_redacted`.
- Markup: thin dark runs inside a text line, at least MARK_MIN pt and less than
  90% of the column width, not on a rule: strike-through (middle of the line)
  or underline (below it); the text-layer letters under them are reported.
  Where the text layer gives zero-height boxes (letter-spaced pages), the line
  box is taken as 0.55 x the line pitch above the baseline.

Checks:
- Every text-layer letter of the page equals the page_text.csv letters (asserted).
- OCR (tesseract, psm 6) per cell: alnum letters counted in both; a cell with
  OCR_EXTRA or more and OCR_RATIO times the text-layer letters is flagged
  `text_layer_short` (rendered text not in the text layer). For the change rows
  over such a cell, `<column>_ocr` holds the OCR text before the point where the
  text-layer text starts, followed by the text-layer text (`prefix`), or the
  OCR text alone where the text layer has none (`all`).

Outputs (output_cpmp/step4/):
- amendment_cells.csv: one row per cell, with bbox, text-layer text, OCR text, flags.
- amendment_changes.csv: one row per change row (doc, amendment, page, row,
  section as printed, description, rationale, status flags).
- amendment_redactions.csv: redaction bars inside table bodies.
- amendment_headers.csv: per amendment, the "Amendment" heading, Document
  History text and Overall Rationale text (from page_text.csv), and the number
  of redaction bars between the "Overall Rationale" line and the table header.

Needs: pypdfium2, numpy, pandas, tesseract on the PATH.
Run:   python3 scripts/13_cpmp_amendment_tables.py
"""
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pypdfium2 as pdfium

BASE = Path(__file__).resolve().parent.parent
PDF_DIR = BASE / "sources" / "pdf"
STEP2 = BASE / "output_cpmp" / "step2"
OUT_DIR = BASE / "output_cpmp" / "step4"
SCALE = 3
DARK = 100
RULE_MAX = 2.5   # pt
PARA_GAP = 1.6   # x median line pitch
OCR_EXTRA = 5
OCR_RATIO = 1.15   # a cell is text_layer_short if OCR has >= OCR_EXTRA and >= OCR_RATIO x the text-layer letters
LINE_TOL = 4.5     # pt, chars sorted by vertical mid: a gap of less than this to the previous char keeps the line
OCR_DPI = 300
MARK_MIN = 12    # pt, shortest strike-through or underline run


def letters_only(text):
    return re.sub(r"\s+", "", text)


def page_chars(pdf_page, page_text):
    """Text-layer letters with bbox (top-left origin, pt) and the separator after each letter from page_text."""
    tp = pdf_page.get_textpage()
    _, height = pdf_page.get_size()
    chars = []
    for i in range(tp.count_chars()):
        c = tp.get_text_range(i, 1).replace("\r", "").replace("￾", "-")
        if not c or c.isspace():
            continue
        assert len(c) == 1, (i, c)
        left, bottom, right, top = tp.get_charbox(i)
        chars.append({"c": c, "x0": left, "x1": right, "y0": height - top, "y1": height - bottom})
    seps = []
    k = 0
    for j, c in enumerate(page_text):
        if c.isspace():
            continue
        assert k < len(chars) and chars[k]["c"] == c, f"page_text letter {k} '{c}' != text layer '{chars[k]['c'] if k < len(chars) else None}'"
        nxt = page_text[j + 1] if j + 1 < len(page_text) else ""
        chars[k]["sep"] = " " if nxt.isspace() else ""
        k += 1
    assert k == len(chars), f"page_text has {k} letters, text layer {len(chars)}"
    for i, ch in enumerate(chars):
        ch["i"] = i
    return chars


def dark_image(pdf_page):
    gray = np.asarray(pdf_page.render(scale=SCALE).to_pil().convert("L"))
    return gray < DARK


def runs(mask):
    """(start, end) of runs of True in a 1-d bool array, end exclusive."""
    d = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def horizontal_bands(dark, x0, x1, y0, y1, cover=0.95):
    """Dark bands (pt) covering >= cover of [x0, x1] between y0 and y1 (pt)."""
    px0, px1, py0, py1 = int(x0 * SCALE) + 2, int(x1 * SCALE) - 2, int(y0 * SCALE), int(y1 * SCALE)
    frac = dark[py0:py1, px0:px1].mean(axis=1)
    return [((py0 + a) / SCALE, (py0 + b) / SCALE) for a, b in runs(frac >= cover)]


def text_of(chars):
    """Chars in stream order, lines by y; space where page_text has one or the stream is not contiguous."""
    chars = sorted(chars, key=lambda ch: ch["i"])
    out = []
    for n, ch in enumerate(chars):
        out.append(ch["c"])
        if n + 1 < len(chars):
            nxt = chars[n + 1]
            if ch["sep"] or nxt["i"] != ch["i"] + 1:
                out.append(" ")
    return "".join(out)


def lines_of(chars):
    """Group chars into lines by vertical overlap; returns list of (top, bottom, chars) by top."""
    lines = []
    for ch in sorted(chars, key=lambda ch: (ch["y0"] + ch["y1"]) / 2):
        mid = (ch["y0"] + ch["y1"]) / 2
        if lines and mid - lines[-1]["mid"] < LINE_TOL:
            lines[-1]["mid"] = mid
            lines[-1]["chars"].append(ch)
            lines[-1]["top"] = min(lines[-1]["top"], ch["y0"])
            lines[-1]["bottom"] = max(lines[-1]["bottom"], ch["y1"])
        else:
            lines.append({"mid": mid, "top": ch["y0"], "bottom": ch["y1"], "chars": [ch]})
    return lines


def ocr_box(pdf_page, box):
    x0, y0, x1, y1 = box
    scale = OCR_DPI / 72
    image = pdf_page.render(scale=scale, crop=(x0, pdf_page.get_size()[1] - y1, pdf_page.get_size()[0] - x1, y0)).to_pil()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "cell.png"
        image.save(png)
        result = subprocess.run(["tesseract", str(png), "stdout", "-l", "eng", "--psm", "6"],
                                check=True, capture_output=True, text=True)
    return re.sub(r"\s+", " ", result.stdout).strip()


def ocr_prefix(ocr, layer):
    """OCR text before the point where the text-layer text starts, plus the text-layer text.

    Only the part the text layer lacks comes from OCR. The start is found by matching the first
    15 letters/digits of the text layer in the OCR letters; if the text layer is empty, the OCR text is returned."""
    if not layer:
        return ocr, "all"
    key = "".join(ch for ch in layer if ch.isalnum())[:15]
    pos = [i for i, ch in enumerate(ocr) if ch.isalnum()]
    letters = "".join(ocr[i] for i in pos)
    k = letters.find(key)
    assert k > 0, f"text-layer start not found in OCR: {layer[:40]!r} / {ocr[:80]!r}"
    return ocr[:pos[k]].strip() + " " + layer, "prefix"


def bars_between(pdf_page, chars, y_from, y_to):
    """Redaction bars (dark runs >= 30 pt wide and > RULE_MAX pt high) between two y positions (pt)."""
    dark = dark_image(pdf_page)
    found = []
    for py in range(int(y_from * SCALE), int(y_to * SCALE)):
        for a, b in runs(dark[py]):
            if (b - a) / SCALE >= 30:
                found.append((py, a, b))
    bands = []
    for py, a, b in found:
        if bands and py - bands[-1]["y1"] <= 1 and a < bands[-1]["x1"] and b > bands[-1]["x0"]:
            bands[-1].update(y1=py, x0=min(a, bands[-1]["x0"]), x1=max(b, bands[-1]["x1"]))
        else:
            bands.append({"y0": py, "y1": py, "x0": a, "x1": b})
    return [(round(b["x0"] / SCALE, 1), round(b["y0"] / SCALE, 1), round(b["x1"] / SCALE, 1), round((b["y1"] + 1) / SCALE, 1))
            for b in bands if (b["y1"] + 1 - b["y0"]) / SCALE > RULE_MAX]


def find_header(chars):
    """The line holding 'Description of Change' and 'Brief Rational', and the x of the three column starts."""
    for line in lines_of(chars):
        seq = sorted(line["chars"], key=lambda ch: ch["x0"])
        s = "".join(ch["c"] for ch in seq)
        if "DescriptionofChange" in s and "BriefRational" in s:
            desc_x = seq[s.index("Description")]["x0"]
            brief_x = seq[s.index("Brief")]["x0"]
            sec = [ch for ch in chars if abs(ch["y0"] - line["top"]) < 3 and ch["x0"] < desc_x]
            sec_s = "".join(ch["c"] for ch in sorted(sec, key=lambda ch: ch["x0"]))
            assert sec_s.startswith("Section"), sec_s
            return {"top": line["top"], "bottom": line["bottom"], "sec_x": min(ch["x0"] for ch in sec),
                    "desc_x": desc_x, "brief_x": brief_x}
    raise AssertionError("header line not found")


def read_page(pdf_page, page_text):
    chars = page_chars(pdf_page, page_text)
    dark = dark_image(pdf_page)
    width, height = pdf_page.get_size()
    hdr = find_header(chars)
    # Rules spanning at least half the table width, below the header top.
    span_x0, span_x1 = hdr["sec_x"], hdr["brief_x"] + 0.5 * (hdr["brief_x"] - hdr["desc_x"])
    wide = [b for b in horizontal_bands(dark, span_x0, span_x1, hdr["top"], height - 20)
            if b[1] - b[0] <= RULE_MAX]
    assert len(wide) >= 2, f"table rules not found: {wide}"
    body_top = min(b[1] for b in wide if b[0] > hdr["top"])
    # A table that runs on to the next page has no bottom rule: the last text line above the footer counts too.
    # Footer lines: page number, "Approved on ...", a "CCI" stamp.
    below = [ln for ln in lines_of([ch for ch in chars if ch["y0"] > body_top and hdr["sec_x"] - 10 <= ch["x0"] <= width - 50])]
    footer = lambda ln: re.fullmatch(r"\d+|Approvedon.*|CCI", "".join(ch["c"] for ch in sorted(ln["chars"], key=lambda ch: ch["x0"])))
    text_bottom = max((ln["bottom"] for ln in below if not footer(ln)), default=0)
    body_bottom = max(max(b[0] for b in wide), text_bottom + 1)
    # Table left/right from the dark run on the body-top rule row.
    row = dark[int((body_top - 0.5) * SCALE)]
    run = max(runs(row), key=lambda r: r[1] - r[0])
    left, right = run[0] / SCALE, run[1] / SCALE
    cols = [(left, hdr["desc_x"] - 3), (hdr["desc_x"] - 3, hdr["brief_x"] - 3), (hdr["brief_x"] - 3, right)]
    # Style: vertical rule just left of the Description column start.
    vx0, vx1 = int((hdr["desc_x"] - 8) * SCALE), int(hdr["desc_x"] * SCALE)
    vfrac = dark[int(body_top * SCALE):int(body_bottom * SCALE), vx0:vx1].mean(axis=0)
    style = "grid" if vfrac.max() >= 0.8 else "open"
    # Rules and redaction bars per column.
    col_rules, bars = [], []
    for x0, x1 in cols:
        bands = horizontal_bands(dark, x0, x1, body_top - 1, body_bottom + 1)
        col_rules.append(sorted({round(b[0], 1) for b in bands if b[1] - b[0] <= RULE_MAX} | {round(body_top, 1), round(body_bottom, 1)}))
        bars.extend((x0, b[0], x1, b[1]) for b in bands if b[1] - b[0] > RULE_MAX)
    # One region per bar: y band from the column test, x extent from the dark run on its middle row.
    regions = []
    for x0, y0, x1, y1 in sorted(bars, key=lambda b: (round(b[1]), b[0])):
        if any(abs(r[1] - y0) < 1 and abs(r[3] - y1) < 1 for r in regions):
            continue
        mid = dark[int((y0 + y1) / 2 * SCALE)]
        a, b = max((r for r in runs(mid) if r[0] / SCALE <= x1 and r[1] / SCALE >= x0), key=lambda r: r[1] - r[0])
        regions.append((a / SCALE, y0, b / SCALE, y1))
    for k, (x0, x1) in enumerate(cols):
        for rx0, ry0, rx1, ry1 in regions:
            if rx0 < x1 - 1 and rx1 > x0 + 1:
                col_rules[k] = sorted(set(col_rules[k]) | {round(ry0, 1), round(ry1, 1)})
    in_bar = lambda ch: any(x0 <= (ch["x0"] + ch["x1"]) / 2 <= x1 and y0 <= (ch["y0"] + ch["y1"]) / 2 <= y1 for x0, y0, x1, y1 in regions)
    body = [ch for ch in chars if body_top < (ch["y0"] + ch["y1"]) / 2 < body_bottom
            and left <= (ch["x0"] + ch["x1"]) / 2 <= right]
    redaction_marks = [ch for ch in body if in_bar(ch)]
    body = [ch for ch in body if not in_bar(ch)]
    col_chars = [[ch for ch in body if c0 <= (ch["x0"] + ch["x1"]) / 2 < c1] for c0, c1 in cols]
    cells = []
    for k, ((x0, x1), rules, cc) in enumerate(zip(cols, col_rules, col_chars)):
        for y0, y1 in zip(rules[:-1], rules[1:]):
            inside = [ch for ch in cc if y0 < (ch["y0"] + ch["y1"]) / 2 < y1]
            if y1 - y0 < 4 and not inside:
                continue
            cells.append({"col": k + 1, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "chars": inside})
    desc_lines = lines_of(col_chars[1])
    pitch = float(np.median([b["top"] - a["top"] for a, b in zip(desc_lines[:-1], desc_lines[1:])]))
    return {"pitch": pitch, "dark": dark, "hdr": hdr, "style": style, "cols": cols, "col_rules": col_rules, "regions": regions,
            "redaction_marks": text_of(redaction_marks) if redaction_marks else "",
            "cells": cells, "col_chars": col_chars, "body_top": body_top, "body_bottom": body_bottom}


def markup(pg, chars, x0, x1):
    """Struck-through and underlined text: thin dark runs of at least MARK_MIN pt inside a text line.

    Position in the line box (top 0, bottom 1): 0.3-0.75 strike-through, below 0.85 underline.
    Returns the text-layer letters under each run, runs joined by ' | '."""
    dark = pg["dark"]
    rules = sorted({y for rs in pg["col_rules"] for y in rs})
    struck, under = [], []
    for ln in lines_of(chars):
        top, bottom = ln["top"], ln["bottom"]
        if bottom - top < 2:
            # Letter-spaced pages: the text layer gives zero-height boxes at the baseline.
            top = bottom - 0.55 * pg["pitch"]
        found = {"strike": [], "under": []}
        for py in range(int(top * SCALE), int((bottom + 2) * SCALE)):
            if any(abs(py / SCALE - y) <= 1.2 for y in rules):
                continue
            rel = (py / SCALE - top) / (bottom - top)
            kind = "strike" if 0.25 <= rel <= 0.8 else "under" if rel > 0.85 else None
            if kind is None:
                continue
            for a, b in runs(dark[py, int(x0 * SCALE):int(x1 * SCALE)]):
                if MARK_MIN <= (b - a) / SCALE < 0.9 * (x1 - x0):
                    found[kind].append((x0 + a / SCALE, x0 + b / SCALE))
        for kind, spans in found.items():
            merged = []
            for a, b in sorted(spans):
                if merged and a <= merged[-1][1] + 3:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], b))
                else:
                    merged.append((a, b))
            for ra, rb in merged:
                under_run = [ch for ch in ln["chars"] if ra - 1 <= (ch["x0"] + ch["x1"]) / 2 <= rb + 1]
                if under_run:
                    (struck if kind == "strike" else under).append(text_of(under_run))
    dedup = lambda xs: " | ".join(dict.fromkeys(xs))
    return dedup(struck), dedup(under)


def split_rows(pg):
    """Change rows of one page: list of dicts with y0, y1, section/desc/rationale chars."""
    groups = [c for c in pg["cells"] if c["col"] == 1]
    inner = sorted(set(pg["col_rules"][1]) | set(pg["col_rules"][2]))
    rows = []
    for g in groups:
        cuts = [y for y in inner if g["y0"] + 0.5 < y < g["y1"] - 0.5]
        if pg["style"] == "open" and not cuts:
            rat = [ln for ln in lines_of([ch for ch in pg["col_chars"][2] if g["y0"] < (ch["y0"] + ch["y1"]) / 2 < g["y1"]])]
            if len(rat) > 1:
                pitch = pg["pitch"]
                cuts = [b["top"] - 2 for a, b in zip(rat[:-1], rat[1:]) if b["top"] - a["top"] > PARA_GAP * pitch]
        bounds = [g["y0"]] + cuts + [g["y1"]]
        for y0, y1 in zip(bounds[:-1], bounds[1:]):
            pick = lambda k: [ch for ch in pg["col_chars"][k] if y0 < (ch["y0"] + ch["y1"]) / 2 < y1]
            bar = any(not (r[3] <= y0 or r[1] >= y1) for r in pg["regions"])
            rows.append({"y0": y0, "y1": y1, "group_y0": g["y0"], "section": g["chars"], "desc": pick(1), "rat": pick(2),
                         "first_in_group": y0 == g["y0"], "redaction": bar})
    return rows


def main():
    pt = pd.read_csv(STEP2 / "page_text.csv").fillna({"text": ""})
    pt["doc"] = pt.sponsor_protocol_no.str.replace("H0P-MC-", "", regex=False)
    flat = pt.text.map(letters_only)
    table_pages = pt[flat.str.contains("Section#andName") & flat.str.contains("BriefRational")]

    cell_rows, change_rows, redaction_rows, header_rows = [], [], [], []
    for doc, pages in table_pages.groupby("doc", sort=False):
        file = pages.file.iloc[0]
        pdf = pdfium.PdfDocument(str(PDF_DIR / file))
        doc_pages = pt[pt.doc == doc].set_index("page")
        # Amendments: a table starts on a page with "Overall Rationale for the Amendment".
        amendment = None
        previous = None
        for n in sorted(pages.page):
            text = doc_pages.loc[n, "text"]
            start = re.search(r"Overall\s*Rationale\s*for\s*the\s*Amendment", text)
            if start:
                heads = list(re.finditer(r"Amendment\s*[\[(]?\s*([a-z])\s*[\])]?(?=\s)", text[:start.start()]))
                assert heads, f"{doc} p{n}: amendment heading not found"
                amendment = heads[-1].group(1)
                hist = re.search(r"DOCUMENT\s*HISTORY(.*?)Amendment\s*[\[(]?\s*" + amendment, text, re.S)
                rat = re.search(r"Overall\s*Rationale\s*for\s*the\s*Amendment\s*:\s*(.*?)\n\s*Section\s*#\s*and", text, re.S)
                assert rat, f"{doc} p{n}: overall rationale not delimited"
                page_chars_ = page_chars(pdf[n - 1], text)
                seq = "".join(ch["c"] for ch in page_chars_)
                k = seq.index("OverallRationalefortheAmendment")
                rationale_bars = bars_between(pdf[n - 1], page_chars_, page_chars_[k]["y1"], find_header(page_chars_)["top"] - 1)
                header_rows.append({"doc": doc, "file": file, "amendment": amendment, "page": n,
                                    "redaction_bars_in_rationale": len(rationale_bars),
                                    "heading": re.sub(r"\s+", " ", text[heads[-1].start():start.start()]).strip(),
                                    "document_history": re.sub(r"\s+", " ", hist.group(1)).strip() if hist else "",
                                    "overall_rationale": rat.group(1).strip()})
                previous = None
            assert amendment, f"{doc} p{n}: table page before any amendment start"
            pdf_page = pdf[n - 1]
            pg = read_page(pdf_page, text)
            for x0, y0, x1, y1 in pg["regions"]:
                redaction_rows.append({"doc": doc, "amendment": amendment, "page": n, "x0": round(x0, 1), "y0": round(y0, 1),
                                       "x1": round(x1, 1), "y1": round(y1, 1),
                                       "columns": ";".join(str(k + 1) for k, (c0, c1) in enumerate(pg["cols"]) if x0 < c1 - 1 and x1 > c0 + 1)})
            for c in pg["cells"]:
                layer = text_of(c["chars"]) if c["chars"] else ""
                ocr = ocr_box(pdf_page, (c["x0"] + 1, c["y0"] + 0.5, c["x1"] - 1, c["y1"] - 0.5)) if c["y1"] - c["y0"] > 4 else ""
                n_layer = sum(ch.isalnum() for ch in layer)
                n_ocr = sum(ch.isalnum() for ch in ocr)
                cell_rows.append({"doc": doc, "amendment": amendment, "page": n, "style": pg["style"], "col": c["col"],
                                  "x0": round(c["x0"], 1), "y0": round(c["y0"], 1), "x1": round(c["x1"], 1), "y1": round(c["y1"], 1),
                                  "layer_text": layer, "ocr_text": ocr, "layer_letters": n_layer, "ocr_letters": n_ocr,
                                  "text_layer_short": n_ocr - n_layer >= OCR_EXTRA and n_ocr >= OCR_RATIO * n_layer})
            short = [c for c, row in zip(pg["cells"], cell_rows[-len(pg["cells"]):]) if row["text_layer_short"]]
            for r in split_rows(pg):
                sec, desc, rat = (text_of(r[k]) if r[k] else "" for k in ("section", "desc", "rat"))
                rec = {"doc": doc, "file": file, "amendment": amendment, "page": n, "style": pg["style"],
                       "y0": round(r["y0"], 1), "y1": round(r["y1"], 1), "section_as_printed": sec,
                       "description": desc, "rationale": rat, "redaction_in_row": r["redaction"], "status": "",
                       "text_layer_short": "", "section_ocr": "", "description_ocr": "", "rationale_ocr": ""}
                for k, key in ((1, "section"), (2, "description"), (3, "rationale")):
                    x0, x1 = pg["cols"][k - 1]
                    if any(c["col"] == k and c["y0"] < r["y1"] - 1 and c["y1"] > r["y0"] + 1 for c in short):
                        layer_text = {"section": sec, "description": desc, "rationale": rat}[key]
                        ocr_text = ocr_box(pdf_page, (x0 + 1, r["y0"] + 0.5, x1 - 1, r["y1"] - 0.5))
                        rec[key + "_ocr"], part = ocr_prefix(ocr_text, layer_text)
                        rec["text_layer_short"] = ";".join(filter(None, [rec["text_layer_short"], f"{key}:{part}"]))
                rec["description_struck"], rec["description_underlined"] = markup(pg, r["desc"], *pg["cols"][1])
                rec["rationale_struck"], rec["rationale_underlined"] = markup(pg, r["rat"], *pg["cols"][2])
                if not (sec or desc or rat):
                    rec["status"] = "empty_row_redacted" if r["redaction"] else "empty_row"
                    change_rows.append(rec)
                    continue
                at_top = abs(r["group_y0"] - pg["body_top"]) < 1 and previous is not None
                if at_top and sec and r["first_in_group"] and not desc and not rat:
                    previous["section_as_printed"] = previous["section_as_printed"] + " " + sec
                    previous["status"] = ";".join(filter(None, [previous["status"], f"section_continued_on_p{n}"]))
                    continue
                if not sec and at_top:
                    starts_new = bool(desc) and bool(rat) and desc[0].isupper() and rat[0].isupper()
                    if r["first_in_group"] and not starts_new:
                        for key, val in (("description", desc), ("rationale", rat)):
                            if val:
                                previous[key] = (previous[key] + " " + val).strip()
                        previous["status"] = ";".join(filter(None, [previous["status"], f"continued_on_p{n}"]))
                        previous["y1_next_page"] = round(r["y1"], 1)
                        continue
                    rec["section_as_printed"] = previous["section_as_printed"]
                    rec["status"] = "section_from_previous_page"
                elif not sec and not r["first_in_group"]:
                    raise AssertionError(f"{doc} p{n}: row in a group with empty section cell")
                elif not r["first_in_group"]:
                    rec["status"] = "section_from_merged_cell"
                change_rows.append(rec)
                previous = rec
        pdf.close()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cells = pd.DataFrame(cell_rows)
    changes = pd.DataFrame(change_rows)
    changes.insert(3, "row", changes.groupby(["doc", "amendment"]).cumcount() + 1)
    cells.to_csv(OUT_DIR / "amendment_cells.csv", index=False)
    changes.to_csv(OUT_DIR / "amendment_changes.csv", index=False)
    pd.DataFrame(redaction_rows, columns=["doc", "amendment", "page", "x0", "y0", "x1", "y1", "columns"]).to_csv(OUT_DIR / "amendment_redactions.csv", index=False)
    pd.DataFrame(header_rows).to_csv(OUT_DIR / "amendment_headers.csv", index=False)
    print("amendments:", len(header_rows), "| table pages:", len(table_pages), "| cells:", len(cells),
          "| change rows:", len(changes), "| redaction bars:", len(redaction_rows))
    print("text_layer_short cells:", int(cells.text_layer_short.sum()))
    print(changes.groupby(["doc", "amendment"]).size().to_string())


if __name__ == "__main__":
    main()
