"""Generate notebooks/12_cpmp_usdm.ipynb (Plan 1 restarted on CPMP, Step 3: USDM v4 JSON, first pass).

Input: output_cpmp/step2/page_text.csv, output_cpmp/step2/sections.csv, inventory.csv,
       usdm-rdf (DDF-RA v4.0.0 model and CT).
Output: output_cpmp/step3/cpmp_usdm.json, output_cpmp/step3/mapping_log.csv.

The notebook is built as a Python dict and written with json.dump.
Run:  python3 scripts/build_12_cpmp_usdm_nb.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "notebooks" / "12_cpmp_usdm.ipynb"


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
# CPMP, Step 3 – USDM v4 JSON, first pass

Scope agreed 2026-10-25:

- **Structure A**: one `Study` (the master protocol, NCT05986292) with 13 `StudyDefinitionDocument`s: the master protocol and the 12 posted ISAs. The master's `childIds` are the ISAs. The three disease-state addenda (DSA) are cited in the ISAs but not public; they are logged, not invented.
- **First-pass content**: documents, document versions (current version with approval date; earlier versions from each document's "Document History" table), section text as `NarrativeContent`, study titles, identifiers and organizations.
- **Not in this pass**: study designs (one per ISA, later), eligibility, objectives and endpoints, interventions and arms, and `StudyAmendment` content from the summary-of-changes tables. The SoA (activities, encounters, timelines, biomedical concepts) belongs to soa2usdm.

Rules as in REMAP-CAP Step 3: every value is taken from the documents by pattern (page text from `10_cpmp_page_text.py`, section text from `11_cpmp_structure.ipynb`, title-page fields from the Step 1 inventory); nothing is retyped. A required attribute with no source is left out and logged as `required_not_in_document`; something USDM cannot hold is logged as `not_expressible`. Every `Code` is checked against `USDM_CT.xlsx` sheet 2.
"""))

cells.append(code_cell(r"""
import json
import os
import re
from datetime import datetime
from pathlib import Path

import openpyxl
import pandas as pd
import yaml

BASE = Path.cwd().parent
STEP2 = BASE / "output_cpmp" / "step2"
OUT_DIR = BASE / "output_cpmp" / "step3"
USDM_RDF = Path(os.environ.get("USDM_RDF_DIR", BASE.parent.parent / "GitHub" / "usdm-rdf"))
assert (STEP2 / "sections.csv").is_file(), "run from usdm-master-protocol/notebooks/ after 11_cpmp_structure.ipynb"
assert (USDM_RDF / "downloads" / "dataStructure.yml").is_file(), f"usdm-rdf not found at {USDM_RDF} (set USDM_RDF_DIR)"
OUT_DIR.mkdir(parents=True, exist_ok=True)

meta = json.loads((USDM_RDF / "downloads" / ".fetch_meta.json").read_text())
meta_ct = json.loads((USDM_RDF / "downloads" / ".fetch_meta_ct.json").read_text())
assert meta["ddf_ra_tag"] == "v4.0.0" and meta_ct["ddf_ra_tag"] == "v4.0.0", "expected DDF-RA v4.0.0 pins"
MODEL = yaml.safe_load((USDM_RDF / "downloads" / "dataStructure.yml").read_text())

pt = pd.read_csv(STEP2 / "page_text.csv").fillna({"text": ""})
pt["doc"] = pt.sponsor_protocol_no.str.replace("H0P-MC-", "", regex=False)
sections = pd.read_csv(STEP2 / "sections.csv", dtype={"number": str}).fillna({"text": "", "number": ""})
inventory = pd.read_csv(BASE / "inventory.csv")
inventory = inventory[inventory.ctgov_filename.fillna("").str.startswith("Prot")].copy()
inventory["doc"] = inventory.sponsor_protocol_no.str.replace("H0P-MC-", "", regex=False)
DOCS = list(dict.fromkeys(pt.doc))
ISAS = [d for d in DOCS if d != "CPMP"]
assert DOCS[0] == "CPMP" and len(ISAS) == 12
print("DDF-RA tag:", meta["ddf_ra_tag"], "| documents:", len(DOCS), "| sections:", len(sections))
"""))

