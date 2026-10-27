"""Generate notebooks/14_cpmp_components.ipynb (CPMP Step 5a/5b: design components across the ISA grid).

Input: output_cpmp/step5/eligibility_items.csv, table_cells.csv, section_redactions.csv
       (scripts/14_cpmp_design_text.py), output_cpmp/step2/sections.csv, page_text.csv,
       output_cpmp/step4/amendment_changes.csv.
Output (output_cpmp/step5/): grid.csv, criteria.csv, objectives_endpoints.csv, interventions.csv,
       components.csv, crosswalk_proposals.csv, cq_*.csv.

The notebook is built as a Python dict and written with json.dump.
Run:  python3 scripts/build_14_cpmp_components_nb.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "notebooks" / "14_cpmp_components.ipynb"


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
# CPMP, Step 5a/5b – design components across the ISA grid

Question (2026-10-25): what do the 12 ISAs actually design, and which design components recur across the 4 compound × 3 disease-state grid? The documents are read for their design content — eligibility criteria, objectives and endpoints, study interventions — not for their structure.

Agreed rules:

1. Component tables first (this notebook); USDM `StudyDesign`s per ISA in a second notebook.
2. Identity: two occurrences are the same component when their text is identical after whitespace is collapsed. A second, weaker key replaces the document's own compound code, ISA number and disease name by placeholders (`template`): same template = same wording written for another compound or disease. Everything else that looks alike is a **crosswalk proposal** for review, never merged here.
3. Grid class per component, from the set of documents it occurs in: `master`, `all ISAs`, `compound column` (one compound, several disease states), `disease row` (one disease state, several compounds), `single ISA`, `other`. Content common across a disease row is never called DSA content: the DSAs are not public.

Source: `scripts/14_cpmp_design_text.py` (page layout read from the text layer and the rendered page; rules in its docstring). Nothing is typed here.
"""))

cells.append(code_cell(r"""
import difflib
import re
from pathlib import Path

import pandas as pd

BASE = Path.cwd().parent
STEP2 = BASE / "output_cpmp" / "step2"
STEP4 = BASE / "output_cpmp" / "step4"
STEP5 = BASE / "output_cpmp" / "step5"
assert (STEP5 / "eligibility_items.csv").is_file(), "run scripts/14_cpmp_design_text.py first"

elig = pd.read_csv(STEP5 / "eligibility_items.csv", dtype=str).fillna("")
cells = pd.read_csv(STEP5 / "table_cells.csv", dtype={"text": str}).fillna({"text": "", "continued_on": ""})
sred = pd.read_csv(STEP5 / "section_redactions.csv")
sections = pd.read_csv(STEP2 / "sections.csv", dtype={"number": str}).fillna({"text": "", "number": ""})
pt = pd.read_csv(STEP2 / "page_text.csv").fillna({"text": ""})
changes = pd.read_csv(STEP4 / "amendment_changes.csv").fillna("")
DOCS = list(dict.fromkeys(elig.doc))
ISAS = [d for d in DOCS if d != "CPMP"]
flat = lambda s: re.sub(r"\s+", " ", s).strip()
print("documents:", len(DOCS), "| eligibility items:", len(elig), "| table cells:", len(cells))
"""))

cells.append(markdown_cell(r"""
## The grid, from the documents

Each ISA's §5 opens with the same kind of sentence: "The master protocol CPMP and OA DSA CPMP(1) provide eligibility criteria that must be followed for this study. LY3016859 specific inclusion and exclusion criteria are listed here." The disease state is the abbreviation before "DSA", the compound the code before "specific". Long forms of the abbreviations from the abbreviation lines ("CLBP = chronic low back pain").
"""))

