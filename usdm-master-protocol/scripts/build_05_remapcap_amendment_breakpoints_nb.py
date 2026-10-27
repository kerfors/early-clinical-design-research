"""Generate notebooks/05_remapcap_amendment_breakpoints.ipynb (Plan 1, Step 5 on REMAP-CAP).

The notebook is built as a Python dict and written with json.dump.
Run:  python3 scripts/build_05_remapcap_amendment_breakpoints_nb.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "notebooks" / "05_remapcap_amendment_breakpoints.ipynb"


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
# Plan 1, Step 5 – Core Protocol V4.1 as amendment, and the breakpoint table

1. Read Core Protocol V4.1 (29 May 2026) with the **Step 2 code, unchanged** (cells are loaded from `02_remapcap_structure.ipynb` and executed with a different `DOCS` list).
2. Compare Core V4.0 and V4.1 section by section.
3. Trace what the Corticosteroid DSA V6 inherits from the Core, and which of it changed in V4.1.
4. Add a second `StudyVersion` (Core 4.1 / PANDA 1.0 / Corticosteroid DSA 6) with a `StudyAmendment` to the Step 3 JSON. The DSA and PANDA document versions are shared by reference; everything inside the study version is copied, then the Core-derived content is replaced with V4.1 text.
5. Write the breakpoint table: each breakpoint with USDM element and document evidence (REMAP-CAP, and CPMP from Step 1 where it applies).

Rules as in Step 3: text from the documents by section number; a value only where a document states it; anything else logged.
"""))

cells.append(code_cell(r"""
import contextlib
import copy
import difflib
import hashlib
import io
import json
import os
import re
from pathlib import Path

import pandas as pd
import yaml

BASE = Path.cwd().parent
OUT_DIR = BASE / "output_remapcap" / "step5"
STEP3 = BASE / "output_remapcap" / "step3"
USDM_RDF = Path(os.environ.get("USDM_RDF_DIR", BASE.parent.parent / "GitHub" / "usdm-rdf"))
assert (BASE / "notebooks" / "02_remapcap_structure.ipynb").is_file(), "run from usdm-master-protocol/notebooks/"
assert (USDM_RDF / "downloads" / "dataStructure.yml").is_file(), f"usdm-rdf not found at {USDM_RDF} (set USDM_RDF_DIR)"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL = yaml.safe_load((USDM_RDF / "downloads" / "dataStructure.yml").read_text())

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
for key in ("cell-03", "cell-05", "cell-07", "cell-09"):
    exec(step2_src[key], g)
S = g["sections"]
print(S.groupby("doc").agg(sections=("number", "size"), chars=("n_chars", "sum")))
print("headings not found:", int((~pd.concat(g["located"].values()).found).sum()))
"""))

cells.append(markdown_cell(r"""
## Core V4.0 → V4.1, section by section

Similarity = `difflib.SequenceMatcher` ratio on the section text (1.0 = identical). Sections are matched on number; no section was added or removed in the TOC and no title changed.

Known defect in V4.1: the body has two new headings, **7.6.3 Exploratory outcomes** and **7.6.4 Adaptations to the primary endpoint in the event of a pandemic**, that are **not in the V4.1 TOC**. TOC-driven splitting therefore puts them inside 7.6.2. They are split off here by their heading text and reported separately.
"""))

cells.append(code_cell(r"""
v40 = S[S.doc == "CORE"].set_index("number")
v41 = S[S.doc == "CORE_41"].set_index("number")
assert set(v40.index) == set(v41.index)
assert (v40.title == v41.title.reindex(v40.index)).all()

text41 = v41.text.to_dict()
m = re.search(r"\s7\.6\.3\.\s*Exploratory outcomes\s(.*?)\s7\.6\.4\.\s*(Adaptations to the primary endpoint in the event of a pandemic)\s(.*)$",
              text41["7.6.2"])
assert m, "7.6.3 / 7.6.4 headings not found inside V4.1 7.6.2"
text41["7.6.3"] = m.group(1)
text41["7.6.4"] = m.group(3)
text41["7.6.2"] = text41["7.6.2"][:m.start()].strip()
titles41 = dict(v41.title)
titles41["7.6.3"] = "Exploratory outcomes"
titles41["7.6.4"] = m.group(2)


def sentences(t):
    return [x for x in re.split(r"(?<=[.;:])\s+", t) if x]


rows = []
for n in sorted(set(v40.index) | {"7.6.3", "7.6.4"}, key=lambda x: [int(p) for p in x.split(".")]):
    a = v40.text.get(n, "")
    b = text41[n]
    if a == b:
        continue
    diff = [l for l in difflib.unified_diff(sentences(a), sentences(b), lineterm="", n=0)
            if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    rows.append({"section": n, "title": titles41[n], "in_v40_toc": n in v40.index, "in_v41_toc": n in v41.index,
                 "similarity": round(difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(), 3),
                 "sentences_removed": sum(l[0] == "-" for l in diff), "sentences_added": sum(l[0] == "+" for l in diff),
                 "first_change": next((l for l in diff), "")[:200]})
core_diff = pd.DataFrame(rows)
core_diff[["section", "title", "in_v41_toc", "similarity", "sentences_removed", "sentences_added"]]
"""))

