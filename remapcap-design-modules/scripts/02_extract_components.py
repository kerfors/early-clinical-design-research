"""REMAP-CAP design modules, step 2: components (list items) from mapped sections.

Section text comes from step 1 (output/step1/sections.csv) for the bounds; list items
are cut from line positions (pdftotext -bbox-layout), because the collapsed section
text does not show where the last item ends.

Rules (logged per item in output/step2/components.csv, rule column):
  R-glyph   a line that is, or starts with, a list glyph (bullet, filled circle, 'o',
            square) opens an item; level = rank of the glyph's x among the glyph x
            positions in that section.
  R-number  a line starting '<n>. ' (single integer, not a heading 'n.n') opens a
            level-1 item (numbered lists in the Core).
  R-cont    a line indented beyond the body margin continues the current item.
  R-margin  a line at the body margin that opens no item ends the list; its text is
            section text (lead-in before the first item, trailing text after).
  R-row     lines on one row (|dy| <= 4 pt) are joined in x order; only the body band
            60 < y < 775 is read (running header and footer bands excluded).
  R-group   a line equal to an unnumbered TOC entry of the document is a group heading for
            the items after it (e.g. Core 8.8.2 "Inpatient data"); it closes the open item.
            TOC entries that are table or figure captions are not group headings.
  Glyph levels: glyph x positions within 3 pt are one level (bullet 90.0 vs filled circle 89.4).
  Each item has seq (running number in the section) and item (the printed number or the
  glyph-derived label); the glyph itself is kept (checkbox vs bullet).
  R-sentence  section text outside list items is split into sentences (step 1 rule) and
            written to output/step2/statements.csv.
  Known residue: Core 4.1 7.6.3 is not in its TOC, so its sub-heading "Respiratory Infection
            Ordinal Weighted Score" is not recognised and stays in the last 7.6.3 item.
  R-hyphen  a line ending in 'word-' is joined to the next line without a space (a word split at
            a line end, e.g. 'pre- specified'), unless the next word is 'and', 'or' or 'to'.
  R-table   a 'Table n:' caption ends the list and opens a table: the caption, the table rows and
            table notes (body-margin lines starting with '*') go to section_text.csv table_text,
            not to statements. A body-margin line that is neither a caption nor a note ends the
            table; reading continues as section text. A table breaks the section text: no
            sentence runs across it (marker TABLE_BREAK in section_text.csv lead_in/trailing).
Body margin = most frequent line xMin in the document (per page fails on list-heavy pages).
"""
import html
import re
import subprocess
from collections import Counter
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent.parent
SRC = HERE.parent / "usdm-master-protocol" / "sources" / "remapcap"
STEP1 = HERE / "output" / "step1"
OUT = HERE / "output" / "step2"
OUT.mkdir(parents=True, exist_ok=True)

DOCS = {
    "CORE40": ("Core Protocol", "superseded/REMAP-CAP-Core-Protocol-V4-05-November-2024_CLEAN-m9gf.pdf"),
    "CORE41": ("Core Protocol", "current/REMAP-CAP-Core-Protocol-V41-29-MAY-2026_CLEAN.pdf"),
    "PANDA": ("Patient, Pathogen and Disease Appendix", "current/REMAP-CAP-Pathogen-ANd-Disease-Appendix-PANDA-V1-05-NOV-2024.pdf"),
    "CS_DSA": ("Corticosteroid Domain-Specific Appendix", "current/REMAP-CAP-Corticosteroid-DSA-V6-05-NOV-2024_CLEAN.pdf"),
    "AB_DSA": ("Antibiotic Domain-Specific Appendix", "current/REMAP-CAP-Antibiotic-DSA-V4-05-NOV-2024_CLEAN.pdf"),
    "TAB_DSA": ("Tropical Antibiotic Domain-Specific Appendix", "current/REMAP-CAP-Tropical-Antibiotic-DSA-V1-22-APR-2026.pdf"),
    "IAV_DSA": ("Influenza Antiviral Domain-Specific Appendix", "current/REMAP-CAP-Influenza-Antiviral-DSA-V4_CLEAN-05-OCT-2026.pdf"),
    "MD_DSA": ("Macrolide Duration Domain-Specific Appendix", "current/REMAP-CAP-Macrolide-Duration-DSA-V4-05-NOV-2024_CLEAN.pdf"),
    "IG_DSA": ("COVID-19 Immunoglobulin Therapy Domain-Specific Appendix", "current/REMAP-CAP-COVID-19-Immunoglobulin-DSA-V4-05-NOV-2024_CLEAN.pdf"),
    "MV_DSA": ("Mechanical Ventilation Domain-Specific Appendix", "current/REMAP-CAP-Mechanical-Ventilation-DSA-V20-05-NOV-2024_CLEAN.pdf"),
    "END_DSA": ("Endothelial Modulation Domain-Specific Appendix", "current/REMAP-CAP-Endothelial-DSA-V2-05-NOV-2024_CLEAN.pdf"),
    "IIM_DSA": ("Influenza Immune Modulation Domain-Specific Appendix", "current/REMAP-CAP-Influenza-IM-DSA-V21-09-May-2025_CLEAN.pdf"),
}