cells.append(code_cell(r"""
grid = []
for doc in ISAS:
    s5 = sections[(sections.doc == doc) & (sections.title == "Study Population")]
    assert len(s5) == 1, doc
    t = flat(s5.text.iloc[0])
    dis = re.search(r"\b(OA|CLBP|DPNP)\b(?:\s+CPMP\s*\(\d\))?\s+DSA", t)
    cmp_ = re.search(r"(LY\d{7})[- ]specific", t)
    assert dis and cmp_, (doc, t[:200])
    grid.append({"doc": doc, "disease": dis.group(1), "compound": cmp_.group(1), "evidence": f"{doc} §5 p{s5.start_page.iloc[0]}: {t[:160]}"})
grid = pd.DataFrame(grid)
LONG = dict(set(re.findall(r"\b(OA|CLBP|DPNP)\s*=\s*([a-z][a-z ]+?)[;.\n]", " ".join(pt.text))))
assert set(LONG) == {"OA", "CLBP", "DPNP"}, LONG
grid.to_csv(STEP5 / "grid.csv", index=False)
print(grid.pivot(index="compound", columns="disease", values="doc").to_string())
print(LONG)
G = grid.set_index("doc")
"""))

cells.append(markdown_cell(r"""
## Identity keys

- `text`: whitespace collapsed.
- `template`: as `text`, with the document's own compound code → `{compound}`, own ISA number (e.g. "OA01") → `{isa}`, own disease abbreviation and long form → `{disease}`. Only the document's own values are replaced, so a criterion of OA02 naming LY3526318 and one of BP02 naming LY3526318 stay different from one naming another compound.
"""))

cells.append(code_cell(r"""
def template(doc, text):
    t = flat(text)
    if doc in G.index:
        g = G.loc[doc]
        t = t.replace(g.compound, "{compound}").replace(doc, "{isa}")
        t = re.sub(rf"\b{g.disease}\b", "{disease}", t)
        t = re.sub(LONG[g.disease], "{disease}", t, flags=re.I)
    return t


def grid_class(docs):
    docs = set(docs)
    if "CPMP" in docs:
        return "master" if docs == {"CPMP"} else "master+ISA"
    if docs == set(ISAS):
        return "all ISAs"
    if len(docs) == 1:
        return "single ISA"
    comps = set(G.loc[list(docs), "compound"])
    dis = set(G.loc[list(docs), "disease"])
    if len(comps) == 1:
        full = set(grid[grid.compound == next(iter(comps))].doc)
        return "compound column" + ("" if docs == full else " (part)")
    if len(dis) == 1:
        full = set(grid[grid.disease == next(iter(dis))].doc)
        return "disease row" + ("" if docs == full else " (part)")
    return "other"


print(template("OA01", "are men or women who abide by the reproductive and contraceptive requirements provided in OA01 Section 10.2, Appendix 2"))
"""))

cells.append(markdown_cell(r"""
## Eligibility criteria

One row per numbered criterion (paragraphs inside a criterion kept, joined by " ¶ "). Statements in the eligibility sections (list intros, placeholders such as "Age requirements for participation will be specified in the DSA and/or ISAs.") and redaction bars are counted per document.

The criterion numbers of the ISAs look like a grid code: first digit the disease state, then a block per compound. Tested here against the grid read from §5 (not assumed).
"""))