cells.append(markdown_cell(r"""
## What the Corticosteroid DSA inherits, and what changed

Each row is one Step 2 `refers_to` statement from CS_DSA to the Core (or "Core Protocol documents"). The column `core_location` is an **analyst reading**: the Core (or PANDA) section where that content is found, chosen by topic, with the reason in `basis`. The DSA itself never cites a section number. `changed_in_v41` is then computed from the diff above.
"""))

cells.append(code_cell(r"""
INHERITED = [
    ("7", "primary endpoint specified in the Core Protocol documents", "CORE 7.6.1", "primary endpoint definition"),
    ("8.1.1", "Age Strata, as defined in Core Protocol documents", "PANDA 2", "age categories are defined in PANDA §2, not in the Core"),
    ("8.1.2", "These States are defined in Core Protocol documents", "PANDA 4.3", "Moderate/Severe State defined in PANDA §4.3"),
    ("8.2", "platform-level inclusion and none of the platform-level exclusion criteria", "CORE 7.4.1; CORE 7.4.2", "platform inclusion / exclusion criteria"),
    ("8.5.1", "primary outcome as specified in Core Protocol documents", "CORE 7.6.1", "primary endpoint definition"),
    ("8.5.2", "All secondary endpoints as specified in the Core Protocol", "CORE 7.6.2", "secondary endpoints"),
    ("9.3", "Refer to relevant core protocol documents for criteria for the discontinuation", "CORE 8.6", "Core 8.6 'Criteria for discontinuation of an allocated intervention within the Platform'"),
    ("10.1", "stopping rules for this domain are those outlined in the relevant Core Protocol documents", "CORE 7.8.6; CORE 7.8.7", "statistical triggers and actions"),
    ("10.2", "borrowing between all strata as specified in Core Protocol documents", "CORE 7.8.3", "treatment-by-strata borrowing (gamma)"),
    ("10.3", "the cap on the maximum or minimum proportion of patients assigned to an intervention", "CORE 7.8.7", "RAR allocation cap"),
    ("10.7", "threshold probability for statistical triggers for superiority, efficacy, and inferiority", "CORE 7.8.6", "statistical triggers"),
    ("10.8", "threshold probability of a statistical trigger for futility", "CORE 7.8.6", "futility trigger"),
]
dsa = S[S.doc == "CS_DSA"].set_index("number")
step2_sections = pd.read_csv(BASE / "output_remapcap" / "step2" / "sections.csv")
step2_keys = set(zip(step2_sections.doc, step2_sections.number))
changed = set(core_diff.section)
rows = []
for dsa_sec, phrase, location, basis in INHERITED:
    assert phrase.lower() in dsa.loc[dsa_sec, "text"].lower(), f"phrase not in CS_DSA {dsa_sec}: {phrase}"
    targets = [t.strip() for t in location.split(";")]
    for t in targets:
        assert tuple(t.split(" ")) in step2_keys, f"{t} not a Step 2 section"
    core_changed = [t for t in targets if t.startswith("CORE") and t.split(" ")[1] in changed]
    rows.append({"dsa_section": dsa_sec, "dsa_statement": phrase, "core_location": location, "basis": basis,
                 "changed_in_v41": "; ".join(core_changed)})
inherited = pd.DataFrame(rows)
inherited
"""))