cells.append(markdown_cell(r"""
## Helpers

`LOG` columns as in REMAP-CAP Step 3: `object`, `attribute`, `status`, `value`, `evidence`, `note`. Status values: `mapped`, `derived`, `required_not_in_document`, `not_expressible`, `deferred` (in scope of a later pass).
"""))

cells.append(code_cell(r"""
LOG = []
_counter = {}


def new_id(cls):
    _counter[cls] = _counter.get(cls, 0) + 1
    return f"{cls}_{_counter[cls]}"


def log(obj, attribute, status, value="", evidence="", note=""):
    LOG.append({"object": obj, "attribute": attribute, "status": status,
                "value": str(value)[:300], "evidence": evidence, "note": note})


def page(doc, n):
    rows = pt[(pt.doc == doc) & (pt.page == n)]
    assert len(rows) == 1, f"{doc} p{n}"
    return rows.text.iloc[0]


def flat(text):
    return re.sub(r"\s+", " ", text).strip()


def field(doc, label, n=2, stop=r"\n[A-Z][A-Za-z ()]+:"):
    t = page(doc, n)
    m = re.search(rf"{label}\s*:\s*(.+?)(?={stop}|\Z)", t, re.S)
    assert m, f"{doc} p{n}: '{label}' not found"
    return flat(m.group(1))


def parse_date(text):
    for fmt in ("%d-%b-%Y", "%d%b%Y", "%d %B %Y", "%d-%B-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(text)
"""))

cells.append(markdown_cell(r"""
## Codes

As in REMAP-CAP Step 3: DDF-native value sets checked against sheet 2 of `USDM_CT.xlsx`; language as ISO 639-1. `Code.codeSystemVersion` records where the code was taken from (no CT package date is stated in any source).
"""))

cells.append(code_cell(r"""
wb = openpyxl.load_workbook(USDM_RDF / "downloads" / "USDM_CT.xlsx", read_only=True)
vs_rows = list(wb.worksheets[1].iter_rows(values_only=True))
header_idx = next(i for i, r in enumerate(vs_rows) if r[0] == "Project")
DDF_VALUE_SETS = {}
for r in vs_rows[header_idx + 1:]:
    if r[3] and r[5]:
        DDF_VALUE_SETS.setdefault(str(r[3]).strip(), {})[str(r[5]).strip()] = str(r[6]).strip()
VERSION_NOTE = {"DDF": "USDM_CT.xlsx DDF-RA v4.0.0", "ISO639": "ISO 639-1:2002"}


def code(c, decode, source, codelist=None):
    if source == "DDF":
        assert DDF_VALUE_SETS[codelist].get(c) == decode, f"{c} '{decode}' not in {codelist}: {DDF_VALUE_SETS[codelist].get(c)}"
    elif source != "ISO639":
        raise ValueError(source)
    return {"id": new_id("Code"), "code": c, "codeSystem": "ISO 639-1" if source == "ISO639" else "http://www.cdisc.org",
            "codeSystemVersion": VERSION_NOTE[source], "decode": decode, "instanceType": "Code"}
"""))

cells.append(markdown_cell(r"""
## Facts per document, from the title pages

- Page 1 is the ClinicalTrials.gov cover sheet (NCT number). Page 2 is the document's own title page.
- Document number: "Protocol Number" (master) / "ISA Number" (ISA). Title: "Protocol Title" (master) / "ISA Title" (ISA). Acronym: "Acronym".
- Current version and approval date: Step 1 inventory (`amendment_on_title_page`, `approval_date_on_title_page`, read from the title page). The version is the amendment letter as printed, without brackets, or `original` where the title page says "This is the original protocol / ISA".
- Earlier versions: the "Document History" table (Document / Date), read from the page text.
"""))

