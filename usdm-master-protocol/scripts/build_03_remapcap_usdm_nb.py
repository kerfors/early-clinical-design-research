"""Generate notebooks/03_remapcap_usdm.ipynb (Plan 1, Step 3 on REMAP-CAP).

The notebook is built as a Python dict and written with json.dump.
Run:  python3 scripts/build_03_remapcap_usdm_nb.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "notebooks" / "03_remapcap_usdm.ipynb"


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
# Plan 1, Step 3 – REMAP-CAP into USDM v4 JSON

Input: the section texts from Step 2 (`output_remapcap/step2/sections.csv`), the USDM v4 model and CT from the `usdm-rdf` repo (DDF-RA v4.0.0).

Decisions (2026-10-24):
- **One study design** = the Corticosteroid domain. Core Protocol platform criteria are shared `EligibilityCriterionItem`s at `StudyVersion` level, referenced by the design. Core objectives and endpoints are copied into the design; each copy is logged. No Core-only design (it has no interventions, so it cannot meet `arms 1..*`).
- **Strata and states** (PANDA) are not forced into a class. The PANDA text is kept as `NarrativeContent` of the PANDA document version; the gap goes to the breakpoint table.

Rules:
- All text values are taken from `sections.csv` by section number. Nothing is retyped.
- A value is filled only where the document states it. A required attribute with no source in the documents is **left out** and logged as `required_not_in_document`. The Step 4 validation will then report it.
- Every `Code` is checked against `USDM_CT.xlsx` (DDF-native value sets) or was looked up in NCIt (SDTM/Protocol Terminology concepts; codelist membership not checked, see log).

Output: `output_remapcap/step3/remapcap_usdm.json`, `output_remapcap/step3/mapping_log.csv`.
"""))

cells.append(code_cell(r"""
import json
import os
import re
from pathlib import Path

import openpyxl
import pandas as pd
import yaml

BASE = Path.cwd().parent
STEP2 = BASE / "output_remapcap" / "step2"
OUT_DIR = BASE / "output_remapcap" / "step3"
USDM_RDF = Path(os.environ.get("USDM_RDF_DIR", BASE.parent.parent / "GitHub" / "usdm-rdf"))
assert STEP2.is_dir(), f"run this notebook from usdm-master-protocol/notebooks/ (missing {STEP2})"
assert (USDM_RDF / "downloads" / "dataStructure.yml").is_file(), f"usdm-rdf not found at {USDM_RDF} (set USDM_RDF_DIR)"
OUT_DIR.mkdir(parents=True, exist_ok=True)

meta = json.loads((USDM_RDF / "downloads" / ".fetch_meta.json").read_text())
meta_ct = json.loads((USDM_RDF / "downloads" / ".fetch_meta_ct.json").read_text())
assert meta["ddf_ra_tag"] == "v4.0.0" and meta_ct["ddf_ra_tag"] == "v4.0.0", "expected DDF-RA v4.0.0 pins"
MODEL = yaml.safe_load((USDM_RDF / "downloads" / "dataStructure.yml").read_text())

sections = pd.read_csv(STEP2 / "sections.csv").fillna({"text": ""})
print("DDF-RA tag:", meta["ddf_ra_tag"], "| sections:", len(sections))
"""))

cells.append(markdown_cell(r"""
## Helpers

- `sec(doc, number)` – one section row from Step 2 (fails if missing).
- `LOG` – one row per mapping decision: `object`, `attribute`, `status`, `value`, `evidence` (document + section + page), `note`.
  Status values: `mapped`, `mapped_copy_from_core` (Core content copied into the domain design), `derived` (follows from stated text; the reasoning is in `note`), `required_not_in_document`, `not_expressible`.
- `new_id(cls)` – sequential ids `Class_n`.
"""))