cells.append(markdown_cell(r"""
## Which endpoint does the unchanged DSA have under Core V4.1?

CS_DSA §8.5.1 takes "the primary outcome as specified in Core Protocol documents", without a version. Core V4.1 §7.6.2 states the transition rule: "DSAs dated before this Core Protocol amendment will additionally report the pre-specified endpoints as indicated in their respective documents and previous versions of the Core Protocol". CS_DSA V6 (5 Nov 2024) is dated before Core V4.1 (29 May 2026).

Reading used for StudyVersion 2 (logged as `derived` / `ambiguous_in_document`):
- primary endpoint of the domain = the V4.1 primary endpoint (the unversioned reference resolves to the Core in force);
- additionally reported = the V4.0 primary endpoint "Survival and Recovery Trajectory". V4.1 lists it as an exploratory outcome (§7.6.3); for a pre-V4.1 DSA the documents do not say at which level it is reported, so its `level` is left out.
"""))

cells.append(code_cell(r"""
rule = "DSAs dated before this Core Protocol amendment will additionally report the pre-specified endpoints"
assert rule in text41["7.6.2"], "transition rule not found in V4.1 7.6.2"
assert "Survival and Recovery Trajectory" in text41["7.6.3"]
primary41 = re.split(r"(?<=[.!?])\s+", text41["7.6.1"].strip(), maxsplit=1)[0]
key41 = [b.strip() for b in text41["7.6.2"].split("for the trial are:")[1].split("There will be a list")[0].split("•") if b.strip()]
assert key41 == ["Mortality, censored at 90 days", "Days alive and free of organ-failure support to day 28",
                 "Days alive and out of hospital to day 28"], key41
srt40 = re.split(r"(?<=[.!?])\s+", v40.loc["7.6.1", "text"].strip(), maxsplit=1)[0]
print("V4.1 primary endpoint:", primary41[:160], "...")
print("V4.1 key secondary:", key41)
"""))

cells.append(markdown_cell(r"""
## StudyVersion 2 with StudyAmendment

- Core document gets a second version (4.1, Approved, approval date from V4.1 §2.2.9).
- StudyVersion 2 = deep copy of StudyVersion 1 with new ids (suffix `_v41`). References to document versions stay shared: PANDA 1.0 and CS_DSA 6 are the same objects as in StudyVersion 1; the Core reference points to the 4.1 version.
- Replaced with V4.1 text: Core primary/secondary objective (6.1, 6.2), Core primary endpoint (7.6.1), key secondary endpoints (7.6.2); domain endpoints per the transition rule above.
- Unchanged but copied: all 16 eligibility criteria and items, 3 interventions, 3 arms, PANDA narrative items. Checked: Core 7.4.1 and 7.4.2 are identical in V4.0 and V4.1.
- `StudyAmendment`: V4.1 calls itself "this Core Protocol amendment" (§7.6.2). `number` 4.1 and approval date from §2.2.9. One `StudyChange` per changed section, each with a `DocumentContentReference` to the Core document. Not stated anywhere: amendment `summary`, `primaryReason`, `geographicScopes`; change `summary` and `rationale`.
"""))

