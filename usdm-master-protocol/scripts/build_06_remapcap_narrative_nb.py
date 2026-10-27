"""Generate notebooks/06_remapcap_narrative.ipynb (Plan 1, Step 6 on REMAP-CAP).

Adds the section text of Core Protocol V4.0, Core Protocol V4.1 and the
Corticosteroid DSA V6 to the Step 5 USDM JSON as NarrativeContent, the same
way Step 3 added PANDA 1.0. Nothing else in the JSON changes.

The notebook is built as a Python dict and written with json.dump.
Run:  python3 scripts/build_06_remapcap_narrative_nb.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "notebooks" / "06_remapcap_narrative.ipynb"


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
# Plan 1, Step 6 – section text of all REMAP-CAP document versions as NarrativeContent

Step 3 put the 17 PANDA 1.0 sections into the USDM JSON as `NarrativeContent`. The Core Protocol and the Corticosteroid DSA had no section content. This step adds it, so that statements and allocations (cdd-layer) can point at USDM `NarrativeContent` for every document version in scope:

| document version | source of the section text | StudyVersion holding the items |
|---|---|---|
| Core Protocol V4.0 | Step 2 `sections.csv` (`CORE`) | StudyVersion 1 |
| Core Protocol V4.1 | Core V4.1 PDF, read with the Step 2 code unchanged (as in Step 5); 7.6.3 and 7.6.4 split from 7.6.2 as in Step 5 | StudyVersion 2 |
| Corticosteroid DSA V6 | Step 2 `sections.csv` (`CS_DSA`) | StudyVersion 1 |

Rules as in Step 3: one `NarrativeContent` per numbered section, in document order, `previousId` / `nextId` along that order, `childIds` from the section number (7.6 is the parent of 7.6.1). The text goes into a `NarrativeContentItem` at `StudyVersion` level. A heading with no text of its own gets no item (`contentItemId` is 0..1). Nothing is retyped; nothing else in the JSON changes.

The Corticosteroid DSA V6 document version is shared by both StudyVersions (Step 5). Its items are placed in StudyVersion 1 only; see the log.
"""))

cells.append(code_cell(r"""
import contextlib
import copy
import hashlib
import io
import json
import os
import re
from pathlib import Path

import pandas as pd
import yaml

BASE = Path.cwd().parent
STEP2 = BASE / "output_remapcap" / "step2"
STEP5 = BASE / "output_remapcap" / "step5"
OUT_DIR = BASE / "output_remapcap" / "step6"
USDM_RDF = Path(os.environ.get("USDM_RDF_DIR", BASE.parent.parent / "GitHub" / "usdm-rdf"))
assert (BASE / "notebooks" / "02_remapcap_structure.ipynb").is_file(), "run from usdm-master-protocol/notebooks/"
assert (USDM_RDF / "downloads" / "dataStructure.yml").is_file(), f"usdm-rdf not found at {USDM_RDF} (set USDM_RDF_DIR)"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL = yaml.safe_load((USDM_RDF / "downloads" / "dataStructure.yml").read_text())

sections = pd.read_csv(STEP2 / "sections.csv").fillna({"text": ""})
usdm = json.loads((STEP5 / "remapcap_usdm_v2.json").read_text())
study = usdm["study"]
LOG = []


def log(obj, attribute, status, value="", evidence="", note=""):
    LOG.append({"object": obj, "attribute": attribute, "status": status,
                "value": str(value)[:300], "evidence": evidence, "note": note})
"""))

cells.append(markdown_cell(r"""
## Core Protocol V4.1 sections (Step 2 code, as in Step 5)
"""))

