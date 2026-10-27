"""Generate notebooks/11_cpmp_structure.ipynb (Plan 1 restarted on CPMP, Step 2: structure).

Input: output_cpmp/step2/page_text.csv (scripts/10_cpmp_page_text.py).
Output: output_cpmp/step2/toc.csv, sections.csv, cross_references.csv.

The notebook is built as a Python dict and written with json.dump.
Run:  python3 scripts/build_11_cpmp_structure_nb.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "notebooks" / "11_cpmp_structure.ipynb"


def lines(text):
    text = text.strip("\n")
    parts = text.split("\n")
    return [p + "\n" for p in parts[:-1]] + [parts[-1]]


def markdown_cell(text):
    return {"cell_type": "markdown", "metadata": {}, "source": lines(text)}


def code_cell(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines(text)}


cells = []

cells.append(markdown_cell(r"""
# CPMP, Step 2 – structure and cross-layer statements

The REMAP-CAP Step 2 (`02_remapcap_structure.ipynb`) applied to the 13 posted CPMP protocols: the master protocol H0P-MC-CPMP (a) and 12 ISAs. The disease-state addenda (DSA) are not public.

Input is the page text from `scripts/10_cpmp_page_text.py` (`output_cpmp/step2/page_text.csv`), not the PDFs, because 8 of the 13 PDFs have letter-spaced pages and OA05 has image-only pages.

Differences from the REMAP-CAP Step 2, each caused by the CPMP documents:

1. **TOC numbers are not used as section numbers.** In letter-spaced TOC pages the text layer puts number glyphs out of order (BP03: ".3. Schedule of Activities", "4 3. Justification for Dose"), and OA03 prints some numbers neither in the TOC nor in the body. The TOC gives the order and the titles. Each heading is located in the body by its title (letters and digits only, so glued words do not matter), and the section number is the one printed on the body heading (`number_source = body`). Where the body heading has no number, the TOC number is used if it has one (`toc`); otherwise the section has no number (`none`).
2. **Redacted TOC entries.** A TOC line with dot leaders and a page number but no title is a redacted entry (the title is under a CCI box). It is kept in `toc.csv` as `redacted_title` and not searched in the body. `CCI` / `PPD` markers, also letter-spaced ("C CI"), are removed from titles; a title that is only "CI" or "PD" (the remainder of a split marker, OA03) counts as redacted.
3. **Not found in the body.** A titled TOC entry not found in the body is classified from the evidence between the neighbouring found headings: `redacted` if that stretch contains a CCI marker (also a line that is only "CI" remnants, as under the OA03 Schema box), otherwise `not_found`.
4. **Running headers** are removed: "CONFIDENTIAL … H0P-MC-…" lines, page-number lines, and the "Approved on … GMT" signature stamp.
"""))

cells.append(code_cell(r"""
import re
from pathlib import Path

import pandas as pd

BASE = Path.cwd().parent
STEP2 = BASE / "output_cpmp" / "step2"
assert (STEP2 / "page_text.csv").is_file(), "run from usdm-master-protocol/notebooks/ after scripts/10_cpmp_page_text.py"

pt = pd.read_csv(STEP2 / "page_text.csv").fillna({"text": ""})
pt["doc"] = pt.sponsor_protocol_no.str.replace("H0P-MC-", "", regex=False)
DOCS = list(dict.fromkeys(pt.doc))
assert len(DOCS) == 13 and DOCS[0] == "CPMP", DOCS
LAYER = dict(zip(pt.doc, pt.layer))


def despace(s):
    return re.sub(r"\s+", "", s)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def is_header(ln):
    d = despace(ln)
    return ((d.startswith("CONFIDENTIAL") and "H0P-MC-" in d)
            or re.fullmatch(r"\d{1,3}", d) is not None
            or re.fullmatch(r"Approvedon\d{1,2}\w{3}\d{4}GMT", d) is not None)


pages = {doc: ["\n".join(ln for ln in r.text.split("\n") if not is_header(ln))
               for r in pt[pt.doc == doc].sort_values("page").itertuples()]
         for doc in DOCS}
