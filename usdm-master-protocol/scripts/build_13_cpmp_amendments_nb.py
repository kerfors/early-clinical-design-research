"""Generate notebooks/13_cpmp_amendments.ipynb (CPMP Step 4: StudyAmendment from the summary-of-changes tables).

Input: output_cpmp/step3/cpmp_usdm.json, output_cpmp/step3/mapping_log.csv,
       output_cpmp/step4/amendment_changes.csv, amendment_headers.csv, amendment_redactions.csv
       (scripts/13_cpmp_amendment_tables.py), output_cpmp/step2/toc.csv,
       notebooks/12_cpmp_usdm.ipynb (setup, helper and code cells, executed unchanged),
       usdm-rdf (DDF-RA v4.0.0 model and CT).
Output: output_cpmp/step4/cpmp_usdm_v2.json, output_cpmp/step4/mapping_log_step4.csv,
        output_cpmp/step4/cross_layer_changes.csv.

The notebook is built as a Python dict and written with json.dump.
Run:  python3 scripts/build_13_cpmp_amendments_nb.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "notebooks" / "13_cpmp_amendments.ipynb"


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
# CPMP, Step 4 – StudyAmendment from the summary-of-changes tables

Decisions agreed 2026-10-25:

- **D1** All 12 amendments (master (a), 10 ISAs (a), NP03 (a) and (b)) sit on the one `StudyVersion` of Step 3. USDM v4.0.0 has no link from a `StudyAmendment` to a document or document version; the amended document is reached only through `StudyChange.changedSections.appliesToId`.
- **D2** `primaryReason` (1..1, a coded `StudyAmendmentReason`) is not coded in any document: left out and logged. The overall rationale text goes to `summary`.
- **D3** Output is a new file, `output_cpmp/step4/cpmp_usdm_v2.json` = Step 3 JSON + amendments. Step 3 files are not changed.
- **D4** "Throughout the protocol" rows are kept as a `StudyChange`; `sectionNumber` is left out and logged.

Source: the cells and change rows read by `scripts/13_cpmp_amendment_tables.py` (text layer, word spacing from Step 2 page text, OCR check per cell; see its docstring for the rules). Nothing is retyped here. One `StudyChange` per change row of the table: section → `DocumentContentReference`, description of change → `summary`, brief rationale → `rationale`.
"""))

cells.append(markdown_cell(r"""
## Setup: Step 3 helpers, unchanged

The setup, helper and code cells of `12_cpmp_usdm.ipynb` are executed as they are (selected by content, asserted). Then `OUT_DIR` is pointed to `step4`, the log is emptied for this step, and the id counters continue from the ids already in the Step 3 JSON.
"""))

cells.append(code_cell(r"""
import json
from pathlib import Path

nb12 = json.loads((Path.cwd() / "12_cpmp_usdm.ipynb").read_text())
markers = ["MODEL = yaml.safe_load", "def new_id(cls):", "def code(c, decode, source, codelist=None):"]
picked = []
for m in markers:
    found = [c for c in nb12["cells"] if c["cell_type"] == "code" and m in "".join(c["source"])]
    assert len(found) == 1, (m, len(found))
    picked.append("".join(found[0]["source"]))
for src in picked:
    exec(src)

STEP3 = BASE / "output_cpmp" / "step3"
OUT_DIR = BASE / "output_cpmp" / "step4"
usdm = json.loads((STEP3 / "cpmp_usdm.json").read_text())
log3 = pd.read_csv(STEP3 / "mapping_log.csv").fillna("")
LOG.clear()
_counter.clear()


def all_ids(o, out):
    if isinstance(o, dict):
        if "instanceType" in o:
            out.append(o["id"])
        for v in o.values():
            all_ids(v, out)
    elif isinstance(o, list):
        for v in o:
            all_ids(v, out)
    return out


for i in all_ids(usdm, []):
    cls, n = i.rsplit("_", 1)
    if n.isdigit():
        _counter[cls] = max(_counter.get(cls, 0), int(n))
study = usdm["study"]
(study_version,) = study["versions"]
assert "amendments" not in study_version
docs_by_no = {d["name"]: d for d in study["documentedBy"]}
print("Step 3 objects:", len(all_ids(usdm, [])), "| documents:", len(docs_by_no), "| counters continue from", len(_counter), "classes")
"""))

