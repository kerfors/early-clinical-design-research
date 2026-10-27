"""Review table for the crosswalk proposals in one ratio band (default 0.97 <= ratio < 1.0).

One row per proposal (pair of criteria), with the group it falls in when merged, both texts in
full, and a rule-based recommendation. The `decision` column is left empty for Kerstin.

Recommendation rules (in order):
  - numbers differ between the two texts                       -> keep apart (different value)
  - equal after normalising case, whitespace, punctuation,
    superscript/'m2' units and the ISA placeholder             -> merge (typography / text layer)
  - otherwise                                                  -> review

Inputs:  step5/crosswalk_proposals.csv, criteria.csv, components.csv, grid.csv
Output:  output/crosswalk_review_<lo>-<hi>.csv

Run: python scripts/06_crosswalk_review.py [min_ratio] [max_ratio]
"""
import re
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
STEP5 = BASE.parent / "usdm-master-protocol" / "output_cpmp" / "step5"
OUTPUT = BASE / "output"


def numbers(text):
    t = re.sub(r"\b(this ISA|[A-Z]{2}\d{2})\b", "{isa}", str(text))
    return sorted(re.findall(r"\d+(?:\.\d+)?", t.replace("m2", "m").replace("m²", "m")))


def normal(text):
    t = str(text).lower()
    t = re.sub(r"\b(this isa|[a-z]{2}\d{2})\b", "{isa}", t)
    t = t.replace("m2", "m").replace("m²", "m")
    t = re.sub(r"[^a-z0-9{}]+", "", t)
    return t


def main():
    lo = float(sys.argv[1]) if len(sys.argv) > 1 else 0.97
    hi = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    xw = pd.read_csv(STEP5 / "crosswalk_proposals.csv")
    crit = pd.read_csv(STEP5 / "criteria.csv")
    grid = pd.read_csv(STEP5 / "grid.csv")
    compound_of = dict(zip(grid["doc"], grid["compound"]))
    key_of = {(r.doc, int(r.number)): r.template for r in crit.itertuples() if pd.notna(r.number)}
    page_of = {(r.doc, int(r.number)): int(r.page) for r in crit.itertuples() if pd.notna(r.number)}

    band = xw[(xw["ratio"] >= lo) & (xw["ratio"] < hi)].copy()
    parent = {}

    def find(k):
        parent.setdefault(k, k)
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for r in band.itertuples():
        a, b = find(key_of[(r.doc_a, int(r.number_a))]), find(key_of[(r.doc_b, int(r.number_b))])
        if a != b:
            parent[b] = a
    roots = sorted({find(k) for k in parent})
    group_of = {root: i + 1 for i, root in enumerate(roots)}

    rows = []
    for r in band.itertuples():
        a = (r.doc_a, int(r.number_a))
        b = (r.doc_b, int(r.number_b))
        if numbers(r.text_a) != numbers(r.text_b):
            rec, why = "keep apart", f"numbers differ: {numbers(r.text_a)} vs {numbers(r.text_b)}"
        elif normal(r.text_a) == normal(r.text_b):
            rec, why = "merge", "same after case, whitespace, punctuation and unit normalisation"
        else:
            rec, why = "review", "wording differs"
        rows.append({
            "group": group_of[find(key_of[a])],
            "ratio": r.ratio,
            "reason": r.reason,
            "a": f"{r.doc_a} [{r.number_a}] p{page_of[a]}",
            "b": f"{r.doc_b} [{r.number_b}] p{page_of[b]}",
            "compounds": "same" if compound_of[r.doc_a] == compound_of[r.doc_b] else "different",
            "recommendation": rec,
            "why": why,
            "text_a": r.text_a,
            "text_b": r.text_b,
            "decision": "",
        })
    out = pd.DataFrame(rows).sort_values(["group", "a", "b"])
    path = OUTPUT / f"crosswalk_review_{lo:.2f}-{hi:.2f}.csv"
    out.to_csv(path, index=False)
    print(out.groupby(["recommendation", "compounds"]).size().to_string())
    print(f"{len(out)} proposals in {out['group'].nunique()} groups -> {path}")


if __name__ == "__main__":
    main()