cells.append(code_cell(r"""
HISTORY_ENTRY = re.compile(r"(Original\s*Protocol|Amendment\s*[\[(]?\s*([a-z])\s*[\])]?)\s*"
                           r"(\d{1,2}[- ]?(?:January|February|March|April|May|June|July|August|September|October|November|December|[A-Z][a-z]{2})[- ]?\d{4})?")


def history(doc):
    texts = pt[pt.doc == doc].sort_values("page").text
    joined = "\n".join(texts)
    m = re.search(r"DOCUMENT\s*HISTORY(.*?)Overall\s*Rationale", joined, re.S)
    if not m:
        return []
    out = []
    for e in HISTORY_ENTRY.finditer(m.group(1)):
        version = "original" if e.group(1).startswith("Original") else e.group(2)
        out.append({"version": version, "date": parse_date(flat(e.group(3)).replace(" ", " ")) if e.group(3) else ""})
    return out


facts = {}
for doc in DOCS:
    inv = inventory[inventory.doc == doc].iloc[0]
    is_master = doc == "CPMP"
    amend = re.sub(r"[\[\]()\s.]", "", str(inv.amendment_on_title_page))
    version = "original" if amend.lower().startswith("thisistheoriginal") else amend
    assert re.fullmatch(r"[a-z]|original", version), (doc, inv.amendment_on_title_page)
    nct = re.search(r"NCT\d{8}", page(doc, 1)).group(0)
    assert nct == inv.nct_id, (doc, nct, inv.nct_id)
    facts[doc] = {
        "number": field(doc, "Protocol Number" if is_master else "ISA Number"),
        "title": field(doc, "Protocol Title" if is_master else "ISA Title"),
        "acronym": field(doc, "Acronym"),
        "version": version,
        "version_as_printed": str(inv.amendment_on_title_page),
        "approved": parse_date(str(inv.approval_date_on_title_page)),
        "nct": nct,
        "history": history(doc),
    }
    assert facts[doc]["number"] == inv.sponsor_protocol_no, (doc, facts[doc]["number"])
facts["CPMP"]["short_title"] = field("CPMP", "Short Title")
pd.DataFrame([{"doc": d, **{k: v for k, v in f.items() if k != "history"},
               "history": "; ".join(f"{h['version']} {h['date']}" for h in f["history"])} for d, f in facts.items()])
"""))

cells.append(markdown_cell(r"""
## Documents and document versions

- Master: `type` = Protocol (C70817), title page "Master Protocol".
- ISA: the title page calls it an "Intervention-Specific Appendix" to the master protocol. As for the REMAP-CAP appendices, value set C215477 has only "Protocol", so `type` is `not_expressible`.
- `name` = document number, `label` = acronym, `description` = title, all from the title page.
- Master `childIds` = the 12 ISAs. Each ISA states that it is an appendix to the master protocol (§2, checked per ISA). The DSA layer between them is not public (`not_expressible`, logged once per DSA cited).
- Current version: `status` Approved (C25425); "Electronically Signed and Approved by Lilly" on the title page. Approval date as `GovernanceDate` Approval Date (C71476).
- Earlier versions (from "Document History", ordered by their date; NP03 lists amendment (a) before the original): `version` and nothing else. The table gives a "Date" per version, not an approval, effective or issued date (the three `GovernanceDate` types), and no status; both are logged.
"""))