print({d: len(p) for d, p in pages.items()})
"""))

cells.append(markdown_cell(r"""
## Table of contents
"""))

cells.append(code_cell(r"""
LEADER_LINE = re.compile(r"\.{4,}[\s.]*\d(?:\s?\d){0,2}\s*$")
TOC_ENTRY = re.compile(r"(.*?)\.{3,}[\s.]*(\d(?: ?\d){0,2})(?=\s|$)")
NUM_PREFIX = re.compile(r"^(\d+(?:\.\d+)*)\.?(?=\D|$)")
REDACTION = re.compile(r"\bC\s*C\s*I\b|\bP\s*P\s*D\b")


def toc_pages(pp):
    start = next(i for i, p in enumerate(pp) if re.search(r"(?i)table\s*of\s*contents", p))
    end = start
    while end + 1 < len(pp) and len(re.findall(r"\.{4,}[\s.]*\d", pp[end + 1])) >= 3:
        end += 1
    return list(range(start, end + 1))


def parse_toc(doc):
    pp = pages[doc]
    kept = []
    for i in toc_pages(pp):
        for ln in pp[i].split("\n"):
            ln = ln.strip()
            if ln and not re.fullmatch(r"(?i)table\s*of\s*contents", ln):
                kept.append(ln)
    text = " ".join(kept)
    rows = []
    for m in TOC_ENTRY.finditer(text):
        entry = REDACTION.sub(" ", m.group(1)).strip(" .")
        d = despace(entry)
        n = NUM_PREFIX.match(d)
        title = re.sub(r"\s+", " ", re.sub(r"^[\d.\s]+", "", entry)).strip()
        if despace(title) in ("CI", "PD"):
            title = ""
        rows.append({"doc": doc, "toc_number": n.group(1) if n else "", "title": title,
                     "toc_page": int(despace(m.group(2))), "redacted_title": title == "",
                     "redaction_marker_in_entry": bool(REDACTION.search(m.group(1)))})
    return pd.DataFrame(rows)


toc = pd.concat([parse_toc(doc) for doc in DOCS], ignore_index=True)
print(toc.groupby("doc", sort=False).agg(entries=("title", "size"), redacted_title=("redacted_title", "sum"),
                                         no_toc_number=("toc_number", lambda s: int((s == "").sum()))))
"""))

cells.append(markdown_cell(r"""
## Headings in the body

A body line is a heading for a TOC entry if, after an optional leading number, its letters and digits equal the title's, or the line and up to two following lines start with the title (headings wrapped over lines). Search runs in TOC order from the last heading found. Lines with dot leaders are skipped (NP03 p41 repeats TOC-like lines).
"""))

cells.append(code_cell(r"""
def body_lines(doc):
    pp = pages[doc]
    first = toc_pages(pp)[-1] + 1
    return [(i + 1, ln.strip()) for i in range(first, len(pp)) for ln in pp[i].split("\n")
            if ln.strip() and not LEADER_LINE.search(ln)]


def heading_at(lines_, j, key):
    d = despace(lines_[j][1])
    n = NUM_PREFIX.match(d)
    rest = norm(d[n.end():] if n else d)
    if not rest:
        return None
    if rest == key or (rest.startswith(key) and len(rest) <= len(key) + 3):
        return n.group(1) if n else ""
    if len(rest) < len(key):
        joined = rest
        for k in (1, 2):
            if j + k < len(lines_):
                joined += norm(lines_[j + k][1])
                if joined.startswith(key):
                    return n.group(1) if n else ""
    return None


located, lines_by_doc = [], {}
for doc in DOCS:
    lines_ = body_lines(doc)
    lines_by_doc[doc] = lines_
    pos = 0
    for r in toc[toc.doc == doc].itertuples():
        hit, body_number = None, ""
        if not r.redacted_title:
            key = norm(r.title)
            for j in range(pos, len(lines_)):
                found = heading_at(lines_, j, key)
                if found is not None:
                    hit, body_number = j, found
                    break
        located.append({"doc": doc, "toc_index": r.Index, "toc_number": r.toc_number, "body_number": body_number,
                        "title": r.title, "toc_page": r.toc_page, "redacted_title": r.redacted_title,
                        "line_idx": hit, "body_page": lines_[hit][0] if hit is not None else None})
        if hit is not None:
            pos = hit + 1
loc = pd.DataFrame(located)
loc["found"] = loc.line_idx.notna()


