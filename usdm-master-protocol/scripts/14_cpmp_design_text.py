"""CPMP: design content of the 13 protocols, read from the page layout.

Part of Plan 1 on CPMP, Step 5 (design components across the ISA grid).
Reuses the text and geometry functions of scripts/13_cpmp_amendment_tables.py
(text layer with word spacing from page_text.csv, rendered page for rules and
redaction bars). Types nothing.

Eligibility (sections "Inclusion Criteria" and "Exclusion Criteria", up to the
next section heading):
- Lines from the text layer; running header (top 60 pt) and footer lines (page
  number, "Approved on ...", a "CCI" stamp) dropped.
- A line starting with "[digits]" starts a criterion. A following line further
  right than the criterion's bracket (or "OR" / "AND" alone; a bold line only
  if it starts at the criterion's text column) continues it; a gap
  of more than PARA_GAP pt starts a new paragraph inside the criterion (newline
  in `text`), e.g. CPMP [5] "Reproductive and contraceptive requirements will be
  specified in the ISAs." or the bullets and note of CPMP [21].
- Category headings nest by indent: a bold line further right than the last
  heading is a sub-heading ("Additional Considerations for Participants Taking
  Metformin: / Medical Conditions", NP03); `category` is the path.
- Section headings: bold lines starting with a section number, or equal to a
  section title of the document (OA03 prints no numbers). Other bold lines are category headings ("Medical
  Conditions"); consecutive bold lines are one heading. Bold: most letters in a
  font whose name contains "Bold". Four documents (BP02, NP02, OA02, OA05) carry
  their text layer in an invisible font ("CALS_InvisibleTTFont..."), so there
  bold is read from the rendered page: dark area per letter in the line box of
  at least BOLD_INK pt^2 (body text 9-13, headings 16-21 on the pages checked).
- Lines that are only "CCI" inside a redaction bar are dropped (the bar is the item).
- Other lines at the left margin are statements: the list intro ("Participants
  are excluded ...") or a statement in a category ("Age requirements for
  participation will be specified in the DSA and/or ISAs.").
- Redaction bars (rendered page, as in script 13) inside the region are items
  of their own, in reading order: hidden criteria cannot be counted.

Output: output_cpmp/step5/eligibility_items.csv, one row per criterion,
statement, heading or redaction bar, in document order.

Needs: pypdfium2, numpy, pandas (and script 13 next to this file).
Run:   python3 scripts/14_cpmp_design_text.py
"""
import ctypes
import importlib.util
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_raw

BASE = Path(__file__).resolve().parent.parent
STEP2 = BASE / "output_cpmp" / "step2"
OUT_DIR = BASE / "output_cpmp" / "step5"
_spec = importlib.util.spec_from_file_location("s13", Path(__file__).resolve().parent / "13_cpmp_amendment_tables.py")
s13 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(s13)

HEADER_MAX = 60     # pt from the top: running header
INK_SCALE = 4       # render scale for the ink measure
OPEN_GAP = 8        # pt: text closer than this below a table's last rule belongs to an open last row
COL_RULE = 0.65     # share of the table height a column rule covers
PARA_GAP = 6        # pt between lines: new paragraph inside a criterion
BOLD_INK = 14.5     # dark pt^2 per letter: bold threshold where the text layer is an invisible font
FOOTER = re.compile(r"\d+|Approvedon.*|CCI|-+")


def line_top(ln):
    """Top of a line box; letter-spaced pages give zero-height boxes at the baseline, taken as a 9 pt box."""
    return ln["top"] if ln["bottom"] - ln["top"] >= 2 else ln["bottom"] - 9


def chars_with_font(pdf_page, page_text):
    """script 13 page_chars, plus font name and size per letter (same order)."""
    chars = s13.page_chars(pdf_page, page_text)
    tp = pdf_page.get_textpage()
    fonts = []
    for i in range(tp.count_chars()):
        c = tp.get_text_range(i, 1).replace("\r", "").replace("￾", "-")
        if not c or c.isspace():
            continue
        buf, flags = ctypes.create_string_buffer(256), ctypes.c_int(0)
        pdfium_raw.FPDFText_GetFontInfo(tp.raw, i, buf, 256, ctypes.byref(flags))
        fonts.append((buf.value.decode("latin-1"), pdfium_raw.FPDFText_GetFontSize(tp.raw, i)))
    assert len(fonts) == len(chars)
    for ch, (name, sz) in zip(chars, fonts):
        ch["font"], ch["size"] = name, sz
    return chars


