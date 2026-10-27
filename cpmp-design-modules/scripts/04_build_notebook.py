"""Generate notebooks/01_cq_check.ipynb (built with the json module).

The notebook runs each competency query (queries/*.rq) over output/inferred.ttl and
checks the answer against pandas computed directly from the Step 5 / Step 2 tables.
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
NB = BASE / "notebooks" / "01_cq_check.ipynb"


def lines(text):
    text = text.strip("\n") + "\n"
    out = text.splitlines(keepends=True)
    return out


def markdown_cell(text):
    return {"cell_type": "markdown", "metadata": {}, "source": lines(text)}


def code_cell(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines(text)}


cells = [
    markdown_cell("""
# CPMP design modules: competency questions

Each competency question is a SPARQL query in `queries/`, run over `output/inferred.ttl`
(the modules merged and classified with ELK, `scripts/02_reason.py`). Each answer is
checked against pandas computed directly from the Step 5 and Step 2 tables. A mismatch
stops the notebook.

Modules: master, three disease states (content not public), four compounds (no document of
their own), twelve ISAs with documents, three ISAs registered on CT.gov with no documents.
"""),
    code_cell("""
import re
from pathlib import Path

import pandas as pd
import rdflib

BASE = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
STEP5 = BASE.parent / "usdm-master-protocol" / "output_cpmp" / "step5"
STEP2 = BASE.parent / "usdm-master-protocol" / "output_cpmp" / "step2"
NS = "https://kerfors.github.io/early-clinical-design-research/cpmp-design-modules/"

graph = rdflib.Graph()
graph.parse(BASE / "output" / "inferred.ttl")


def norm(text):
    return re.sub(r"\\s+", " ", str(text)).strip()


def short(value):
    return str(value).replace(NS, "cpmp:")


def run(name):
    res = graph.query((BASE / "queries" / f"{name}.rq").read_text())
    return pd.DataFrame([[short(v) for v in row] for row in res], columns=[str(v) for v in res.vars])


components = pd.read_csv(STEP5 / "components.csv")
components = components[components["kind"] != "intervention attribute"].copy()
grid = pd.read_csv(STEP5 / "grid.csv")
disease_of = dict(zip(grid["doc"], grid["disease"]))
compound_of = dict(zip(grid["doc"], grid["compound"]))

# Crosswalk decisions (sources/crosswalk_decisions.csv), applied independently of the build.
criteria = pd.read_csv(STEP5 / "criteria.csv")
key_of = {(r.doc, int(r.number)): r.template for r in criteria.itertuples() if pd.notna(r.number)}
decisions = pd.read_csv(BASE / "sources" / "crosswalk_decisions.csv")
links = [(key_of[(a.split()[0], int(a.split()[1].strip("[]")))], key_of[(b.split()[0], int(b.split()[1].strip("[]")))])
         for a, b in decisions.loc[decisions["decision"] == "merge", ["a", "b"]].values]
group_of = {}
for ka, kb in links:
    ga, gb = group_of.get(ka, {ka}), group_of.get(kb, {kb})
    merged = ga | gb
    for k in merged:
        group_of[k] = merged
n_docs = dict(zip(components["key"], components["n_docs"]))
canonical = {k: sorted(g, key=lambda x: (-n_docs[x], x))[0] for k, g in group_of.items()}
components["key"] = components["key"].map(lambda k: canonical.get(k, k))
components = (components.groupby("key", as_index=False)
              .agg(kind=("kind", "first"), list=("list", "first"),
                   docs=("docs", lambda s: ";".join(sorted({d for x in s for d in x.split(";")})))))


def sharing(docs):
    if docs == ["CPMP"]:
        return "master"
    if len(docs) == 1:
        return "single ISA"
    if len({compound_of[d] for d in docs}) > 1:
        return "other"
    return "compound column" if len(docs) == 3 else "compound column (part)"


components["class"] = components["docs"].str.split(";").map(sharing)
components["label"] = components["key"].map(norm)
print(len(links), "merge decisions ->", len(set(map(frozenset, group_of.values()))), "merged components")
xref = pd.read_csv(STEP2 / "cross_references.csv")
print(len(graph), "triples;", len(components), "components (criteria, objectives, endpoints)")
"""),
    markdown_cell("""
## Reasoner check: inferred compound design

Each ISA design is asserted under the master design and its disease-state design only.
Its compound design is inferred (it has every component of the compound design). The
inferred compound must equal the compound named in the ISA section 5 sentence, and the
three ISAs without documents must have none.
"""),
    code_cell("""