cells.append(code_cell(r"""
crit = elig[elig.item == "criterion"].copy()
crit["number"] = crit.number.astype(int)
crit["text"] = crit.text.str.replace("\n", " ¶ ", regex=False)
crit["template"] = [template(d, t) for d, t in zip(crit.doc, crit.text)]
crit = crit.merge(grid[["doc", "disease", "compound"]], on="doc", how="left").fillna({"disease": "", "compound": ""})
crit["digit"] = crit.number // 1000
crit["block"] = crit.number % 1000 // 25 * 25
crit["slot"] = crit.number % 25
isa = crit[crit.doc != "CPMP"]
check = isa.groupby("doc").agg(disease=("disease", "first"), compound=("compound", "first"),
                               digits=("digit", lambda s: sorted(set(s))), blocks=("block", lambda s: sorted(set(s))))
print(check.to_string())
by_dis = check.groupby("disease").digits.apply(lambda s: sorted({d for x in s for d in x}))
by_cmp = check.groupby("compound").blocks.apply(lambda s: sorted({b for x in s for b in x}))
print("digits per disease:", by_dis.to_dict())
print("blocks per compound:", by_cmp.to_dict())
numbering_holds = all(len(v) == 1 for v in by_dis) and all(len(v) == 1 for v in by_cmp) and len({v[0] for v in by_dis}) == 3
print("numbering = disease digit x 1000 + compound block:", numbering_holds)

other = elig[elig.item != "criterion"]
counts = (other.assign(n=1).pivot_table(index="doc", columns="item", values="n", aggfunc="sum", fill_value=0)
          .join(crit.groupby("doc").size().rename("criteria")).reindex(DOCS).fillna(0).astype(int))
print(counts.to_string())
placeholders = other[(other.item == "statement") & other.text.str.contains(r"specified in|described in|provided in", case=False)]
inner = crit[crit.text.str.contains(r"will be specified in|are specified in", case=False)]
print(placeholders[["doc", "kind", "category", "text"]].to_string(index=False))
print(inner[["doc", "number", "text"]].to_string(index=False))
crit.drop(columns=["file"]).to_csv(STEP5 / "criteria.csv", index=False)
"""))

cells.append(markdown_cell(r"""
## Objectives and endpoints

From the ruled tables of the "Objectives and Endpoints" section: row 1 is the header; a row whose second cell is empty and whose first cell is a level ("Primary", "Secondary", "Tertiary/Exploratory") sets the level of the rows below it; every other row is one objective with its endpoint cell. An endpoint cell with list bullets (text-layer character U+F0B7) holds several endpoints, split at the bullets. Tables or rows hidden by redaction bars are counted, not filled.
"""))

cells.append(code_cell(r"""
LEVELS = {"Primary", "Secondary", "Tertiary/Exploratory", "Exploratory", "Tertiary"}
oe_rows, oe_red = [], []
oc = cells[cells.section == "objectives_endpoints"]
for (doc, table), t in oc.groupby(["doc", "table"], sort=False):
    level = ""
    for row, r in t.groupby("row"):
        texts = list(r.sort_values("col").text)
        if row == 1:
            continue
        if r.redacted.any() and not any(texts):
            oe_red.append({"doc": doc, "what": "table row", "page": r.page.iloc[0]})
            continue
        if texts[0] in LEVELS and not "".join(texts[1:]):
            level = texts[0]
            continue
        assert len(texts) == 2, (doc, row, texts)
        objective, ep_cell = flat(texts[0]), texts[1]
        parts = [flat(p) for p in re.split("", ep_cell) if flat(p)]
        lead = parts[0] if not ep_cell.lstrip().startswith("") and len(parts) > 1 else ""
        endpoints = parts[1:] if lead else parts
        for k, ep in enumerate(endpoints, 1):
            oe_rows.append({"doc": doc, "level": level, "objective": objective, "endpoint_lead": lead, "endpoint_no": k,
                            "endpoint": ep, "page": r.page.iloc[0], "redacted_in_row": bool(r.redacted.any())})
oe = pd.DataFrame(oe_rows)
for r in sred[sred.section == "objectives_endpoints"].itertuples():
    oe_red.append({"doc": r.doc, "what": "redaction bar outside a table row", "page": r.page})
oe_red = pd.DataFrame(oe_red)
oe["objective_template"] = [template(d, t) for d, t in zip(oe.doc, oe.objective)]
oe["endpoint_template"] = [template(d, (l + " " + t).strip()) for d, l, t in zip(oe.doc, oe.endpoint_lead, oe.endpoint)]
oe.to_csv(STEP5 / "objectives_endpoints.csv", index=False)
print(oe.groupby(["doc", "level"]).size().unstack(fill_value=0).reindex(DOCS).fillna(0).astype(int).to_string())
print(oe_red.groupby(["doc", "what"]).size().to_string())
"""))

cells.append(markdown_cell(r"""
## Study interventions

From the ruled table of the "Study Intervention(s) Administered" section: first column the attribute (row label), the other columns one intervention each, named in the header row. Long format, one row per intervention × attribute. Row labels keep their text-layer spelling (letter spacing lost in some documents: "DoseFormulation"); the attribute key used for comparison removes spaces only.
"""))