cells.append(code_cell(r"""
usdm = json.loads((STEP3 / "remapcap_usdm.json").read_text())
study = usdm["study"]
LOG = []


def log(obj, attribute, status, value="", evidence="", note=""):
    LOG.append({"object": obj, "attribute": attribute, "status": status, "value": str(value)[:300], "evidence": evidence, "note": note})


docs = {d["name"]: d for d in study["documentedBy"]}
core_doc = docs["REMAP-CAP Core Protocol"]
v1 = study["versions"][0]
core_v40 = core_doc["versions"][0]
history = text41["2.2.9"]
m41 = re.search(r"Version 4\.1: Approved by the ITSC on (\d{1,2}) (\w+) (\d{4})", history)
assert m41, history
approved41 = pd.to_datetime(" ".join(m41.groups()), format="%d %B %Y").date().isoformat()
core_v41 = copy.deepcopy(core_v40)


def reid(node, suffix, mapping):
    if isinstance(node, dict):
        if "instanceType" in node and "id" in node:
            new = node["id"] + suffix
            mapping[node["id"]] = new
            node["id"] = new
        for v in node.values():
            reid(v, suffix, mapping)
    elif isinstance(node, list):
        for v in node:
            reid(v, suffix, mapping)


reid(core_v41, "_v41", {})
core_v41["version"] = "4.1"
core_v41["dateValues"][0]["dateValue"] = approved41
core_v41["dateValues"][0]["name"] = "CORE 4.1 approval"
core_doc["versions"].append(core_v41)
log(core_v41["id"], "version", "mapped", "4.1", "CORE_41 cover page")
log(core_v41["dateValues"][0]["id"], "dateValue", "mapped", approved41, "CORE_41 2.2.9 'Core Protocol Version History'")
log(core_v41["dateValues"][0]["id"], "geographicScopes", "required_not_in_document", "", "CORE_41 2.2.9", "approval by the ITSC, no geographic scope stated")

v2 = copy.deepcopy(v1)
idmap = {}
reid(v2, "_v41", idmap)
REF_KEYS = {a for c in MODEL.values() for a, s in (c.get("Attributes") or {}).items() if s["Relationship Type"] == "Ref"}


def remap_refs(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in REF_KEYS:
                node[k] = [idmap.get(x, x) for x in v] if isinstance(v, list) else idmap.get(v, v)
            else:
                remap_refs(v)
    elif isinstance(node, list):
        for v in node:
            remap_refs(v)


remap_refs(v2)
swap = {core_v40["id"]: core_v41["id"]}
v2["documentVersionIds"] = [swap.get(x, x) for x in v2["documentVersionIds"]]
design = v2["studyDesigns"][0]
design["documentVersionIds"] = [swap.get(x, x) for x in design["documentVersionIds"]]
v2["versionIdentifier"] = "Core 4.1 / PANDA 1.0 / Corticosteroid DSA 6"
log(v2["id"], "versionIdentifier", "derived", v2["versionIdentifier"], "decision 2026-10-24", "set of document versions")
log(v2["id"], "(copy)", "not_expressible", "", "", "a new Core version needs a full new StudyVersion; unchanged DSA content (criteria, interventions, arms) is copied, not shared")

for n in ("7.4.1", "7.4.2"):
    assert v40.loc[n, "text"] == text41[n], f"Core {n} changed"
obj_p, obj_s, obj_d = design["objectives"]
obj_p["text"] = text41["6.1"]
obj_s["text"] = text41["6.2"]
log(obj_p["id"], "text", "mapped_copy_from_core", text41["6.1"], "CORE_41 6.1 'Primary objective'")
log(obj_s["id"], "text", "mapped_copy_from_core", text41["6.2"], "CORE_41 6.2 'Secondary objectives'")
obj_p["endpoints"][0]["text"] = primary41
log(obj_p["endpoints"][0]["id"], "text", "mapped_copy_from_core", primary41, "CORE_41 7.6.1 'Primary Endpoint'")
sec_template = obj_s["endpoints"][0]
obj_s["endpoints"] = []
for k, t in enumerate(key41, start=1):
    e = copy.deepcopy(sec_template)
    e["id"] = f"Endpoint_v41_sec{k}"
    e["level"]["id"] = f"Code_v41_sec{k}"
    e["name"] = f"CORE_41 7.6.2 #{k}"
    e["text"] = t
    obj_s["endpoints"].append(e)
    log(e["id"], "text", "mapped_copy_from_core", t, "CORE_41 7.6.2 'Secondary Endpoints'")
    log(e["id"], "purpose", "required_not_in_document", "", "CORE_41 7.6.2", "purpose not stated")

dom_primary = obj_d["endpoints"][0]
dom_primary["text"] = primary41
log(dom_primary["id"], "text", "derived", primary41, "CS_DSA 8.5.1 -> CORE_41 7.6.1",
    "unversioned 'Core Protocol documents' resolved to the Core in force (4.1)")
additional = copy.deepcopy(dom_primary)
additional["id"] = "Endpoint_v41_additional"
additional["name"] = "CORE 7.6.1 (V4.0) additionally reported"
additional["text"] = srt40
del additional["level"]
obj_d["endpoints"].insert(1, additional)
log(additional["id"], "text", "derived", srt40, "CORE_41 7.6.2 transition rule; CORE 7.6.1 (V4.0)",
    "DSA dated before Core 4.1 additionally reports the pre-specified endpoint of the earlier Core version")
log(additional["id"], "level", "ambiguous_in_document", "", "CORE_41 7.6.2; CORE_41 7.6.3",
    "V4.1 lists Survival and Recovery Trajectory as exploratory; for a pre-V4.1 DSA the level is not stated")
log(additional["id"], "purpose", "required_not_in_document", "", "CORE_41 7.6.2", "purpose not stated")

changes = []
for r in core_diff.itertuples():
    chg = {"id": f"StudyChange_{len(changes) + 1}", "name": f"Core {r.section} {r.title}",
           "changedSections": [{"id": f"DocumentContentReference_{len(changes) + 1}", "sectionNumber": r.section,
                                "sectionTitle": r.title, "appliesToId": core_doc["id"], "instanceType": "DocumentContentReference"}],
           "instanceType": "StudyChange"}
    changes.append(chg)
    log(chg["id"], "changedSections", "derived", f"{r.section} {r.title}", "Core 4.0 vs 4.1 text comparison",
        "change found by comparing the two versions; not stated in V4.1")
    log(chg["id"], "summary", "required_not_in_document", "", "CORE_41", "V4.1 has no summary of changes")
    log(chg["id"], "rationale", "required_not_in_document", "", "CORE_41", "no rationale stated")
    log(chg["changedSections"][0]["id"], "appliesToId", "not_expressible", core_doc["id"], "",
        "points to the Core document, not to version 4.0 or 4.1")
amendment = {"id": "StudyAmendment_1", "name": "Core Protocol Version 4.1", "number": "4.1",
             "dateValues": [copy.deepcopy(core_v41["dateValues"][0])], "changes": changes, "instanceType": "StudyAmendment"}
amendment["dateValues"][0]["id"] = "GovernanceDate_amendment_1"
amendment["dateValues"][0]["type"]["id"] = "Code_amendment_1"
v2["amendments"] = [amendment]
log(amendment["id"], "number", "derived", "4.1", "CORE_41 2.2.9; CORE_41 7.6.2 'this Core Protocol amendment'")
for attr in ("summary", "primaryReason", "geographicScopes"):
    log(amendment["id"], attr, "required_not_in_document", "", "CORE_41", "not stated")
log(amendment["dateValues"][0]["id"], "geographicScopes", "required_not_in_document", "", "CORE_41 2.2.9", "not stated")
log(amendment["id"], "(scope)", "not_expressible", "", "CS_DSA 8.5.1; CORE_41 7.6.2",
    "the amendment changes the Core only, but changes the effective endpoint of an unchanged DSA; StudyChange can only point at Core sections")
study["versions"].append(v2)
print("StudyVersion 2:", v2["id"], "| changes:", len(changes))
"""))