def page_lines(pdf_page, page_text, page_no):
    _, height = pdf_page.get_size()
    chars = chars_with_font(pdf_page, page_text)
    invisible = any("Invisible" in ch["font"] for ch in chars)
    ink = np.asarray(pdf_page.render(scale=INK_SCALE).to_pil().convert("L")) < 128 if invisible else None
    out = []
    for ln in s13.lines_of(chars):
        if ln["top"] < HEADER_MAX:
            continue
        seq = sorted(ln["chars"], key=lambda ch: ch["x0"])
        letters = "".join(ch["c"] for ch in seq)
        if ln["top"] > height - 80 and FOOTER.fullmatch(letters):
            continue
        body = [ch for ch in ln["chars"] if ch["c"].isalnum()] or ln["chars"]
        if invisible:
            y0, y1 = ln["top"], ln["bottom"]
            if y1 - y0 < 2:
                y0 = y1 - 7
            x0, x1 = min(ch["x0"] for ch in ln["chars"]), max(ch["x1"] for ch in ln["chars"])
            area = ink[int(y0 * INK_SCALE):int(y1 * INK_SCALE) + 1, int(x0 * INK_SCALE):int(x1 * INK_SCALE) + 1].sum()
            bold = area / INK_SCALE ** 2 / len(body) >= BOLD_INK
        else:
            bold = sum("Bold" in ch["font"] for ch in body) > len(body) / 2
        k = letters.find("]")
        text_x = seq[k + 1]["x0"] if 0 <= k < len(seq) - 1 else seq[0]["x0"]
        out.append({"page": page_no, "top": ln["top"], "bottom": ln["bottom"], "x0": seq[0]["x0"], "text_x": text_x,
                    "text": s13.text_of(ln["chars"]), "letters": letters, "bold": bold, "bold_by": "ink" if invisible else "font",
                    "size": max(ch["size"] for ch in body)})
    return out