# section number prefix -> component kind (first match wins, longest prefix first)
DSA_KINDS = [
    ("8.1.1", "applicability_age"), ("8.1.2", "applicability_state"), ("8.1.3", "domain_strata"),
    ("8.2.1", "domain_inclusion"), ("8.2.2", "domain_exclusion"), ("8.2.3", "intervention_exclusion"),
    ("8.3", "intervention"), ("8.5.1", "endpoint_primary"), ("8.5.2", "endpoint_secondary"),
    ("9.2", "data_collection"), ("9.3", "discontinuation"),
    ("10.2", "allocation_unit_of_analysis"), ("10.3", "allocation_rar"), ("10.4", "allocation_reveal"),
    ("10.5", "allocation_interactions"), ("10.6", "allocation_nesting"),
    ("10.7", "allocation_threshold"), ("10.8", "allocation_threshold"),
]
CORE_KINDS = [
    ("7.4.1", "platform_inclusion"), ("7.4.2", "platform_exclusion"),
    ("7.6.1", "endpoint_primary"), ("7.6.2", "endpoint_secondary"), ("7.6.3", "endpoint_exploratory"),
    ("7.8.7", "allocation_rar"), ("8.8.2", "data_collection"),
]
PANDA_KINDS = [("2", "category_patient"), ("3.4", "category_pathogen_stratum"), ("3", "category_pathogen"),
               ("4.1", "category_acquisition"), ("4.2", "category_disease_entity"),
               ("4.3", "category_illness_severity"), ("4.4", "category_clinical_feature")]


# DSA component kinds by title key (parent section title, section title), not by number: the nine DSAs
# number the same sections differently (COVID-19 Immunoglobulin has no 9.1 Microbiology; priors and
# thresholds sit at different 10.x). Resolved per DSA to a number-prefix table; a kind applies to the
# keyed section and its subsections, as the number table did.
# Gate: for CS, AB, TAB and IAV the resolved table equals DSA_KINDS above (for the numbers they have).
DSA_TITLE_KINDS = [
    ("population", r"age strata", "applicability_age"),
    ("population", r"(illness severity )?state", "applicability_state"),
    ("population", r"domain-specific strata", "domain_strata"),
    ("eligibility criteria", r"domain inclusion criteria", "domain_inclusion"),
    ("eligibility criteria", r"domain exclusion criteria", "domain_exclusion"),
    ("eligibility criteria", r"intervention exclusion criteria", "intervention_exclusion"),
    ("trial design", r"interventions", "intervention"),
    ("endpoints", r"primary endpoint", "endpoint_primary"),
    ("endpoints", r"secondary endpoints", "endpoint_secondary"),
    ("trial conduct", r"domain-specific data collection", "data_collection"),
    ("trial conduct", r"criteria for discontinuation", "discontinuation"),
    ("statistical considerations", r"unit-of-analysis and strata", "allocation_unit_of_analysis"),
    ("statistical considerations", r"application of response-adaptive randomi[sz]ation", "allocation_rar"),
    ("statistical considerations", r"timing of revealing of randomi[sz]ation status", "allocation_reveal"),
    ("statistical considerations", r"interactions with interventions in other domains", "allocation_interactions"),
    ("statistical considerations", r"nesting( of interventions)?", "allocation_nesting"),
    ("statistical considerations", r"threshold .*", "allocation_threshold"),
]
DSA_MAIN_BODY = {"trial design", "trial conduct", "statistical considerations"}  # top-level ancestor of a keyed section
DSA_KINDS_BY_DOC = {}


