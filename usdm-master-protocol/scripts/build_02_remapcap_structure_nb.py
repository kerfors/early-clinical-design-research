"""Generate notebooks/02_remapcap_structure.ipynb (Plan 1, Step 2 on REMAP-CAP).

The notebook is built as a Python dict and written with json.dump.
Run:  python3 scripts/build_02_remapcap_structure_nb.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "notebooks" / "02_remapcap_structure.ipynb"


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
# Plan 1, Step 2 – REMAP-CAP: section structure and cross-layer statements

Documents (decided 2026-10-24):

| Role | Document | Version | Dated |
|---|---|---|---|
| CORE | REMAP-CAP Core Protocol | 4.0 | 5 Nov 2024 |
| PANDA | Patient, Pathogen and Disease Appendix | 1.0 | 5 Nov 2024 |
| CS_DSA | Corticosteroid Domain-Specific Appendix | 6 | 5 Nov 2024 |

Core V4.1 (29 May 2026) is kept for Step 5 (amendment).

What this notebook does:
1. Checks each PDF against `sources/remapcap/manifest.csv` (sha256). Fails if different.
2. Reads the table of contents (TOC) of each document and finds each numbered heading in the body.
3. Splits the body into sections and sentences.
4. Finds every sentence that names another protocol layer, and classifies it with explicit phrase rules (adapted from the EU-PEARL MPT/ISA rules in `../eupearl-templates/`).

Only document text is used. Nothing is inferred beyond the phrase rules.
"""))

cells.append(code_cell(r"""
import hashlib
import re
from pathlib import Path

import pandas as pd
import pypdfium2 as pdfium

BASE = Path.cwd().parent
SRC = BASE / "sources" / "remapcap"
OUT_DIR = BASE / "output_remapcap" / "step2"
assert SRC.is_dir(), f"run this notebook from usdm-master-protocol/notebooks/ (missing {SRC})"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DOCS = {
    "CORE": "superseded/REMAP-CAP-Core-Protocol-V4-05-November-2024_CLEAN-m9gf.pdf",
    "PANDA": "current/REMAP-CAP-Pathogen-ANd-Disease-Appendix-PANDA-V1-05-NOV-2024.pdf",
    "CS_DSA": "current/REMAP-CAP-Corticosteroid-DSA-V6-05-NOV-2024_CLEAN.pdf",
}

manifest = pd.read_csv(SRC / "manifest.csv").set_index("file")
for role, rel in DOCS.items():
    digest = hashlib.sha256((SRC / rel).read_bytes()).hexdigest()
    assert digest == manifest.loc[rel, "sha256"], f"{role}: file differs from manifest"
    print(f"{role:7s} ok  {rel}")
"""))

cells.append(markdown_cell(r"""
## Page text and running headers

Each page starts with a running header (document name, version, date, and for CORE/CS_DSA "CONFIDENTIAL Page x of y"; for PANDA a bare page number).
These header lines are removed before the text is used. The header patterns below were read from the documents.
"""))

cells.append(code_cell(r"""
HEADER_PATTERNS = [
    r"^Core Protocol Version [\d.]+ Dated \d{1,2} \w+ \d{4}$",
    r"^Patient, Pathogen and Disease Appendix Version [\d.]+ Dated \d{1,2} \w+ \d{4}$",
    r"^Corticosteroid Domain-Specific Appendix Version [\d.]+ Dated \d{1,2} \w+ \d{4}$",
    r"^(CONFIDENTIAL )?Page \d+ of \d+$",
    r"^\d{1,3}$",
]
HEADER_RE = re.compile("|".join(HEADER_PATTERNS))


def read_pages(path):
    pdf = pdfium.PdfDocument(str(path))
    pages = []
    for i in range(len(pdf)):
        page = pdf[i]
        textpage = page.get_textpage()
        raw = textpage.get_text_range().replace("\r", "").replace("￾", "-")
        textpage.close()
        page.close()
        kept = [ln for ln in raw.split("\n") if not HEADER_RE.match(ln.strip())]
        pages.append("\n".join(kept))
    pdf.close()
    return pages


pages = {role: read_pages(SRC / rel) for role, rel in DOCS.items()}
for role, pp in pages.items():
    print(f"{role:7s} pages={len(pp)}")
"""))