cells.append(markdown_cell(r"""
## Self-check (as in Step 3)
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
missing = []
for oid, o in objects.items():
    attrs = model_attrs(o["instanceType"])
    for k, v in o.items():
        assert k in attrs, f"{o['instanceType']}.{k}"
        if attrs[k]["Relationship Type"] == "Ref":
            for ref in (v if isinstance(v, list) else [v]):
                assert ref in objects, f"{oid}.{k} -> {ref}"
    for a, spec in attrs.items():
        if spec["Cardinality"].startswith("1") and (a not in o or (spec["Cardinality"] == "1..*" and len(o[a]) == 0)):
            missing.append((oid, o["instanceType"], a))

step3_log = pd.read_csv(STEP3 / "mapping_log.csv")
known = {(r.object, r.attribute) for r in step3_log.itertuples() if r.status in ("required_not_in_document", "not_expressible")}
known |= {(r["object"], r["attribute"]) for r in LOG if r["status"] in ("required_not_in_document", "not_expressible", "ambiguous_in_document")}
unexplained = [m for m in missing if (m[0], m[2]) not in known and (re.sub(r"_v41$", "", m[0]), m[2]) not in known]
assert not unexplained, unexplained
print("objects:", len(objects), "| required absent:", len(missing), "(all logged in Step 3 or Step 5)")
"""))

cells.append(markdown_cell(r"""
## Breakpoint table

One row per breakpoint. `kind`: **model** – USDM v4.0.0 cannot express it; **mapping** – USDM can hold it, but only by copying or by a convention not in the model; **content** – required by USDM, not stated in the protocol text. `area` uses the five Plan 1 headings. Every evidence pointer is checked against the logs and section tables before writing.
"""))