cells.append(markdown_cell(r"""
## Inputs from the table extraction

- `amendment_headers.csv`: per amendment the heading ("Amendment [a]", "Amendment (a)", "Amendment a"), the Document History text, the Overall Rationale text and the number of redaction bars in it.
- `amendment_changes.csv`: one row per table row. Rows with no text inside a redaction bar (`empty_row_redacted`) and a layout gap with no text (`empty_row`) are not changes; they are logged.
- Where the text layer is short of the printed page (Step 13 OCR check), `<column>_ocr` holds the OCR text for the missing part followed by the text-layer text; it is used instead of the text-layer value and logged as `derived` (OCR).
"""))

cells.append(code_cell(r"""
STEP4 = BASE / "output_cpmp" / "step4"
heads = pd.read_csv(STEP4 / "amendment_headers.csv").fillna("")
rows = pd.read_csv(STEP4 / "amendment_changes.csv").fillna("")
reds = pd.read_csv(STEP4 / "amendment_redactions.csv").fillna("")
toc = pd.read_csv(STEP2 / "toc.csv", dtype=str).fillna("")
for col in ("redaction_in_row",):
    rows[col] = rows[col].astype(str) == "True"
assert len(heads) == 12 and heads.groupby("doc").size().max() == 2
print(heads[["doc", "amendment", "page", "heading", "redaction_bars_in_rationale"]].to_string(index=False))
print(rows.groupby(["doc", "amendment"]).size().rename("table rows").reset_index().T.to_string(header=False))
print(rows.status.replace("", "-").value_counts().to_string())
"""))

cells.append(markdown_cell(r"""
## Section references

`Section # and Name` as printed, split into number and title by pattern: an optional leading "Section", a number made of digits and dots, then the title (a trailing dot of the number and a leading comma of the title are dropped, e.g. "Section 10.2, Appendix 2"). Letter spacing lost in the text layer stays as it is ("4.1.1DesignOutline"). A cell without a number ("Throughout the protocol") has no `sectionNumber` (D4) and keeps the cell text as `sectionTitle` (derived).

Each number is looked up in the Step 2 TOC of the same document (the current version; for NP03 (a) that is the TOC of version (b)) and the result is logged: `toc_match` (number and title as in the TOC, ignoring case and spaces), `toc_number_only` (number found, title differs) or `not_in_toc`.
"""))

cells.append(code_cell(r"""
SECTION = re.compile(r"^(?:Section\s*)?(\d+(?:\.\d+)*)\.?\s*,?\s*(.*)$", re.S)
squash = lambda s: re.sub(r"\s+", "", s).lower()


def section_ref(doc, printed):
    m = SECTION.match(printed)
    if not m:
        return None, printed, "no_number"
    number, title = m.group(1), m.group(2).strip()
    t = toc[(toc.doc == doc) & (toc.toc_number == number)]
    if t.empty:
        check = "not_in_toc"
    elif squash(t.title.iloc[0]) == squash(title):
        check = "toc_match"
    else:
        check = f"toc_number_only (TOC: {t.title.iloc[0]})"
    return number, title, check


checks = []
for r in rows[~rows.status.isin(["empty_row", "empty_row_redacted"])].itertuples():
    sec = r.section_ocr or r.section_as_printed
    n, t, c = section_ref(r.doc, sec)
    checks.append({"doc": r.doc, "amendment": r.amendment, "row": r.row, "printed": sec, "number": n, "title": t, "check": c})
checks = pd.DataFrame(checks)
print(checks.check.str.split(" ").str[0].value_counts().to_string())
print(checks[~checks.check.isin(["toc_match"])].to_string(index=False))
"""))