cells.append(markdown_cell(r"""
## Table of contents

TOC lines have the form `<number>. <title> ........ <page>`. Long titles wrap over two lines, so lines are joined until a line ends with dot leaders and a page number.
Unnumbered TOC entries (sub-headings without a number, e.g. under Core 7.8.x) are kept with `number` empty; they are not used to split the body.
"""))

cells.append(code_cell(r"""
TOC_END_RE = re.compile(r"\.{4,}\s*(\d+)\s*$")
TOC_NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s*(.+)$")


def toc_pages(pp):
    idx = [i for i, p in enumerate(pp) if re.search(r"(?i)table of contents", p)]
    assert idx, "no TOC page"
    start = idx[0]
    end = start
    while end + 1 < len(pp) and len(re.findall(r"\.{4,}\s*\d+\s*$", pp[end + 1], re.M)) >= 3:
        end += 1
    return list(range(start, end + 1))


def parse_toc(pp):
    rows = []
    buffer = ""
    for i in toc_pages(pp):
        for ln in pp[i].split("\n"):
            ln = ln.strip()
            if not ln or re.match(r"(?i)^(table of contents|table of tables|table of figures)$", ln):
                continue
            buffer = (buffer + " " + ln).strip()
            m = TOC_END_RE.search(buffer)
            if not m:
                continue
            entry = TOC_END_RE.sub("", buffer).strip()
            page = int(m.group(1))
            buffer = ""
            n = TOC_NUM_RE.match(entry)
            number, title = (n.group(1), n.group(2).strip()) if n else ("", entry)
            if re.match(r"(?i)^(table|figure) \d+", title):
                continue
            rows.append({"number": number, "title": title, "toc_page": page,
                         "level": number.count(".") + 1 if number else None})
    return pd.DataFrame(rows)


toc = {role: parse_toc(pp) for role, pp in pages.items()}
for role, df in toc.items():
    print(f"{role:7s} TOC entries={len(df)} numbered={int((df.number != '').sum())} unnumbered={int((df.number == '').sum())}")
toc["CS_DSA"].head(12)
"""))

cells.append(markdown_cell(r"""
## Locate numbered headings in the body

Search starts after the TOC pages. For each numbered TOC entry, in TOC order, the first line after the previous heading that starts with the number and the first words of the title is taken as the heading.
Not found → `found = False` (listed for review, not guessed).
"""))

cells.append(code_cell(r"""
def body_lines(pp, start_page):
    out = []
    for i in range(start_page, len(pp)):
        for ln in pp[i].split("\n"):
            if ln.strip():
                out.append((i + 1, ln.strip()))
    return out


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def locate_headings(role):
    pp = pages[role]
    first_body = toc_pages(pp)[-1] + 1
    lines_ = body_lines(pp, first_body)
    rows = []
    pos = 0
    for r in toc[role][toc[role].number != ""].itertuples():
        key = norm(r.title)[:25]
        num_re = re.compile(r"^" + re.escape(r.number) + r"\.?\s*")
        hit = None
        for j in range(pos, len(lines_)):
            page, ln = lines_[j]
            if num_re.match(ln):
                rest = norm(num_re.sub("", ln))
                nxt = norm(lines_[j + 1][1]) if j + 1 < len(lines_) else ""
                if (rest + nxt).startswith(key):
                    hit = j
                    break
        rows.append({"doc": role, "number": r.number, "title": r.title, "level": r.level,
                     "toc_page": r.toc_page, "line_idx": hit,
                     "body_page": lines_[hit][0] if hit is not None else None,
                     "found": hit is not None})
        if hit is not None:
            pos = hit + 1
    return pd.DataFrame(rows), lines_


located = {}
lines_by_doc = {}
for role in DOCS:
    located[role], lines_by_doc[role] = locate_headings(role)
    df = located[role]
    print(f"{role:7s} numbered={len(df)} found={int(df.found.sum())} not_found={int((~df.found).sum())}")
pd.concat(located.values()).query("not found")[["doc", "number", "title", "toc_page"]]
"""))

