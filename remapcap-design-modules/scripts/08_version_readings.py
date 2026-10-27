"""REMAP-CAP design modules, step 5 part 1b: R6 (statement level) and R7, version consequences.

Inputs: output/step5/inheritance_readings.csv (step 5 part 1), output/step1/sections.csv,
../usdm-master-protocol/output_remapcap/step5/core_v40_v41_diff.csv (first change per section),
the source PDFs (document dates from the running headers).
Output: output/step5/statement_versions.csv, run log on stdout.

Rules (analyst readings, README step 5):
  V-date        a document's date is the date in its own running header ("Version n Dated ...").
  V-current     an unversioned statement resolves to the Core version in force now (4.1).
  V-transition  Core 4.1 7.6.2: "DSAs dated before this Core Protocol amendment will additionally
                report the pre-specified endpoints as indicated in their respective documents and
                previous versions of the Core Protocol". "This amendment" is read as the version
                that contains the sentence (4.1). A DSA dated before Core 4.1 whose statement
                resolves to Core 7.6.1 or 7.6.2 therefore resolves to 4.1 and, additionally, 4.0.
"""
import re
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd

from rcap_docs import DOCS, DSAS  # scripts/rcap_docs.py

HERE = Path(__file__).resolve().parent.parent
SRC = HERE.parent / "usdm-master-protocol" / "sources" / "remapcap"
DIFF = HERE.parent / "usdm-master-protocol" / "output_remapcap" / "step5" / "core_v40_v41_diff.csv"
OUT = HERE / "output" / "step5"
FILES = {k: DOCS[k].file for k in ["CORE41"] + DSAS}  # scripts/rcap_docs.py
TRANSITION = ("DSAs dated before this Core Protocol amendment will additionally report the pre-specified "
              "endpoints as indicated in their respective documents and previous versions of the Core Protocol")


dates = {doc: DOCS[doc].date for doc in FILES}  # header version/date, read in scripts/rcap_docs.py
for d, v in dates.items():
    print(f"V-date {d}: {v}")

sections = pd.read_csv(HERE / "output" / "step1" / "sections.csv", dtype=str, keep_default_na=False)
t41 = sections[(sections.doc == "CORE41") & (sections.number == "7.6.2")].text.iloc[0]
assert TRANSITION in re.sub(r"pre- specified", "pre-specified", t41), "transition sentence not in Core 4.1 7.6.2"
diff = pd.read_csv(DIFF, dtype=str, keep_default_na=False).set_index("section")

rd = pd.read_csv(OUT / "inheritance_readings.csv", dtype=str, keep_default_na=False)
rows = []
for r in rd[(rd.resolution != "") & (rd.target_change != "")].itertuples():
    targets = r.resolution.split(";")
    before = dates[r.doc] < dates["CORE41"]
    endpoint = any(t in ("CORE 7.6.1", "CORE 7.6.2") for t in targets)
    if before and endpoint:
        versions, rule = "4.1 + 4.0 (additionally)", "V-current + V-transition"
    else:
        versions, rule = "4.1", "V-current"
    rows.append({"doc": r.doc, "doc_date": dates[r.doc].isoformat(), "dated_before_core_4_1": before,
                 "section": r.section, "target_phrase": r.target_phrase, "resolution": r.resolution,
                 "resolves_to_core_versions": versions, "rule": rule,
                 "first_change_in_4_1": " | ".join(diff.loc[t.split(" ")[1], "first_change"][:140]
                                                   for t in targets if t.split(" ")[1] in diff.index),
                 "status": "analyst-reading", "sentence": r.sentence})
out = pd.DataFrame(rows)
out.to_csv(OUT / "statement_versions.csv", index=False)
print(f"statements resolving to a Core section changed in 4.1: {len(out)}")
print(out.groupby(["doc", "doc_date", "resolves_to_core_versions"]).size().to_string())