cells.append(code_cell(r"""
documents, doc_versions, narrative_items = {}, {}, []
approved_code = ("C25425", "Approved", "DDF", "C188723")

for doc in DOCS:
    f = facts[doc]
    is_master = doc == "CPMP"
    d_id = new_id("StudyDefinitionDocument")
    document = {"id": d_id, "name": f["number"], "label": f["acronym"], "description": f["title"],
                "language": code("en", "English", "ISO639"), "childIds": [], "versions": [],
                "instanceType": "StudyDefinitionDocument"}
    log(d_id, "name", "mapped", f["number"], f"{doc} p2 title page")
    log(d_id, "description", "mapped", f["title"], f"{doc} p2 title page")
    log(d_id, "language", "derived", "en", f"{doc} text", "documents are written in English")
    log(d_id, "templateName", "required_not_in_document", "", "", "no template is named in the document")
    if is_master:
        document["type"] = code("C70817", "Protocol", "DDF", "C215477")
        log(d_id, "type", "mapped", "Protocol", "CPMP p2 title page 'Master Protocol'")
    else:
        log(d_id, "type", "not_expressible", "", f"{doc} p2 title page",
            "type 1..1; an intervention-specific appendix to the master protocol; value set C215477 has only 'Protocol'")

    earlier = sorted((h for h in f["history"] if h["version"] != f["version"]), key=lambda h: h["date"])
    assert all(h["date"] for h in earlier), (doc, earlier)
    for h in earlier:
        v_id = new_id("StudyDefinitionDocumentVersion")
        document["versions"].append({"id": v_id, "version": h["version"], "instanceType": "StudyDefinitionDocumentVersion"})
        log(v_id, "version", "mapped", h["version"], f"{doc} Document History")
        log(v_id, "status", "required_not_in_document", "", f"{doc} Document History", "earlier version; status not stated")
        log(v_id, "dateValues", "not_expressible", h["date"], f"{doc} Document History",
            "table column 'Date'; not stated to be an approval, effective or issued date (GovernanceDate types C207413)")

    v_id = new_id("StudyDefinitionDocumentVersion")
    date = {"id": new_id("GovernanceDate"), "name": f"{doc} approval", "type": code("C71476", "Approval Date", "DDF", "C207413"),
            "dateValue": f["approved"], "instanceType": "GovernanceDate"}
    version = {"id": v_id, "version": f["version"], "status": code(*approved_code), "dateValues": [date], "contents": [],
               "instanceType": "StudyDefinitionDocumentVersion"}
    log(v_id, "version", "mapped", f["version"], f"{doc} p2 title page 'Amendment Number: {f['version_as_printed']}'")
    log(v_id, "status", "mapped", "Approved", f"{doc} p2 title page", "electronically signed and approved by Lilly")
    log(date["id"], "dateValue", "mapped", f["approved"], f"{doc} p2 title page (Step 1 inventory)")
    log(date["id"], "geographicScopes", "required_not_in_document", "", f"{doc} p2 title page", "1..*; no geographic scope stated")
    document["versions"].append(version)
    documents[doc], doc_versions[doc] = document, version

for doc in ISAS:
    s2 = sections[(sections.doc == doc) & (sections.number == "2")]
    assert len(s2) == 1, doc
    m = re.search(r"is an appendix to (?:the )?.{0,40}?Master\s*Protocol", s2.text.iloc[0], re.I)
    assert m, f"{doc} §2: appendix statement not found"
    log(documents[doc]["id"], "(parent)", "mapped", "child of H0P-MC-CPMP", f"{doc} 2 p{s2.start_page.iloc[0]}", flat(m.group(0)))
documents["CPMP"]["childIds"] = [documents[d]["id"] for d in ISAS]

dsas = sorted(set(re.findall(r"CPMP\s*[\[(]\s*(\d)\s*[\])]", " ".join(sections[sections.layer == "ISA"].text))))
for n in dsas:
    log("-", f"StudyDefinitionDocument (DSA H0P-MC-CPMP({n}))", "not_expressible", f"H0P-MC-CPMP({n})", "ISA text",
        "disease-state addendum cited in the ISAs; not public, so not represented. The master -> DSA -> ISA layering is reduced to master -> ISA")
print({d: [v["version"] for v in documents[d]["versions"]] for d in DOCS}, "| DSAs cited:", dsas)
"""))

cells.append(markdown_cell(r"""
## Section text as NarrativeContent

One `NarrativeContent` per section of the current version (Step 2 `sections.csv`), in document order, `previousId` / `nextId` along that order, `childIds` from the section number where both numbers exist. Sections without a number (OA03: 30, the numbers are printed neither in the TOC nor in the body) get no `sectionNumber` and no parent; logged. Headings without text get no item. Items sit in the one `StudyVersion`.
"""))