cells.append(markdown_cell(r"""
## Sections and sentences

A section's text runs from its heading line to the next found heading. Sentences are split on `. ! ?` followed by white space; line-end hyphenation is not repaired (the documents use few hyphen breaks).
"""))

cells.append(code_cell(r"""
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def sections_for(role):
    df = located[role][located[role].found].sort_values("line_idx").reset_index(drop=True)
    lines_ = lines_by_doc[role]
    rows = []
    for k, r in df.iterrows():
        end = int(df.loc[k + 1, "line_idx"]) if k + 1 < len(df) else len(lines_)
        chunk = lines_[int(r.line_idx) + 1:end]
        text = re.sub(r"\s+", " ", " ".join(ln for _, ln in chunk)).strip()
        rows.append({"doc": role, "number": r.number, "title": r.title, "level": r.level,
                     "start_page": r.body_page, "end_page": chunk[-1][0] if chunk else r.body_page,
                     "n_chars": len(text), "text": text})
    return pd.DataFrame(rows)


sections = pd.concat([sections_for(role) for role in DOCS], ignore_index=True)
sentences = (sections.assign(sentence=sections.text.map(SENTENCE_SPLIT.split))
             .explode("sentence")[["doc", "number", "title", "start_page", "sentence"]])
sentences = sentences[sentences.sentence.str.len() > 0].reset_index(drop=True)
print(sections.groupby("doc").agg(sections=("number", "size"), chars=("n_chars", "sum")))
"""))

cells.append(markdown_cell(r"""
## Cross-layer statements

**Step A – mentions.** A sentence is kept if it names a protocol layer (target). Targets and their names in the text:

| Target | Patterns (case-insensitive) |
|---|---|
| CORE | `Core Protocol` |
| PANDA | `PANDA`, `PaNDA`, `Patient, Pathogen and Disease Appendix`, `Patient, Pathogen ANd Disease Appendix` |
| DSA | `DSA(s)`, `Domain-Specific Appendix/Appendices` (not the CS_DSA's own "this DSA") |
| RSA | `RSA(s)`, `Region-Specific Appendix/Appendices` |
| SAA | `Statistical Analysis Appendix` |
| CURRENT_STATE | `Current State` |
| PANDEMIC | `Pandemic Appendix` |

**Step B – relation.** Flags are set only where an explicit phrase occurs. Adapted from the EU-PEARL rules (`refers_to_master`, `extends_master`, `either_location`) to REMAP-CAP wording, which was checked by phrase counts in the three documents before writing the rules:

| Flag | Meaning | Pattern |
|---|---|---|
| `refers_to` | content is given in the target | `(as / is / are / be / that is / those) specified / defined / described / outlined in (the) (relevant) <target>`; `refer(s) to (the) (relevant) <target>`; `see (the) (relevant) <target>`; `guidance provided in the <target>`; `information is contained in the <target>`; `(outcome / endpoint(s) / trigger(s)) (as) specified / described / defined in (the) <target>` |
| `extends` | adds to the target | `additional to those specified in`; `in addition to … <target>` |
| `modifies` | changes what the target says | `modification(s) to … specified in the <target>` |
| `delegates` | the target is where content will be given | `(will be / are / is / be) specified (only) in (each / the / a / that) <target>` |
| `default_overridable` | the doc gives a default that the target may change | `unless (otherwise) specified in (a / the / each) <target>` |
| `version_scoped` | statement names a version relation | `(this / the current / the previous / earlier / previous) version(s) of (the) <target>`; `dated before this <target> amendment` |

Direction matters. Layer rank: CORE 0; PANDA, SAA, CURRENT_STATE, PANDEMIC 1; DSA, RSA 2.
- `direction = up` (target is a higher layer): a `refers_to` statement means the document **takes** the content from the target (inheritance). `delegates` and `default_overridable` are not set.
- `direction = down` (target is a lower layer): the same wording ("… will be specified in the relevant DSA") means the document **hands** the content to the target. Such a `refers_to` is recorded as `delegates`.

Example: "Funding sources for the Platform are specified in the Core Protocol documents" in the CS_DSA is up → `refers_to`. "The criteria for discontinuation specific to each domain are specified in the relevant DSA" in the Core is down → `delegates`.

The rules were first run, then the `mention_only` sentences were read, and the observed phrasings `relevant`, `outlined` and `see` were added. Remaining `mention_only` sentences are listed in the review cell below.

A mention with no flag is `mention_only`. As in EU-PEARL: no flag does **not** mean "independent of the other layer".
Self references (CS_DSA saying "this DSA") are labelled `SELF` and not counted as cross-layer.
"""))