cells.append(code_cell(r"""
LOG = []
_counter = {}


def new_id(cls):
    _counter[cls] = _counter.get(cls, 0) + 1
    return f"{cls}_{_counter[cls]}"


def sec(doc, number):
    rows = sections[(sections.doc == doc) & (sections.number == number)]
    assert len(rows) == 1, f"section {doc} {number} not found exactly once"
    return rows.iloc[0]


def ev(doc, number):
    r = sec(doc, number)
    return f"{doc} {number} '{r.title}' p{r.start_page}"


def log(obj, attribute, status, value="", evidence="", note=""):
    LOG.append({"object": obj, "attribute": attribute, "status": status,
                "value": str(value)[:300], "evidence": evidence, "note": note})


def first_sentence(text):
    return re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]


def bullets(text):
    parts = [p.strip() for p in text.split("•")]
    return [p for p in parts[1:] if p]


def numbered(text):
    parts = re.split(r"\s(?=\d\.\s)", " " + text)
    return [re.sub(r"^\d\.\s*", "", p).strip() for p in parts if re.match(r"\d\.\s", p)]
"""))

cells.append(markdown_cell(r"""
## Codes

Code sources:
- `DDF`: member of a DDF-native value set in sheet 2 of `USDM_CT.xlsx` (checked below, fails if not a member).
- `NCIT`: concept looked up in NCIt via BioPortal on 2026-10-24 (preferred term recorded). These belong to SDTM/Protocol Terminology codelists; membership of the codelist was **not** checked (that CT package is not a pinned source).
- `ISO639`: ISO 639-1 language code.

`Code.codeSystemVersion` is required (1..1). No CT package date is stated anywhere in the sources, so the value records where the code was taken from. This is logged as a finding.
"""))

cells.append(code_cell(r"""
wb = openpyxl.load_workbook(USDM_RDF / "downloads" / "USDM_CT.xlsx", read_only=True)
vs_rows = list(wb.worksheets[1].iter_rows(values_only=True))
header_idx = next(i for i, r in enumerate(vs_rows) if r[0] == "Project")
DDF_VALUE_SETS = {}
for r in vs_rows[header_idx + 1:]:
    if r[3] and r[5]:
        DDF_VALUE_SETS.setdefault(str(r[3]).strip(), {})[str(r[5]).strip()] = str(r[6]).strip()

NCIT_VERIFIED = {
    "C25532": "Inclusion Criteria",
    "C25370": "Exclusion Criteria",
    "C98388": "Interventional Study",
}
VERSION_NOTE = {
    "DDF": "USDM_CT.xlsx DDF-RA v4.0.0",
    "NCIT": "NCIt via BioPortal, looked up 2026-10-24",
    "ISO639": "ISO 639-1:2002",
}


def code(c, decode, source, codelist=None):
    if source == "DDF":
        assert codelist in DDF_VALUE_SETS, f"value set {codelist} not in USDM_CT sheet 2"
        assert DDF_VALUE_SETS[codelist].get(c) == decode, f"{c} '{decode}' not in {codelist}: {DDF_VALUE_SETS[codelist].get(c)}"
    elif source == "NCIT":
        assert NCIT_VERIFIED[c] == decode, f"{c} not verified as '{decode}'"
    elif source != "ISO639":
        raise ValueError(source)
    return {"id": new_id("Code"), "code": c, "codeSystem": "ISO 639-1" if source == "ISO639" else "http://www.cdisc.org",
            "codeSystemVersion": VERSION_NOTE[source], "decode": decode, "instanceType": "Code"}


print({k: len(v) for k, v in DDF_VALUE_SETS.items() if k in ("C188725", "C188726", "C215477", "C188723", "C207416", "C207419", "C188724", "C207413", "C188727")})
"""))

cells.append(markdown_cell(r"""
## Documents: Core Protocol, PANDA, Corticosteroid DSA

`StudyDefinitionDocument.childIds` (DDF-RA issue #614): the Core Protocol is the parent of PANDA and of each DSA. Evidence: Core §2.2 ("The protocol has multiple modules, comprising a Core Protocol, a Patient, Pathogen and Disease Appendix (PANDA) … multiple DSAs …").

Document version status: each document states its approval (Core §2.2.9 by the ITSC; PANDA authorization page by the ITSC; DSA §3.1 and §5 by the DSWG), so status = Approved (C25425).
"""))