cells.append(markdown_cell(r"""
## StudyAmendment and StudyChange

Per amendment:

- `name` = document number and amendment letter as on the title page ("H0P-MC-BP02(a)"); `number` = the letter; `summary` = the Overall Rationale text (whitespace collapsed, as all Step 3 text values; the text-layer bullet character U+F0B7 of the master's list is kept as it is). Redaction bars inside the rationale are logged.
- `dateValues`: the approval date of the document version the amendment produces (Step 3, title page). NP03 (a) is no longer the current version: its date "12 March 2021" is printed in the Appendix 5 heading and the Document History "Date" column, not stated to be an approval date; it is logged as `not_expressible`, as for earlier versions in Step 3.
- `previousId`: NP03 (b) → NP03 (a), the only document with two amendments.
- `primaryReason`, `geographicScopes`: not stated (D2), logged.

Per change row: `name` = "<document>(<letter>) row <n>"; `summary` = description of change; `rationale` = brief rationale; `changedSections` = one `DocumentContentReference` with `appliesToId` = the amended document. Continuations across a page break are already joined by the extraction (status kept in the log evidence). Strike-through and underline in a description (tracked-change markup, e.g. "have ~~completed~~ __participated in__") are lost in a string; logged as `not_expressible` with the struck and underlined text.
"""))