def status(r):
    if r.redacted_title:
        return "redacted_title"
    if r.found:
        return "found"
    same = loc[loc.doc == r.doc]
    before = same[(same.index < r.name) & same.found].line_idx.max()
    after = same[(same.index > r.name) & same.found].line_idx.min()
    lines_ = lines_by_doc[r.doc]
    a = 0 if pd.isna(before) else int(before)
    b = len(lines_) if pd.isna(after) else int(after)
    stretch = [ln for _, ln in lines_[a:b]]
    marker = any(REDACTION.search(ln) or re.fullmatch(r"(?:C?\s*C\s*I\s*)+", ln) for ln in stretch)
    return "redacted" if marker else "not_found"


loc["status"] = loc.apply(status, axis=1)
print(pd.crosstab(loc.doc, loc.status).reindex(DOCS))
print(loc[loc.status == "not_found"][["doc", "toc_number", "title"]].to_string(index=False))
"""))

cells.append(markdown_cell(r"""
## Sections

Section text runs from the line after a heading to the line before the next found heading, as in REMAP-CAP Step 2. Section number: body heading number, else TOC number, else none (`number_source`). Level = number of dots + 1 where a number exists.
"""))

cells.append(code_cell(r"""
def section_number(r):
    if r.body_number:
        return r.body_number, "body"
    if r.toc_number:
        return r.toc_number, "toc"
    return "", "none"


rows = []
for doc in DOCS:
    df = loc[(loc.doc == doc) & loc.found].sort_values("line_idx").reset_index(drop=True)
    lines_ = lines_by_doc[doc]
    for k, r in df.iterrows():
        end = int(df.loc[k + 1, "line_idx"]) if k + 1 < len(df) else len(lines_)
        chunk = lines_[int(r.line_idx) + 1:end]
        text = re.sub(r"\s+", " ", " ".join(ln for _, ln in chunk)).strip()
        number, source = section_number(r)
        rows.append({"doc": doc, "layer": LAYER[doc], "number": number, "number_source": source, "title": r.title,
                     "level": number.count(".") + 1 if number else None,
                     "start_page": int(r.body_page), "end_page": int(chunk[-1][0]) if chunk else int(r.body_page),
                     "n_chars": len(text), "text": text})
sections = pd.DataFrame(rows)
dup = sections[(sections.number != "") & sections.duplicated(["doc", "number"], keep=False)]
assert dup.empty, dup[["doc", "number", "title"]]
print(sections.groupby("doc", sort=False).agg(sections=("title", "size"), chars=("n_chars", "sum"),
                                              no_number=("number", lambda s: int((s == "").sum()))))
print(pd.crosstab(sections.doc, sections.number_source).reindex(DOCS))
"""))

cells.append(markdown_cell(r"""
## Cross-layer statements

Same approach as REMAP-CAP Step 2: a sentence is kept if it names a layer; a relation flag is set only where an explicit phrase occurs; no flag = `mention_only`. Patterns allow missing spaces (`\s*`) because letter-spaced pages can glue words.

**Targets.**

| Target | Patterns (case-insensitive) |
|---|---|
| MASTER | `master protocol`, `CPMP` not followed by `(n)` / `[n]` |
| DSA | `DSA(s)`, `disease-state addendum / addenda / appendix`, `CPMP(n)` / `CPMP[n]` |
| ISA | `ISA(s)`, `intervention-specific appendix / appendices` |
| SAP | `SAP`, `statistical analysis plan` (master protocol SAP, ISA SAP, DSA SAP); checked first, its phrase is removed before MASTER / ISA / DSA are tested |

Self references are labelled `SELF`: in the master protocol, MASTER; in an ISA, "this ISA" / "this intervention-specific appendix" and the ISA's own code (e.g. "BP01", "ISA BP01", "BP01 ISA"). An ISA naming another ISA's code is labelled `OTHER_ISA` (template carry-over, Step 1 finding 6).

**Relations** (wording checked in the 13 documents before writing the rules):