hierarchy = pd.read_csv(BASE / "output" / "design_hierarchy.csv")
inferred_compound = (hierarchy[(hierarchy["role"] == "compound x disease state")
                               & hierarchy["superclass"].str.startswith("cpmp:Compound_")]
                     .assign(compound=lambda t: t["superclass"].str.replace("cpmp:Compound_", "", regex=False)))
if (inferred_compound["status"] != "inferred").any():
    raise AssertionError("a compound design is asserted")
got = dict(zip(inferred_compound["design"].str.replace("cpmp:ISA_", "", regex=False), inferred_compound["compound"]))
if got != compound_of:
    raise AssertionError(f"inferred compounds differ: {got} vs {compound_of}")
isa_all = sorted(hierarchy.loc[hierarchy["role"] == "compound x disease state", "design"].unique())
no_compound = sorted(set(isa_all) - {f"cpmp:ISA_{d}" for d in got})
print("inferred compound = stated compound for", len(got), "ISAs")
print("ISA designs with no compound design:", no_compound)
"""),
    markdown_cell("""
## CQ1 Which components are disease-independent?

Two readings:

- **CQ1a, by module:** part of the master design or of a compound design. This is the Step 5
  definition (`cq3_disease_independent.csv`: classes master and compound column).
- **CQ1b, by occurrence:** part of a design in each of the three disease states.
"""),
    code_cell("""
cq1a = run("cq1a_module_independent")
expected_a = set(components.loc[components["class"].isin(["master", "compound column"]), "label"])
if set(cq1a["label"]) != expected_a or len(cq1a) != len(expected_a):
    raise AssertionError("CQ1a differs from pandas")
step5_cq3 = pd.read_csv(STEP5 / "cq3_disease_independent.csv")
step5_counts = step5_cq3[step5_cq3["kind"] != "intervention attribute"].groupby("class").size().to_dict()
print("CQ1a:", len(cq1a), "components; by role", cq1a.groupby("role").size().to_dict(), "; Step 5 cq3", step5_counts)

cq1b = run("cq1b_occurrence_independent")
n_states = components["docs"].str.split(";").map(lambda ds: 3 if ds == ["CPMP"] else len({disease_of[d] for d in ds}))
expected_b = set(components.loc[n_states == 3, "label"])
if set(cq1b["label"]) != expected_b:
    raise AssertionError("CQ1b differs from pandas")
only_b = components[components["label"].isin(set(cq1b["label"]) - set(cq1a["label"]))]
print("CQ1b:", len(cq1b), "components")
print("In CQ1b but not CQ1a:")
print(only_b[["kind", "class", "docs", "label"]].to_string(index=False))
"""),
    markdown_cell("""
## CQ2 What does a new ISA in a disease state inherit before anything is written for it?

Test case: OA07, BP07, NP07 (LY4065967), registered on CT.gov with no documents posted.
Expected: every master component plus every slot of its disease-state design, and nothing
from a compound design.
"""),
    code_cell("""
cq2 = run("cq2_new_isa_inherits")
n_master = int((components["class"] == "master").sum())
action = rdflib.URIRef("http://purl.obolibrary.org/obo/IAO_0000007")
slot_classes = {short(s) for s in graph.subjects(rdflib.RDFS.subClassOf, rdflib.URIRef(NS + "DelegatedSlot"))
                if (s, rdflib.RDFS.subClassOf, action) not in graph}
per_isa = cq2.groupby("isa").agg(parts=("part", "nunique"), sources=("from", lambda s: sorted(set(s))))
print(per_isa.to_string())
for isa, row in per_isa.iterrows():
    if row["parts"] != n_master + len(slot_classes):
        raise AssertionError(f"{isa}: {row['parts']} parts, expected {n_master} + {len(slot_classes)}")
if sorted(per_isa.index) != no_compound:
    raise AssertionError("CQ2 ISAs differ from the ISAs with no compound design")
print(f"each inherits {n_master} master components + {len(slot_classes)} disease-state slots")
"""),
    markdown_cell("""
## CQ3 Which designs differ only in the disease-state module?

For each ISA: its components beyond its inferred compound design. Two ISAs in one compound
column with the same set differ only in the disease-state module (whose content is not
public).
"""),
    code_cell("""