cells.append(code_cell(r"""
for doc in DOCS:
    secs = sections[sections.doc == doc].reset_index(drop=True)
    contents = []
    for r in secs.itertuples():
        name = f"{doc} {r.number}" if r.number else f"{doc} '{r.title}'"
        c = {"id": new_id("NarrativeContent"), "name": name, "sectionTitle": r.title,
             "displaySectionTitle": True, "displaySectionNumber": bool(r.number), "childIds": [],
             "instanceType": "NarrativeContent"}
        if r.number:
            c["sectionNumber"] = r.number
        else:
            log(c["id"], "sectionNumber", "not_in_document", "", f"{doc} p{r.start_page}", "no section number printed in TOC or body")
        if r.text:
            item = {"id": new_id("NarrativeContentItem"), "name": name, "text": r.text, "instanceType": "NarrativeContentItem"}
            narrative_items.append(item)
            c["contentItemId"] = item["id"]
        contents.append(c)
    for i, c in enumerate(contents):
        if i > 0:
            c["previousId"] = contents[i - 1]["id"]
        if i + 1 < len(contents):
            c["nextId"] = contents[i + 1]["id"]
    by_number = {c["sectionNumber"]: c for c in contents if "sectionNumber" in c}
    for c in contents:
        n = c.get("sectionNumber", "")
        if "." in n:
            parent = n.rsplit(".", 1)[0]
            if parent in by_number:
                by_number[parent]["childIds"].append(c["id"])
            else:
                log(c["id"], "(parent)", "not_in_document", parent, f"{doc} {n}", "parent section number not printed")
    doc_versions[doc]["contents"] = contents
print(pd.Series({d: len(doc_versions[d]["contents"]) for d in DOCS}).to_string())
"""))

cells.append(markdown_cell(r"""
## Study, study version, titles, identifiers, organizations

- Titles (master title page): Official Study Title = "Protocol Title"; Study Acronym = "Acronym"; "Short Title" as Brief Study Title (derived: the document's label is "Short Title").
- Identifiers: NCT05986292 (ClinicalTrials.gov, cover sheet); H0P-MC-CPMP (sponsor protocol number, title page). The ISAs' own NCT numbers cannot be identifiers of this study (`not_expressible`, one log row per ISA). The master IND 144915 has no named issuing organization (`required_not_in_document`, as the REMAP-CAP UTN).
- Organizations: Eli Lilly and Company ("Sponsor Name", type Pharmaceutical Company C54149, derived); ClinicalTrials.gov (Clinical Study Registry C93453). Their `identifier` / `identifierScheme` are not stated.
"""))