cells.append(code_cell(r"""
TARGETS = {
    "CORE": r"core protocol",
    "PANDA": r"\bpanda\b|patient, pathogen and disease appendix",
    "DSA": r"\bdsas?\b|domain[- ]specific appendi(?:x|ces)",
    "RSA": r"\brsas?\b|region(?:al)?[- ]specific appendi(?:x|ces)",
    "SAA": r"statistical analysis appendix",
    "CURRENT_STATE": r"current state",
    "PANDEMIC": r"pandemic appendix",
}
SELF_DSA = r"\bthis (?:version of the )?(?:dsa|domain[- ]specific appendix)\b|\bthe corticosteroid (?:dsa|domain[- ]specific appendix)\b"


def relation_patterns(t):
    rel = r"(?:the\s+)?(?:relevant\s+)?(?:current version of the\s+)?"
    return {
        "refers_to": [rf"\b(?:as|is|are|be|that is|those)\s+(?:specified|defined|described|outlined)\s+in\s+{rel}(?:{t})",
                      rf"\brefers?\s+to\s+{rel}(?:{t})",
                      rf"\bsee\s+{rel}(?:{t})",
                      rf"\bguidance provided in the\s+(?:{t})",
                      rf"\binformation is contained in the\s+(?:{t})",
                      rf"\b(?:outcome|endpoint|endpoints|triggers?)\s+(?:as\s+)?(?:specified|described|defined)\s+in\s+{rel}(?:{t})"],
        "extends": [rf"\badditional to those specified in (?:the\s+)?(?:{t})",
                    rf"\bin addition to\b[^.]*\b(?:{t})"],
        "modifies": [rf"\bmodifications?\s+to\b[^.]*\bspecified in (?:the\s+)?(?:{t})"],
        "delegates": [rf"\b(?:will be|are|is|be)\s+specified\s+(?:only\s+)?in\s+(?:each|the|a|that)\s+(?:{t})"],
        "default_overridable": [rf"\bunless\s+(?:otherwise\s+)?specified\s+in\s+(?:a|the|each)\s+(?:{t})"],
        "version_scoped": [rf"\b(?:this|the current|the previous|previous|earlier)\s+versions?\s+of\s+(?:the\s+)?(?:{t})",
                           rf"\bdated before this\s+(?:{t})\s+amendment"],
    }


RANK = {"CORE": 0, "PANDA": 1, "SAA": 1, "CURRENT_STATE": 1, "PANDEMIC": 1, "DSA": 2, "RSA": 2, "CS_DSA": 2}
DOWNWARD_ONLY = {"delegates", "default_overridable"}
FLAGS = list(relation_patterns("x").keys())
rows = []
for s in sentences.itertuples():
    low = s.sentence.lower()
    for target, tpat in TARGETS.items():
        if not re.search(tpat, low):
            continue
        if target == "DSA" and s.doc == "CS_DSA":
            without_self = re.sub(SELF_DSA, "", low)
            if not re.search(tpat, without_self):
                target = "SELF"
        flags = {f: any(re.search(p, low) for p in pats) for f, pats in relation_patterns(tpat).items()} \
            if target != "SELF" else {f: False for f in FLAGS}
        if target == "SELF":
            direction = "self"
        elif RANK[target] > RANK[s.doc]:
            direction = "down"
            if flags["refers_to"]:
                flags["refers_to"] = False
                flags["delegates"] = True
        else:
            direction = "up" if RANK[target] < RANK[s.doc] else "same_rank"
            flags.update({f: False for f in DOWNWARD_ONLY})
        label = "+".join(f for f in FLAGS if flags[f]) or "mention_only"
        rows.append({"doc": s.doc, "section": s.number, "section_title": s.title, "page": s.start_page,
                     "target": target, "direction": direction, "relation": label, **flags, "sentence": s.sentence})

xrefs = pd.DataFrame(rows)
cross = xrefs[(xrefs.target != "SELF") & (xrefs.target != xrefs.doc.map({"CORE": "CORE", "PANDA": "PANDA", "CS_DSA": "-"}))]
pd.crosstab([cross.doc, cross.target], cross.relation, margins=True)
"""))