cq3 = run("cq3_isa_specific")
cq3["doc"] = cq3["isa"].str.replace("cpmp:ISA_", "", regex=False)
expected = [(doc, norm(r["key"])) for _, r in components[components["class"] != "compound column"].iterrows()
            for doc in r["docs"].split(";") if doc != "CPMP"]
if sorted(expected) != sorted(zip(cq3["doc"], cq3["label"])):
    raise AssertionError("CQ3 differs from pandas")
specific = cq3.groupby("doc")["label"].apply(frozenset)
rows = []
for compound, docs in grid.groupby("compound")["doc"]:
    sets = {d: specific.get(d, frozenset()) for d in docs}
    union = frozenset().union(*sets.values())
    for d in sorted(docs):
        rows.append({
            "compound": compound,
            "isa": d,
            "specific": len(sets[d]),
            "shared_in_column": len([x for x in sets[d] if sum(x in s for s in sets.values()) > 1]),
            "only_this_isa": len([x for x in sets[d] if sum(x in s for s in sets.values()) == 1]),
            "same_set_as": ", ".join(o for o in sorted(docs) if o != d and sets[o] == sets[d]),
        })
    _ = union
cq3_table = pd.DataFrame(rows)
print(cq3_table.to_string(index=False))
print()
print(cq3.groupby(["sharing"]).size().to_string())
"""),
    code_cell("""
# The ISA-specific components of the compound columns whose ISAs have the same set.
same = cq3_table[cq3_table["same_set_as"] != ""]
for compound in sorted(same["compound"].unique()):
    first = same[same["compound"] == compound]["isa"].iloc[0]
    print(compound, "-", ", ".join(sorted(same[same["compound"] == compound]["isa"])))
    for label in sorted(specific[first]):
        print("   ", label[:150])
"""),
    markdown_cell("""
## CQ4 Where does a delegation point to a module with no public content?

CQ4: master components and slots that delegate to the disease-state designs.
CQ4b: ISA sentences that refer to the disease-state addendum (Step 2 `refers_to`).
"""),
    code_cell("""
cq4 = run("cq4_delegation_not_public")
cq4["slot_kind"] = cq4["slot_kind"].replace("None", "")
sources = cq4.groupby(["kind", "slot_kind", "label"])["target"].nunique().reset_index()
print(sources.to_string(index=False))

delegating = components[(components["class"] == "master")
                        & components["label"].str.contains(r"as described in the (?:DSA|disease[- ]state addenda)")]
dsa = xref[(xref["doc"] == "CPMP") & (xref["target"] == "DSA") & (xref["delegates"])].copy()
dsa["sentence_n"] = dsa["sentence"].map(norm)
dsa = dsa[~dsa["section_title"].astype(str).str.contains("Abbreviations")]
all_delegating = components[(components["class"] == "master")
                            & components["label"].str.contains(r"(?:will be specified in|as described in) the (?:ISAs|DSA|disease[- ]state addenda)")]
dsa = dsa[~dsa["sentence_n"].map(lambda s: any(k in s for k in all_delegating["label"]))]
expected_slots = set(dsa["sentence_n"])
got_slots = set(sources.loc[sources["kind"] == "slot", "label"])
got_comps = set(sources.loc[sources["kind"] == "master component", "label"])
if got_slots != expected_slots or got_comps != set(delegating["label"]):
    raise AssertionError("CQ4 differs from pandas")
if (sources["target"] != 3).any():
    raise AssertionError("a delegation does not reach all three disease-state designs")
n_content = int((sources["slot_kind"] == "content").sum())
print(f"CQ4: {len(got_comps)} master components and {len(got_slots)} slots delegate to the 3 disease-state designs; "
      f"{n_content} slots name content, {len(got_slots) - n_content} are role statements")

cq4b = run("cq4b_isa_depends_on_dsa")
refers = xref[(xref["doc"] != "CPMP") & (xref["target"] == "DSA") & (xref["relation"] == "refers_to")]
if len(cq4b) != len(refers):
    raise AssertionError(f"CQ4b {len(cq4b)} rows, pandas {len(refers)}")
cq4b["doc"] = cq4b["isa"].str.replace("cpmp:ISA_", "", regex=False)
if cq4b.groupby("doc").size().to_dict() != refers.groupby("doc").size().to_dict():
    raise AssertionError("CQ4b per ISA differs from pandas")
print(f"CQ4b: {len(cq4b)} ISA sentences refer to a disease-state addendum")
print(cq4b.groupby("section").size().sort_values(ascending=False).head(10).to_string())
"""),
    markdown_cell("""
## Schedule (SoA cells)