cells.append(code_cell(r"""
iv_rows = []
ic = cells[cells.section == "interventions"]
for (doc, table), t in ic.groupby(["doc", "table"], sort=False):
    header = t[t.row == 1].sort_values("col")
    names = list(header.text)[1:]
    for row, r in t[t.row > 1].groupby("row"):
        r = r.sort_values("col")
        label = flat(r.text.iloc[0])
        for name, (_, c) in zip(names, list(r.iloc[1:].iterrows())):
            iv_rows.append({"doc": doc, "intervention": flat(name), "attribute": label, "attribute_key": re.sub(r"\s+", "", label).lower(),
                            "value": flat(c.text), "redacted": bool(c.redacted), "page": c.page})
iv = pd.DataFrame(iv_rows)
iv["value_template"] = [template(d, v) for d, v in zip(iv.doc, iv.value)]
iv.to_csv(STEP5 / "interventions.csv", index=False)
master_iv = sections[(sections.doc == "CPMP") & sections.title.str.contains("Intervention Administered")].text.iloc[0]
print("master §6.1:", flat(master_iv))
print(iv[iv.intervention != "Placebo"].pivot_table(index="attribute_key", columns="doc", values="value", aggfunc="first").reindex(columns=ISAS).fillna("").to_string(max_colwidth=22))
print("redacted values:", iv[iv.redacted][["doc", "intervention", "attribute"]].values.tolist())
"""))

cells.append(markdown_cell(r"""
## Components and grid classes

One table for all three kinds. A component is a distinct `template` (wording) within its kind; it lists the documents it occurs in, whether the text is identical in all of them (`text_identical`) or only the template, and its grid class. For interventions the component is attribute + value per compound column (placebo rows included as such).
"""))

cells.append(code_cell(r"""
comp_rows = []


def add(kind, df, key, text_col, extra):
    for k, g in df.groupby(key, sort=False):
        docs = list(dict.fromkeys(g.doc))
        comp_rows.append({"kind": kind, "key": k if isinstance(k, str) else " | ".join(k), "docs": ";".join(docs), "n_docs": len(docs),
                          "class": grid_class(docs), "text_identical": g[text_col].nunique() == 1,
                          "example": g[text_col].iloc[0], **extra(g)})


add("criterion", crit, "template", "text", lambda g: {"numbers": ";".join(f"{d}:{n}" for d, n in zip(g.doc, g.number)),
                                                       "list": ";".join(sorted(set(g.kind)))})
add("objective", oe.drop_duplicates(["doc", "objective"]), "objective_template", "objective", lambda g: {"numbers": "", "list": ";".join(sorted(set(g.level)))})
add("endpoint", oe, "endpoint_template", "endpoint", lambda g: {"numbers": "", "list": ";".join(sorted(set(g.level)))})
ivc = iv.assign(iv_key=[f"{'placebo' if n == 'Placebo' else 'drug'} | {a} | {v}" for n, a, v in zip(iv.intervention, iv.attribute_key, iv.value_template)])
add("intervention attribute", ivc[~ivc.redacted], "iv_key", "value", lambda g: {"numbers": "", "list": ";".join(sorted(set(g.intervention)))})
comp = pd.DataFrame(comp_rows)
comp.to_csv(STEP5 / "components.csv", index=False)
print(comp.pivot_table(index="kind", columns="class", values="key", aggfunc="count", fill_value=0).to_string())
"""))

cells.append(markdown_cell(r"""
## Crosswalk proposals (for review)

Pairs of criteria with different wording that may be the same component:
- `same_slot`: ISA criteria with the same number modulo 1000 (same compound block and position) in different disease states, if the numbering test above holds;
- `similar`: wording similarity (difflib ratio) of at least 0.85 between templates, any documents.

Nothing is merged; the pairs are listed with their texts for Kerstin's review.
"""))