| Flag | Pattern (examples from the documents) |
|---|---|
| `refers_to` | `(are / is / be / as / been) (stated / described / defined / outlined / provided / summarized / specified / included / detailed) in … <target>` (up to 90 characters between, for lists such as "in the Master Protocol … and CLBP disease-state addendum"); `<target> … (describes / provides / includes / contains / defines)` as subject ("The CPMP Master Protocol describes the overall study design rationale"); `(please) refer to`, `see`, `per`, `in accordance with`, `consistent with` `<target>`; `can be found in … <target>`; `(provided) and (justified) in`; `<verb> within <target>`; `will be in <target>`; `if indicated in <target>`. A dot inside a section number ("Section 7.1 of Master Protocol CPMP") does not end the phrase window. |
| `extends` | `in addition to … <target>`; `additional … (may be) (included / specified / defined / described) in … <target>` |
| `overrides` | `not needed for ED per the <target>` |
| `delegates` | down only: a `refers_to` phrase pointing at a lower layer; `<target> will (define / contain / include / specify)` |
| `default_overridable` | `unless (otherwise) (specified / noted / stated) in … <target>`; `<target> … more restrictive`, `more restrictive in <target>` ("If an ISA criterion is more restrictive, it should be applied") |
| `version_scoped` | `(this / the current / previous / earlier / future) (version / amendment)(s) of … <target>` |

Direction as in REMAP-CAP: rank MASTER 0, DSA 1, ISA 2, SAP 3. Up (target higher): `refers_to` = the document takes the content (inheritance); `delegates` and `default_overridable` are not set. Down: a `refers_to` phrase is recorded as `delegates`.
"""))

cells.append(code_cell(r"""
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
sentences = (sections.assign(sentence=sections.text.map(SENTENCE_SPLIT.split))
             .explode("sentence")[["doc", "layer", "number", "title", "start_page", "sentence"]])
sentences = sentences[sentences.sentence.fillna("").str.len() > 0].reset_index(drop=True)

T = {
    "SAP": r"(?:master\s*protocol\s*|isa\s*|dsa\s*)?\bsaps?\b|statistical\s*analysis\s*plans?",
    "MASTER": r"master\s*protocol|\bcpmp\b(?!\s*[\[(]\s*\d)",
    "DSA": r"\bdsas?\b|disease[-\s]*state[-\s]*(?:addend(?:um|a)|appendi(?:x|ces))|\bcpmp\s*[\[(]\s*\d\s*[\])]",
    "ISA": r"\bisas?\b|intervention[-\s]*specific\s*appendi(?:x|ces)",
}
RANK = {"MASTER": 0, "DSA": 1, "ISA": 2, "SAP": 3}
DOC_RANK = {d: (0 if LAYER[d] == "master" else 2) for d in DOCS}
ISA_CODES = [d for d in DOCS if d != "CPMP"]
VERB_IN = r"(?:specified|described|defined|outlined|provided|summarized|stated|included|detailed|indicated)"


def relation_patterns(t):
    pre = r"(?:the\s*|each\s*|an?\s*|that\s*|their\s*)?(?:respective\s*|individual\s*|relevant\s*)?"
    w = r"(?:[^.]|\.(?=\d))"  # within one sentence; a dot inside a section number ("Section 7.1") does not end it
    return {
        "refers_to": [rf"\b(?:are|is|be|as|been|being)\s*(?:{VERB_IN}|found)(?:\s*and\s*[a-z]+)?\s*(?:only\s*)?(?:with)?in\b{w}{{0,90}}?(?:{t})",
                      rf"\b{VERB_IN}\s*within\s*{pre}(?:{t})",
                      rf"\bwill\s*be\s*(?:with)?in\s*{pre}(?:{t})",
                      rf"\bif\s*indicated\s*in\s*{pre}(?:{t})",
                      rf"(?:{t}){w}{{0,80}}?\b(?:describes?|provides?|includes?|contains?|defines?)\b",
                      rf"\b(?:please\s*)?refer\s*to\b{w}{{0,90}}?(?:{t})",
                      rf"\bsee\b{w}{{0,60}}?(?:{t})",
                      rf"\bper\s*{pre}{w}{{0,40}}?(?:{t})",
                      rf"\bin\s*accordance\s*with\s*{pre}(?:{t})",
                      rf"\bconsistent\s*with\s*{pre}(?:{t})"],
        "extends": [rf"\bin\s*addition\s*to\b{w}*(?:{t})",
                    rf"\badditional\b{w}*\b(?:may\s*be\s*|will\s*be\s*|are\s*|is\s*)?(?:included|specified|defined|described|detailed)\s*(?:with)?in\b{w}*(?:{t})"],
        "overrides": [rf"\bnot\s*needed\s*for\s*ed\s*per\s*{pre}(?:{t})"],
        "delegates": [rf"(?:{t})\s*(?:will|shall)\s*(?:define|contain|include|specify)"],
        "default_overridable": [rf"\bunless\s*(?:otherwise\s*)?(?:specified|noted|stated)\s*in\b{w}*(?:{t})",
                                rf"(?:{t}){w}*\bmore\s*restrictive", rf"\bmore\s*restrictive\s*in\s*{pre}(?:{t})"],
        "version_scoped": [rf"\b(?:this|the\s*current|previous|earlier|future)\s*(?:versions?|amendments?)\s*of\b{w}{{0,20}}(?:{t})"],
    }


