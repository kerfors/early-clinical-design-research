"""Generate notebooks/01_cq_check.ipynb (built with the json module).

The notebook runs each competency query (queries/*.rq) over output/inferred.ttl and checks the
answer against pandas computed from the step 3 identity tables. A mismatch stops the notebook.
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
NB = BASE / "notebooks" / "01_cq_check.ipynb"


def lines(text):
    text = text.strip("\n") + "\n"
    return text.splitlines(keepends=True)


def markdown_cell(text):
    return {"cell_type": "markdown", "metadata": {}, "source": lines(text)}


def code_cell(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines(text)}


cells = [
    markdown_cell("""
# REMAP-CAP design modules: competency questions (identity only)

Each competency question is a SPARQL query in `queries/`, run over `output/inferred.ttl` (the modules
merged and classified with ELK, `scripts/05_reason.py`). Each answer is checked against pandas computed
from the step 3 identity tables. A mismatch stops the notebook.

Scope: Core 4.0 and 4.1, PANDA 1, and the nine PANDA-era DSAs (`scripts/rcap_docs.py`): Corticosteroid (CS),
Antibiotic (AB), Tropical Antibiotic (TAB), Influenza Antiviral (IAV), Macrolide Duration (MD), COVID-19
Immunoglobulin (IG), Mechanical Ventilation (MV), Endothelial Modulation (END), Influenza Immune Modulation (IIM).
Identity is exact text (whitespace collapsed) with Kerstin's crosswalk decisions applied
(`sources/crosswalk_decisions.csv`). The last section compares
exact identity, the decisions, and an upper bound with every review pair merged.

R4 and R5 use the delegation and default readings (step 5 part 2). R2 uses the readings of both parts.
"""),
    code_cell("""
import re
import sys
from pathlib import Path

import pandas as pd
import rdflib

BASE = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
NS = "https://kerfors.github.io/early-clinical-design-research/remapcap-design-modules/"
sys.path.insert(0, str(BASE / "scripts"))
from rcap_docs import DSAS, SHORT  # scripts/rcap_docs.py
NOT_DSA = ["CORE40", "CORE41", "PANDA"]

graph = rdflib.Graph()
graph.parse(BASE / "output" / "inferred.ttl")
occ = pd.read_csv(BASE / "output" / "step3" / "occurrences.csv", dtype=str, keep_default_na=False)
rev = pd.read_csv(BASE / "output" / "step3" / "core_revisions.csv", dtype=str, keep_default_na=False)
sections = pd.read_csv(BASE / "output" / "step1" / "sections.csv", dtype=str, keep_default_na=False)
docs_of = occ.groupby("component").doc.apply(lambda v: frozenset(v))
text_of = occ.drop_duplicates("component").set_index("component").text


def short(value):
    return str(value).replace(NS, "rcap:")


def run(name):
    query = (BASE / "queries" / name).read_text()
    rows = [[short(x) if x is not None else "" for x in r] for r in graph.query(query)]
    return rows


# the DSA lists in the queries (VALUES, R1 count) equal DSAS
dsa_iris = {"rcap:DomainDesign_" + SHORT[d] for d in DSAS}
for name in ["r1_common_to_all_dsas.rq", "r2e_per_dsa.rq", "r3_dsa_pairs.rq"]:
    text = (BASE / "queries" / name).read_text()
    blocks = re.findall(r"VALUES \\?(?:d|dsa|a|b) \\{([^}]*)\\}", text)
    assert blocks and all(set(b.split()) == dsa_iris for b in blocks), name
assert re.search(r"COUNT\\(DISTINCT \\?d\\) = (\\d+)", (BASE / "queries" / "r1_common_to_all_dsas.rq").read_text()).group(1) == str(len(DSAS))
print(len(graph), "triples;", len(DSAS), "DSAs")
"""),
    markdown_cell("""
## Classification

Expected from the build rules: both Core versions are inferred under the version-independent
`CoreDesign`; each DSA design is asserted under `CoreDesign` (unversioned binding) and is **not**
inferred under either Core version.
"""),
    code_cell("""
