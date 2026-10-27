"""REMAP-CAP design modules, step 5: the inheritance readings as an OWL module.

Inputs: output/step5/inheritance_readings.csv, output/step5/statement_versions.csv,
output/step3/occurrences.csv, sources/topic_rules.csv.
Outputs: modules/readings.ttl, output/step5/readings_index.csv.

Each reading (one DSA statement that takes content from the Core Protocol, core protocol documents,
PANDA or the Statistical Analysis Appendix) is an individual of rcap:InheritanceReading
(IAO_0000030, information content entity). Its annotations:
  readingOf             the DSA design
  statement             the step 2 sentence component(s) of that statement (M-match below)
  resolvesToSection     target section(s), or none (unresolved, version_scoped, out of scope)
  dependsOn             the components occurring in the target section in each Core version the
                        statement resolves to (only for sections mapped to component kinds)
  targetPhrase, binding, resolvesToCoreVersions, sectionChangedIn41, rule, ruleSource,
  reviewStatus, evidenceDoc, evidenceSection, evidenceText
M-match: a step 2 sentence component of the same document and section whose text is contained in
the step 1 sentence (both with whitespace collapsed and line-end hyphens joined) is the statement.
Review status (Kerstin, 2026-10-24 and 2026-10-25):
  agreed rules 1-11 -> "rule agreed 2026-10-24"; title rules 12-14 -> "rule accepted 2026-10-25";
  unresolved -> "left unresolved 2026-10-25"; V-current and V-transition -> "accepted 2026-10-25".
"""
import hashlib
import re
from pathlib import Path

import pandas as pd
import rdflib
from rdflib import Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

HERE = Path(__file__).resolve().parent.parent
STEP3 = HERE / "output" / "step3"
STEP5 = HERE / "output" / "step5"
NS = "https://kerfors.github.io/early-clinical-design-research/remapcap-design-modules/"
R = rdflib.Namespace(NS)
OBO = rdflib.Namespace("http://purl.obolibrary.org/obo/")
from rcap_docs import SHORT, TITLES  # scripts/rcap_docs.py
PROPS = ["readingOf", "statement", "resolvesToSection", "dependsOn", "targetPhrase", "binding",
         "resolvesToCoreVersions", "sectionChangedIn41", "rule", "ruleSource", "reviewStatus",
         "evidenceDoc", "evidenceSection", "evidenceText", "note"]
SUS = {"and", "or", "to"}
HYPHEN = re.compile(r"\b(\w+)- (\w+)")
TRANSITION_START = "DSAs dated before this Core Protocol amendment will additionally report"


def norm(t):
    t = re.sub(r"\s+", " ", t).strip()
    return HYPHEN.sub(lambda m: m.group(0) if m.group(2).lower() in SUS else m.group(1) + "-" + m.group(2), t)


rd = pd.read_csv(STEP5 / "inheritance_readings.csv", dtype=str, keep_default_na=False)
sv = pd.read_csv(STEP5 / "statement_versions.csv", dtype=str, keep_default_na=False)
occ = pd.read_csv(STEP3 / "occurrences.csv", dtype=str, keep_default_na=False)
rules = pd.read_csv(HERE / "sources" / "topic_rules.csv", dtype=str, keep_default_na=False).set_index("order")
left = pd.read_csv(HERE / "sources" / "left_unresolved.csv", dtype=str, keep_default_na=False)
left_unresolved = {(r.doc, r.section): r.decided for r in left.itertuples()}
unres = rd[rd.rule_source.str.startswith("unresolved")]
assert set(zip(unres.doc, unres.section)) == set(left_unresolved), "unresolved readings differ from sources/left_unresolved.csv"
versions_of = {(r.doc, r.section, r.sentence): (r.resolves_to_core_versions, r.rule) for r in sv.itertuples()}

g = rdflib.Graph()
g.bind("rcap", R)
g.bind("obo", OBO)
onto = URIRef(NS + "modules/readings")
g.add((onto, RDF.type, OWL.Ontology))
g.add((onto, OWL.imports, URIRef(NS + "modules/components")))
g.add((R.InheritanceReading, RDF.type, OWL.Class))
g.add((R.InheritanceReading, RDFS.subClassOf, OBO.IAO_0000030))
g.add((R.InheritanceReading, RDFS.label, Literal("inheritance reading (analyst reading of a DSA statement that takes content from another layer)")))
for p in PROPS:
    g.add((R[p], RDF.type, OWL.AnnotationProperty))