One component per SoA cell (activity key × visit) from the CPMP SoA join (`cpmp-soa-join/output/layered_grid.csv`),
with the join's activity crosswalk. The statements (delegation, override, addition) come from
`sources/soa_statements.csv` (`scripts/05_extract_soa_statements.py`). Master cells overridden in an ISA are
master defaults, outside the master definition.
"""),
    code_cell("""
soa = pd.read_csv(BASE.parent / "cpmp-soa-join" / "output" / "layered_grid.csv")
stm = pd.read_csv(BASE / "sources" / "soa_statements.csv").fillna("")
isa_of_nct = dict(zip(soa["nct_id"], soa["isa"]))
master_cells = set(map(tuple, soa.loc[soa["master_mark"], ["activity_key", "visit"]].drop_duplicates().values))
ovr = stm[stm["statement_kind"] == "override_ed"].copy()
ovr["isa"] = ovr["nct_id"].map(isa_of_nct)
ovr["target_kind"] = ovr["activity_key"].map(lambda a: "master default" if (a, "ED") in master_cells else "disease state (not public)")
defaults = sorted({a for a, k in zip(ovr["activity_key"], ovr["target_kind"]) if k == "master default"})
n_sched_slots = len(stm[stm["statement_kind"].str.startswith("delegation")].drop_duplicates(["statement_kind", "activity_key", "text"]))
print(len(master_cells), "master cells;", len(defaults), "defaults:", defaults, ";", n_sched_slots, "schedule slots")
"""),
    markdown_cell("""
### CQ5 What schedule does a new ISA inherit?
"""),
    code_cell("""
cq5 = run("cq5_new_isa_schedule")
cq5_counts = cq5.groupby(["isa", "how"]).size().unstack(fill_value=0)
print(cq5_counts.to_string())
expected5 = {"master cell": len(master_cells) - len(defaults), "master slot": n_sched_slots,
             "default assumed, no document": len(defaults)}
for isa, row in cq5_counts.iterrows():
    if row.to_dict() != expected5:
        raise AssertionError(f"{isa}: {row.to_dict()} != {expected5}")
if sorted(cq5_counts.index) != no_compound:
    raise AssertionError("CQ5 ISAs differ from the ISAs with no compound design")
"""),
    markdown_cell("""
### CQ6 Which master SoA cells are overridden, and what does each override point at?
"""),
    code_cell("""
cq6 = run("cq6_overrides")
cq6["isa"] = cq6["isa"].str.replace("cpmp:ISA_", "", regex=False)
got6 = set(zip(cq6["isa"], cq6["activity"], cq6["target_kind"]))
exp6 = set(zip(ovr["isa"], ovr["activity_key"], ovr["target_kind"]))
if got6 != exp6:
    raise AssertionError(f"CQ6 differs: {got6 ^ exp6}")
join6 = pd.read_csv(BASE.parent / "cpmp-soa-join" / "output" / "override_ed_cells.csv")
if set(zip(join6["isa"], join6["activity_key"])) != {(i, a) for i, a, _ in got6}:
    raise AssertionError("CQ6 differs from the join's override_ed_cells.csv")
print(cq6.groupby(["target_kind", "activity"])["isa"].apply(lambda s: ", ".join(sorted(s))).to_string())
print()
print("sentence:", cq6["sentence"].iloc[0])
"""),
    markdown_cell("""
### CQ7 Which SoA cells does each compound design hold?

Rule (agreed, as for the criteria): a cell goes to a compound module when all three ISAs of that compound,
and no ISA of another compound, mark it. Cells marked in ISAs of more than one compound stay in each ISA.
The second table reconciles with the join's `compound_columns.csv`, which counts every cell marked in all
three ISAs of a compound.
"""),
    code_cell("""
cq7 = run("cq7_compound_schedule")
cq7["compound"] = cq7["compound"].str.replace("cpmp:Compound_", "", regex=False)
own_cells = soa[soa["isa_mark"] & (soa["kind"] != "restated")]
docs = own_cells.groupby(["activity_key", "visit"])["isa"].apply(lambda s: sorted(set(s)))
exp7 = {(compound_of[d[0]], a, v) for (a, v), d in docs.items()
        if len(d) == 3 and len({compound_of[x] for x in d}) == 1}
if set(zip(cq7["compound"], cq7["activity"], cq7["visit"])) != exp7:
    raise AssertionError("CQ7 differs from pandas")