def eligibility(doc, file, secs, pt_doc, pdf):
    secs = secs.reset_index(drop=True)
    first = secs.index[secs.title.str.contains("Inclusion Criteria", case=False)].min()
    last = secs.index[secs.title.str.contains("Exclusion Criteria", case=False)].max()
    nxt = secs.loc[last + 1]
    start_title = re.sub(r"\s+", "", secs.loc[first, "title"])
    end_title = re.sub(r"\s+", "", nxt.title)
    lines, bars = [], []
    for n in range(int(secs.loc[first, "start_page"]), int(nxt.start_page) + 1):
        pdf_page = pdf[n - 1]
        page_text = pt_doc.loc[n, "text"]
        lines.extend(page_lines(pdf_page, page_text, n))
        _, height = pdf_page.get_size()
        for x0, y0, x1, y1 in s13.bars_between(pdf_page, None, HEADER_MAX, height - 80):
            bars.append({"page": n, "top": y0, "bottom": y1, "x0": x0, "x1": x1})
    # Region: from the Inclusion Criteria heading line to the next section heading line.
    titles = {re.sub(r"\s+", "", t) for t in secs.title}
    is_heading = lambda ln: ln["bold"] and (bool(re.match(r"\d+(\.\d+)*\.?[A-Z]", ln["letters"]))
                                          or re.sub(r"^[\d.]+", "", ln["letters"]) in titles)
    i0 = [i for i, ln in enumerate(lines) if is_heading(ln) and ln["letters"].endswith(start_title)]
    assert i0, f"{doc}: heading '{start_title}' not found; headings: {[ln['letters'] for ln in lines if is_heading(ln)]}"
    i0 = i0[0]
    i1 = [i for i, ln in enumerate(lines) if i > i0 and is_heading(ln) and ln["letters"].endswith(end_title)]
    assert i1, f"{doc}: heading '{end_title}' not found; headings: {[ln['letters'] for ln in lines if is_heading(ln)]}"
    i1 = i1[0]
    region = lines[i0:i1]
    first_pos, last_pos = (region[0]["page"], region[0]["top"]), (lines[i1]["page"], lines[i1]["top"])
    bars = [b for b in bars if first_pos < (b["page"], b["top"]) < last_pos]
    # Merge bars and lines in reading order (page, top).
    stream = [("line", ln) for ln in region] + [("bar", b) for b in bars]
    stream.sort(key=lambda kv: (kv[1]["page"], kv[1]["top"]))
    items, kind, category, current, headings = [], "", "", None, []
    in_bar = lambda ln: any(b["page"] == ln["page"] and b["top"] - 1 <= ln["top"] <= b["bottom"] + 1 for b in bars)
    stream = [(w, ln) for w, ln in stream if not (w == "line" and ln["letters"] == "CCI" and in_bar(ln))]
    for what, ln in stream:
        if what == "bar":
            items.append({"doc": doc, "file": file, "kind": kind, "category": category, "item": "redaction", "number": "",
                          "text": "", "page": ln["page"], "top": round(ln["top"], 1)})
            current = None
            continue
        if is_heading(ln):
            kind = "inclusion" if "Inclusion" in ln["letters"] else "exclusion" if "Exclusion" in ln["letters"] else kind
            category, current, headings = "", None, []
            continue
        m = re.match(r"\[\s*(\d+)\s*\]\s*(.*)", ln["text"], re.S)
        if m:
            current = {"doc": doc, "file": file, "kind": kind, "category": category, "item": "criterion", "number": m.group(1),
                       "text": m.group(2), "page": ln["page"], "top": round(ln["top"], 1), "bracket_x": ln["x0"], "text_x": ln["text_x"],
                       "last": (ln["page"], ln["bottom"])}
            items.append(current)
            continue
        continues = (ln["letters"] in ("OR", "AND") or (not ln["bold"] and ln["x0"] > current["bracket_x"] + 2)
                     or (ln["bold"] and ln["x0"] >= current["text_x"] - 2)) if current is not None else False
        if continues:
            # Continuation of the criterion; a vertical gap starts a new paragraph inside it.
            gap = ln["page"] != current["last"][0] or line_top(ln) - current["last"][1] > PARA_GAP
            current["text"] += ("\n" if gap else " ") + ln["text"]
            current["last"] = (ln["page"], ln["bottom"])
            continue
        current = None
        if ln["bold"]:
            if items and items[-1]["item"] == "heading" and items[-1]["page"] == ln["page"] and ln["top"] - items[-1]["bottom"] < 4:
                items[-1]["text"] += " " + ln["text"]
                items[-1]["bottom"] = ln["bottom"]
                headings[-1] = (headings[-1][0], items[-1]["text"])
            else:
                while headings and ln["x0"] <= headings[-1][0] + 10:
                    headings.pop()
                headings.append((ln["x0"], ln["text"]))
                items.append({"doc": doc, "file": file, "kind": kind, "category": "", "item": "heading", "number": "",
                              "text": ln["text"], "page": ln["page"], "top": round(ln["top"], 1), "bottom": ln["bottom"]})
            category = " / ".join(t for _, t in headings)
            items[-1]["category"] = category
            continue
        if items and items[-1]["item"] == "statement" and ln["x0"] > items[-1]["x0"] - 2 and ln["top"] - items[-1]["bottom"] < 4:
            items[-1]["text"] += " " + ln["text"]
            items[-1]["bottom"] = ln["bottom"]
            continue
        items.append({"doc": doc, "file": file, "kind": kind, "category": category, "item": "statement", "number": "",
                      "text": ln["text"], "page": ln["page"], "top": round(ln["top"], 1), "x0": ln["x0"], "bottom": ln["bottom"]})
    for it in items:
        it["text"] = "\n".join(re.sub(r"\s+", " ", part).strip() for part in it["text"].split("\n"))
    return items


