"""Extract the SoA cross-layer statements (delegation, override, addition) with their text.

Same four patterns and the same activity crosswalk as the CPMP SoA join
(scripts/build_cpmp_join_notebook.py, section 4), applied to the consolidated outputs of
the soa2usdm collection `cpmp`. The join keeps only flags; the modules need the sentence
as evidence, so the statements are written out here.

Inputs (read only):
  ~/repos/GitHub/soa2usdm-collections/collections/cpmp  (must be at commit cf9541d, clean)
  ../cpmp-soa-join/activity_crosswalk.csv
Output:
  sources/soa_statements.csv  one row per statement x activity key

Run on the Mac shell (git needed): python scripts/05_extract_soa_statements.py
"""
import json
import re
import subprocess
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parent
COLLECTIONS = REPO.parent / "GitHub" / "soa2usdm-collections"
COLLECTION = COLLECTIONS / "collections" / "cpmp"
CROSSWALK = REPO / "cpmp-soa-join" / "activity_crosswalk.csv"
OUT = BASE / "sources" / "soa_statements.csv"
COMMIT = "cf9541d"

PATTERNS = [
    ("delegation_activity", re.compile(r"included in each ISA|defined in each respective ISA", re.I)),
    ("delegation_visits", re.compile(r"Visits after V7 may be specified in the ISA", re.I)),
    ("override_ed", re.compile(r"not needed for ED per the CPMP SoA", re.I)),
    ("addition_stated", re.compile(r"in addition to schedule described in", re.I)),
]


def main():
    head = subprocess.run(["git", "-C", str(COLLECTIONS), "rev-parse", "--short=7", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    if head != COMMIT:
        raise SystemExit(f"soa2usdm-collections at {head}, expected {COMMIT}")
    dirty = subprocess.run(["git", "-C", str(COLLECTIONS), "status", "--porcelain", "collections/cpmp"],
                           check=True, capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit(f"collections/cpmp has uncommitted changes:\n{dirty}")

    xw = pd.read_csv(CROSSWALK, dtype=str).fillna("")
    if not xw["name_as_printed"].is_unique:
        raise SystemExit("crosswalk name_as_printed not unique")
    xw["key"] = xw["activity_key"].where(xw["use"] == "yes", xw["name_as_printed"])
    key = dict(zip(xw["name_as_printed"], xw["key"]))

    studies = pd.read_excel(COLLECTION / "studies_protocols.xlsx", sheet_name="studies")
    rows = []
    for nct in studies["nct_id"]:
        path = COLLECTION / "protocols" / nct / "SoA2USDM" / "consolidated" / f"{nct}_consolidated.json"
        d = json.loads(path.read_text(encoding="utf-8"))
        acts = {a["xact_id"]: a["activity_name"] for a in d["unified_activities"]}
        for n in d["unified_annotations"]:
            for kind, pat in PATTERNS:
                if not pat.search(n["annotation_text"]):
                    continue
                names = [acts[x] for x in n["referenced_xacts"]]
                missing = [a for a in names if a not in key]
                if missing:
                    raise SystemExit(f"{nct}: names not in crosswalk: {missing}")
                # A statement on no activity (e.g. visits after V7) is kept with an empty key.
                for a in names or [""]:
                    rows.append({
                        "nct_id": nct,
                        "statement_kind": kind,
                        "activity_name": a,
                        "activity_key": key[a] if a else "",
                        "referenced_props": ";".join(str(p) for p in n["referenced_props"]),
                        "names_dsa": bool(re.search(r"\bDSA\b", n["annotation_text"])),
                        "text": re.sub(r"\s+", " ", n["annotation_text"]).strip(),
                        "source": f"soa2usdm-collections {COMMIT} {path.relative_to(COLLECTIONS)}",
                    })
    out = pd.DataFrame(rows).drop_duplicates()
    OUT.parent.mkdir(exist_ok=True)
    out.to_csv(OUT, index=False)
    print(out.groupby(["statement_kind", "names_dsa"]).size().to_string())
    print(f"{len(out)} rows -> {OUT}")


if __name__ == "__main__":
    main()