cells.append(code_cell(r"""
DOC_TYPE_PROTOCOL = ("C70817", "Protocol")
documents = {}
doc_versions = {}
narrative_items = []

DOC_FACTS = {
    "CORE": {"name": "REMAP-CAP Core Protocol", "version": "4.0", "approved": "2024-11-05",
             "approval_ev": ev("CORE", "2.2.9"), "approved_by": "ITSC"},
    "PANDA": {"name": "Patient, Pathogen and Disease Appendix (PANDA) to the Core Protocol", "version": "1.0",
              "approved": "2024-11-05", "approval_ev": "PANDA p3 authorization page (ITSC, 5 November 2024)",
              "approved_by": "ITSC"},
    "CS_DSA": {"name": "Corticosteroid Domain-Specific Appendix", "version": "6", "approved": "2024-11-05",
               "approval_ev": ev("CS_DSA", "3.1"), "approved_by": "Corticosteroid DSWG"},
}

for role, f in DOC_FACTS.items():
    doc_id = new_id("StudyDefinitionDocument")
    ver_id = new_id("StudyDefinitionDocumentVersion")
    doc = {"id": doc_id, "name": f["name"], "language": code("en", "English", "ISO639"),
           "childIds": [], "versions": [], "instanceType": "StudyDefinitionDocument"}
    log(doc_id, "name", "mapped", f["name"], f"{role} title page")
    log(doc_id, "language", "derived", "en", f"{role} text", "documents are written in English")
    if role == "CORE":
        doc["type"] = code(*DOC_TYPE_PROTOCOL, "DDF", "C215477")
        log(doc_id, "type", "mapped", "Protocol", "CORE title page 'CORE PROTOCOL'")
    else:
        log(doc_id, "type", "not_expressible", "", f"{role} title page",
            "type 1..1; value set C215477 has only 'Protocol'; an appendix to a protocol has no value")
    log(doc_id, "templateName", "required_not_in_document", "", "", "no template is named in the document")
    version = {"id": ver_id, "version": f["version"],
               "status": code("C25425", "Approved", "DDF", "C188723"),
               "dateValues": [], "contents": [], "instanceType": "StudyDefinitionDocumentVersion"}
    log(ver_id, "version", "mapped", f["version"], f"{role} cover page 'Version {f['version']} dated …'")
    log(ver_id, "status", "mapped", "Approved", f["approval_ev"], f"approved by {f['approved_by']}")
    date = {"id": new_id("GovernanceDate"), "name": f"{role} approval", "type": code("C71476", "Approval Date", "DDF", "C207413"),
            "dateValue": f["approved"], "instanceType": "GovernanceDate"}
    log(date["id"], "dateValue", "mapped", f["approved"], f["approval_ev"])
    log(date["id"], "geographicScopes", "required_not_in_document", "", f["approval_ev"],
        f"1..*; approval by the {f['approved_by']}, no geographic scope stated")
    version["dateValues"].append(date)
    doc["versions"].append(version)
    documents[role] = doc
    doc_versions[role] = version

documents["CORE"]["childIds"] = [documents["PANDA"]["id"], documents["CS_DSA"]["id"]]
log(documents["CORE"]["id"], "childIds", "mapped", "PANDA, CS_DSA", ev("CORE", "2.2"),
    "Core is parent of PANDA and of each DSA")
"""))

cells.append(markdown_cell(r"""
### PANDA text as narrative content

All 17 PANDA sections become `NarrativeContent` of the PANDA document version, with the text in `NarrativeContentItem`s at `StudyVersion` level. This keeps the strata and states definitions (§2, §4.3) in the JSON without forcing them into a class.
"""))