FLAGS = list(relation_patterns("x").keys())
DOWNWARD_ONLY = {"delegates", "default_overridable"}


def self_pattern(doc):
    if doc == "CPMP":
        return None
    return rf"\bthis\s*(?:isa|intervention[-\s]*specific\s*appendix)\b|\b(?:isa\s*)?(?:h0p-mc-)?{doc.lower()}\b(?:\s*isa\b)?"


rows = []
for s in sentences.itertuples():
    low = s.sentence.lower()
    rest = low
    for target in ("SAP", "MASTER", "DSA", "ISA"):
        tpat = T[target]
        if not re.search(tpat, rest):
            continue
        label_target = target
        if target == "MASTER" and s.doc == "CPMP":
            label_target = "SELF"
        if target == "ISA" and s.doc != "CPMP":
            without_self = re.sub(self_pattern(s.doc), " ", rest)
            others = [c for c in ISA_CODES if c != s.doc and re.search(rf"\b{c.lower()}\b", rest)]
            if others:
                label_target = "OTHER_ISA"
            elif not re.search(tpat, without_self):
                label_target = "SELF"
        if label_target in ("SELF", "OTHER_ISA"):
            flags = {f: False for f in FLAGS}
            direction = label_target.lower()
        else:
            flags = {f: any(re.search(p, rest) for p in pats) for f, pats in relation_patterns(tpat).items()}
            if RANK[target] > DOC_RANK[s.doc]:
                direction = "down"
                if flags["refers_to"]:
                    flags["refers_to"] = False
                    flags["delegates"] = True
            else:
                direction = "up" if RANK[target] < DOC_RANK[s.doc] else "same_rank"
                flags.update({f: False for f in DOWNWARD_ONLY})
        label = "+".join(f for f in FLAGS if flags[f]) or "mention_only"
        rows.append({"doc": s.doc, "layer": s.layer, "section": s.number, "section_title": s.title, "page": s.start_page,
                     "target": label_target, "direction": direction, "relation": label, **flags, "sentence": s.sentence})
        if target == "SAP":
            rest = re.sub(tpat, " ", rest)

xrefs = pd.DataFrame(rows)
cross = xrefs[~xrefs.target.isin(["SELF"])]
print(pd.crosstab([cross.layer, cross.target], cross.relation, margins=True).to_string())
"""))

cells.append(markdown_cell(r"""
## Review: sentences that name another layer but match no rule

Read these before trusting the counts above (as in REMAP-CAP Step 2).
"""))

cells.append(code_cell(r"""
pd.set_option("display.max_colwidth", 200)
mo = cross[(cross.relation == "mention_only") & cross.target.isin(["MASTER", "DSA"]) & (cross.layer == "ISA")]
print("ISA -> MASTER/DSA mention_only:", len(mo))
mo.drop_duplicates("sentence")[["doc", "section", "target", "sentence"]].head(40)
"""))

cells.append(code_cell(r"""
mo = cross[(cross.relation == "mention_only") & (cross.layer == "master") & cross.target.isin(["DSA", "ISA"])]
print("master -> DSA/ISA mention_only:", len(mo))
mo.drop_duplicates("sentence")[["section", "target", "sentence"]].head(40)
"""))

cells.append(markdown_cell(r"""
## Outputs
"""))

cells.append(code_cell(r"""
toc.to_csv(STEP2 / "toc.csv", index=False)
loc.drop(columns=["line_idx"]).to_csv(STEP2 / "headings.csv", index=False)
sections.to_csv(STEP2 / "sections.csv", index=False)
xrefs.to_csv(STEP2 / "cross_references.csv", index=False)
for f in ("toc.csv", "headings.csv", "sections.csv", "cross_references.csv"):
    print(f"{f:22s} {(STEP2 / f).stat().st_size:>10,d} bytes")
"""))

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}
for i, c in enumerate(notebook["cells"]):
    c["id"] = f"cell-{i:02d}"

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)
print("wrote", OUT)
