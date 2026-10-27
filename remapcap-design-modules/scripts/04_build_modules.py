"""REMAP-CAP design modules, step 4: OWL modules from the step 3 identity tables.

Inputs (read only): output/step3/occurrences.csv, components_index.csv, core_revisions.csv;
output/step1/sections.csv; imports/upstream_import.ttl; the source PDFs (evidence location).
Outputs: modules/*.ttl, modules/catalog-v001.xml, output/build_log.csv, output/components.csv.

Rules (README, step 4; every application is in output/build_log.csv):
  B-parent     component parent by kind family: inclusion criteria (platform, domain) ->
               OBI_0500027; exclusion criteria (platform, domain, intervention) -> OBI_0500028;
               endpoint -> rcap:EndpointSpecification (IAO_0000033, decision 8); intervention ->
               rcap:InterventionSpecification (IAO_0000007); data collection, PANDA category,
               allocation, applicability, discontinuation -> authored classes under IAO_0000033.
               A sentence (unit = sentence) is a rcap:DesignStatement (IAO_0000033).
               An item whose occurrences span two kind families -> IAO_0000033 directly.
  B-role       the kind of an occurrence (primary / secondary / exploratory endpoint, ...) is an
               annotation on that occurrence's has-part axiom, not on the component (I-move).
  B-core       CoreDesign (version-independent) = clinical study design and has part some C,
               for each Core component in both versions (same, moved) and each revision parent.
               CoreDesign_4_0 / _4_1 = the same over each version's own components; each
               revision is a subclass of its parent. Each Core module has owl:versionIRI.
  B-dsa        each DSA design is asserted subClassOf CoreDesign (the version-independent one),
               annotated binding "unversioned" (no DSA names a Core version); evidence: Core 1.2
               glossary and the DSA's own "The Core Protocol contains all information that is
               generic to the trial" sentence (E-locate). It has part each component of its own
               document, with evidence per occurrence.
  B-domain     Domain_X subClassOf rcap:Domain (OBI_0000750, decision 7) and has part some A for
               each item of DSA 8.3.1 (the arms), glyph annotated. BFO_0000051 because OBI_0001938
               has range value specification and an arm is an action specification.
  B-panda      PANDA design: own components; rcap:appendixTo CoreDesign (annotation, glossary
               evidence); not subClassOf CoreDesign: no document says PANDA inherits Core content.
  B-shared     for each pair S of DSAs, and for S = all DSAs in scope (the shapes R3 and R1 ask
               about; module building only as far as the queries need): the components whose documents are exactly S
               (no Core, no PANDA) define SharedDSA_<S> = design and has part some C. Derived from
               the data; the reasoner places the DSA designs under them.
  B-about      an unconditional inclusion item (not starting "If") naming "influenza", "pneumonia"
               or "respiratory tract infection" is_about some the MONDO term; a qualifier in the
               text that the term does not carry ("community-acquired", "lower") is logged.
  E-locate     an evidence sentence not inside a step 1 section is located by exact text in the
               document's page text (pdftotext); its page is recorded.
"""
import hashlib
import re
import subprocess
from pathlib import Path

import pandas as pd
import rdflib
import rdflib.collection
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, XSD

BASE = Path(__file__).resolve().parents[1]
STEP1 = BASE / "output" / "step1"
STEP3 = BASE / "output" / "step3"
MODULES = BASE / "modules"
OUTPUT = BASE / "output"
SRC = BASE.parent / "usdm-master-protocol" / "sources" / "remapcap"

NS = "https://kerfors.github.io/early-clinical-design-research/remapcap-design-modules/"
R = rdflib.Namespace(NS)
OBO = rdflib.Namespace("http://purl.obolibrary.org/obo/")
DESIGN = OBO.OBI_0500001
INCLUSION, EXCLUSION = OBO.OBI_0500027, OBO.OBI_0500028
DIRECTIVE, ACTION, INDEPENDENT = OBO.IAO_0000033, OBO.IAO_0000007, OBO.OBI_0000750
HAS_PART, IS_ABOUT = OBO.BFO_0000051, OBO.IAO_0000136

from rcap_docs import DOCS as SHARED_DOCS, DSAS, SHORT  # scripts/rcap_docs.py

DOCS = {k: (d.title, d.date_text, d.file) for k, d in SHARED_DOCS.items()}