cells.append(code_cell(r"""
panda_secs = sections[sections.doc == "PANDA"].reset_index(drop=True)
contents = []
for r in panda_secs.itertuples():
    item = {"id": new_id("NarrativeContentItem"), "name": f"PANDA {r.number}", "text": r.text,
            "instanceType": "NarrativeContentItem"}
    narrative_items.append(item)
    contents.append({"id": new_id("NarrativeContent"), "name": f"PANDA {r.number}", "sectionNumber": r.number,
                     "sectionTitle": r.title, "displaySectionTitle": True, "displaySectionNumber": True,
                     "contentItemId": item["id"], "childIds": [], "instanceType": "NarrativeContent"})
for i, c in enumerate(contents):
    if i > 0:
        c["previousId"] = contents[i - 1]["id"]
    if i + 1 < len(contents):
        c["nextId"] = contents[i + 1]["id"]
by_number = {c["sectionNumber"]: c for c in contents}
for c in contents:
    parent = c["sectionNumber"].rsplit(".", 1)[0] if "." in c["sectionNumber"] else None
    if parent:
        by_number[parent]["childIds"].append(c["id"])
doc_versions["PANDA"]["contents"] = contents
for n in ("2", "4.3"):
    log(by_number[n]["id"], "text", "not_expressible", sec("PANDA", n).title, ev("PANDA", n),
        "strata/states kept as narrative only; no USDM class for dynamic analysis strata / illness states (decision 2026-10-24)")
print("PANDA narrative sections:", len(contents))
"""))

cells.append(markdown_cell(r"""
## Eligibility

- Core §7.4.1 (3 inclusion) and §7.4.2 (3 exclusion): platform level. Items at `StudyVersion.eligibilityCriterionItems`.
- CS_DSA §8.2.1 (4 inclusion) and §8.2.2 (6 exclusion): domain level.
- CS_DSA §8.2.3: intervention-level exclusion (pregnancy, depends on site regulatory approval). Logged as `not_expressible`: USDM eligibility criteria apply to a design/population, not to one intervention, and cannot carry a site condition.
- Order within each list follows the document (`previousId` / `nextId`).
"""))

cells.append(code_cell(r"""
criterion_items = []
criteria = []
CRIT_SOURCES = [
    ("CORE", "7.4.1", numbered, ("C25532", "Inclusion Criteria"), "platform"),
    ("CORE", "7.4.2", numbered, ("C25370", "Exclusion Criteria"), "platform"),
    ("CS_DSA", "8.2.1", bullets, ("C25532", "Inclusion Criteria"), "domain"),
    ("CS_DSA", "8.2.2", bullets, ("C25370", "Exclusion Criteria"), "domain"),
]
for doc, number, splitter, cat, level in CRIT_SOURCES:
    texts = splitter(sec(doc, number).text)
    previous = None
    for k, text in enumerate(texts, start=1):
        item = {"id": new_id("EligibilityCriterionItem"), "name": f"{doc} {number} #{k}", "text": text,
                "instanceType": "EligibilityCriterionItem"}
        crit = {"id": new_id("EligibilityCriterion"), "name": f"{doc} {number} #{k}", "identifier": f"{doc} {number} #{k}",
                "category": code(*cat, "NCIT"), "criterionItemId": item["id"], "instanceType": "EligibilityCriterion"}
        if previous:
            crit["previousId"] = previous["id"]
            previous["nextId"] = crit["id"]
        criterion_items.append(item)
        criteria.append(crit)
        previous = crit
        log(crit["id"], "criterionItemId", "mapped", text, ev(doc, number), f"{level} {cat[1].lower()}")
    print(f"{doc} {number}: {len(texts)} criteria")

log("-", "EligibilityCriterion (intervention level)", "not_expressible", first_sentence(sec("CS_DSA", "8.2.3").text),
    ev("CS_DSA", "8.2.3"), "criterion scoped to one intervention and conditional on site regulatory approval (pregnancy)")
log("-", "EligibilityCriterion (inheritance)", "not_expressible", first_sentence(sec("CS_DSA", "8.2").text), ev("CS_DSA", "8.2"),
    "domain eligibility = platform criteria + domain criteria; USDM gives one flat criteria list per design, the layer is visible only in 'identifier'")
"""))