def resolve_dsa_kinds(doc, sec):
    by_number = dict(zip(sec.number, sec.title))
    table = []
    for r in sec.itertuples():
        parent = by_number.get(r.number.rsplit(".", 1)[0], "") if "." in r.number else ""
        top = by_number.get(r.number.split(".")[0], "").strip().lower()
        if top not in DSA_MAIN_BODY:
            continue  # e.g. IAV 14 'Appendix 1: Region-Specific Modifications for Japan'
        for parent_key, title_re, kind in DSA_TITLE_KINDS:
            if parent.strip().lower() == parent_key and re.fullmatch(title_re, r.title.strip(), re.I):
                table.append((r.number, kind))
    nums = [n for n, _ in table]
    assert len(nums) == len(set(nums)), f"{doc}: a section has two kinds: {table}"
    return sorted(table, key=lambda t: -len(t[0]))


def kind_for(doc, number):
    table = CORE_KINDS if doc.startswith("CORE") else PANDA_KINDS if doc == "PANDA" else DSA_KINDS_BY_DOC[doc]
    for prefix, kind in table:
        if number == prefix or number.startswith(prefix + "."):
            return kind
    return None


def header_re(name):
    own = rf"^{re.escape(name)} Version [\d.]+ [Dd]ated \d{{1,2}} \w+ \d{{4}}$"
    return re.compile("|".join([own, r"^(CONFIDENTIAL )?Page \d+ of \d+$", r"^\d{1,3}$"]))


LINE_RE = re.compile(r'<line xMin="([\d.]+)" yMin="([\d.]+)"[^>]*>(.*?)</line>', re.S)
WORD_RE = re.compile(r">([^<]*)</word>")


BODY_Y = (60.0, 775.0)  # header band y 37-43, footer band y 783-792 in all seven documents
ROW_DY = 4.0


def page_lines(path, hre):
    """Lines in the body band, sorted top-down; lines on the same row (|dy| <= ROW_DY) are
    joined in x order, so a bullet glyph and its text form one row (R-row)."""
    bbox_html = subprocess.run(["pdftotext", "-bbox-layout", str(path), "-"], capture_output=True, text=True,
                          check=True).stdout
    raw = []
    for pno, page in enumerate(bbox_html.split("<page ")[1:], start=1):
        for m in LINE_RE.finditer(page):
            text = " ".join(html.unescape(w) for w in WORD_RE.findall(m.group(3))).strip()
            y = float(m.group(2))
            if text and BODY_Y[0] < y < BODY_Y[1]:
                raw.append({"page": pno, "x": float(m.group(1)), "y": y, "text": text})
    raw.sort(key=lambda r: (r["page"], r["y"], r["x"]))
    rows = []
    for r in raw:
        if rows and rows[-1]["page"] == r["page"] and abs(r["y"] - rows[-1]["y0"]) <= ROW_DY:
            rows[-1]["parts"].append((r["x"], r["text"]))
        else:
            rows.append({"page": r["page"], "y0": r["y"], "parts": [(r["x"], r["text"])]})
    out = []
    for r in rows:
        parts = sorted(r["parts"])
        text = " ".join(t for _, t in parts)
        if hre.match(text):
            HEADER_ROWS_IN_BAND.append({"file": path.name, "page": r["page"], "y": r["y0"], "text": text})
            continue
        out.append({"page": r["page"], "x": parts[0][0], "y": r["y0"], "text": text})
    return pd.DataFrame(out)


HEADER_ROWS_IN_BAND = []


SUSPENDED = {"and", "or", "to"}


def join_lines(a, b):
    """R-hyphen: a line ending in 'word-' joins the next without a space, unless the next word is
    'and', 'or' or 'to' (a suspended hyphen such as 'pre- and post-')."""
    if not a:
        return b
    m = re.match(r"(\w+)", b)
    if re.search(r"\w-$", a) and m and m.group(1).lower() not in SUSPENDED:
        return a + b
    return a + " " + b


def join_all(parts):
    out = ""
    for x in parts:
        out = join_lines(out, x)
    return out


TABLE_BREAK = " \u2016 "  # R-table: section text before and after a table is not joined into one sentence
GLYPHS = "•●▪■◦☐☒"
GLYPH_RE = re.compile(rf"^([{GLYPHS}]|o(?=\s|$))\s*(.*)$")
NUM_RE = re.compile(r"^(\d{1,2})\.\s+(\S.*)$")
sections = pd.read_csv(STEP1 / "sections.csv", dtype=str, keep_default_na=False)
# step 1 R-outline: section numbers that are not in the text layer; their body heading line has no number
recon = pd.read_csv(STEP1 / "reconstructed_numbers.csv", dtype=str, keep_default_na=False)
RECONSTRUCTED = set(zip(recon[recon.number_source == "reconstructed"].doc,
                        recon[recon.number_source == "reconstructed"].number))