cells.append(code_cell(r"""
def evidence(r):
    return f"{r.doc}({r.amendment}) p{r.page} summary-of-changes row {r.row}" + (f" [{r.status}]" if r.status else "")


amendments, by_key = [], {}
for h in heads.sort_values(["doc", "amendment"]).itertuples():
    document = docs_by_no[f"H0P-MC-{h.doc}"]
    current = document["versions"][-1]
    a_id = new_id("StudyAmendment")
    amend = {"id": a_id, "name": f"{document['name']}({h.amendment})", "number": h.amendment,
             "summary": flat(h.overall_rationale), "changes": [], "instanceType": "StudyAmendment"}
    ev = f"{h.doc} p{h.page} '{h.heading}'"
    log(a_id, "name", "derived", amend["name"], ev, "document number + amendment letter, as on the title page")
    log(a_id, "number", "mapped", h.amendment, ev)
    log(a_id, "summary", "mapped", amend["summary"], f"{h.doc} p{h.page} 'Overall Rationale for the Amendment'")
    if h.redaction_bars_in_rationale:
        log(a_id, "summary", "redacted_in_document", h.redaction_bars_in_rationale, f"{h.doc} p{h.page}",
            f"{h.redaction_bars_in_rationale} redaction bar(s) in the Overall Rationale; hidden text not in the text layer")
    if current["version"] == h.amendment:
        (vdate,) = current["dateValues"]
        date = {"id": new_id("GovernanceDate"), "name": f"{amend['name']} approval", "type": code("C71476", "Approval Date", "DDF", "C207413"),
                "dateValue": vdate["dateValue"], "instanceType": "GovernanceDate"}
        amend["dateValues"] = [date]
        log(date["id"], "dateValue", "mapped", vdate["dateValue"], f"{h.doc} p2 title page (Step 3 {current['id']})",
            "approval date of the document version produced by this amendment")
        log(date["id"], "geographicScopes", "required_not_in_document", "", f"{h.doc} p2 title page", "1..*; no geographic scope stated")
    else:
        m = re.search(r"\d{1,2} \w+ \d{4}", h.heading)
        assert m and h.doc == "NP03" and h.amendment == "a", (h.doc, h.amendment, h.heading)
        log(a_id, "dateValues", "not_expressible", parse_date(m.group(0)), ev,
            "date in the Appendix 5 heading and the Document History 'Date' column; not stated to be an approval, effective or issued date")
    log(a_id, "primaryReason", "required_not_in_document", "", ev,
        "1..1 coded StudyAmendmentReason (C207415); the document gives the reason as text only (summary); decision D2")
    log(a_id, "geographicScopes", "required_not_in_document", "", ev, "1..*; no geographic scope stated")
    log(a_id, "(amended document version)", "not_expressible", f"{document['name']} version {h.amendment}", ev,
        "StudyAmendment has no reference to the StudyDefinitionDocument or the document version it produces; "
        "only StudyChange.changedSections.appliesToId points to the document (not the version)")

    for r in rows[(rows.doc == h.doc) & (rows.amendment == h.amendment)].itertuples():
        if r.status in ("empty_row", "empty_row_redacted"):
            log(a_id, "changes", "redacted_in_document" if r.status == "empty_row_redacted" else "not_a_change", "",
                evidence(r), "table row hidden by a redaction bar" if r.status == "empty_row_redacted" else "layout gap with no text")
            continue
        c_id = new_id("StudyChange")
        change = {"id": c_id, "name": f"{document['name']}({h.amendment}) row {r.row}", "instanceType": "StudyChange"}
        desc = r.description_ocr or r.description
        if desc:
            change["summary"] = flat(desc)
            log(c_id, "summary", "derived" if r.description_ocr else "mapped", change["summary"], evidence(r),
                "first part from OCR (text layer lacks it), rest text layer; checked visually 2026-10-25" if r.description_ocr else "Description of Change")
        else:
            log(c_id, "summary", "required_not_in_document", "", evidence(r),
                "description cell hidden by a redaction bar" if r.redaction_in_row else "Description of Change cell empty")
        if r.rationale:
            change["rationale"] = flat(r.rationale)
            log(c_id, "rationale", "mapped", change["rationale"], evidence(r), "Brief Rationale")
        else:
            log(c_id, "rationale", "required_not_in_document", "", evidence(r), "Brief Rationale cell empty")
        if r.redaction_in_row and desc:
            log(c_id, "(row)", "redacted_in_document", "", evidence(r), "a redaction bar overlaps this row")
        marks = [f"{k}: {v}" for k, v in (("struck", r.description_struck), ("underlined", r.description_underlined),
                                           ("rationale struck", r.rationale_struck), ("rationale underlined", r.rationale_underlined)) if v]
        if marks:
            log(c_id, "summary", "not_expressible", "; ".join(marks), evidence(r), "tracked-change markup in the cell; a string carries no markup")

        sec = r.section_ocr or r.section_as_printed
        number, title, check = section_ref(h.doc, sec)
        ref = {"id": new_id("DocumentContentReference"), "sectionTitle": title, "appliesToId": document["id"],
               "instanceType": "DocumentContentReference"}
        if number:
            ref["sectionNumber"] = number
            log(ref["id"], "sectionNumber", "derived" if r.section_ocr else "mapped", number, evidence(r), f"Section # and Name '{flat(sec)}'; {check}")
        else:
            log(ref["id"], "sectionNumber", "required_not_in_document", "", evidence(r), f"'{flat(sec)}' names no section; decision D4")
            log(ref["id"], "sectionTitle", "derived", title, evidence(r), "the table's Section # and Name text; not a section title")
        if r.section_ocr:
            log(ref["id"], "sectionTitle", "derived", title, evidence(r), "from OCR (text layer lacks the cell); checked visually 2026-10-25")
        change["changedSections"] = [ref]
        amend["changes"].append(change)
    amendments.append(amend)
    by_key[(h.doc, h.amendment)] = amend

by_key[("NP03", "b")]["previousId"] = by_key[("NP03", "a")]["id"]
log(by_key[("NP03", "b")]["id"], "previousId", "mapped", by_key[("NP03", "a")]["id"], "NP03 p41 Appendix 5 'Protocol Amendment History'")
log("-", "StudyAmendment.number", "not_expressible", "a (x11), b (x1)", "title pages",
    "'number' identifies an amendment only within one document; 11 amendments have number 'a'")
study_version["amendments"] = amendments
print(pd.DataFrame([{"amendment": a["name"], "changes": len(a["changes"]), "date": a.get("dateValues", [{}])[0].get("dateValue", "-")} for a in amendments]).to_string(index=False))
"""))