cells.append(code_cell(r"""
step2_nb = json.loads((BASE / "notebooks" / "02_remapcap_structure.ipynb").read_text())
step2_src = {c["id"]: "".join(c["source"]) for c in step2_nb["cells"] if c["cell_type"] == "code"}
g = {"__name__": "__main__"}
with contextlib.redirect_stdout(io.StringIO()):
    exec(step2_src["cell-01"], g)
g["DOCS"] = {
    "CORE": "superseded/REMAP-CAP-Core-Protocol-V4-05-November-2024_CLEAN-m9gf.pdf",
    "CORE_41": "current/REMAP-CAP-Core-Protocol-V41-29-MAY-2026_CLEAN.pdf",
    "CS_DSA": "current/REMAP-CAP-Corticosteroid-DSA-V6-05-NOV-2024_CLEAN.pdf",
}
manifest = g["manifest"]
for role, rel in g["DOCS"].items():
    assert hashlib.sha256((g["SRC"] / rel).read_bytes()).hexdigest() == manifest.loc[rel, "sha256"], f"{role}: differs from manifest"
with contextlib.redirect_stdout(io.StringIO()):
    for key in ("cell-03", "cell-05", "cell-07", "cell-09"):
        exec(step2_src[key], g)
S = g["sections"]
assert int((~g["located"]["CORE_41"].found).sum()) == 0, "V4.1 heading not found"
for doc in ("CORE", "CS_DSA"):
    again = S[S.doc == doc][["number", "text"]].fillna("").reset_index(drop=True)
    step2 = sections[sections.doc == doc][["number", "text"]].reset_index(drop=True)
    assert again.equals(step2), f"{doc}: re-read differs from Step 2 sections.csv"
v41 = S[S.doc == "CORE_41"].reset_index(drop=True)

core40 = sections[sections.doc == "CORE"].reset_index(drop=True)
assert list(v41.number) == list(core40.number), "V4.1 numbered sections differ from V4.0"

rows41 = v41.to_dict("records")
k = next(i for i, r in enumerate(rows41) if r["number"] == "7.6.2")
m = re.search(r"\s7\.6\.3\.\s*Exploratory outcomes\s(.*?)\s7\.6\.4\.\s*(Adaptations to the primary endpoint in the event of a pandemic)\s(.*)$",
              rows41[k]["text"])
assert m, "7.6.3 / 7.6.4 headings not found inside V4.1 7.6.2"
split = [
    {**rows41[k], "number": "7.6.3", "title": "Exploratory outcomes", "level": 4.0, "text": m.group(1)},
    {**rows41[k], "number": "7.6.4", "title": m.group(2), "level": 4.0, "text": m.group(3)},
]
rows41[k] = {**rows41[k], "text": rows41[k]["text"][:m.start()].strip()}
rows41[k + 1:k + 1] = split
core41 = pd.DataFrame(rows41)
for r in split:
    r_id = f"CORE_41 {r['number']}"
    log(r_id, "sectionNumber", "derived", r["number"], "CORE_41 7.6.2 (body)",
        "heading in the V4.1 body but not in the V4.1 TOC; split from 7.6.2 by heading text, as in Step 5")
print("CORE_41 sections:", len(core41), "| CORE:", len(core40), "| CS_DSA:", int((sections.doc == "CS_DSA").sum()))
"""))

cells.append(markdown_cell(r"""
## NarrativeContent per document version

Ids continue the Step 3 numbering (`NarrativeContent_n`, `NarrativeContentItem_n`), after the highest number already in the JSON.
"""))