for doc in DOCS:
    if doc.endswith("_DSA"):
        DSA_KINDS_BY_DOC[doc] = resolve_dsa_kinds(doc, sections[sections.doc == doc])
for doc in ["CS_DSA", "AB_DSA", "TAB_DSA", "IAV_DSA"]:
    have = set(sections[sections.doc == doc].number)
    want = sorted((p, k) for p, k in DSA_KINDS if p in have)
    got = sorted(DSA_KINDS_BY_DOC[doc])
    assert got == want, f"gate: {doc} title-key kinds {got} != number kinds {want}"
print("gate ok: title-key kinds equal the number kinds for CS, AB, TAB, IAV")
for doc, table in DSA_KINDS_BY_DOC.items():
    print(f"  {doc:8s} " + " ".join(f"{n}={k}" for n, k in sorted(table, key=lambda t: [int(x) for x in t[0].split('.')])))

MARGINS = {}
TOC_UNNUMBERED = {}
rows, texts = [], []
for doc, (name, rel) in DOCS.items():
    lines = page_lines(SRC / rel, header_re(name))
    doc_margin = Counter(round(x) for x in lines.x).most_common(1)[0][0]
    MARGINS[doc] = doc_margin
    sec = sections[sections.doc == doc].reset_index(drop=True)
    toc_rows = lines[(lines.page <= 12) & lines.text.str.contains(r"\.{4,}\s*\d+\s*$")]
    toc_unnumbered = {re.sub(r"[^a-z0-9]", "", re.sub(r"\.{4,}\s*\d+\s*$", "", t).lower())
                      for t in toc_rows.text if not re.match(r"^\d", t) and not re.match(r"(?i)^(table|figure) \d+", t)}
    toc_unnumbered.discard("")
    # R-outline headings are sections, not group headings
    toc_unnumbered -= {re.sub(r"[^a-z0-9]", "", t.lower())
                       for t in sections[(sections.doc == doc) &
                                         sections.number.map(lambda n: (doc, n) in RECONSTRUCTED)].title}
    TOC_UNNUMBERED[doc] = len(toc_unnumbered)
    # position of each heading line: search in order, as step 1 did
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    pos, starts = 0, []
    lines = lines.reset_index(drop=True)
    for r in sec.itertuples():
        num_re = re.compile(r"^" + re.escape(r.number) + r"\.?\s*")
        key = norm(r.title)[:25]
        hit = None
        if r.start_page and (doc, r.number) in RECONSTRUCTED:
            full = norm(r.title)
            for j in range(pos, len(lines)):
                here = norm(lines.at[j, "text"])
                nxt = norm(lines.at[j + 1, "text"]) if j + 1 < len(lines) else ""
                if lines.at[j, "page"] >= int(float(r.start_page)) and \
                        (here == full or (len(here) < len(full) and (here + nxt).startswith(full))):
                    hit = j
                    break
        elif r.start_page:
            for j in range(pos, len(lines)):
                ln = lines.at[j, "text"]
                if lines.at[j, "page"] >= int(float(r.start_page)) and num_re.match(ln):
                    nxt = norm(lines.at[j + 1, "text"]) if j + 1 < len(lines) else ""
                    if (norm(num_re.sub("", ln)) + nxt).startswith(key):
                        hit = j
                        break
        starts.append(hit)
        if hit is not None:
            pos = hit + 1
    sec["line_start"] = starts
    for k, r in sec.iterrows():
        kind = kind_for(doc, r.number)
        if kind is None:
            continue
        if r.line_start is None or pd.isna(r.line_start):
            # 7.6.3 / 7.6.4 in Core 4.1 have no TOC entry; bounds come from their heading text
            hits = lines.index[lines.text.str.match(r"^" + re.escape(r.number) + r"\.(?:\s|$)")].tolist()
            assert hits, f"{doc} {r.number}: heading line not found"
            start = hits[0]
        else:
            start = int(r.line_start)
        later = [int(v) for v in sec.line_start.iloc[k + 1:] if v is not None and not pd.isna(v) and int(v) > start]
        nested = lines.index[(lines.index > start) & lines.text.str.match(r"^\d+(\.\d+)+\.(?:\s|$)")].tolist()
        end = min(later + nested + [len(lines)])
        block = lines.iloc[start + 1:end]
        glyph_x = []
        for gx in sorted(b.x for b in block.itertuples() if GLYPH_RE.match(b.text)):
            if not glyph_x or gx - glyph_x[-1] > 3:
                glyph_x.append(gx)
        item, n, seq = None, [0, 0, 0, 0], 0
        lead, trail, table = [], [], []
        in_table = False
        group = ""  # R-table: a 'Table n:' caption ends the list; the rest of the section is table text

        def close():
            if item is not None:
                rows.append(item)

        for b in block.itertuples():
            m_g, m_n = GLYPH_RE.match(b.text), NUM_RE.match(b.text)
            if norm(b.text) in toc_unnumbered:
                close()
                item = None
                group = b.text
                continue
            if re.match(r"^Table \d+[:.]", b.text):
                close()
                item = None
                (lead if seq == 0 else trail).append(TABLE_BREAK)
                table.append(b.text)
                in_table = True
                continue
            at_margin = abs(b.x - doc_margin) <= 3
            if in_table and at_margin and not b.text.startswith("*"):
                in_table = False  # prose at the body margin after a table: back to section text
            if in_table:
                table.append(b.text)
                continue
            if m_g:
                close()
                level = min(range(len(glyph_x)), key=lambda i: abs(glyph_x[i] - b.x)) + 1
                n[level - 1] += 1
                n[level:] = [0] * (4 - level)
                seq += 1
                item = {"doc": doc, "section": r.number, "section_title": r.title, "kind": kind, "seq": seq,
                        "item": ".".join(str(v) for v in n[:level]), "level": level, "glyph": m_g.group(1),
                        "group": group, "page": b.page, "rule": "R-glyph", "text": m_g.group(2), "_gx": b.x}
            elif m_n and not re.match(r"^\d+\.\d", b.text):
                close()
                n = [int(m_n.group(1)), 0, 0, 0]
                seq += 1
                item = {"doc": doc, "section": r.number, "section_title": r.title, "kind": kind, "seq": seq,
                        "item": m_n.group(1), "level": 1, "glyph": "", "group": group, "page": b.page,
                        "rule": "R-number", "text": m_n.group(2), "_gx": b.x}
            elif item is not None and not at_margin and b.x > item["_gx"] + 5:
                item["text"] = join_lines(item["text"], b.text).strip()
                item["rule"] += "+R-cont" if "R-cont" not in item["rule"] else ""

            else:
                close()
                item = None
                (lead if seq == 0 else trail).append(b.text)
        close()
        texts.append({"doc": doc, "section": r.number, "section_title": r.title, "kind": kind, "items": seq,
                      "lead_in": join_all(lead), "trailing": join_all(trail), "table_text": " ".join(table)})