hier = pd.read_csv(BASE / "output" / "design_hierarchy.csv")
core_versions = hier[hier.design.isin(["rcap:CoreDesign_4_0", "rcap:CoreDesign_4_1"])]
assert set(core_versions.superclass) == {"rcap:CoreDesign"} and set(core_versions.status) == {"inferred"}
dsa_rows = hier[hier.design.str.startswith("rcap:DomainDesign_")]
assert not dsa_rows.superclass.isin(["rcap:CoreDesign_4_0", "rcap:CoreDesign_4_1"]).any()
assert set(dsa_rows[dsa_rows.superclass == "rcap:CoreDesign"].status) == {"asserted"}
hier
"""),
    markdown_cell("""
## R1: components in all DSAs in scope and in no Core version and no PANDA

The query works on the modules, whose Core components cover only the Core sections mapped to component
kinds. The second check compares each answer with the full text of every Core 4.0, Core 4.1 and PANDA
section, so a hit is not an artefact of the section mapping.
"""),
    code_cell("""
r1 = pd.DataFrame(run("r1_common_to_all_dsas.rq"), columns=["component", "text"])
expected = sorted("rcap:" + c for c, d in docs_of.items() if d == frozenset(DSAS))
assert sorted(r1.component) == expected, (sorted(r1.component), expected)

full = sections[sections.doc.isin(NOT_DSA)].text
wordings = occ.groupby("component").text.apply(set)
r1["in_full_core_or_panda_text"] = r1.component.map(
    lambda c: any(full.str.contains(re.escape(t)).any() for t in wordings[c[5:]]))
r1["n_wordings"] = r1.component.map(lambda c: len(wordings[c[5:]]))
assert not r1.in_full_core_or_panda_text.any()
r1["kinds"] = r1.component.map(lambda c: ";".join(sorted(set(occ[occ.component == c[5:]].kind))))
r1
"""),
    markdown_cell("""
## R3: DSA pairs sharing components beyond Core and PANDA

Shared = both DSAs have part of it, and no Core version and no PANDA has part of it.
"""),
    code_cell("""
r3 = pd.DataFrame(run("r3_dsa_pairs.rq"), columns=["a", "b", "shared"])
r3["shared"] = r3.shared.astype(int)
rows = []
for i, a in enumerate(DSAS):
    for b in DSAS[i + 1:]:
        n = sum(1 for d in docs_of if {a, b} <= d and not (d & set(NOT_DSA)))
        pair = sorted(["rcap:DomainDesign_" + SHORT[a], "rcap:DomainDesign_" + SHORT[b]])
        rows.append({"a": pair[0], "b": pair[1], "expected": n})
check = r3.merge(pd.DataFrame(rows), on=["a", "b"], how="outer")
assert (check.shared == check.expected).all(), check
check.sort_values("shared", ascending=False)
"""),
    markdown_cell("""
## R6 (module level): what a DSA inherits from a Core that changed

A DSA design is a subclass of the version-independent `CoreDesign`. For a Core component whose text
differs between 4.0 and 4.1, `CoreDesign` has part only the version-independent parent: every DSA
inherits the component, and neither version's content (R6a).
R6b lists Core components that differ between the versions without a text change (moved: same text,
other section and kind) and components in one version only; `CoreDesign` does not have part of those.
"""),
    code_cell("""
r6a = pd.DataFrame(run("r6a_inherited_revised.rq"), columns=["dsa", "parent", "text_40", "text_41"])
revised = rev[rev.status == "revised"]
assert len(r6a) == len(revised) * len(DSAS)
assert set(r6a.text_40) == set(revised.text_40) and set(r6a.text_41) == set(revised.text_41)
r6a.drop_duplicates("parent")[["parent", "text_40", "text_41"]]
"""),
    code_cell("""
r6b = pd.DataFrame(run("r6b_core_role_or_version_only.rq"),
                   columns=["component", "status", "kinds_40", "kinds_41", "sections_40", "sections_41"])
