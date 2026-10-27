"""Crosswalk sensitivity: which modules would change if crosswalk proposals were merged?

The build merges no crosswalk proposal (agreed 2026-10-25). This script merges the
proposals in one ratio band (default 0.97 <= ratio < 1.0, the text-layer variants) into
single components, recomputes the Step 5 sharing class with the same rule, and lists the
components whose module would change. It writes no module files.

Inputs:  step5/components.csv, criteria.csv, crosswalk_proposals.csv, grid.csv
Outputs: output/crosswalk_sensitivity_<band>.csv (one row per merged component)

Run: python scripts/03_crosswalk_sensitivity.py [min_ratio] [max_ratio]
"""
import re
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
STEP5 = BASE.parent / "usdm-master-protocol" / "output_cpmp" / "step5"
OUTPUT = BASE / "output"


def norm(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def sharing_class(docs, compound_of):
    if docs == ["CPMP"]:
        return "master"
    if "CPMP" in docs:
        return "master + ISA"
    if len(docs) == 1:
        return "single ISA"
    if len({compound_of[d] for d in docs}) > 1:
        return "other"
    return "compound column" if len(docs) == 3 else "compound column (part)"


def main():
    lo = float(sys.argv[1]) if len(sys.argv) > 1 else 0.97
    hi = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    comps = pd.read_csv(STEP5 / "components.csv")
    comps = comps[comps["kind"] == "criterion"].copy()
    crit = pd.read_csv(STEP5 / "criteria.csv")
    xw = pd.read_csv(STEP5 / "crosswalk_proposals.csv")
    grid = pd.read_csv(STEP5 / "grid.csv")
    compound_of = dict(zip(grid["doc"], grid["compound"]))

    key_of = {}
    for _, r in crit.iterrows():
        if pd.notna(r["number"]):
            key_of[(r["doc"], int(r["number"]))] = r["template"]
    if not set(key_of.values()) <= set(comps["key"]):
        raise SystemExit("criteria template not among component keys")

    band = xw[(xw["ratio"] >= lo) & (xw["ratio"] < hi)]
    parent = {k: k for k in comps["key"]}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for _, r in band.iterrows():
        a = key_of[(r["doc_a"], int(r["number_a"]))]
        b = key_of[(r["doc_b"], int(r["number_b"]))]
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    comps["group"] = comps["key"].map(find)
    rows = []
    for group, members in comps.groupby("group"):
        if len(members) == 1:
            continue
        docs = sorted({d for ds in members["docs"] for d in ds.split(";")})
        new_class = sharing_class(docs, compound_of)
        rows.append({
            "members": len(members),
            "classes_before": "; ".join(sorted(members["class"])),
            "class_after": new_class,
            "docs_after": ";".join(docs),
            "keys": " || ".join(norm(k)[:120] for k in members["key"]),
        })
    out = pd.DataFrame(rows).sort_values(["class_after", "docs_after"])
    name = f"crosswalk_sensitivity_{lo:.2f}-{hi:.2f}.csv"
    out.to_csv(OUTPUT / name, index=False)
    changed_modules = out[out.apply(lambda r: r["class_after"] not in r["classes_before"].split("; ")
                                    or len(set(r["classes_before"].split("; "))) > 1, axis=1)]
    print(f"band {lo}-{hi}: {len(band)} proposals -> {len(out)} merged components; "
          f"{len(changed_modules)} change module")
    print(out.groupby(["classes_before", "class_after"]).size().to_string())


if __name__ == "__main__":
    main()