cells.append(code_cell(r"""
BREAKPOINTS = [
    ("substudy unit", "model", "No class for a domain / substudy. The Corticosteroid domain is a StudyDesign; the platform (Core) has no design of its own because StudyDesign needs arms, cells, epochs.",
     "StudyVersion.studyDesigns; StudyDesign.arms 1..*",
     "Step 3 decision; CORE 2.2.3 'Domain-Specific Appendices'", "CPMP: master (NCT05986292) has no interventions of its own; each ISA is its own study with own NCT"),
    ("three layers", "model", "Document hierarchy is expressible (Core childIds = PANDA, DSA), but appendices have no document type: value set C215477 has only 'Protocol'.",
     "StudyDefinitionDocument.childIds; StudyDefinitionDocument.type",
     "CORE 2.2; PANDA and CS_DSA title pages", "CPMP: same three layers (master, DSA CPMP(n), ISA)"),
    ("three layers", "model", "The population layer (PANDA: age strata, illness states) has no class; states are dynamic and allow re-randomisation. Kept as narrative.",
     "StudyDesignPopulation.cohorts; StudyCohort", "PANDA 2; PANDA 4.3; CS_DSA 8.1.1; CS_DSA 8.1.2",
     "CPMP: DSA = disease-state layer (not public)"),
    ("three layers", "mapping", "The DSA reaches the population layer only through 'Core Protocol documents' (13 uses); strata and states are defined in PANDA, not in the Core.",
     "(no element)", "CS_DSA 8.1.1; CS_DSA 8.1.2; CORE 7.8.3", ""),
    ("inherited content", "model", "Inherited Core endpoint can only be copied into the domain design; Endpoint is composed (Value), not referenceable.",
     "Objective.endpoints (Value)", "CS_DSA 8.5.1; CORE 7.6.1", "CPMP: ISA states objectives/endpoints are in master and DSA"),
    ("inherited content", "mapping", "Domain eligibility = platform + domain criteria in one flat list; the layer survives only in EligibilityCriterion.identifier.",
     "StudyDesign.eligibilityCriteria; StudyVersion.eligibilityCriterionItems", "CS_DSA 8.2; CORE 7.4.1; CORE 7.4.2", "CPMP: ISA eligibility delegates to master and DSA"),
    ("inherited content", "model", "Core defaults that a DSA may override ('unless otherwise specified in a DSA', 6 statements) and delegations to DSAs (15) have no representation.",
     "(no element)", "CORE 7.5.2; CORE 7.6; CORE 7.8.7", ""),
    ("inherited content", "model", "Intervention-level exclusion conditional on site regulatory approval (pregnancy, dexamethasone).",
     "EligibilityCriterion (design level only)", "CS_DSA 8.2.3", ""),
    ("inherited content", "model", "Arm available only in one illness state (hydrocortisone, Severe State only).",
     "StudyArm; StudyCell", "CS_DSA 8.3.3", ""),
    ("version granularity", "model", "No binding of a DSA version to a Core version; DSA references are unversioned ('the Core Protocol').",
     "StudyVersion.documentVersionIds; StudyDefinitionDocument.childIds", "CS_DSA 2; PANDA 6", ""),
    ("version granularity", "model", "A Core amendment changes the effective primary endpoint of an unchanged DSA (V4.1 transition rule); StudyAmendment/StudyChange can only cite Core sections.",
     "StudyAmendment.changes; StudyChange.changedSections", "CORE_41 7.6.2; CORE_41 7.6.1; CS_DSA 8.5.1", ""),
    ("version granularity", "model", "DocumentContentReference.appliesToId points to the document, not to a document version.",
     "DocumentContentReference.appliesToId", "Step 5 StudyChange_1..", ""),
    ("version granularity", "mapping", "A new Core version needs a complete new StudyVersion; unchanged DSA content is copied (16 criteria, 3 interventions, 3 arms).",
     "Study.versions; StudyVersion (composition)", "Step 5 StudyVersion 2", ""),
    ("version granularity", "model", "Master Protocol Indicator: both published M11 mappings (HL7 CSP IG ballot May 2026 row 83, DDF-RA v4.0.0 row 88) target StudyDefinitionDocumentVersion.children, the location before DDF-RA #614 (closed) moved it to the document; in v4.0.0 only StudyDefinitionDocument.childIds can carry it, the same for every version.",
     "StudyDefinitionDocument.childIds", "m11-rdf reports/d2-residue.csv", ""),
    ("version granularity", "content", "Version histories give version numbers and approval dates only: no amendment summary, reason, scope or change rationale.",
     "StudyAmendment.summary, primaryReason, geographicScopes; StudyChange.summary, rationale", "CORE 2.2.9; CORE_41 2.2.9; CS_DSA 3.1", "CPMP: ISA and master posted with amendment summary tables"),
    ("version granularity", "content", "Website listing and document content disagree (COVID-19 Antiviral II current V1.1 older than superseded V2; Immunoglobulin 2.2 file date vs document date); V4.1 TOC misses 7.6.3 and 7.6.4.",
     "(source quality)", "remapcap_inventory.csv; CORE_41 7.6.2", ""),
    ("version granularity", "model", "Versions branch by region (Immunoglobulin 2.2 Canada, 2.3 USA, 2.4.2 AUS, 2.5 NZ; Core 3.1 UK); Study.versions has no predecessor link and no branch or region qualifier.",
     "Study.versions; StudyVersion.versionIdentifier", "remapcap_inventory.csv", ""),
    ("substudy identity", "model", "One registry entry for the whole platform (NCT02735707); a domain has no identifier of its own.",
     "StudyIdentifier (StudyVersion level only)", "CORE 2.4", "CPMP: opposite pattern, master and each ISA have own NCT (FDA Master Protocols guidance Appendix C)"),
    ("substudy identity", "content", "Universal Trial Number stated, issuing organization not; registry organization identifier not stated.",
     "StudyIdentifier.scopeId; Organization.identifier", "CORE 2.4", ""),
    ("codes", "model", "Code.codeSystemVersion is 1..1; no CT package date in any source. Value records where the code came from.",
     "Code.codeSystemVersion", "Step 3 code helper", ""),
    ("content gaps", "content", "Required, not stated in the documents: design model, rationale, epochs, cells; arm type; intervention role and type ('No corticosteroid' has no substance); endpoint purpose; domain objective level; template name.",
     "see mapping_log.csv", "Step 3 mapping_log.csv", ""),
]
bp = pd.DataFrame(BREAKPOINTS, columns=["area", "kind", "breakpoint", "usdm_element", "evidence_remapcap", "cpmp_note"])
bp.insert(0, "id", [f"BP{k:02d}" for k in range(1, len(bp) + 1)])

section_keys = set(zip(S.doc, S.number)) | {("CORE_41", "7.6.3"), ("CORE_41", "7.6.4")} | step2_keys
for r in bp.itertuples():
    for ref in re.findall(r"\b(CORE_41|CORE|PANDA|CS_DSA) (\d+(?:\.\d+)*)\b", r.evidence_remapcap):
        assert ref in section_keys, f"{r.id}: evidence {ref} not a section"
print(bp.groupby(["area", "kind"]).size())
"""))