FAMILY = {"platform_inclusion": "inclusion", "domain_inclusion": "inclusion",
          "platform_exclusion": "exclusion", "domain_exclusion": "exclusion", "intervention_exclusion": "exclusion",
          "endpoint_primary": "endpoint", "endpoint_secondary": "endpoint", "endpoint_exploratory": "endpoint",
          "intervention": "intervention", "data_collection": "data_collection", "discontinuation": "discontinuation",
          "applicability_age": "applicability", "applicability_state": "applicability", "domain_strata": "applicability"}
for k in ["allocation_rar", "allocation_unit_of_analysis", "allocation_reveal", "allocation_interactions",
          "allocation_nesting", "allocation_threshold"]:
    FAMILY[k] = "allocation"
for k in ["category_patient", "category_pathogen", "category_pathogen_stratum", "category_acquisition",
          "category_disease_entity", "category_illness_severity", "category_clinical_feature"]:
    FAMILY[k] = "category"

AUTHORED = {  # class: (parent, label, definition source)
    "EndpointSpecification": (DIRECTIVE, "endpoint specification", "decision 8: no endpoint class in OBI/IAO; as in cpmp-design-modules"),
    "InterventionSpecification": (ACTION, "intervention specification", "decision 7 / README upstream terms"),
    "DataCollectionSpecification": (DIRECTIVE, "data collection specification", "README upstream terms: no data-item term in OBI"),
    "CategorySpecification": (DIRECTIVE, "patient, pathogen or disease category specification", "README upstream terms: no stratification term in OBI"),
    "AllocationSpecification": (DIRECTIVE, "allocation specification", "README upstream terms"),
    "ApplicabilitySpecification": (DIRECTIVE, "domain applicability specification", "README upstream terms"),
    "DiscontinuationSpecification": (DIRECTIVE, "discontinuation specification", "README upstream terms"),
    "DesignStatement": (DIRECTIVE, "design statement (sentence of a protocol document)", "step 2 R-sentence"),
    "Domain": (INDEPENDENT, "REMAP-CAP domain", "decision 7"),
}
FAMILY_PARENT = {"inclusion": INCLUSION, "exclusion": EXCLUSION, "endpoint": R.EndpointSpecification,
                 "intervention": R.InterventionSpecification, "data_collection": R.DataCollectionSpecification,
                 "category": R.CategorySpecification, "allocation": R.AllocationSpecification,
                 "applicability": R.ApplicabilitySpecification, "discontinuation": R.DiscontinuationSpecification}
ANNOTATION_PROPS = ["text", "occursIn", "coreStatus", "revisionOf", "inVersion", "binding", "appendixTo",
                    "evidenceDoc", "evidenceSection", "evidencePosition", "evidencePage", "evidenceText",
                    "occurrenceKind", "evidenceGroup", "evidenceGlyph", "evidenceRule", "upstreamGap",
                    "documentTitle", "documentDate", "note"]
ABOUT_TERMS = [("influenza", OBO.MONDO_0005812), ("pneumonia", OBO.MONDO_0005249),
               ("respiratory tract infection", OBO.MONDO_0024355)]
ABOUT_QUALIFIERS = ["community-acquired", "lower"]

log_rows = []


def log(step, item, rule, detail):
    log_rows.append({"step": step, "item": item, "rule": rule, "detail": detail})


def new_graph():
    g = rdflib.Graph()
    g.bind("rcap", R)
    g.bind("obo", OBO)
    g.bind("owl", OWL)
    g.bind("dcterms", DCTERMS)
    return g


def ontology(g, name, imports, version=None):
    onto = URIRef(NS + "modules/" + name)
    g.add((onto, RDF.type, OWL.Ontology))
    if version:
        g.add((onto, OWL.versionIRI, URIRef(NS + "modules/" + version)))
    for imp in imports:
        g.add((onto, OWL.imports, URIRef(imp) if imp.startswith("http") else URIRef(NS + "modules/" + imp)))
    return onto


def some(g, prop, filler):
    r = BNode()
    g.add((r, RDF.type, OWL.Restriction))
    g.add((r, OWL.onProperty, prop))
    g.add((r, OWL.someValuesFrom, filler))
    return r