def region_bounds(doc, secs, pt_doc, pdf, title_pattern):
    """(start page, start y, end page, end y): from the heading of the first section whose title matches
    title_pattern to the heading of the next section in sections.csv order."""
    secs = secs.reset_index(drop=True)
    hits = secs.index[secs.title.str.contains(title_pattern, case=False, regex=True)]
    assert len(hits) == 1, (doc, title_pattern, list(secs.title[hits]))
    k = hits[0]
    titles = {re.sub(r"\s+", "", t) for t in secs.title}
    want = [re.sub(r"\s+", "", secs.loc[k, "title"]), re.sub(r"\s+", "", secs.loc[k + 1, "title"])]
    found = []
    for n in range(int(secs.loc[k, "start_page"]), int(secs.loc[k + 1, "start_page"]) + 1):
        for ln in page_lines(pdf[n - 1], pt_doc.loc[n, "text"], n):
            stem = re.sub(r"^[\d.]+", "", ln["letters"])
            if ln["bold"] and stem in titles and stem == want[len(found)]:
                found.append((n, ln["top"], ln["bottom"]))
                if len(found) == 2:
                    break
        if len(found) == 2:
            break
    assert len(found) == 2, (doc, want, found)
    return found[0][0], found[0][2], found[1][0], found[1][1]