cells.append(code_cell(r"""
props = []
ct = crit.reset_index(drop=True)
for i in range(len(ct)):
    for j in range(i + 1, len(ct)):
        a, b = ct.loc[i], ct.loc[j]
        if a.template == b.template or a.doc == b.doc:
            continue
        ratio = difflib.SequenceMatcher(None, a.template, b.template, autojunk=False).ratio()
        slot = numbering_holds and a.doc != "CPMP" and b.doc != "CPMP" and a.number % 1000 == b.number % 1000
        if slot or ratio >= 0.85:
            props.append({"reason": "same_slot" if slot else "similar", "ratio": round(ratio, 3),
                          "doc_a": a.doc, "number_a": a.number, "doc_b": b.doc, "number_b": b.number,
                          "text_a": a.text, "text_b": b.text})
props = pd.DataFrame(props).sort_values(["reason", "ratio"], ascending=[True, False])
props.to_csv(STEP5 / "crosswalk_proposals.csv", index=False)
print(props.groupby("reason").size().to_string())
print(props[props.ratio < 1].head(25)[["reason", "ratio", "doc_a", "number_a", "doc_b", "number_b", "text_a", "text_b"]].to_string(index=False, max_colwidth=60))
"""))

cells.append(markdown_cell(r"""
## Competency questions

1. Which endpoints and instruments are used across the ISAs, per disease state? (ISA tables only; master endpoints apply to all.)
2. Which eligibility criteria are shared across disease states?
3. Which components are disease-independent (same wording in all three disease states of a compound, or in the master)?
4. Which design changes rest on the same stated reason? (Step 4 amendment rows with the same brief rationale in more than one document.)

The fifth question of the summary (CDISC domains and terminologies a new ISA needs) needs the CDISC mapping, a later step.
"""))

cells.append(code_cell(r"""
cq1 = (oe[oe.doc != "CPMP"].merge(grid, on="doc").groupby(["disease", "endpoint_template"])
       .agg(isas=("doc", lambda s: ";".join(dict.fromkeys(s))), level=("level", "first")).reset_index())
cq1.to_csv(STEP5 / "cq1_endpoints_by_disease.csv", index=False)
print("CQ1:", len(cq1), "rows"); print(cq1.to_string(index=False, max_colwidth=80))

cr = crit[crit.doc != "CPMP"].groupby("template").agg(docs=("doc", lambda s: ";".join(dict.fromkeys(s))),
                                                      diseases=("disease", lambda s: ";".join(sorted(set(s)))),
                                                      compounds=("compound", lambda s: ";".join(sorted(set(s)))),
                                                      identical=("text", lambda s: s.nunique() == 1)).reset_index()
cq2 = cr[cr.diseases.str.count(";") >= 1].sort_values("docs")
cq2.to_csv(STEP5 / "cq2_criteria_across_diseases.csv", index=False)
print("CQ2:", len(cq2), "criteria in more than one disease state"); print(cq2.to_string(index=False, max_colwidth=70))

cq3 = comp[comp["class"].isin(["master", "master+ISA", "all ISAs", "compound column"])][["kind", "class", "n_docs", "text_identical", "example"]]
cq3.to_csv(STEP5 / "cq3_disease_independent.csv", index=False)
print("CQ3:"); print(cq3.groupby(["kind", "class"]).size().to_string())

rat = changes[(changes.rationale != "") & ~changes.status.isin(["empty_row", "empty_row_redacted"])]
cq4 = rat.groupby("rationale").agg(docs=("doc", lambda s: ";".join(dict.fromkeys(s))), n_docs=("doc", "nunique"),
                                   sections=("section_as_printed", lambda s: " | ".join(dict.fromkeys(s)))).reset_index()
cq4 = cq4[cq4.n_docs > 1].sort_values("n_docs", ascending=False)
cq4.to_csv(STEP5 / "cq4_shared_rationale.csv", index=False)
print("CQ4:", len(cq4), "rationales stated in more than one document"); print(cq4.to_string(index=False, max_colwidth=60))
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