def defined(g, cls, members):
    """cls == DESIGN and (has part some m) for each m."""
    parts = [DESIGN] + [some(g, HAS_PART, m) for m in members]
    node = BNode()
    g.add((node, RDF.type, OWL.Class))
    lst = BNode()
    rdflib.collection.Collection(g, lst, parts)
    g.add((node, OWL.intersectionOf, lst))
    g.add((cls, OWL.equivalentClass, node))


def annotate_axiom(g, s, p, o, annotations):
    ax = BNode()
    g.add((ax, RDF.type, OWL.Axiom))
    g.add((ax, OWL.annotatedSource, s))
    g.add((ax, OWL.annotatedProperty, p))
    g.add((ax, OWL.annotatedTarget, o))
    for ap, value in annotations:
        g.add((ax, ap, value))


def page_texts(rel):
    out = subprocess.run(["pdftotext", str(SRC / rel), "-"], capture_output=True, text=True, check=True).stdout
    return [re.sub(r"\s+", " ", p) for p in out.split("\f")]


def locate(doc, sentence):
    """E-locate: page of an exact sentence in the document's page text."""
    pages = [i + 1 for i, t in enumerate(page_texts(DOCS[doc][2])) if sentence in t]
    if len(pages) != 1:
        raise SystemExit(f"E-locate: {doc}: expected one page for {sentence[:60]!r}, found {pages}")
    return pages[0]