cells.append(markdown_cell(r"""
## Objectives and endpoints

- Core §6.1 primary objective, §6.2 secondary objectives: copied into the domain design (`mapped_copy_from_core`).
- Core §7.6.1 primary endpoint (first sentence = definition), under the primary objective.
- Core §7.6.2: the two "generic key secondary endpoints" (bullets between "for the trial are:" and "The index hospital"), under the secondary objective.
- CS_DSA §7 domain objective (first sentence). The document does not give it a level (primary/secondary): `level` left out.
- CS_DSA §8.5.1: "the primary outcome as specified in Core Protocol documents". USDM `Endpoint` is composed (Value), so the Core primary endpoint cannot be referenced; it is copied under the domain objective.
- CS_DSA §8.5.2: domain-specific secondary outcome "serious adverse events (SAE) as defined in the Core Protocol".
- `Endpoint.purpose` (1..1) is not stated for any endpoint.
"""))

cells.append(code_cell(r"""
def objective(text, level, evidence, status):
    o = {"id": new_id("Objective"), "name": evidence.split(" '")[0], "text": text, "endpoints": [], "instanceType": "Objective"}
    if level:
        o["level"] = code(*level, "DDF", "C188725")
    else:
        log(o["id"], "level", "required_not_in_document", "", evidence, "objective has no primary/secondary label")
    log(o["id"], "text", status, text, evidence)
    return o


def endpoint(text, level, evidence, status):
    e = {"id": new_id("Endpoint"), "name": evidence.split(" '")[0], "text": text,
         "level": code(*level, "DDF", "C188726"), "instanceType": "Endpoint"}
    log(e["id"], "text", status, text, evidence)
    log(e["id"], "purpose", "required_not_in_document", "", evidence, "purpose (efficacy/safety …) not stated")
    return e


PRIMARY_OBJ, SECONDARY_OBJ = ("C85826", "Primary Objective"), ("C85827", "Secondary Objective")
PRIMARY_EP, SECONDARY_EP = ("C94496", "Primary Endpoint"), ("C139173", "Secondary Endpoint")

core_primary_ep_text = first_sentence(sec("CORE", "7.6.1").text)
sec_text = sec("CORE", "7.6.2").text
key_secondary = bullets(sec_text.split("for the trial are:")[1].split("The index hospital")[0])
assert key_secondary == ["Hospital length-of-stay", "Mortality, censored at 90 days"], key_secondary

obj_core_primary = objective(sec("CORE", "6.1").text, PRIMARY_OBJ, ev("CORE", "6.1"), "mapped_copy_from_core")
obj_core_primary["endpoints"].append(endpoint(core_primary_ep_text, PRIMARY_EP, ev("CORE", "7.6.1"), "mapped_copy_from_core"))
obj_core_secondary = objective(sec("CORE", "6.2").text, SECONDARY_OBJ, ev("CORE", "6.2"), "mapped_copy_from_core")
for t in key_secondary:
    obj_core_secondary["endpoints"].append(endpoint(t, SECONDARY_EP, ev("CORE", "7.6.2"), "mapped_copy_from_core"))

obj_domain = objective(first_sentence(sec("CS_DSA", "7").text), None, ev("CS_DSA", "7"), "mapped")
obj_domain["endpoints"].append(endpoint(core_primary_ep_text, PRIMARY_EP, ev("CS_DSA", "8.5.1") + " -> " + ev("CORE", "7.6.1"),
                                        "mapped_copy_from_core"))
sae_text = sec("CS_DSA", "8.5.2").text.split("will be: •")[1].split("There are no")[0].strip()
obj_domain["endpoints"].append(endpoint(sae_text, SECONDARY_EP, ev("CS_DSA", "8.5.2"), "mapped"))
log(obj_domain["endpoints"][0]["id"], "inheritance", "not_expressible", first_sentence(sec("CS_DSA", "8.5.1").text),
    ev("CS_DSA", "8.5.1"), "Endpoint is a Value (composed) attribute: the inherited Core endpoint can only be copied, not referenced")
objectives = [obj_core_primary, obj_core_secondary, obj_domain]
print("objectives:", len(objectives), "| endpoints:", sum(len(o["endpoints"]) for o in objectives))
"""))