def grid_tables(pdf_page, page_text, y_from, y_to):
    """Ruled tables between y_from and y_to (pt): rows of cells, a cell spanning columns where an inner rule is absent.

    Row rules: thin dark runs covering >= 60% of the table width. Table: consecutive row rules with the same
    x extent. Column rules: pixel columns dark over >= COL_RULE of the table height outside redaction bars
    (lower than 1 because band rows have no inner rules; higher than aligned letter stems, about 0.5); where a bar covers the column boundary of a row, the boundary is kept. Redaction bars inside a cell
    flag it; "CCI" letters inside a bar are dropped."""
    chars = s13.page_chars(pdf_page, page_text)
    dark = s13.dark_image(pdf_page)
    S = s13.SCALE
    segs = []
    for py in range(int(y_from * S), int(y_to * S)):
        for a, b in s13.runs(dark[py]):
            if (b - a) / S >= 8:
                segs.append((py / S, a / S, b / S))
    # Group dark runs of consecutive pixel rows that overlap horizontally; thin wide bands are rules,
    # bands higher than RULE_MAX are redaction bars.
    bands = []
    for y, a, b in segs:
        prev = [band for band in bands if 1e-6 < y - band["y1"] <= 1 / S + 1e-6 and a < band["x1"] and b > band["x0"]]
        same = [band for band in bands if abs(y - band["y1"]) <= 1e-6 and band["y0"] < y and a < band["x1"] and b > band["x0"]]
        if same:
            same[0].update(x0=min(a, same[0]["x0"]), x1=max(b, same[0]["x1"]))
        elif prev:
            prev[0].update(y1=y, x0=min(a, prev[0]["x0"]), x1=max(b, prev[0]["x1"]))
        else:
            bands.append({"y0": y, "y1": y, "x0": a, "x1": b})
    rules = [b for b in bands if b["y1"] - b["y0"] <= s13.RULE_MAX and b["x1"] - b["x0"] >= 100]
    bars = [b for b in bands if b["y1"] - b["y0"] > s13.RULE_MAX]
    # Column rules are read with redaction bars blanked out.
    ruled = dark.copy()
    valid = np.ones_like(dark)
    for b in bars:
        ruled[int(b["y0"] * S):int(b["y1"] * S) + 1, int(b["x0"] * S):int(b["x1"] * S) + 1] = False
        valid[int(b["y0"] * S):int(b["y1"] * S) + 1, int(b["x0"] * S):int(b["x1"] * S) + 1] = False
    tables = []
    for r in rules:
        t = tables[-1] if tables else None
        if t and abs(r["x0"] - t["x0"]) < 4 and abs(r["x1"] - t["x1"]) < 4 and r["y0"] - t["rules"][-1] < 250:
            t["rules"].append(r["y0"])
        elif t and r["x1"] - r["x0"] >= 0.6 * (t["x1"] - t["x0"]) and r["x0"] >= t["x0"] - 4 and r["x1"] <= t["x1"] + 4 and r["y0"] - t["rules"][-1] < 250:
            t["rules"].append(r["y0"])
        else:
            tables.append({"x0": r["x0"], "x1": r["x1"], "rules": [r["y0"]]})
    out = []
    for t in tables:
        # A row left open at the table end (page break, or a redaction bar hiding the closing rule) ends at the
        # last text line that follows the last rule without a gap of more than OPEN_GAP pt, or at a bar.
        # The ruled image (bars blanked) is built below; build it first.
        below = sorted((ln for ln in s13.lines_of([ch for ch in chars if t["x0"] < (ch["x0"] + ch["x1"]) / 2 < t["x1"]
                                                    and t["rules"][-1] + 1 < ch["y0"] < y_to])), key=lambda ln: ln["top"])
        end, last = None, t["rules"][-1]
        for ln in below:
            ln_top = line_top(ln)
            if ln_top - last > OPEN_GAP or any(b["y0"] <= ln_top <= b["y1"] for b in bars):
                break
            end = last = ln["bottom"]
        # Only where the table's left border continues below its last rule (an open row has side borders;
        # a note under a closed table has none).
        r0 = t["rules"][-1]
        border = ruled[int((r0 + 1.5) * S):int((r0 + 5) * S), int(t["x0"] * S) - 1:int(t["x0"] * S) + 3]
        if end is not None and border.size and border.any(axis=1).mean() > 0.8:
            t["rules"].append(end + 1)
            t["open_end"] = True
        if len(t["rules"]) < 2:
            continue
        top, bottom = t["rules"][0], t["rules"][-1]
        win = (slice(int(top * S), int(bottom * S)), slice(int(t["x0"] * S) - 2, int(t["x1"] * S) + 3))
        frac = ruled[win].sum(axis=0) / np.maximum(valid[win].sum(axis=0), 1)
        cols = []
        for a, b in s13.runs(frac >= COL_RULE):
            cols.append((int(t["x0"] * S) - 2 + (a + b) / 2) / S)
        assert len(cols) >= 2, "table without column rules"
        tbars = [b for b in bars if b["y0"] < bottom and b["y1"] > top]
        rows = []
        for y0, y1 in zip(t["rules"][:-1], t["rules"][1:]):
            if y1 - y0 < 3:
                continue
            cells = []
            for k, (x0, x1) in enumerate(zip(cols[:-1], cols[1:])):
                band = ruled[int((y0 + 1) * S):int((y1 - 1) * S), int(x0 * S) - 2:int(x0 * S) + 3]
                covered = dark[int((y0 + 1) * S):int((y1 - 1) * S), int(x0 * S) - 2:int(x0 * S) + 3].all(axis=1).mean() > 0.5
                inner = k > 0 and (covered or band.mean(axis=0).max() >= 0.8)
                if k > 0 and not inner:
                    cells[-1]["x1"] = x1
                    cells[-1]["span"] += 1
                else:
                    cells.append({"x0": x0, "x1": x1, "span": 1, "col": k + 1})
            for c in cells:
                in_bar = lambda ch: any(b["x0"] <= ch["x0"] <= b["x1"] and b["y0"] - 1 <= ch["y0"] <= b["y1"] + 1 for b in tbars)
                inside = [ch for ch in chars if c["x0"] < (ch["x0"] + ch["x1"]) / 2 < c["x1"] and y0 < (ch["y0"] + ch["y1"]) / 2 < y1]
                c["redacted"] = any(b["x0"] < c["x1"] and b["x1"] > c["x0"] and b["y0"] < y1 and b["y1"] > y0 for b in tbars)
                kept = [ch for ch in inside if not in_bar(ch)]
                lines = s13.lines_of(kept)
                paras, last = [], None
                for ln in lines:
                    txt = s13.text_of(ln["chars"])
                    if last is not None and line_top(ln) - last > PARA_GAP:
                        paras.append(txt)
                    elif paras:
                        paras[-1] += " " + txt
                    else:
                        paras.append(txt)
                    last = ln["bottom"]
                c["text"] = "\n".join(re.sub(r"\s+", " ", x).strip() for x in paras)
            rows.append({"y0": y0, "y1": y1, "cells": cells})
        out.append({"top": top, "bottom": bottom, "x0": t["x0"], "x1": t["x1"], "ncols": len(cols) - 1, "rows": rows,
                    "open_end": t.get("open_end", False)})
    return out, bars