rows = []
for r in rd.itertuples():
    rid = R["reading-" + hashlib.sha1(f"{r.doc}|{r.section}|{r.sentence}".encode()).hexdigest()[:10]]
    g.add((rid, RDF.type, OWL.NamedIndividual))
    g.add((rid, RDF.type, R.InheritanceReading))
    g.add((rid, R.readingOf, R["DomainDesign_" + SHORT[r.doc]]))
    g.add((rid, R.evidenceDoc, Literal(TITLES[r.doc])))
    g.add((rid, R.evidenceSection, Literal(r.section)))
    g.add((rid, R.evidenceText, Literal(r.sentence)))
    g.add((rid, R.targetPhrase, Literal(r.target_phrase)))
    if r.binding:
        g.add((rid, R.binding, Literal(r.binding)))
    # M-match
    s1 = norm(r.sentence)
    cand = occ[(occ.doc == r.doc) & (occ.section == r.section) & (occ.unit == "sentence")]
    matched = sorted({c.component for c in cand.itertuples() if norm(c.text) in s1})
    for c in matched:
        g.add((rid, R.statement, R[c]))
    # resolution and review status
    if r.resolution:
        source = rules.loc[r.rule, "source"]
        status = ("analyst-reading; rule agreed " if source.startswith("agreed") else "analyst-reading; rule accepted ") + \
            re.search(r"\d{4}-\d{2}-\d{2}", source).group(0)
        g.add((rid, R.rule, Literal(f"topic rule {r.rule}")))
        g.add((rid, R.ruleSource, Literal(source)))
        versions, vrule = versions_of.get((r.doc, r.section, r.sentence), ("4.1", "V-current"))
        if r.resolution.startswith("PANDA"):
            versions, vrule = "PANDA 1.0", "single version"
        g.add((rid, R.resolvesToCoreVersions, Literal(versions)))
        g.add((rid, R.note, Literal(f"{vrule}; V-current and V-transition accepted 2026-10-25")))
        dep = set()
        for t in r.resolution.split(";"):
            g.add((rid, R.resolvesToSection, Literal(t)))
            layer, num = t.split(" ")
            docs = ["PANDA"] if layer == "PANDA" else (["CORE41", "CORE40"] if "4.0" in versions else ["CORE41"])
            dep |= set(occ[occ.doc.isin(docs) & (occ.section == num)].component)
        for c in sorted(dep):
            g.add((rid, R.dependsOn, R[c]))
        if r.target_change:
            g.add((rid, R.sectionChangedIn41, Literal(r.target_change)))
    else:
        status = f"left unresolved {left_unresolved[(r.doc, r.section)]}" if r.rule_source.startswith("unresolved") \
            else r.rule_source
        versions, dep = "", set()
        g.add((rid, R.ruleSource, Literal(r.rule_source)))
    g.add((rid, R.reviewStatus, Literal(status)))
    rows.append({"reading": str(rid).replace(NS, "rcap:"), "doc": r.doc, "section": r.section,
                 "resolution": r.resolution, "core_versions": versions, "changed_in_41": r.target_change,
                 "statement_components": len(matched), "depends_on_components": len(dep),
                 "review_status": status, "sentence": r.sentence})

# The transition sentence refers to the Core version that contains it (reading accepted 2026-10-25).
tc = occ[occ.doc.isin(["CORE40", "CORE41"]) & occ.text.str.startswith(TRANSITION_START)].component.unique()
assert len(tc) == 1, f"transition sentence components: {tc}"
g.add((R[tc[0]], R.note, Literal("Refers to the Core version that contains it ('this Core Protocol amendment'): "
                                 "in Core 4.1 it applies to DSAs dated before 29 May 2026. Reading accepted by "
                                 "Kerstin 2026-10-25 (V-transition).")))

g.serialize(HERE / "modules" / "readings.ttl", format="turtle")
idx = pd.DataFrame(rows)
idx.to_csv(STEP5 / "readings_index.csv", index=False)
print(f"readings: {len(idx)}; resolved: {int((idx.resolution != '').sum())}; "
      f"statement matched: {int((idx.statement_components > 0).sum())}; with dependsOn: {int((idx.depends_on_components > 0).sum())}")
print("not matched to a step 2 sentence component:")
print(idx[idx.statement_components == 0][["doc", "section", "sentence"]].to_string(max_colwidth=90))
print(idx.review_status.value_counts().to_string())