cells.append(markdown_cell(r"""
## Interventions and arms

- Three interventions from CS_DSA §8.3.1 (names after the checkbox), descriptions from §8.3.2–8.3.4.
- `StudyIntervention.role` and `.type` (both 1..1): not stated. "No corticosteroid (no placebo)" is a strategy without a substance.
- Arms: REMAP-CAP allocates participants to interventions within a domain; one arm per intervention is a structural reading, logged as `derived`. `StudyArm.type` (1..1) not stated. `dataOriginType` = Data Generated Within Study: participants are randomized in the trial (Core §7.7.1 Randomization).
- Hydrocortisone is available only in the Severe State (§8.3.1, §8.3.3): an arm restricted to one illness state is `not_expressible`.
"""))

cells.append(code_cell(r"""
names = [n.strip() for n in sec("CS_DSA", "8.3.1").text.split("☐")[1:]]
assert len(names) == 3, names
desc_sections = ["8.3.2", "8.3.3", "8.3.4"]
interventions, arms = [], []
for name, number in zip(names, desc_sections):
    si = {"id": new_id("StudyIntervention"), "name": name, "description": sec("CS_DSA", number).text,
          "instanceType": "StudyIntervention"}
    log(si["id"], "name", "mapped", name, ev("CS_DSA", "8.3.1"))
    log(si["id"], "description", "mapped", sec("CS_DSA", number).title, ev("CS_DSA", number))
    log(si["id"], "role", "required_not_in_document", "", ev("CS_DSA", number), "no experimental/comparator/control role stated")
    log(si["id"], "type", "required_not_in_document", "", ev("CS_DSA", number),
        "type 1..1; 'No corticosteroid' has no substance" if number == "8.3.2" else "type 1..1; not stated")
    interventions.append(si)
    arm = {"id": new_id("StudyArm"), "name": name, "dataOriginType": code("C188866", "Data Generated Within Study", "DDF", "C188727"),
           "dataOriginDescription": first_sentence(sec("CS_DSA", "8.3.1").text), "instanceType": "StudyArm"}
    log(arm["id"], "(arm)", "derived", name, ev("CS_DSA", "8.3.1"), "one arm per randomized intervention")
    log(arm["id"], "type", "required_not_in_document", "", ev("CS_DSA", "8.3.1"), "arm type not stated")
    arms.append(arm)
log(arms[1]["id"], "(state restriction)", "not_expressible", "Severe State only", ev("CS_DSA", "8.3.3"),
    "arm available only to participants in one illness severity state")
print([i["name"] for i in interventions])
"""))

cells.append(markdown_cell(r"""
## Study design (Corticosteroid domain), population, study version, study

Design-level codes, each stated in the Core title "Randomized, Embedded, Multifactorial Adaptive Platform trial": `characteristics` Randomized (C46079) and Adaptive (C98704), copied from the Core. `studyType` Interventional (C98388).
Left out (required, not stated for the domain): `rationale` (CS_DSA §6 is a 9-page narrative background, not a design rationale), `model` (the Core says "multifactorial" for the platform; the domain's own model is not stated), `epochs` and `studyCells` (no epochs are described).
"""))