cells.append(markdown_cell(r"""
## Changes that name another layer

Rows whose description or rationale names the master protocol, CPMP, an ISA, a DSA or a disease-state addendum (pattern below). They record that a change in one layer is caused by, or moves content to, another layer, sometimes with the other layer's version ("Master protocol updates for CPMP amendment (a)"). USDM has no place for this beyond the text; the list is written out as input for the cdd-layer.
"""))

cells.append(code_cell(r"""
LAYER = re.compile(r"master|CPMP|\bISAs?\b|\bDSAs?\b|disease[- ]state", re.I)
VERSIONED = re.compile(r"(?:CPMP|master protocol)\s*(?:amendment\s*)?[\[(]?\s*[a-z]\s*[\])]|amendment\s*[\[(]\s*[a-z]\s*[\])]", re.I)
cross = []
for a in amendments:
    for c in a["changes"]:
        for field_name in ("summary", "rationale"):
            text = c.get(field_name, "")
            if LAYER.search(text):
                cross.append({"amendment": a["name"], "change": c["name"], "field": field_name, "text": text,
                              "names_version": bool(VERSIONED.search(text)),
                              "section": c["changedSections"][0].get("sectionNumber", "") + " " + c["changedSections"][0]["sectionTitle"]})
cross = pd.DataFrame(cross)
print(len(cross), "rows;", int(cross.names_version.sum()), "name a version")
print(cross[["amendment", "field", "names_version", "text"]].to_string(index=False, max_colwidth=90))
"""))

cells.append(markdown_cell(r"""
## Self-check against the model

Same check as Step 3 (`model_attrs` and `walk` as there; that cell itself is not executed, since it checks the Step 3 log): every `instanceType` is a model class, every key an attribute of it, every reference resolves; every absent required attribute is logged (Step 3 log or this step's log) as `required_not_in_document` or `not_expressible`.
"""))

cells.append(code_cell(r"""
def model_attrs(cls):
    out = {}
    for sc in MODEL[cls].get("Super Classes", []) or []:
        out.update(model_attrs(sc["$ref"].split("/")[-1]))
    out.update(MODEL[cls].get("Attributes", {}) or {})
    return out


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


objects = {}
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
logged = pd.concat([log3, pd.DataFrame(LOG)])
known = {(r.object, r.attribute) for r in logged.itertuples() if r.status in ("required_not_in_document", "not_expressible")}
unexplained = [m for m in missing if (m[0], m[2]) not in known]
assert not unexplained, unexplained
new = [m for m in missing if m[0] in {x["object"] for x in LOG}]
print("objects:", len(objects), "| required absent:", len(missing), f"(all logged; {len(new)} in this step)")
print(pd.Series([m[1] + "." + m[2] for m in new]).value_counts().to_string())
print(pd.DataFrame(LOG).status.value_counts().to_string())
"""))

cells.append(code_cell(r"""
usdm["systemName"] = "early-clinical-design-research/13_cpmp_amendments"
usdm["systemVersion"] = "2026-10-25"
with open(OUT_DIR / "cpmp_usdm_v2.json", "w", encoding="utf-8") as f:
    json.dump(usdm, f, indent=1, ensure_ascii=False)
pd.DataFrame(LOG).to_csv(OUT_DIR / "mapping_log_step4.csv", index=False)
cross.to_csv(OUT_DIR / "cross_layer_changes.csv", index=False)
for name in ("cpmp_usdm_v2.json", "mapping_log_step4.csv", "cross_layer_changes.csv"):
    print(f"{name:26s} {(OUT_DIR / name).stat().st_size:>10,d} bytes")
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