cells.append(markdown_cell(r"""
## CS_DSA → CORE: the inheritance statements

These are the statements Step 3 must carry: content the Corticosteroid DSA does not repeat, but takes from the Core Protocol.
"""))

cells.append(code_cell(r"""
pd.set_option("display.max_colwidth", 220)
cross[(cross.doc == "CS_DSA") & (cross.target == "CORE") & (cross.relation != "mention_only")][["section", "section_title", "page", "relation", "sentence"]]
"""))

cells.append(markdown_cell(r"""
Review: CS_DSA sentences that name the Core Protocol but match no rule. Read these before trusting the counts above.
"""))

cells.append(code_cell(r"""
cross[(cross.doc == "CS_DSA") & (cross.target == "CORE") & (cross.relation == "mention_only")][["section", "page", "sentence"]]
"""))

cells.append(markdown_cell(r"""
## CORE → DSA: what the Core Protocol hands down

Core statements that delegate content to DSAs or allow a DSA to override a default (`unless specified in a DSA`). These define where the Core leaves room for a domain.
"""))

cells.append(code_cell(r"""
cross[(cross.doc == "CORE") & (cross.target == "DSA") & (cross.relation != "mention_only")][["section", "section_title", "page", "relation", "sentence"]]
"""))

cells.append(markdown_cell(r"""
## Version-scoped statements (input for Step 5)
"""))

cells.append(code_cell(r"""
xrefs[xrefs.version_scoped][["doc", "section", "page", "target", "sentence"]]
"""))

cells.append(markdown_cell(r"""
## Write outputs

| File | Content |
|---|---|
| `toc.csv` | parsed TOC entries per document (numbered and unnumbered) |
| `headings.csv` | numbered TOC entries with body page and `found` flag |
| `sections.csv` | section text per numbered heading |
| `cross_references.csv` | every sentence naming a layer, with target, flags and sentence |
"""))

cells.append(code_cell(r"""
pd.concat([df.assign(doc=role) for role, df in toc.items()], ignore_index=True).to_csv(OUT_DIR / "toc.csv", index=False)
pd.concat(located.values(), ignore_index=True).drop(columns=["line_idx"]).to_csv(OUT_DIR / "headings.csv", index=False)
sections.to_csv(OUT_DIR / "sections.csv", index=False)
xrefs.to_csv(OUT_DIR / "cross_references.csv", index=False)
for f in sorted(OUT_DIR.iterdir()):
    print(f"{f.name:24s} {f.stat().st_size:>10,d} bytes")
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