cells.append(code_cell(r"""
design_id = new_id("InterventionalStudyDesign")
population = {"id": new_id("StudyDesignPopulation"), "name": "Corticosteroid domain population",
              "includesHealthySubjects": False, "criterionIds": [c["id"] for c in criteria],
              "cohorts": [], "instanceType": "StudyDesignPopulation"}
log(population["id"], "includesHealthySubjects", "derived", False, ev("CORE", "7.4.1"),
    "inclusion requires hospitalized patient with acute respiratory tract infection")
log(population["id"], "cohorts", "not_expressible", "", ev("CS_DSA", "8.1.1") + "; " + ev("PANDA", "4.3"),
    "age strata and illness states are analysis strata/dynamic states, not cohorts (decision 2026-10-24)")

design = {
    "id": design_id,
    "name": "Corticosteroid Domain",
    "studyType": code("C98388", "Interventional Study", "NCIT"),
    "characteristics": [code("C46079", "Randomized", "DDF", "C207416"), code("C98704", "Adaptive", "DDF", "C207416")],
    "eligibilityCriteria": criteria,
    "objectives": objectives,
    "arms": arms,
    "studyInterventionIds": [i["id"] for i in interventions],
    "population": population,
    "documentVersionIds": [doc_versions[r]["id"] for r in ("CORE", "PANDA", "CS_DSA")],
    "instanceType": "InterventionalStudyDesign",
}
log(design_id, "name", "mapped", "Corticosteroid Domain", ev("CS_DSA", "6.1"))
log(design_id, "characteristics", "mapped_copy_from_core", "Randomized; Adaptive", "CORE title page")
log(design_id, "studyType", "derived", "Interventional Study", ev("CORE", "7.7.1"), "participants are randomized to interventions")
for attr, note in [("rationale", "CS_DSA §6 is a long background narrative; no design rationale statement"),
                   ("model", "platform is 'multifactorial' (Core title); the domain model is not stated"),
                   ("epochs", "no epochs described"), ("studyCells", "no epochs, so no cells")]:
    log(design_id, attr, "required_not_in_document", "", "CS_DSA / CORE", note)
log(design_id, "documentVersionIds", "mapped", "Core 4.0, PANDA 1.0, CS_DSA 6", "decision 2026-10-24",
    "design draws on three document versions; which Core version the DSA binds to is not stated in the DSA")

org = {"id": new_id("Organization"), "name": "ClinicalTrials.gov",
       "type": code("C93453", "Clinical Study Registry", "DDF", "C188724"), "instanceType": "Organization"}
log(org["id"], "name", "mapped", "ClinicalTrials.gov", ev("CORE", "2.4"))
log(org["id"], "identifier", "required_not_in_document", "", ev("CORE", "2.4"), "organization identifier not stated")
log(org["id"], "identifierScheme", "required_not_in_document", "", ev("CORE", "2.4"), "")

nct = re.search(r"NCT\d{8}", sec("CORE", "2.4").text).group(0)
utn = re.search(r"Universal Trial Number is: (\S+?)\.?$", sec("CORE", "2.4").text).group(1)
identifiers = [{"id": new_id("StudyIdentifier"), "text": nct, "scopeId": org["id"], "instanceType": "StudyIdentifier"}]
log(identifiers[0]["id"], "text", "mapped", nct, ev("CORE", "2.4"))
log("-", "StudyIdentifier (UTN)", "required_not_in_document", utn, ev("CORE", "2.4"),
    "Universal Trial Number stated, but its issuing organization (scopeId 1..1) is not")

inventory = pd.read_csv(BASE / "remapcap_inventory.csv")
core_page1 = inventory.loc[inventory.file == "superseded/REMAP-CAP-Core-Protocol-V4-05-November-2024_CLEAN-m9gf.pdf",
                           "document_name_on_page1"].item()
m = re.match(r"^(.+?) \((REMAP-CAP)\): CORE PROTOCOL", core_page1)
assert m, core_page1
title_text, acronym = m.group(1), m.group(2)
titles = [
    {"id": new_id("StudyTitle"), "type": code("C207616", "Official Study Title", "DDF", "C207419"), "text": title_text, "instanceType": "StudyTitle"},
    {"id": new_id("StudyTitle"), "type": code("C94108", "Study Acronym", "DDF", "C207419"), "text": acronym, "instanceType": "StudyTitle"},
]
log(titles[0]["id"], "text", "mapped", title_text, "CORE page 1 (remapcap_inventory.csv)")
log(titles[1]["id"], "text", "mapped", acronym, "CORE page 1 (remapcap_inventory.csv)")

study_version = {
    "id": new_id("StudyVersion"),
    "versionIdentifier": "Core 4.0 / PANDA 1.0 / Corticosteroid DSA 6",
    "titles": titles,
    "studyIdentifiers": identifiers,
    "organizations": [org],
    "documentVersionIds": [v["id"] for v in doc_versions.values()],
    "studyDesigns": [design],
    "eligibilityCriterionItems": criterion_items,
    "narrativeContentItems": narrative_items,
    "studyInterventions": interventions,
    "amendments": [],
    "instanceType": "StudyVersion",
}
log(study_version["id"], "versionIdentifier", "derived", study_version["versionIdentifier"], "decision 2026-10-24",
    "the platform has no single version; StudyVersion is a set of document versions")
log(study_version["id"], "rationale", "required_not_in_document", "", "", "no version rationale stated")
log(study_version["id"], "amendments", "required_not_in_document", "", ev("CORE", "2.2.9"),
    "version histories list versions and approval dates only; StudyAmendment needs summary, changes, primaryReason, geographicScopes (Step 5)")

study = {"id": new_id("Study"), "name": acronym, "versions": [study_version],
         "documentedBy": [documents[r] for r in ("CORE", "PANDA", "CS_DSA")], "instanceType": "Study"}
usdm = {"study": study, "usdmVersion": "4.0.0", "systemName": "early-clinical-design-research/03_remapcap_usdm",
        "systemVersion": "2026-10-24"}
print("criteria", len(criteria), "| items", len(criterion_items), "| arms", len(arms), "| narrative items", len(narrative_items))
"""))

