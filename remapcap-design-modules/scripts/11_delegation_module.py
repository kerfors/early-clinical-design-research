"""REMAP-CAP design modules, step 5 part 2: the delegation and default readings as an OWL module.

Inputs: output/step5/delegation_readings.csv, output/step5/delegation_readings_by_state.csv
(scripts/10_delegation_readings.py), output/step3/occurrences.csv.
Outputs: modules/delegations.ttl, output/step5/delegations_index.csv.

Each pairing (one Core 4.1 statement that delegates content to the DSAs or sets an overridable
default, x one DSA) is an individual of rcap:DelegationReading (IAO_0000030). Its annotations:
  readingOf             the DSA design
  coreStatement         the Core 4.1 sentence component(s) of the statement (M-match below)
  allocationKind        "delegation" or "overridable default"
  topic, response, rule, responseSection, secondaryResponse, conditional, role, reviewer,
  coreSentence40, sameText40, note, reviewStatus, evidenceDoc, evidenceSection, evidenceText
  responseStatement     the step 2 sentence component(s) of the DSA evidence (M-match)
A two-intervention default (rows 5, 13) also has one rcap:DelegationReading per illness-severity
state, with state, armCount and refinesReading (the pairing it refines).
M-match: as scripts/09_readings_module.py (whitespace collapsed, line-end hyphens joined; a sentence
component whose text is contained in the sentence).
Review status: map, rules and draft responses approved by Kerstin 2026-10-25.
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
KIND = {"delegation": "delegation", "default": "overridable default"}
PROPS = ["readingOf", "coreStatement", "allocationKind", "topic", "response", "rule", "responseSection",
         "responseStatement", "secondaryResponse", "conditional", "role", "reviewer", "coreSentence40",
         "sameText40", "state", "armCount", "refinesReading", "note", "reviewStatus",
         "evidenceDoc", "evidenceSection", "evidenceText"]
STATUS = "analyst-reading; map, rules and responses approved 2026-10-25"
SUS = {"and", "or", "to"}
HYPHEN = re.compile(r"\b(\w+)- (\w+)")
EVIDENCE = re.compile(r"\[([\d.]+) p\d+\] (.*)")


def norm(t):
    t = re.sub(r"\s+", " ", t).strip()
    return HYPHEN.sub(lambda m: m.group(0) if m.group(2).lower() in SUS else m.group(1) + "-" + m.group(2), t)


def match(doc, section, sentence):
    s1 = norm(sentence)
    cand = occ[(occ.doc == doc) & (occ.section == section) & (occ.unit == "sentence")]
    return sorted({c.component for c in cand.itertuples() if norm(c.text) in s1})


dr = pd.read_csv(STEP5 / "delegation_readings.csv", dtype=str, keep_default_na=False)
ds = pd.read_csv(STEP5 / "delegation_readings_by_state.csv", dtype=str, keep_default_na=False)
occ = pd.read_csv(STEP3 / "occurrences.csv", dtype=str, keep_default_na=False)
assert len(dr) == 21 * len(SHORT), f"expected {21 * len(SHORT)} pairings (21 Core 4.1 statements x DSAs), got {len(dr)}"

g = rdflib.Graph()
g.bind("rcap", R)
g.bind("obo", OBO)
onto = URIRef(NS + "modules/delegations")
g.add((onto, RDF.type, OWL.Ontology))
g.add((onto, OWL.imports, URIRef(NS + "modules/components")))
g.add((R.DelegationReading, RDF.type, OWL.Class))
g.add((R.DelegationReading, RDFS.subClassOf, OBO.IAO_0000030))
g.add((R.DelegationReading, RDFS.label, Literal(
    "delegation reading (analyst reading of a DSA's response to a Core statement that delegates content or sets an overridable default)")))
for p in PROPS:
    g.add((R[p], RDF.type, OWL.AnnotationProperty))

rid_of, rows = {}, []
for r in dr.itertuples():
    rid = R["delegation-" + hashlib.sha1(f"{r.dsa}|{r.core_section}|{r.core_sentence_4_1}".encode()).hexdigest()[:10]]
    assert rid not in rid_of.values(), f"duplicate id {rid}"
    rid_of[(r.row, r.dsa)] = rid
    g.add((rid, RDF.type, OWL.NamedIndividual))
    g.add((rid, RDF.type, R.DelegationReading))
    g.add((rid, R.readingOf, R["DomainDesign_" + SHORT[r.dsa]]))
    core_c = match("CORE41", r.core_section, r.core_sentence_4_1)
    for c in core_c:
        g.add((rid, R.coreStatement, R[c]))
    for p, v in [("allocationKind", KIND[r.kind]), ("topic", r.topic), ("response", r.response), ("rule", r.rule),
                 ("secondaryResponse", r.secondary_response), ("conditional", r.conditional), ("role", r.role),
                 ("reviewer", r.reviewer), ("coreSentence40", r.core_sentence_4_0), ("sameText40", r.same_text_4_0),
                 ("note", r.note)]:
        if v:
            g.add((rid, R[p], Literal(v)))
    for s in r.primary_sections.split(";") if r.primary_sections else []:
        g.add((rid, R.responseSection, Literal(s)))
    g.add((rid, R.reviewStatus, Literal(STATUS)))
    g.add((rid, R.evidenceDoc, Literal(TITLES[r.dsa])))
    resp_c = set()
    for e in r.evidence.split(" || ") if r.evidence else []:
        m = EVIDENCE.fullmatch(e)
        assert m, f"evidence not parsed: {e}"
        g.add((rid, R.evidenceSection, Literal(m.group(1))))
        g.add((rid, R.evidenceText, Literal(m.group(2))))
        resp_c |= set(match(r.dsa, m.group(1), m.group(2)))
    for c in sorted(resp_c):
        g.add((rid, R.responseStatement, R[c]))
    rows.append({"reading": str(rid).replace(NS, "rcap:"), "row": r.row, "dsa": r.dsa, "core_section": r.core_section,
                 "kind": r.kind, "response": r.response, "state": "", "core_components": len(core_c),
                 "response_components": len(resp_c)})

for s in ds.itertuples():
    parent = rid_of[(s.row, s.dsa)]
    sid = URIRef(f"{parent}-{s.state}")
    g.add((sid, RDF.type, OWL.NamedIndividual))
    g.add((sid, RDF.type, R.DelegationReading))
    g.add((sid, R.readingOf, R["DomainDesign_" + SHORT[s.dsa]]))
    g.add((sid, R.refinesReading, parent))
    g.add((sid, R.state, Literal(s.state)))
    g.add((sid, R.armCount, Literal(int(s.n_arms))))
    g.add((sid, R.response, Literal(s.response)))
    g.add((sid, R.rule, Literal(s.rule)))
    g.add((sid, R.reviewStatus, Literal(STATUS)))
    rows.append({"reading": str(sid).replace(NS, "rcap:"), "row": s.row, "dsa": s.dsa, "core_section": s.core_section,
                 "kind": "default", "response": s.response, "state": s.state, "core_components": "",
                 "response_components": ""})

g.serialize(HERE / "modules" / "delegations.ttl", format="turtle")
idx = pd.DataFrame(rows)
idx.to_csv(STEP5 / "delegations_index.csv", index=False)
pair = idx[idx.state == ""]
print(f"pairings: {len(pair)}; per-state readings: {int((idx.state != '').sum())}")
print("Core statement matched:", int((pair.core_components.astype(int) > 0).sum()), "of", len(pair))
print("Core statements not matched to a step 2 sentence component:",
      sorted(pair[pair.core_components.astype(int) == 0].core_section.unique()))
with_ev = dr.evidence != ""
print("pairings with evidence:", int(with_ev.sum()), "; response statement matched:",
      int((pair.response_components.astype(int) > 0).sum()))