cells.append(code_cell(r"""
mf = facts["CPMP"]
lilly_name = field("CPMP", "Sponsor Name")
lilly = {"id": new_id("Organization"), "name": lilly_name, "type": code("C54149", "Pharmaceutical Company", "DDF", "C188724"),
         "instanceType": "Organization"}
ctgov = {"id": new_id("Organization"), "name": "ClinicalTrials.gov", "type": code("C93453", "Clinical Study Registry", "DDF", "C188724"),
         "instanceType": "Organization"}
log(lilly["id"], "name", "mapped", lilly_name, "CPMP p2 title page 'Sponsor Name'")
log(lilly["id"], "type", "derived", "Pharmaceutical Company", "CPMP p2 title page", "sponsor is Eli Lilly and Company")
log(ctgov["id"], "name", "derived", "ClinicalTrials.gov", "CPMP p1 cover sheet", "NCT numbers are ClinicalTrials.gov identifiers")
for o in (lilly, ctgov):
    log(o["id"], "identifier", "required_not_in_document", "", "", "organization identifier not stated")
    log(o["id"], "identifierScheme", "required_not_in_document", "", "", "")

identifiers = [
    {"id": new_id("StudyIdentifier"), "text": mf["nct"], "scopeId": ctgov["id"], "instanceType": "StudyIdentifier"},
    {"id": new_id("StudyIdentifier"), "text": mf["number"], "scopeId": lilly["id"], "instanceType": "StudyIdentifier"},
]
log(identifiers[0]["id"], "text", "mapped", mf["nct"], "CPMP p1 cover sheet")
log(identifiers[1]["id"], "text", "mapped", mf["number"], "CPMP p2 title page 'Protocol Number'")
ind = re.search(r"IND\s*:?\s*(\d+)", page("CPMP", 2)).group(1)
log("-", "StudyIdentifier (IND)", "required_not_in_document", ind, "CPMP p2 title page", "IND number stated, issuing organization (scopeId 1..1) not named")
for doc in ISAS:
    log(documents[doc]["id"], "(identifier)", "not_expressible", facts[doc]["nct"], f"{doc} p1 cover sheet",
        "each ISA is registered with its own NCT number; USDM identifiers belong to the study version, not to a document")

titles = [
    {"id": new_id("StudyTitle"), "type": code("C207616", "Official Study Title", "DDF", "C207419"), "text": mf["title"], "instanceType": "StudyTitle"},
    {"id": new_id("StudyTitle"), "type": code("C207615", "Brief Study Title", "DDF", "C207419"), "text": mf["short_title"], "instanceType": "StudyTitle"},
    {"id": new_id("StudyTitle"), "type": code("C94108", "Study Acronym", "DDF", "C207419"), "text": mf["acronym"], "instanceType": "StudyTitle"},
]
log(titles[0]["id"], "text", "mapped", mf["title"], "CPMP p2 title page 'Protocol Title'")
log(titles[1]["id"], "type", "derived", "Brief Study Title", "CPMP p2 title page 'Short Title'", "'Short Title' read as brief title")
log(titles[2]["id"], "text", "mapped", mf["acronym"], "CPMP p2 title page 'Acronym'")

version_id = " / ".join(f"{d} ({facts[d]['version']})" for d in DOCS)
study_version = {
    "id": new_id("StudyVersion"), "versionIdentifier": version_id, "titles": titles, "studyIdentifiers": identifiers,
    "organizations": [lilly, ctgov], "documentVersionIds": [doc_versions[d]["id"] for d in DOCS],
    "narrativeContentItems": narrative_items, "instanceType": "StudyVersion",
}
log(study_version["id"], "versionIdentifier", "derived", version_id, "decision 2026-10-25 (structure A)",
    "the programme has no single version; StudyVersion = the set of current document versions")
log(study_version["id"], "rationale", "required_not_in_document", "", "", "no rationale for the set of document versions is stated")
log(study_version["id"], "studyDesigns", "deferred", "", "decision 2026-10-25", "one StudyDesign per ISA in a later pass")
amended = [d for d in DOCS if facts[d]["version"] != "original"]
log(study_version["id"], "amendments", "deferred", ", ".join(amended), "Protocol Amendment Summary of Changes Tables",
    f"{len(amended)} documents have a summary-of-changes table (section, description of change, brief rationale per change); StudyAmendment in a later pass")

study = {"id": new_id("Study"), "name": mf["acronym"], "versions": [study_version],
         "documentedBy": [documents[d] for d in DOCS], "instanceType": "Study"}
usdm = {"study": study, "usdmVersion": "4.0.0", "systemName": "early-clinical-design-research/12_cpmp_usdm",
        "systemVersion": "2026-10-25"}
print("documents", len(study["documentedBy"]), "| narrative items", len(narrative_items))
"""))

cells.append(markdown_cell(r"""
## Self-check against the model

As in REMAP-CAP Step 3: every `instanceType` is a model class, every key an attribute of it, every reference resolves; every absent required attribute is logged as `required_not_in_document` or `not_expressible`.
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
known = {(r["object"], r["attribute"]) for r in LOG if r["status"] in ("required_not_in_document", "not_expressible")}
unexplained = [m for m in missing if (m[0], m[2]) not in known]
assert not unexplained, unexplained
print("objects:", len(objects), "| required absent:", len(missing), "(all logged)")
print(pd.DataFrame(LOG).status.value_counts().to_string())
"""))

cells.append(code_cell(r"""
with open(OUT_DIR / "cpmp_usdm.json", "w", encoding="utf-8") as f:
    json.dump(usdm, f, indent=1, ensure_ascii=False)
pd.DataFrame(LOG).to_csv(OUT_DIR / "mapping_log.csv", index=False)
for f in sorted(OUT_DIR.iterdir()):
    if f.is_file():
        print(f"{f.name:20s} {f.stat().st_size:>10,d} bytes")
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