cells.append(code_cell(r"""
def max_n(prefix):
    found = []

    def walk(o):
        if isinstance(o, dict):
            i = o.get("id", "")
            mm = re.fullmatch(re.escape(prefix) + r"_(\d+)", i) if isinstance(i, str) else None
            if mm:
                found.append(int(mm.group(1)))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(usdm)
    return max(found) if found else 0


_counter = {"NarrativeContent": max_n("NarrativeContent"), "NarrativeContentItem": max_n("NarrativeContentItem")}


def new_id(cls):
    _counter[cls] += 1
    return f"{cls}_{_counter[cls]}"


def build_contents(label, secs, item_list):
    contents = []
    for r in secs.itertuples():
        c = {"id": new_id("NarrativeContent"), "name": f"{label} {r.number}", "sectionNumber": r.number,
             "sectionTitle": r.title, "displaySectionTitle": True, "displaySectionNumber": True,
             "childIds": [], "instanceType": "NarrativeContent"}
        if r.text:
            item = {"id": new_id("NarrativeContentItem"), "name": f"{label} {r.number}", "text": r.text,
                    "instanceType": "NarrativeContentItem"}
            item_list.append(item)
            c["contentItemId"] = item["id"]
        else:
            log(c["id"], "contentItemId", "not_in_document", "", f"{label} {r.number} p{r.start_page}",
                "heading only; no text before the next numbered heading")
        contents.append(c)
    for i, c in enumerate(contents):
        if i > 0:
            c["previousId"] = contents[i - 1]["id"]
        if i + 1 < len(contents):
            c["nextId"] = contents[i + 1]["id"]
    by_number = {c["sectionNumber"]: c for c in contents}
    for c in contents:
        if "." in c["sectionNumber"]:
            parent = c["sectionNumber"].rsplit(".", 1)[0]
            assert parent in by_number, f"{label} {c['sectionNumber']}: parent {parent} not a numbered section"
            by_number[parent]["childIds"].append(c["id"])
    return contents


docs = {d["name"]: d for d in study["documentedBy"]}
core_doc = docs["REMAP-CAP Core Protocol"]
dsa_doc = docs["Corticosteroid Domain-Specific Appendix"]
core_v40, core_v41 = core_doc["versions"]
assert (core_v40["version"], core_v41["version"]) == ("4.0", "4.1")
(dsa_v6,) = dsa_doc["versions"]
assert dsa_v6["version"] == "6"
sv1, sv2 = study["versions"]
assert core_v40["id"] in sv1["documentVersionIds"] and core_v41["id"] in sv2["documentVersionIds"]
assert dsa_v6["id"] in sv1["documentVersionIds"] and dsa_v6["id"] in sv2["documentVersionIds"]
for dv in (core_v40, core_v41, dsa_v6):
    assert not dv.get("contents"), f"{dv['id']} already has contents"

core_v40["contents"] = build_contents("CORE", core40, sv1["narrativeContentItems"])
core_v41["contents"] = build_contents("CORE_41", core41, sv2["narrativeContentItems"])
dsa_v6["contents"] = build_contents("CS_DSA", sections[sections.doc == "CS_DSA"].reset_index(drop=True), sv1["narrativeContentItems"])
log(dsa_v6["id"], "contents", "not_expressible", "", "Step 5 decision: CS_DSA V6 shared by StudyVersion 1 and 2",
    "NarrativeContentItem sits at StudyVersion level, the document version is shared; its items are placed in StudyVersion 1 only, so StudyVersion 2 holds a document version whose text it does not contain")
for dv in (core_v40, core_v41, dsa_v6):
    n_items = sum(1 for c in dv["contents"] if "contentItemId" in c)
    print(f"{dv['id']:40s} sections={len(dv['contents']):4d} with text={n_items:4d}")
"""))

cells.append(markdown_cell(r"""
## Self-check (as in Step 5)

Every object has a known class, unique id, only model attributes, and resolvable references. Required attributes of the new objects are all present.
"""))

cells.append(code_cell(r"""
def model_attrs(cls):
    out = {}
    for sc in MODEL[cls].get("Super Classes", []) or []:
        out.update(model_attrs(sc["$ref"].split("/")[-1]))
    out.update(MODEL[cls].get("Attributes", {}) or {})
    return out


objects = {}


def walk(o):
    if isinstance(o, dict):
        if "instanceType" in o:
            assert o["instanceType"] in MODEL, o["instanceType"]
            assert o["id"] not in objects, f"duplicate id {o['id']}"
            objects[o["id"]] = o
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)


walk(study)
for oid, o in objects.items():
    attrs = model_attrs(o["instanceType"])
    for k, v in o.items():
        assert k in attrs, f"{o['instanceType']}.{k}"
        if attrs[k]["Relationship Type"] == "Ref":
            for ref in (v if isinstance(v, list) else [v]):
                assert ref in objects, f"{oid}.{k} -> {ref}"
new = [o for o in objects.values() if o["instanceType"] in ("NarrativeContent", "NarrativeContentItem")]
for o in new:
    for a, spec in model_attrs(o["instanceType"]).items():
        if spec["Cardinality"].startswith("1"):
            assert a in o, f"{o['id']} missing {a}"
print("objects:", len(objects), "| NarrativeContent + items:", len(new))
"""))

cells.append(markdown_cell(r"""
## Outputs

| file | content |
|---|---|
| `remapcap_usdm_v3.json` | Step 5 JSON + NarrativeContent for Core V4.0, Core V4.1, CS_DSA V6 |
| `mapping_log_step6.csv` | decisions and absences logged in this step |

Validation: `python3 scripts/04_run_usdm_rdf_validator.py output_remapcap/step6/remapcap_usdm_v3.json output_remapcap/step6/validation`
"""))

cells.append(code_cell(r"""
usdm["systemVersion"] = "2026-10-25 step6"
with open(OUT_DIR / "remapcap_usdm_v3.json", "w", encoding="utf-8") as f:
    json.dump(usdm, f, indent=1, ensure_ascii=False)
pd.DataFrame(LOG).to_csv(OUT_DIR / "mapping_log_step6.csv", index=False)
for f in sorted(OUT_DIR.iterdir()):
    if f.is_file():
        print(f"{f.name:26s} {f.stat().st_size:>10,d} bytes")
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
