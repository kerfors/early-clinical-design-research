"""REMAP-CAP headings without text, for publication.

Input: output/step1/sections.csv (not in the public repo: it holds the section text).
Output: output/step1/headings.csv: doc, number, title, level, start_page, end_page, title_key.
All twelve documents in scope (Core 4.0, Core 4.1, PANDA, nine DSAs), one row per section, in
document order. No text, no character counts.

title_key: the title in lower case with every run of characters other than a-z replaced by one
space, trimmed. Exact match only: no domain names masked, no fuzzy matching. Two DSA headings with
the same title_key are the same heading of the DSA template that no document states.

Checks (fail fast): (doc, number) is unique; every title has a non-empty title_key; the documents
are the twelve in output/documents.csv.
Run:    python3 scripts/12_headings.py   (from remapcap-design-modules/)
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent.parent
STEP1 = HERE / "output" / "step1"

sections = pd.read_csv(STEP1 / "sections.csv", dtype=str)
documents = pd.read_csv(HERE / "output" / "documents.csv", dtype=str)

assert set(sections.doc) == set(documents.key), set(sections.doc) ^ set(documents.key)
assert not sections.duplicated(["doc", "number"]).any(), sections[sections.duplicated(["doc", "number"], keep=False)]

headings = sections[["doc", "number", "title", "level", "start_page", "end_page"]].copy()
headings["level"] = headings.level.astype(float).astype(int)
headings["title_key"] = headings.title.str.lower().str.replace(r"[^a-z]+", " ", regex=True).str.strip()
assert (headings.title_key != "").all(), headings[headings.title_key == ""]

headings.to_csv(STEP1 / "headings.csv", index=False)
print(headings.groupby("doc", sort=False).size().to_string())
dsa = headings[headings.doc.str.endswith("_DSA")]
in_docs = dsa.groupby("title_key").doc.nunique()
print(f"DSA headings {len(dsa)}, distinct title keys {len(in_docs)}: in all {dsa.doc.nunique()} DSAs "
      f"{(in_docs == dsa.doc.nunique()).sum()}, in 2 or more {(in_docs >= 2).sum()}, in one {(in_docs == 1).sum()}")