cells.append(markdown_cell(r"""
## Write outputs

| File | Content |
|---|---|
| `core_v40_v41_diff.csv` | changed Core sections, with similarity and sentence counts |
| `inherited_from_core.csv` | CS_DSA inheritance statements, analyst Core location, changed in V4.1 |
| `remapcap_usdm_v2.json` | Step 3 JSON + Core 4.1 document version + StudyVersion 2 with StudyAmendment |
| `mapping_log_step5.csv` | mapping decisions added in this step |
| `breakpoints.csv`, `breakpoints.md` | the breakpoint table |
"""))

cells.append(code_cell(r"""
core_diff.to_csv(OUT_DIR / "core_v40_v41_diff.csv", index=False)
inherited.to_csv(OUT_DIR / "inherited_from_core.csv", index=False)
usdm["systemVersion"] = "2026-10-24 step5"
with open(OUT_DIR / "remapcap_usdm_v2.json", "w", encoding="utf-8") as f:
    json.dump(usdm, f, indent=1, ensure_ascii=False)
pd.DataFrame(LOG).to_csv(OUT_DIR / "mapping_log_step5.csv", index=False)
bp.to_csv(OUT_DIR / "breakpoints.csv", index=False)

md = ["# REMAP-CAP in USDM v4.0.0 – breakpoint table", "",
      "Core Protocol 4.0 / 4.1, PANDA 1.0, Corticosteroid DSA 6. Generated by `notebooks/05_remapcap_amendment_breakpoints.ipynb`.", "",
      "| id | area | kind | breakpoint | USDM element | evidence (REMAP-CAP) | CPMP |", "|---|---|---|---|---|---|---|"]
for r in bp.itertuples():
    md.append(f"| {r.id} | {r.area} | {r.kind} | {r.breakpoint} | {r.usdm_element} | {r.evidence_remapcap} | {r.cpmp_note} |")
(OUT_DIR / "breakpoints.md").write_text("\n".join(md) + "\n", encoding="utf-8")
for f in sorted(OUT_DIR.iterdir()):
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