comp = pd.DataFrame(rows)
pd.DataFrame(HEADER_ROWS_IN_BAND).to_csv(OUT / "header_rows_in_band.csv", index=False)
comp = comp.drop(columns="_gx")
comp["text"] = comp.text.str.replace(r"\s+", " ", regex=True).str.strip()
comp.to_csv(OUT / "components.csv", index=False)
st = pd.DataFrame(texts)
st.to_csv(OUT / "section_text.csv", index=False)
print(comp.groupby(["kind", "doc"]).size().unstack(fill_value=0).to_string())
# R-sentence: section text outside list items (lead-in, trailing, or the whole section when it has
# no list) is split into sentences with the step 1 rule; each sentence is a statement component.
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
srows = []
for t in st.itertuples():
    for part in ("lead_in", "trailing"):
        segments = [re.sub(r"\s+", " ", seg).strip() for seg in getattr(t, part).split(TABLE_BREAK)]
        sentences = [x for seg in segments for x in SENTENCE_SPLIT.split(seg) if x]
        for i, sent in enumerate(sentences):
            srows.append({"doc": t.doc, "section": t.section, "section_title": t.section_title, "kind": t.kind,
                          "part": part, "n": i + 1, "sentence": sent})
stmts = pd.DataFrame(srows)
stmts.to_csv(OUT / "statements.csv", index=False)
print("statements:", len(stmts))
print(stmts.groupby(["kind", "doc"]).size().unstack(fill_value=0).to_string())
print("body margin per document:", MARGINS)
print("unnumbered TOC headings per document:", TOC_UNNUMBERED)
print("sections without items:", st[st["items"] == 0][["doc", "section", "kind"]].values.tolist())