marked = soa[soa["isa_mark"]].groupby(["compound", "activity_key", "visit"])["isa"].nunique()
in_all_3 = marked[marked == 3].reset_index()
in_all_3["where"] = [
    "compound module" if (c, a, v) in exp7
    else ("restated master cell" if (a, v) in master_cells else "shared with other compounds (stays in ISAs)")
    for c, a, v in zip(in_all_3["compound"], in_all_3["activity_key"], in_all_3["visit"])]
recon = in_all_3.pivot_table(index="compound", columns="where", values="visit", aggfunc="count", fill_value=0)
recon["total"] = recon.sum(axis=1)
join7 = pd.read_csv(BASE.parent / "cpmp-soa-join" / "output" / "compound_columns.csv").set_index("compound")
recon["join in_all_3"] = join7["in_all_3"]
if (recon["total"] != recon["join in_all_3"]).any():
    raise AssertionError("reconciliation with the join's compound_columns.csv fails")
print(recon.to_string())
cross = docs[docs.map(lambda d: len({compound_of[x] for x in d}) > 1)]
print()
print(len(cross), "cells marked in ISAs of more than one compound;",
      int((cross.map(len) == 12).sum()), "of them in all 12 ISAs")
"""),
    markdown_cell("""
### CQ8 Where do the ISAs schedule what the master delegates?
"""),
    code_cell("""
cq8 = run("cq8_delegated_filled")
cq8["isa"] = cq8["isa"].str.replace("cpmp:ISA_", "", regex=False)
deleg8 = soa[soa["delegated_by_master"] & soa["isa_mark"]]
if set(zip(cq8["activity"], cq8["isa"], cq8["visit"])) != set(zip(deleg8["activity_key"], deleg8["isa"], deleg8["visit"])):
    raise AssertionError("CQ8 differs from the join grid")
view8 = cq8.groupby(["activity", "isa"])["visit"].apply(lambda s: " ".join(sorted(s))).unstack()
print(view8.to_string())
slots8 = sorted(stm.loc[stm["statement_kind"] == "delegation_activity", "activity_key"].unique())
print()
print("delegated with no ISA cell:", sorted(set(slots8) - set(cq8["activity"])))
"""),
    code_cell("""
summary = pd.DataFrame([
    {"question": "reasoner: inferred compound = stated compound", "answer": f"{len(got)} ISAs; no compound: {', '.join(no_compound)}", "check": "pass"},
    {"question": "CQ1a disease-independent by module", "answer": f"{len(cq1a)} components", "check": "pass"},
    {"question": "CQ1b disease-independent by occurrence", "answer": f"{len(cq1b)} components (+{len(only_b)} vs CQ1a)", "check": "pass"},
    {"question": "CQ2 new ISA inherits", "answer": f"{n_master} master components + {len(slot_classes)} slots", "check": "pass"},
    {"question": "CQ3 ISA-specific components", "answer": f"{len(cq3)} rows; same set within column: {len(same)} ISAs", "check": "pass"},
    {"question": "CQ4 delegation to non-public module", "answer": f"{len(got_comps)} components + {len(got_slots)} slots ({n_content} content, {len(got_slots) - n_content} role statements)", "check": "pass"},
    {"question": "CQ4b ISA references to the DSA", "answer": f"{len(cq4b)} sentences", "check": "pass"},
    {"question": "CQ5 new ISA inherits (schedule)", "answer": f"{expected5['master cell']} master cells + {expected5['master slot']} slots + {expected5['default assumed, no document']} defaults", "check": "pass"},
    {"question": "CQ6 overrides", "answer": f"{len(cq6)}: {int((cq6['target_kind'] == 'master default').sum())} master defaults, {int((cq6['target_kind'] != 'master default').sum())} to disease state", "check": "pass"},
    {"question": "CQ7 compound schedule modules", "answer": "; ".join(f"{c} {n}" for c, n in cq7.groupby('compound').size().items()) + f"; {len(cross)} cells cross-compound", "check": "pass"},
    {"question": "CQ8 delegated activities filled by ISAs", "answer": f"{cq8['activity'].nunique()} of {len(slots8)} activities; {len(cq8)} ISA cells", "check": "pass"},
])
summary.to_csv(BASE / "output" / "cq_results.csv", index=False)
print(summary.to_string(index=False))
"""),
]

for i, cell in enumerate(cells):
    cell["id"] = f"cell-{i:02d}"

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

NB.parent.mkdir(exist_ok=True)
with open(NB, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)
print(NB)