exp = rev[rev.status.isin(["moved", "only_40", "only_41"])]
assert r6b.status.value_counts().to_dict() == exp.status.value_counts().to_dict()
moved = r6b[r6b.status == "moved"]
assert (moved.kinds_40 != moved.kinds_41).all()
print(r6b.status.value_counts().to_dict())
moved.assign(text=moved.component.map(lambda c: text_of[c[5:]][:90]))
"""),
    markdown_cell("""
## R6 (statement level) and R7: readings

From `modules/readings.ttl` (`scripts/09_readings_module.py`): one `InheritanceReading` per DSA statement that
takes content from the Core Protocol or core protocol documents, resolved by `sources/topic_rules.csv`
(rules agreed 2026-10-24, title rules accepted 2026-10-25). V-current: an unversioned statement resolves to
Core 4.1. V-transition: Core 4.1 7.6.2 ("DSAs dated before this Core Protocol amendment will additionally
report the pre-specified endpoints ... previous versions of the Core Protocol"), so a DSA dated before Core
4.1 whose statement resolves to 7.6.1 or 7.6.2 resolves to 4.1 and, additionally, 4.0. All analyst readings.
"""),
    code_cell("""
r6s = pd.DataFrame(run("r6s_statements_on_changed_core.rq"), columns=["dsa", "section", "target", "change", "versions"])
sv = pd.read_csv(BASE / "output" / "step5" / "statement_versions.csv", dtype=str, keep_default_na=False)
assert len(r6s) == len(sv)
exp = sv.assign(dsa="rcap:DomainDesign_" + sv.doc.map(SHORT)).groupby("dsa").size()
assert r6s.groupby("dsa").size().to_dict() == exp.to_dict()
r6s.groupby("dsa").size().rename("statements on Core sections changed in 4.1")
"""),
    code_cell("""
r7 = pd.DataFrame(run("r7_two_core_versions.rq"), columns=["dsa", "versions", "n"])
r7["n"] = r7.n.astype(int)
exp = sv.assign(dsa="rcap:DomainDesign_" + sv.doc.map(SHORT)).groupby(["dsa", "resolves_to_core_versions"]).size()
assert {(r.dsa, r.versions): r.n for r in r7.itertuples()} == exp.to_dict()
r7.pivot(index="dsa", columns="versions", values="n").fillna(0).astype(int)
"""),
    markdown_cell("""
## R4 and R5: delegations and defaults

From `modules/delegations.ttl` (`scripts/11_delegation_module.py`): one `DelegationReading` per Core 4.1
statement that delegates content to the DSAs (15) or sets an overridable default (6), x each DSA, read by
`sources/template_map.csv` and `sources/response_rules.csv` (`scripts/10_delegation_readings.py`).
The two-intervention defaults (no RAR, the RAR cap) also have one reading per illness-severity state.
Map, rules and responses approved by Kerstin 2026-10-25; all analyst readings. Statistical rows are for a
trial-design reviewer.
"""),
    code_cell("""
dr = pd.read_csv(BASE / "output" / "step5" / "delegation_readings.csv", dtype=str, keep_default_na=False)
ds = pd.read_csv(BASE / "output" / "step5" / "delegation_readings_by_state.csv", dtype=str, keep_default_na=False)
r4 = pd.DataFrame(run("r4_unanswered_delegations.rq"), columns=["dsa", "topic", "response", "secondary"])
exp = dr[(dr.kind == "delegation") & (dr.role == "paired")
         & (dr.response.isin(["no_answer", "condition_not_stated", "defers_back"]) | (dr.secondary_response == "defers_back"))]
exp_set = {("rcap:DomainDesign_" + SHORT[r.dsa], r.topic, r.response, r.secondary_response) for r in exp.itertuples()}
assert set(map(tuple, r4.values.tolist())) == exp_set and len(r4) == len(exp)
r4
"""),
    code_cell("""
r5 = pd.DataFrame(run("r5_defaults.rq"), columns=["dsa", "topic", "response", "state", "state_response", "arms"])
pair = dr[dr.kind == "default"]
exp_pair = {("rcap:DomainDesign_" + SHORT[r.dsa], r.topic, r.response) for r in pair.itertuples()}
assert set(r5[["dsa", "topic", "response"]].itertuples(index=False, name=None)) == exp_pair
st = r5[r5.state != ""]
exp_state = {("rcap:DomainDesign_" + SHORT[r.dsa], r.topic, r.state, r.response, r.n_arms) for r in ds.itertuples()}
assert set(st[["dsa", "topic", "state", "state_response", "arms"]].itertuples(index=False, name=None)) == exp_state
assert len(st) == len(ds)
display(r5[r5.state == ""].pivot(index="topic", columns="dsa", values="response"))
st
"""),
    markdown_cell("""
## R2: what a DSA inherits before it states anything, against Tropical Antibiotic 1

- R2a: the components of Core 4.1 (V-current) and PANDA 1.0, per occurrence kind.
- R2b: the Core 4.1 overridable defaults (hold while the DSA is silent) and delegations (slots to fill).
- R2c: TAB 1 per kind: `points_at` = inherited components in the sections TAB's inheritance statements
  resolve to (part 1); `restates` = TAB components that Core 4.1 or PANDA also state; `states_own_*` = TAB
  components no Core 4.1 or PANDA text states, shared with another DSA or TAB only.
- R2d: TAB's answers to the slots and defaults (part 2), and its pointers to sections without components.
- R2e: the same counts for all DSAs in scope: components, restatements, inherited components reached and not
  reached by the DSA's inheritance statements, silent defaults.
"""),
    code_cell("""
r2a = pd.DataFrame(run("r2a_inherited_by_kind.rq"), columns=["kind", "n"])
r2a["n"] = r2a.n.astype(int)
up = occ[occ.doc.isin(["CORE41", "PANDA"])]
exp = up.drop_duplicates(["component", "kind"]).groupby("kind").size()
assert r2a.set_index("kind").n.to_dict() == exp.to_dict()
r2b = pd.DataFrame(run("r2b_slots_and_defaults.rq"), columns=["allocation_kind", "role", "topic", "conditional"])
exp = dr.assign(allocation_kind=dr.kind.map({"delegation": "delegation", "default": "overridable default"})) \\
    .drop_duplicates(["allocation_kind", "role", "topic", "conditional"])
assert len(r2b) == len(exp) == 21
assert set(r2b.itertuples(index=False, name=None)) == \\
    set(exp[["allocation_kind", "role", "topic", "conditional"]].itertuples(index=False, name=None))
print(up.component.nunique(), "inherited components,", r2a.n.sum(), "component-kind pairs")
r2b.groupby(["allocation_kind", "role"]).size().rename("Core 4.1 statements")
"""),
    code_cell("""
r2c = pd.DataFrame(run("r2c_tab_by_kind.rq"), columns=["kind", "how", "n"])
r2c["n"] = r2c.n.astype(int)
up_c = set(up.component)
other_c = set(occ[occ.doc.isin(["CS_DSA", "AB_DSA", "IAV_DSA"])].component)
tab = occ[occ.doc == "TAB_DSA"].drop_duplicates(["component", "kind"])
tab = tab.assign(how=["restates" if c in up_c else "states_own_shared" if c in other_c else "states_own_TAB_only"
                      for c in tab.component])
ri = pd.read_csv(BASE / "output" / "step5" / "readings_index.csv", dtype=str, keep_default_na=False)
dep = set()
for r in ri[(ri.doc == "TAB_DSA") & (ri.resolution != "")].itertuples():
    for t in r.resolution.split(";"):
        layer, num = t.split(" ")
        docs = ["PANDA"] if layer == "PANDA" else (["CORE41", "CORE40"] if "4.0" in r.core_versions else ["CORE41"])
        dep |= set(occ[occ.doc.isin(docs) & (occ.section == num)].component)
pts = up[up.component.isin(dep)].drop_duplicates(["component", "kind"]).assign(how="points_at")
exp = pd.concat([tab, pts]).groupby(["kind", "how"]).size()
assert {(r.kind, r.how): r.n for r in r2c.itertuples()} == exp.to_dict()
table = r2c.pivot(index="kind", columns="how", values="n").join(r2a.set_index("kind").n.rename("inherited"), how="outer")
for col in ["points_at", "restates", "states_own_shared", "states_own_TAB_only"]:
    if col not in table:
        table[col] = 0
table = table[["inherited", "points_at", "restates", "states_own_shared", "states_own_TAB_only"]].fillna(0).astype(int)
display(table.sum().rename("total"))
table
"""),
    code_cell("""
tabr = dr[(dr.dsa == "TAB_DSA") & (dr.role == "paired")]
display(pd.crosstab([tabr.kind, tabr.topic], tabr.response))
ri[(ri.doc == "TAB_DSA") & (ri.depends_on_components.astype(int) == 0)][["section", "resolution", "review_status"]]
"""),
    code_cell("""
r2e = pd.DataFrame(run("r2e_per_dsa.rq"), columns=["dsa", "measure", "n"])
r2e["n"] = r2e.n.astype(int)
r2e = r2e.pivot(index="dsa", columns="measure", values="n") \\
    .reindex(columns=["components", "restates", "reached", "unreached", "silent_defaults"]).fillna(0).astype(int)
rows = {}
for d in DSAS:
    own = set(occ[occ.doc == d].component)
    dep = set()
    for r in ri[(ri.doc == d) & (ri.resolution != "")].itertuples():
        for t in r.resolution.split(";"):
            layer, num = t.split(" ")
            docs = ["PANDA"] if layer == "PANDA" else (["CORE41", "CORE40"] if "4.0" in r.core_versions else ["CORE41"])
            dep |= set(occ[occ.doc.isin(docs) & (occ.section == num)].component)
    silent = dr[(dr.dsa == d) & (dr.kind == "default") & (dr.role == "paired") & (dr.response == "silent")]
    rows["rcap:DomainDesign_" + SHORT[d]] = {"components": len(own), "restates": len(own & up_c), "reached": len(up_c & dep),
                                             "unreached": len(up_c - dep), "silent_defaults": len(silent)}
exp = pd.DataFrame(rows).T[["components", "restates", "reached", "unreached", "silent_defaults"]]
assert r2e[exp.columns].sort_index().equals(exp.sort_index().astype(int))
assert (r2e.reached + r2e.unreached == len(up_c)).all()
r2e[exp.columns]
"""),
    markdown_cell("""
## Crosswalk: exact identity, decisions, upper bound

`exact`: identity by exact text only. `decided`: Kerstin's decisions applied (the modules above).
`all_pairs_merged`: every review pair merged, an upper bound only (many pairs differ in substance).
"""),
    code_cell("""
cw = pd.read_csv(BASE / "output" / "step3" / "crosswalk_review.csv", dtype=str, keep_default_na=False)
dec = pd.read_csv(BASE / "sources" / "crosswalk_decisions.csv", dtype=str, keep_default_na=False)
assert (dec.decision != "").all()
exact_docs = occ.groupby("component_exact").doc.apply(lambda v: frozenset(v))
parent = {}


def find(k):
    parent.setdefault(k, k)
    while parent[k] != k:
        parent[k] = parent[parent[k]]
        k = parent[k]
    return k


for r in cw.itertuples():
    parent[find(r.component_b)] = find(r.component_a)
merged_docs = {}
for c, d in exact_docs.items():
    merged_docs.setdefault(find(c), set()).update(d)
variants = {"exact": [set(d) for d in exact_docs.tolist()], "decided": [set(d) for d in docs_of.tolist()],
            "all_pairs_merged": list(merged_docs.values())}


def shared(sets, a, b):
    return sum(1 for d in sets if {a, b} <= d and not (d & set(NOT_DSA)))


rows = [{"question": "R1 all DSAs in scope", **{k: sum(1 for d in v if d == set(DSAS)) for k, v in variants.items()}}]
for i, a in enumerate(DSAS):
    for b in DSAS[i + 1:]:
        rows.append({"question": "R3 " + SHORT[a] + "-" + SHORT[b], **{k: shared(v, a, b) for k, v in variants.items()}})
table = pd.DataFrame(rows)
assert table.loc[0, "decided"] == len(r1)
table
"""),
]

for i, cell in enumerate(cells):
    cell["id"] = f"cell-{i:02d}"
nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}
NB.parent.mkdir(exist_ok=True)
with open(NB, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print("wrote", NB)