cells.append(markdown_cell(r"""
## Self-check against the model

Before writing: every `instanceType` is a model class, every key is an attribute of that class, every `…Id`/`…Ids` value points to an object in the document. Required attributes that are absent are listed and must all appear in the log as `required_not_in_document` or `not_expressible`; any other absence is a bug and fails here.
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


walk(usdm["study"])
missing_required = []
for oid, o in objects.items():
    attrs = model_attrs(o["instanceType"])
    for k, v in o.items():
        assert k in attrs, f"{o['instanceType']}.{k} is not a model attribute"
        if attrs[k]["Relationship Type"] == "Ref":
            for ref in (v if isinstance(v, list) else [v]):
                assert ref in objects, f"{oid}.{k} -> {ref} not found"
    for a, spec in attrs.items():
        if spec["Cardinality"].startswith("1") and a not in o:
            missing_required.append((oid, o["instanceType"], a))
        if spec["Cardinality"] == "1..*" and a in o and len(o[a]) == 0:
            missing_required.append((oid, o["instanceType"], a))

logged = {(r["object"], r["attribute"]) for r in LOG if r["status"] in ("required_not_in_document", "not_expressible")}
unlogged = [m for m in missing_required if (m[0], m[2]) not in logged]
assert not unlogged, f"required attributes missing without a log entry: {unlogged}"
print("objects:", len(objects), "| required attributes absent (all logged):", len(missing_required))
pd.DataFrame(missing_required, columns=["id", "class", "attribute"]).groupby(["class", "attribute"]).size()
"""))

cells.append(markdown_cell(r"""
## Write outputs
"""))

cells.append(code_cell(r"""
with open(OUT_DIR / "remapcap_usdm.json", "w", encoding="utf-8") as f:
    json.dump(usdm, f, indent=1, ensure_ascii=False)
log_df = pd.DataFrame(LOG)
log_df.to_csv(OUT_DIR / "mapping_log.csv", index=False)
print(log_df.status.value_counts())
for f in sorted(OUT_DIR.iterdir()):
    print(f"{f.name:22s} {f.stat().st_size:>10,d} bytes")
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