def main():
    MODULES.mkdir(exist_ok=True)
    occ = pd.read_csv(STEP3 / "occurrences.csv", dtype=str, keep_default_na=False)
    idx = pd.read_csv(STEP3 / "components_index.csv", dtype=str, keep_default_na=False)
    rev = pd.read_csv(STEP3 / "core_revisions.csv", dtype=str, keep_default_na=False)
    sections = pd.read_csv(STEP1 / "sections.csv", dtype=str, keep_default_na=False)

    # ------------------------------------------------------------ vocabulary (rcap-core.ttl)
    v = new_graph()
    ontology(v, "rcap-core", [NS + "imports/upstream_import"])
    for name, (parent, label, source) in AUTHORED.items():
        v.add((R[name], RDF.type, OWL.Class))
        v.add((R[name], RDFS.subClassOf, parent))
        v.add((R[name], RDFS.label, Literal(label)))
        v.add((R[name], R.note, Literal(source)))
    for p in ANNOTATION_PROPS:
        v.add((R[p], RDF.type, OWL.AnnotationProperty))
    v.serialize(MODULES / "rcap-core.ttl", format="turtle")

    # ------------------------------------------------------------ components (components.ttl)
    fam_of = occ.assign(family=occ.kind.map(FAMILY))
    if fam_of.family.isna().any():
        raise SystemExit(f"kind without family: {sorted(set(fam_of[fam_of.family.isna()].kind))}")
    rev_of_40 = {r.component_40: r for r in rev.itertuples() if r.status == "revised"}
    rev_of_41 = {r.component_41: r for r in rev.itertuples() if r.status == "revised"}
    status_of = {}
    for r in rev.itertuples():
        for c in (r.component_40, r.component_41):
            if c:
                status_of.setdefault(c, set()).add(r.status)

    c = new_graph()
    ontology(c, "components", ["rcap-core"])
    comp_rows = []
    for row in idx.itertuples():
        occs = fam_of[fam_of.component == row.component]
        units = set(occs.unit)
        families = set(occs.family)
        if units == {"sentence"}:
            parent, prule = R.DesignStatement, "B-parent sentence"
        elif len(families) == 1:
            parent, prule = FAMILY_PARENT[families.pop()], "B-parent family"
        else:
            parent, prule = DIRECTIVE, "B-parent families differ"
            log("parent", row.component, prule, f"kinds {row.kinds}: {row.text[:70]}")
        iri = R[row.component]
        c.add((iri, RDF.type, OWL.Class))
        c.add((iri, RDFS.label, Literal(row.text)))
        c.add((iri, R.occursIn, Literal(row.docs)))
        st = ";".join(sorted(status_of.get(row.component, [])))
        if st:
            c.add((iri, R.coreStatus, Literal(st)))
        if row.component in rev_of_40 or row.component in rev_of_41:
            r = rev_of_40.get(row.component) or rev_of_41.get(row.component)
            pv = R[r.parent]
            c.add((iri, RDFS.subClassOf, pv))
            c.add((iri, R.inVersion, Literal("4.0" if row.component in rev_of_40 else "4.1")))
            c.add((iri, R.revisionOf, pv))
        else:
            c.add((iri, RDFS.subClassOf, parent))
        comp_rows.append({"component": row.component, "parent": str(parent).replace(NS, "rcap:").replace(str(OBO), "obo:"),
                          "parent_rule": prule, "core_status": st, "docs": row.docs, "text": row.text})
    for r in rev[rev.status == "revised"].itertuples():
        pv = R[r.parent]
        occs = fam_of[fam_of.component == r.component_40]
        parent = R.DesignStatement if set(occs.unit) == {"sentence"} else FAMILY_PARENT[occs.family.iloc[0]]
        c.add((pv, RDF.type, OWL.Class))
        c.add((pv, RDFS.subClassOf, parent))
        c.add((pv, RDFS.label, Literal(f"Core {r.section} (version-independent): {r.text_41}")))
        c.add((pv, R.note, Literal("I-revision parent: Core 4.0 and 4.1 texts differ; the version-independent "
                                    "component is what an unversioned reference can point at.")))
        log("revision", r.parent, "B-core revision parent", f"{r.section} ratio {r.ratio}")
    c.serialize(MODULES / "components.ttl", format="turtle")
    pd.DataFrame(comp_rows).to_csv(OUTPUT / "components.csv", index=False)

    # B-about on inclusion items
    a = new_graph()
    ontology(a, "about", ["components"])
    incl = occ[(occ.unit == "item") & occ.kind.isin(["platform_inclusion", "domain_inclusion"])]
    for r in incl.drop_duplicates("component").itertuples():
        low = r.text.lower()
        if low.startswith("if "):
            log("about", r.component, "B-about conditional, not asserted", r.text)
            continue
        for word, term in ABOUT_TERMS:
            if word in low:
                a.add((R[r.component], RDFS.subClassOf, some(a, IS_ABOUT, term)))
                gaps = [q for q in ABOUT_QUALIFIERS if q in low]
                if gaps:
                    a.add((R[r.component], R.upstreamGap, Literal(f"not represented by {term.split('/')[-1]}: {', '.join(gaps)}")))
                log("about", r.component, "B-about", f"{word} -> {term.split('/')[-1]}; gap {gaps}: {r.text}")
                break
    a.serialize(MODULES / "about.ttl", format="turtle")

    def has_part_with_evidence(g, design, comp, doc):
        r = some(g, HAS_PART, R[comp])
        g.add((design, RDFS.subClassOf, r))
        for o in occ[(occ.component == comp) & (occ.doc == doc)].itertuples():
            ann = [(R.evidenceDoc, Literal(DOCS[doc][0])), (R.evidenceSection, Literal(o.section)),
                   (R.evidencePosition, Literal(o.position)), (R.evidenceText, Literal(o.text)),
                   (R.occurrenceKind, Literal(o.kind))]
            if o.page:
                ann.append((R.evidencePage, Literal(int(o.page), datatype=XSD.integer)))
            if o.group:
                ann.append((R.evidenceGroup, Literal(o.group)))
            if o.glyph:
                ann.append((R.evidenceGlyph, Literal(o.glyph)))
            annotate_axiom(g, design, RDFS.subClassOf, r, ann)

    def doc_components(doc):
        return list(dict.fromkeys(occ[occ.doc == doc].component))

    def doc_header(g, design, doc, label):
        g.add((design, RDF.type, OWL.Class))
        g.add((design, RDFS.label, Literal(label)))
        g.add((design, R.documentTitle, Literal(DOCS[doc][0])))
        g.add((design, R.documentDate, Literal(DOCS[doc][1])))

    # ------------------------------------------------------------ Core modules
    revised_parents = {r.component_40: R[r.parent] for r in rev[rev.status == "revised"].itertuples()}
    revised_parents.update({r.component_41: R[r.parent] for r in rev[rev.status == "revised"].itertuples()})
    c40, c41 = set(doc_components("CORE40")), set(doc_components("CORE41"))
    stable = sorted(c40 & c41)
    parents = sorted(set(revised_parents.values()))
    g = new_graph()
    ontology(g, "core", ["components"])
    g.add((R.CoreDesign, RDF.type, OWL.Class))
    g.add((R.CoreDesign, RDFS.label, Literal("REMAP-CAP Core design (version-independent)")))
    g.add((R.CoreDesign, R.note, Literal("Components in both Core 4.0 and 4.1 (same or moved) and the version-"
                                         "independent parent of each revised component (B-core).")))
    defined(g, R.CoreDesign, [R[x] for x in stable] + parents)
    g.serialize(MODULES / "core.ttl", format="turtle")
    log("core", "CoreDesign", "B-core", f"{len(stable)} stable components + {len(parents)} revision parents")
    for doc, ver in [("CORE40", "4.0"), ("CORE41", "4.1")]:
        g = new_graph()
        name = f"core-{ver}"
        onto = ontology(g, name, ["core"], version=f"core/{ver}")
        g.add((onto, DCTERMS.isVersionOf, URIRef(NS + "modules/core")))
        design = R[f"CoreDesign_{ver.replace('.', '_')}"]
        doc_header(g, design, doc, f"REMAP-CAP Core design {ver}")
        comps = doc_components(doc)
        defined(g, design, [R[x] for x in comps])
        for comp in comps:
            has_part_with_evidence(g, design, comp, doc)
        g.serialize(MODULES / f"{name}.ttl", format="turtle")
        log("core", str(design).replace(NS, "rcap:"), "B-core", f"{len(comps)} components, versionIRI core/{ver}")

    # glossary evidence (both Core versions)
    gloss = {}
    for doc in ["CORE40", "CORE41"]:
        t = sections[(sections.doc == doc) & (sections.number == "1.2")].text.iloc[0]
        for key, sent in [("DSA", "Domain-Specific Appendix is an appendix to the Core Protocol."),
                          ("PANDA", "The Patient, Pathogen and Disease Appendix (PANDA) is an appendix to the Core Protocol")]:
            if sent not in t:
                raise SystemExit(f"glossary sentence missing in {doc}: {sent}")
            gloss.setdefault(key, []).append((doc, sent))

    # ------------------------------------------------------------ PANDA
    g = new_graph()
    ontology(g, "panda", ["core"])
    design = R.PandaDesign
    doc_header(g, design, "PANDA", "REMAP-CAP PANDA module")
    g.add((design, RDFS.subClassOf, DESIGN))
    for comp in doc_components("PANDA"):
        has_part_with_evidence(g, design, comp, "PANDA")
    g.add((design, R.appendixTo, R.CoreDesign))
    for doc, sent in gloss["PANDA"]:
        annotate_axiom(g, design, R.appendixTo, R.CoreDesign,
                       [(R.evidenceDoc, Literal(DOCS[doc][0])), (R.evidenceSection, Literal("1.2")),
                        (R.evidenceText, Literal(sent)), (R.evidenceRule, Literal("B-panda"))])
    g.serialize(MODULES / "panda.ttl", format="turtle")
    log("panda", "PandaDesign", "B-panda", f"{len(doc_components('PANDA'))} components; appendixTo CoreDesign (annotation)")

    # ------------------------------------------------------------ DSA modules
    generic = "The Core Protocol contains all information that is generic to the trial"
    for doc in DSAS:
        s = SHORT[doc]
        g = new_graph()
        ontology(g, f"dsa-{s}", ["core", "about"])
        design = R[f"DomainDesign_{s}"]
        doc_header(g, design, doc, f"REMAP-CAP {DOCS[doc][0]} design")
        g.add((design, RDFS.subClassOf, R.CoreDesign))
        page = locate(doc, generic)
        ann = [(R.binding, Literal("unversioned")), (R.evidenceRule, Literal("B-dsa")),
               (R.evidenceDoc, Literal(DOCS[doc][0])), (R.evidencePage, Literal(page, datatype=XSD.integer)),
               (R.evidenceText, Literal(generic + " …"))]
        for gdoc, sent in gloss["DSA"]:
            ann.append((R.note, Literal(f"{DOCS[gdoc][0]} 1.2: {sent}")))
        annotate_axiom(g, design, RDFS.subClassOf, R.CoreDesign, ann)
        log("dsa", str(design).replace(NS, "rcap:"), "B-dsa / E-locate", f"generic sentence p.{page}")
        comps = doc_components(doc)
        for comp in comps:
            has_part_with_evidence(g, design, comp, doc)
        dom = R[f"Domain_{s}"]
        g.add((dom, RDF.type, OWL.Class))
        g.add((dom, RDFS.subClassOf, R.Domain))
        g.add((dom, RDFS.label, Literal(f"{DOCS[doc][0].rsplit(' ', 1)[0].replace(' Domain-Specific Appendix', '')} domain")))
        arms = occ[(occ.doc == doc) & (occ.section == "8.3.1") & (occ.unit == "item")]
        if arms.empty:
            raise SystemExit(f"{doc}: no 8.3.1 items")
        for r in arms.itertuples():
            rr = some(g, HAS_PART, R[r.component])
            g.add((dom, RDFS.subClassOf, rr))
            annotate_axiom(g, dom, RDFS.subClassOf, rr, [
                (R.evidenceDoc, Literal(DOCS[doc][0])), (R.evidenceSection, Literal("8.3.1")),
                (R.evidencePage, Literal(int(r.page), datatype=XSD.integer)), (R.evidenceText, Literal(r.text)),
                (R.evidenceGlyph, Literal(r.glyph)), (R.evidenceRule, Literal("B-domain"))])
        g.add((design, RDFS.subClassOf, some(g, HAS_PART, dom)))
        g.serialize(MODULES / f"dsa-{s}.ttl", format="turtle")
        log("dsa", str(dom).replace(NS, "rcap:"), "B-domain", f"{len(arms)} arms: " + " | ".join(arms.text))

    # ------------------------------------------------------------ shared DSA modules (B-shared)
    docs_of = occ.groupby("component").doc.apply(lambda v: tuple(sorted(set(v)))).to_dict()
    groups = {}
    for comp, docs in docs_of.items():
        if len(docs) in (2, len(DSAS)) and set(docs) <= set(DSAS):
            groups.setdefault(docs, []).append(comp)
    g = new_graph()
    ontology(g, "dsa-shared", ["components"])
    shared_rows = []
    for docs, comps in sorted(groups.items(), key=lambda kv: (-len(kv[0]), kv[0])):
        name = "SharedDSA_" + "_".join(SHORT[d] for d in sorted(docs, key=DSAS.index))
        cls = R[name]
        g.add((cls, RDF.type, OWL.Class))
        g.add((cls, RDFS.label, Literal("Shared by " + ", ".join(DOCS[d][0] for d in docs) + " (no Core, no PANDA)")))
        g.add((cls, R.note, Literal("B-shared: derived from the documents' shared components; no document states this grouping.")))
        defined(g, cls, [R[x] for x in sorted(comps)])
        shared_rows.append({"class": name, "docs": ";".join(docs), "n_components": len(comps)})
        log("shared", name, "B-shared", f"{len(comps)} components")
    g.serialize(MODULES / "dsa-shared.ttl", format="turtle")
    pd.DataFrame(shared_rows).to_csv(OUTPUT / "shared_modules.csv", index=False)

    # ------------------------------------------------------------ all + catalog
    # readings.ttl is written by scripts/09_readings_module.py (run after this script, before 05)
    # delegations.ttl is written by scripts/11_delegation_module.py (run after this script, before 05)
    names = ["rcap-core", "components", "about", "core", "core-4.0", "core-4.1", "panda", "dsa-shared"] + [f"dsa-{SHORT[d]}" for d in DSAS] + ["readings", "delegations"]
    g = new_graph()
    ontology(g, "rcap-all", names)
    g.serialize(MODULES / "rcap-all.ttl", format="turtle")
    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
             '<catalog prefer="public" xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">',
             f'  <uri name="{NS}imports/upstream_import" uri="../imports/upstream_import.ttl"/>']
    lines += [f'  <uri name="{NS}modules/{n}" uri="{n}.ttl"/>' for n in names]
    lines.append("</catalog>")
    (MODULES / "catalog-v001.xml").write_text("\n".join(lines) + "\n")

    log("scope", "Biological Sampling Appendix", "decision 9",
        "named in Core 4.0/4.1 2.2 and 2.2.6; no statement delegates content to it; no module")
    pd.DataFrame(log_rows).to_csv(OUTPUT / "build_log.csv", index=False)
    print(f"modules: {len(names)}; components: {len(idx)}; revision parents: {len(parents)}; "
          f"stable Core components: {len(stable)}; shared DSA classes: {len(shared_rows)}")
    print(pd.DataFrame(shared_rows).to_string(index=False))


if __name__ == "__main__":
    main()