def section_tables(doc, file, secs, pt_doc, pdf, title_pattern, what):
    """All ruled tables of one section, one row per cell; plus redaction bars outside tables."""
    p0, y0, p1, y1 = region_bounds(doc, secs, pt_doc, pdf, title_pattern)
    cells, loose = [], []
    tno, rno, prev_open, last_row = 0, 0, False, []
    for n in range(p0, p1 + 1):
        _, height = pdf[n - 1].get_size()
        top = y0 if n == p0 else HEADER_MAX
        bot = y1 if n == p1 else height - 80
        tables, bars = grid_tables(pdf[n - 1], pt_doc.loc[n, "text"], top, bot)
        for j, t in enumerate(tables):
            rows = t["rows"]
            cont = (j == 0 and n > p0 and prev_open and rows and not rows[0]["cells"][0]["text"]
                    and len(rows[0]["cells"]) == len(last_row))
            if cont:
                # First row continues the last row of the previous page's table.
                for c, old in zip(rows[0]["cells"], last_row):
                    if c["text"]:
                        old["text"] = (old["text"] + "\n" + c["text"]).strip()
                    old["redacted"] = old["redacted"] or c["redacted"]
                    old["continued_on"] = n
                rows = rows[1:]
            else:
                tno += 1
                rno = 0
            for r in rows:
                rno += 1
                last_row = []
                for c in r["cells"]:
                    rec = {"doc": doc, "file": file, "section": what, "page": n, "table": tno, "row": rno,
                           "col": c["col"], "span": c["span"], "ncols": t["ncols"], "text": c["text"], "redacted": c["redacted"],
                           "continued_on": ""}
                    cells.append(rec)
                    last_row.append(rec)
            prev_open = t["open_end"]
        for b in bars:
            if not any(t["top"] - 1 <= b["y0"] <= t["bottom"] + 1 for t in tables):
                loose.append({"doc": doc, "file": file, "section": what, "page": n, "y0": round(b["y0"], 1), "y1": round(b["y1"], 1),
                              "x0": round(b["x0"], 1), "x1": round(b["x1"], 1)})
    return cells, loose


def main():
    pt = pd.read_csv(STEP2 / "page_text.csv").fillna({"text": ""})
    pt["doc"] = pt.sponsor_protocol_no.str.replace("H0P-MC-", "", regex=False)
    sections = pd.read_csv(STEP2 / "sections.csv", dtype={"number": str}).fillna({"text": "", "number": ""})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, cells, loose = [], [], []
    for doc in dict.fromkeys(pt.doc):
        pt_doc = pt[pt.doc == doc].set_index("page")
        file = pt_doc.file.iloc[0]
        pdf = pdfium.PdfDocument(str(s13.PDF_DIR / file))
        secs = sections[sections.doc == doc]
        rows.extend(eligibility(doc, file, secs, pt_doc, pdf))
        for pattern, what in ((r"^Objectives", "objectives_endpoints"), (r"Intervention.*Administered", "interventions")):
            c, l = section_tables(doc, file, secs, pt_doc, pdf, pattern, what)
            cells.extend(c)
            loose.extend(l)
        pdf.close()
    pd.DataFrame(cells).to_csv(OUT_DIR / "table_cells.csv", index=False)
    pd.DataFrame(loose, columns=["doc", "file", "section", "page", "y0", "y1", "x0", "x1"]).to_csv(OUT_DIR / "section_redactions.csv", index=False)
    cols = ["doc", "file", "kind", "category", "item", "number", "text", "page", "top"]
    df = pd.DataFrame(rows)[cols]
    df.insert(1, "seq", df.groupby("doc").cumcount() + 1)
    df.to_csv(OUT_DIR / "eligibility_items.csv", index=False)
    print(df.groupby(["doc", "item"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
