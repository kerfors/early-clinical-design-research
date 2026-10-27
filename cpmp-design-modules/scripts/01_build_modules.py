"""Generate the CPMP design modules from the Step 5 tables.

Inputs (read only):
  ../usdm-master-protocol/output_cpmp/step5/components.csv, criteria.csv,
      objectives_endpoints.csv, grid.csv
  ../usdm-master-protocol/output_cpmp/step2/cross_references.csv
  sources/ctgov/NCT*.json            CT.gov records of the three ISAs with no documents
  imports/upstream_import.ttl         from scripts/00_extract_upstream.py
  ../cpmp-soa-join/output/layered_grid.csv   SoA cells with their join kind (commit 9ee4b8a)
  sources/soa_statements.csv          SoA cross-layer statements, from scripts/05_extract_soa_statements.py
  sources/crosswalk_decisions.csv     Kerstin's crosswalk decisions (pairs of criteria: merge / keep apart)

Outputs:
  modules/*.ttl, modules/catalog-v001.xml, output/build_log.csv, output/components_index.csv,
  output/schedule_index.csv

Rules (agreed 2026-10-25, see README):
  - Components: criteria, objectives, endpoints only; identity = Step 5 key (template text).
    Intervention attributes are not built.
  - Module of a component = Step 5 sharing class: master -> master; compound column ->
    compound module; single ISA, compound column (part), other -> each ISA it occurs in.
  - Crosswalk: only pairs decided "merge" in sources/crosswalk_decisions.csv are merged (one component,
    canonical key = the member key occurring in most documents); the sharing class is recomputed.
  - Master design and compound designs are defined classes (has part some C for each component).
    ISA designs are asserted subclasses of master and of their disease-state design (evidence:
    ISA section 5 sentence) and have part each component of their own document.
    The compound design of an ISA is inferred, not asserted.
  - Disease-state designs: is about the upstream term agreed for the disease; slots from the
    master's delegation sentences; content not public.
  - Schedule (agreed 2026-10-25): one component per SoA cell (activity key x visit), activity
    identity from the SoA join's crosswalk. Master cells -> master module; restated cells stay
    master cells (the ISA's has-part is annotated "restated"); other ISA cells take the same
    sharing rule as the criteria.
  - Master defaults: master cells overridden in at least one ISA ("not needed for ED per the
    CPMP SoA") are left out of the MasterDesign definition. Each ISA without an override has
    part them; an overriding ISA carries an `overrides` annotation with the sentence. ISAs with
    no documents have part them, annotated "default assumed, no document".
  - Overrides on activities the master SoA does not have point at the disease-state design.
  - Master SoA delegations (post-randomization activities, visits after V7) are slots of the
    master design that delegate to the ISA designs.
"""
import csv
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import rdflib
import rdflib.collection
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, XSD

BASE = Path(__file__).resolve().parents[1]
STEP5 = BASE.parent / "usdm-master-protocol" / "output_cpmp" / "step5"
STEP2 = BASE.parent / "usdm-master-protocol" / "output_cpmp" / "step2"
CTGOV = BASE / "sources" / "ctgov"
DECISIONS = BASE / "sources" / "crosswalk_decisions.csv"
SOA_GRID = BASE.parent / "cpmp-soa-join" / "output" / "layered_grid.csv"
SOA_STATEMENTS = BASE / "sources" / "soa_statements.csv"
SOA_SOURCE = "soa2usdm-collections cf9541d (consolidated SoA), via cpmp-soa-join 9ee4b8a"
MASTER_NCT = "NCT05986292"
MODULES = BASE / "modules"
OUTPUT = BASE / "output"

NS = "https://kerfors.github.io/early-clinical-design-research/cpmp-design-modules/"
CPMP = rdflib.Namespace(NS)
OBO = rdflib.Namespace("http://purl.obolibrary.org/obo/")
NCIT_ENDPOINT = URIRef("http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C25212")
NCIT_SOA = URIRef("http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#C132349")
ACTION = OBO.IAO_0000007

CLINICAL_STUDY_DESIGN = OBO.OBI_0500001
ELIGIBILITY_CRITERION = OBO.OBI_0500026
INCLUSION = OBO.OBI_0500027
EXCLUSION = OBO.OBI_0500028
OBJECTIVE = OBO.IAO_0000005
DIRECTIVE = OBO.IAO_0000033
HAS_PART = OBO.BFO_0000051
IS_ABOUT = OBO.IAO_0000136

# Disease state -> upstream term, agreed 2026-10-25 (BioPortal check). Gap text is logged.
DISEASE_TERMS = {
    "OA": (OBO.MONDO_0005178, ""),
    "CLBP": (OBO.HP_0003419, "HP phenotype term 'Low back pain'; MONDO has no chronic low back pain; 'chronic' not represented"),
    "DPNP": (OBO.MONDO_0006626, "MONDO 'diabetic neuropathy' covers peripheral and/or autonomic; 'painful' and 'peripheral' not represented"),
}
DISEASE_DIGIT = {"OA": "1", "CLBP": "2", "DPNP": "3"}

# Delegation phrase in a master component's own text (rule).
DELEGATING = re.compile(r"(will be specified in|as described in) the (ISAs|DSA|disease[- ]state addenda)")

# Slot kind (rule, agreed 2026-10-25): a sentence that describes the DSA's role names no content.
ROLE_STATEMENT = re.compile(r"specific study elements|determines what DSA")

log_rows = []


def log(step, item, rule, detail):
    log_rows.append({"step": step, "item": item, "rule": rule, "detail": detail})


def norm(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def short_hash(*parts):
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]


def new_graph():
    g = rdflib.Graph()
    g.bind("cpmp", CPMP)
    g.bind("obo", OBO)
    g.bind("owl", OWL)
    g.bind("dcterms", DCTERMS)
    return g


def ontology(g, name, imports):
    onto = URIRef(NS + "modules/" + name)
    g.add((onto, RDF.type, OWL.Ontology))
    for imp in imports:
        g.add((onto, OWL.imports, URIRef(NS + "modules/" + imp) if not imp.startswith("http") else URIRef(imp)))
    return onto


def some(g, prop, filler):
    r = BNode()
    g.add((r, RDF.type, OWL.Restriction))
    g.add((r, OWL.onProperty, prop))
    g.add((r, OWL.someValuesFrom, filler))
    return r


def intersection(g, members):
    node = BNode()
    g.add((node, RDF.type, OWL.Class))
    lst = BNode()
    rdflib.collection.Collection(g, lst, members)
    g.add((node, OWL.intersectionOf, lst))
    return node


def annotate_axiom(g, s, p, o, annotations):
    ax = BNode()
    g.add((ax, RDF.type, OWL.Axiom))
    g.add((ax, OWL.annotatedSource, s))
    g.add((ax, OWL.annotatedProperty, p))
    g.add((ax, OWL.annotatedTarget, o))
    for ap, value in annotations:
        g.add((ax, ap, value))


def sharing_class(docs, compound_of):
    """Step 5 sharing class, recomputed to check that the rule is the one Step 5 used."""
    if docs == ["CPMP"]:
        return "master"
    if "CPMP" in docs:
        raise SystemExit(f"component in CPMP and ISAs: {docs}")
    if len(docs) == 1:
        return "single ISA"
    compounds = {compound_of[d] for d in docs}
    if len(compounds) > 1:
        return "other"
    return "compound column" if len(docs) == 3 else "compound column (part)"


def main():
    MODULES.mkdir(exist_ok=True)
    OUTPUT.mkdir(exist_ok=True)

    comps = pd.read_csv(STEP5 / "components.csv")
    crit = pd.read_csv(STEP5 / "criteria.csv")
    oe = pd.read_csv(STEP5 / "objectives_endpoints.csv")
    grid = pd.read_csv(STEP5 / "grid.csv")
    xref = pd.read_csv(STEP2 / "cross_references.csv")

    n_all = len(comps)
    comps = comps[comps["kind"] != "intervention attribute"].copy()
    log("scope", "intervention attribute", "not built (agreed 2026-10-25)", f"{n_all - len(comps)} components left out")

    compound_of = dict(zip(grid["doc"], grid["compound"]))
    disease_of = dict(zip(grid["doc"], grid["disease"]))
    isas = list(grid["doc"])
    compounds = sorted(set(grid["compound"]))

    comps["doc_list"] = comps["docs"].str.split(";")
    recomputed = comps["doc_list"].apply(lambda d: sharing_class(d, compound_of))
    mismatch = comps[recomputed != comps["class"]]
    if len(mismatch):
        raise SystemExit(f"sharing class rule differs from Step 5 for {len(mismatch)} components")
    if comps["key"].duplicated().any():
        raise SystemExit("duplicate component keys")

    # Crosswalk decisions: merge the decided pairs (criteria only).
    dec = pd.read_csv(DECISIONS)
    if not set(dec["decision"]) <= {"merge", "keep apart"}:
        raise SystemExit(f"unknown decision values: {set(dec['decision'])}")
    key_of_number = {(r.doc, int(r.number)): r.template for r in crit.itertuples() if pd.notna(r.number)}

    def member_key(ref):
        doc, num = ref.split()
        return key_of_number[(doc, int(num.strip("[]")))]

    parent = {}

    def find(k):
        parent.setdefault(k, k)
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    merges = dec[dec["decision"] == "merge"]
    for r in merges.itertuples():
        ka, kb = find(member_key(r.a)), find(member_key(r.b))
        if ka != kb:
            parent[kb] = ka
    groups = {}
    for k in list(parent):
        groups.setdefault(find(k), set()).add(k)
    alias = {}
    for members in groups.values():
        rows = comps[comps["key"].isin(members)]
        if len(rows) != len(members):
            raise SystemExit(f"crosswalk member not among components: {members}")
        if rows["kind"].nunique() != 1 or rows["list"].nunique() != 1:
            raise SystemExit(f"crosswalk group mixes kinds or lists: {members}")
        canonical = sorted(members, key=lambda k: (-int(rows.loc[rows["key"] == k, "n_docs"].iloc[0]), k))[0]
        for k in members:
            alias[k] = canonical
        docs = sorted({d for ds in rows["doc_list"] for d in ds})
        log("crosswalk", norm(canonical)[:80], "merged (sources/crosswalk_decisions.csv)",
            f"{len(members)} keys; classes {sorted(set(rows['class']))} -> {sharing_class(docs, compound_of)}; docs {';'.join(docs)}")
    variants = {}
    for k, c in alias.items():
        if k != c:
            variants.setdefault(c, []).append(k)
    merged_rows = []
    for _, row in comps.iterrows():
        canonical = alias.get(row["key"], row["key"])
        if canonical != row["key"]:
            continue
        if canonical in variants:
            members = [canonical] + variants[canonical]
            docs = sorted({d for ds in comps.loc[comps["key"].isin(members), "doc_list"] for d in ds})
            row = row.copy()
            row["doc_list"] = docs
            row["docs"] = ";".join(docs)
            row["n_docs"] = len(docs)
            row["class"] = sharing_class(docs, compound_of)
            row["text_identical"] = False
        merged_rows.append(row)
    comps = pd.DataFrame(merged_rows).reset_index(drop=True)
    for _, r in dec[dec["decision"] == "keep apart"].iterrows():
        log("crosswalk", f"{r['a']} / {r['b']}", "kept apart (sources/crosswalk_decisions.csv)", r["note"])

    def comp_iri(row):
        kind = {"criterion": "crit", "objective": "obj", "endpoint": "ep"}[row["kind"]]
        return CPMP[f"{kind}-{short_hash(row['kind'], row['key'])}"]

    comps["iri"] = comps.apply(comp_iri, axis=1)
    if comps["iri"].duplicated().any():
        raise SystemExit("component IRI collision")

    # Evidence per (component, document): number, page, verbatim text.
    evidence = {}
    for _, r in crit.iterrows():
        evidence.setdefault(("criterion", alias.get(r["template"], r["template"]), r["doc"]), []).append(
            (str(int(r["number"])) if pd.notna(r["number"]) else "", int(r["page"]), norm(r["text"])))
    for _, r in oe.iterrows():
        evidence.setdefault(("objective", r["objective_template"], r["doc"]), []).append(("", int(r["page"]), norm(r["objective"])))
        evidence.setdefault(("endpoint", r["endpoint_template"], r["doc"]), []).append(("", int(r["page"]), norm(r["endpoint"])))

    def evidence_for(row, doc):
        rows = evidence.get((row["kind"], row["key"], doc))
        if not rows:
            raise SystemExit(f"no evidence row for {row['kind']} {doc}: {row['key'][:60]}")
        return sorted(set(rows))

    def parent_of(row):
        if row["kind"] == "criterion":
            return {"inclusion": INCLUSION, "exclusion": EXCLUSION}[row["list"]]
        if row["kind"] == "objective":
            return OBJECTIVE
        return CPMP.EndpointSpecification

    def declare_component(g, row):
        c = row["iri"]
        g.add((c, RDF.type, OWL.Class))
        g.add((c, RDFS.subClassOf, parent_of(row)))
        g.add((c, RDFS.label, Literal(norm(row["key"]))))
        g.add((c, CPMP.sharingClass, Literal(row["class"])))
        g.add((c, CPMP.textIdentical, Literal(bool(row["text_identical"]))))
        g.add((c, CPMP.occursIn, Literal(row["docs"])))
        for v in variants.get(row["key"], []):
            g.add((c, CPMP.variantText, Literal(norm(v))))
        if row["class"] == "other":
            g.add((c, CPMP.note, Literal("Occurs in ISAs of more than one compound column; no document groups it.")))

    def has_part(g, design, row, doc):
        r = some(g, HAS_PART, row["iri"])
        g.add((design, RDFS.subClassOf, r))
        for number, page, text in evidence_for(row, doc):
            annotate_axiom(g, design, RDFS.subClassOf, r, [
                (CPMP.evidenceDoc, Literal(doc)),
                (CPMP.evidenceNumber, Literal(number)),
                (CPMP.evidencePage, Literal(page, datatype=XSD.integer)),
                (CPMP.evidenceText, Literal(text)),
            ])

    # ---------------------------------------------------------------- schedule (SoA join)
    soa = pd.read_csv(SOA_GRID)
    stm = pd.read_csv(SOA_STATEMENTS).fillna("")
    nct_of = dict(soa[["isa", "nct_id"]].drop_duplicates().itertuples(index=False, name=None))
    if sorted(nct_of) != sorted(isas):
        raise SystemExit("SoA join ISAs differ from Step 5 grid")
    for isa_code, nct in nct_of.items():
        if compound_of[isa_code] != soa.loc[soa["isa"] == isa_code, "compound"].iloc[0]:
            raise SystemExit(f"{isa_code}: compound differs between Step 5 grid and SoA join")
    isa_of_nct = {v: k for k, v in nct_of.items()}

    def cell_iri(activity, visit):
        return CPMP[f"sched-{short_hash(activity, visit)}"]

    master_cells = set(map(tuple, soa.loc[soa["master_mark"], ["activity_key", "visit"]].drop_duplicates().values))
    overrides = stm[stm["statement_kind"] == "override_ed"]
    defaults = sorted({(a, "ED") for a in overrides["activity_key"] if (a, "ED") in master_cells})
    override_master = {(isa_of_nct[r.nct_id], (r.activity_key, "ED")): r.text
                       for r in overrides.itertuples() if (r.activity_key, "ED") in master_cells}
    override_beyond = [(isa_of_nct[r.nct_id], r.activity_key, r.text)
                       for r in overrides.itertuples() if (r.activity_key, "ED") not in master_cells]
    check = soa[soa["kind"] == "override_ed"]
    if len(check) != len(override_master) + len(override_beyond):
        raise SystemExit("override statements differ from the join's override_ed cells")
    restated = soa[soa["isa_mark"] & (soa["kind"] == "restated")]
    own_cells = soa[soa["isa_mark"] & (soa["kind"] != "restated")]
    if set(map(tuple, own_cells[["activity_key", "visit"]].values)) & master_cells:
        raise SystemExit("an ISA cell that is not 'restated' is also a master cell")
    sched = (own_cells.groupby(["activity_key", "visit"])["isa"].apply(lambda s: sorted(set(s))).reset_index(name="doc_list"))
    sched["class"] = sched["doc_list"].map(lambda d: sharing_class(d, compound_of))
    sched["docs"] = sched["doc_list"].map(";".join)
    sched["iri"] = [cell_iri(a, v) for a, v in zip(sched["activity_key"], sched["visit"])]
    addition = {(isa_of_nct[r.nct_id], r.activity_key): (r.text, r.names_dsa)
                for r in stm[stm["statement_kind"] == "addition_stated"].itertuples()}
    delegations = stm[stm["statement_kind"].str.startswith("delegation")]
    if set(delegations["nct_id"]) != {MASTER_NCT}:
        raise SystemExit("an SoA delegation statement outside the master")
    log("schedule", "master cells", "master marks (SoA join)", f"{len(master_cells)} cells, {len(defaults)} defaults: {', '.join(a for a, _ in defaults)} at ED")
    log("schedule", "ISA cells", "ISA marks, not restated; sharing rule as for criteria",
        f"{len(sched)} cells: {sched['class'].value_counts().to_dict()}")
    log("schedule", "restated", "ISA marks a master cell: has part annotated 'restated'", f"{len(restated)} ISA x cell")
    log("schedule", "overrides", "'not needed for ED per the CPMP SoA'",
        f"{len(override_master)} on master defaults, {len(override_beyond)} on activities not in the master SoA (-> disease state)")

    def declare_cell(g, activity, visit, parent, extra):
        c = cell_iri(activity, visit)
        g.add((c, RDF.type, OWL.Class))
        g.add((c, RDFS.subClassOf, parent))
        g.add((c, RDFS.label, Literal(f"{activity} @ {visit}")))
        g.add((c, CPMP.activityKey, Literal(activity)))
        g.add((c, CPMP.visit, Literal(visit)))
        for p, o in extra:
            g.add((c, p, o))
        return c

    def has_part_cell(g, design, cell, annotations):
        r = some(g, HAS_PART, cell)
        g.add((design, RDFS.subClassOf, r))
        annotate_axiom(g, design, RDFS.subClassOf, r, annotations)

    # ---------------------------------------------------------------- core
    core = new_graph()
    ontology(core, "cpmp-core", [NS + "imports/upstream_import"])
    for p, label, comment in [
        (CPMP.sharingClass, "sharing class", "Step 5 class: master, compound column, compound column (part), single ISA, other."),
        (CPMP.textIdentical, "text identical", "True when every occurrence has the same wording (Step 5); False when identity rests on the Step 5 template."),
        (CPMP.occursIn, "occurs in", "Documents (Step 5 doc codes) the component occurs in."),
        (CPMP.moduleRole, "module role", "master, disease state, compound, compound x disease state."),
        (CPMP.contentStatus, "content status", "Set to 'not public' on the disease-state modules."),
        (CPMP.delegatesTo, "delegates to", "From a master component or slot to the design classes that are to hold its content. Annotation property: links classes to classes."),
        (CPMP.dependsOn, "depends on", "From an ISA design to the disease-state design its text refers to. Each occurrence is an axiom annotation with the sentence."),
        (CPMP.upstreamGap, "upstream gap", "What the upstream term does not represent."),
        (CPMP.compoundStated, "compound stated", "Compound named in the ISA section 5 sentence (grid.csv), kept to check the inferred compound design."),
        (CPMP.diseaseStated, "disease stated", "Disease-state abbreviation stated in the source."),
        (CPMP.evidenceDoc, "evidence document", ""),
        (CPMP.evidenceNumber, "evidence criterion number", ""),
        (CPMP.evidencePage, "evidence page", ""),
        (CPMP.evidenceSection, "evidence section", ""),
        (CPMP.evidenceText, "evidence text", "Verbatim sentence or criterion text from the document."),
        (CPMP.note, "note", ""),
        (CPMP.activityKey, "activity key", "SoA activity identity (SoA join crosswalk)."),
        (CPMP.visit, "visit", "SoA visit number as printed (V1 ... V803, ED)."),
        (CPMP.masterDefault, "master default", "Master SoA cell overridden in at least one ISA; the master protocol does not call it a default."),
        (CPMP.overrides, "overrides", "From an ISA design to the master default or disease-state design it overrides; axiom annotation carries the sentence."),
        (CPMP.allocation, "allocation", "How the ISA has the cell: own, restated, default, default assumed (no document)."),
        (CPMP.additionStated, "addition stated", "ISA sentence 'in addition to schedule described in ...' for this cell's activity."),
        (CPMP.evidenceSource, "evidence source", "Source of an SoA mark."),
        (CPMP.variantText, "variant text", "Another wording of this component, merged by a crosswalk decision."),
        (CPMP.slotKind, "slot kind", "content: the slot names what the other layer must supply; role statement: the sentence only describes the DSA's role (rule-derived)."),
    ]:
        core.add((p, RDF.type, OWL.AnnotationProperty))
        core.add((p, RDFS.label, Literal(label)))
        if comment:
            core.add((p, RDFS.comment, Literal(comment)))
    core.add((CPMP.EndpointSpecification, RDF.type, OWL.Class))
    core.add((CPMP.EndpointSpecification, RDFS.subClassOf, DIRECTIVE))
    core.add((CPMP.EndpointSpecification, RDFS.label, Literal("endpoint specification")))
    core.add((CPMP.EndpointSpecification, DCTERMS.source, NCIT_ENDPOINT))
    core.add((CPMP.EndpointSpecification, RDFS.comment, Literal("Authored: no endpoint class in OBI or IAO (BioPortal check 2026-10-25). Definition source NCIt C25212 'End Point'.")))
    core.add((CPMP.DelegatedSlot, RDF.type, OWL.Class))
    core.add((CPMP.DelegatedSlot, RDFS.subClassOf, DIRECTIVE))
    core.add((CPMP.DelegatedSlot, RDFS.label, Literal("delegated slot")))
    core.add((CPMP.DelegatedSlot, RDFS.comment, Literal("Content the master protocol states will be provided by another layer; one slot per master delegation sentence.")))
    core.serialize(MODULES / "cpmp-core.ttl", format="turtle")

    # ---------------------------------------------------------------- master
    master = new_graph()
    ontology(master, "master", ["cpmp-core"])
    m_design = CPMP.MasterDesign
    master.add((m_design, RDF.type, OWL.Class))
    master.add((m_design, RDFS.label, Literal("CPMP master protocol design")))
    master.add((m_design, CPMP.moduleRole, Literal("master")))
    m_rows = comps[comps["class"] == "master"]
    for _, row in m_rows.iterrows():
        declare_component(master, row)
    m_cells = []
    for activity, visit in sorted(master_cells):
        is_default = (activity, visit) in defaults
        c = declare_cell(master, activity, visit, ACTION, [
            (CPMP.sharingClass, Literal("master")),
            (CPMP.occursIn, Literal("CPMP")),
            (CPMP.evidenceSource, Literal(f"{SOA_SOURCE}, {MASTER_NCT}")),
        ] + ([(CPMP.masterDefault, Literal(True))] if is_default else []))
        if not is_default:
            m_cells.append(c)
    master.add((m_design, OWL.equivalentClass,
                intersection(master, [CLINICAL_STUDY_DESIGN] + [some(master, HAS_PART, c) for c in m_rows["iri"]]
                             + [some(master, HAS_PART, c) for c in m_cells])))
    for _, row in m_rows.iterrows():
        for number, page, text in evidence_for(row, "CPMP"):
            master.add((row["iri"], CPMP.evidencePage, Literal(page, datatype=XSD.integer)))
            if number:
                master.add((row["iri"], CPMP.evidenceNumber, Literal(number)))
    log("master", "MasterDesign", "defined class over master components", f"{len(m_rows)} components ({m_rows['kind'].value_counts().to_dict()})")

    # Delegating master components (phrase rule).
    disease_designs = {d: CPMP[f"DiseaseState_{d}"] for d in DISEASE_TERMS}
    isa_designs = {d: CPMP[f"ISA_{d}"] for d in isas}
    delegating_keys = []
    for _, row in m_rows.iterrows():
        m = DELEGATING.search(norm(row["key"]))
        if not m:
            continue
        targets = isa_designs.values() if m.group(2) == "ISAs" else disease_designs.values()
        for t in targets:
            master.add((row["iri"], CPMP.delegatesTo, t))
        delegating_keys.append(norm(row["key"]))
        log("delegation", norm(row["key"])[:80], "phrase in master component text", f"delegates to {'ISA' if m.group(2) == 'ISAs' else 'disease-state'} designs")

    # Slots from master -> DSA delegation sentences (Step 2).
    dsa = xref[(xref["doc"] == "CPMP") & (xref["target"] == "DSA") & (xref["delegates"])]
    slots = {}
    for _, r in dsa.iterrows():
        sentence = norm(r["sentence"])
        if "Abbreviations" in str(r["section_title"]):
            log("slot", f"CPMP {r['section']} p{r['page']}", "excluded: abbreviation list (Step 2 false positive)", sentence[:80])
            continue
        covered = [k for k in delegating_keys if k in sentence]
        if covered:
            log("slot", f"CPMP {r['section']} p{r['page']}", "excluded: delegation carried by master component(s)", f"{len(covered)} component(s)")
            continue
        key = sentence
        if key not in slots:
            slots[key] = {"iri": CPMP[f"slot-{short_hash(key)}"], "rows": [], "section": str(r["section"])}
        slots[key]["rows"].append(r)
    for key, s in slots.items():
        iri = s["iri"]
        master.add((iri, RDF.type, OWL.Class))
        master.add((iri, RDFS.subClassOf, CPMP.DelegatedSlot))
        if s["section"].startswith("5"):
            master.add((iri, RDFS.subClassOf, ELIGIBILITY_CRITERION))
        master.add((iri, RDFS.label, Literal(key)))
        slot_kind = "role statement" if ROLE_STATEMENT.search(key) else "content"
        master.add((iri, CPMP.slotKind, Literal(slot_kind)))
        for r in s["rows"]:
            master.add((iri, CPMP.evidenceSection, Literal(f"{r['section']} {r['section_title']}")))
            master.add((iri, CPMP.evidencePage, Literal(int(r["page"]), datatype=XSD.integer)))
        for t in disease_designs.values():
            master.add((iri, CPMP.delegatesTo, t))
        also_isa = re.search(r"\bISAs?\b", key) is not None
        if also_isa:
            for t in isa_designs.values():
                master.add((iri, CPMP.delegatesTo, t))
        log("slot", key[:80], f"master -> DSA delegation sentence ({slot_kind})" + ("; sentence also names the ISA: delegates to ISA designs too" if also_isa else ""),
            "sections " + ", ".join(str(r["section"]) for r in s["rows"]))
    # Master SoA delegations: one slot per delegated activity, one for visits after V7.
    n_sched_slots = 0
    for _, r in delegations.drop_duplicates(["statement_kind", "activity_key", "text"]).iterrows():
        if r["statement_kind"] == "delegation_activity":
            label = f"Post-randomization {r['activity_key']}"
            iri = CPMP[f"slot-sched-{short_hash(r['activity_key'])}"]
        else:
            label = "Visits after V7"
            iri = CPMP[f"slot-sched-{short_hash('visits after V7')}"]
        master.add((iri, RDF.type, OWL.Class))
        master.add((iri, RDFS.subClassOf, CPMP.DelegatedSlot))
        master.add((iri, RDFS.subClassOf, ACTION))
        master.add((iri, RDFS.label, Literal(label)))
        if r["activity_key"]:
            master.add((iri, CPMP.activityKey, Literal(r["activity_key"])))
        master.add((iri, CPMP.evidenceText, Literal(r["text"])))
        master.add((iri, CPMP.evidenceSource, Literal(f"{SOA_SOURCE}, {MASTER_NCT}")))
        master.add((m_design, RDFS.subClassOf, some(master, HAS_PART, iri)))
        for t in isa_designs.values():
            master.add((iri, CPMP.delegatesTo, t))
        n_sched_slots += 1
        log("schedule slot", label, f"master SoA {r['statement_kind']}", r["text"])
    master.serialize(MODULES / "master.ttl", format="turtle")

    # ---------------------------------------------------------------- disease states
    # The master names the disease states in prose, without abbreviations; the sentence is
    # attached as evidence, the label keeps the abbreviation used in grid.csv.
    sections = pd.read_csv(STEP2 / "sections.csv")
    states_sentences = []
    for _, r in sections[sections["doc"] == "CPMP"].iterrows():
        for m in re.finditer(r"[^.]*disease states of interest currently (?:include|are) [^.]*\.", norm(r["text"])):
            states_sentences.append((str(r["number"]), int(r["start_page"]), m.group(0).strip()))
    if not states_sentences:
        raise SystemExit("master sentence naming the disease states not found")
    for d, (term, gap) in DISEASE_TERMS.items():
        g = new_graph()
        ontology(g, f"disease-{d}", ["master"])
        design = disease_designs[d]
        g.add((design, RDF.type, OWL.Class))
        g.add((design, RDFS.label, Literal(f"CPMP disease-state design {d}")))
        for number, page, sentence in states_sentences:
            g.add((design, CPMP.evidenceText, Literal(f"CPMP {number} (section start p{page}): {sentence}")))
        g.add((design, CPMP.moduleRole, Literal("disease state")))
        g.add((design, CPMP.contentStatus, Literal("not public")))
        g.add((design, CPMP.diseaseStated, Literal(d)))
        g.add((design, CPMP.note, Literal(f"DSA CPMP({DISEASE_DIGIT[d]}) is cited by the ISAs but not posted publicly.")))
        g.add((design, OWL.equivalentClass, intersection(g, [CLINICAL_STUDY_DESIGN, some(g, IS_ABOUT, term)])))
        if gap:
            g.add((design, CPMP.upstreamGap, Literal(gap)))
            log("disease", d, "upstream gap", gap)
        for s in slots.values():
            g.add((design, RDFS.subClassOf, some(g, HAS_PART, s["iri"])))
        g.serialize(MODULES / f"disease-{d}.ttl", format="turtle")

    # ---------------------------------------------------------------- compounds
    for comp in compounds:
        g = new_graph()
        ontology(g, f"compound-{comp}", ["cpmp-core"])
        rows = comps[(comps["class"] == "compound column") & (comps["doc_list"].map(lambda ds: compound_of.get(ds[0]) == comp))]
        if rows.empty:
            raise SystemExit(f"compound {comp}: no compound-column components; a defined class would be empty")
        design = CPMP[f"Compound_{comp}"]
        g.add((design, RDF.type, OWL.Class))
        g.add((design, RDFS.label, Literal(f"CPMP compound design {comp}")))
        g.add((design, CPMP.moduleRole, Literal("compound")))
        g.add((design, CPMP.note, Literal("No document of its own: components worded the same (Step 5 template) in all three ISAs of this compound.")))
        for _, row in rows.iterrows():
            declare_component(g, row)
        cells = sched[(sched["class"] == "compound column") & (sched["doc_list"].map(lambda ds: compound_of[ds[0]] == comp))]
        for _, s in cells.iterrows():
            declare_cell(g, s["activity_key"], s["visit"], ACTION, [
                (CPMP.sharingClass, Literal(s["class"])), (CPMP.occursIn, Literal(s["docs"]))])
        g.add((design, OWL.equivalentClass,
               intersection(g, [CLINICAL_STUDY_DESIGN] + [some(g, HAS_PART, c) for c in rows["iri"]]
                            + [some(g, HAS_PART, c) for c in cells["iri"]])))
        g.serialize(MODULES / f"compound-{comp}.ttl", format="turtle")
        log("compound", comp, "defined class over compound-column components", f"{len(rows)} components ({rows['kind'].value_counts().to_dict()})")
        log("compound", comp, "schedule cells in all three ISAs of the compound", f"{len(cells)} cells")

    # ---------------------------------------------------------------- ISAs
    dep = xref[(xref["doc"] != "CPMP") & (xref["target"] == "DSA") & (xref["relation"] == "refers_to")]
    for _, gr in grid.iterrows():
        doc, d, comp = gr["doc"], gr["disease"], gr["compound"]
        g = new_graph()
        ontology(g, f"isa-{doc}", ["master", f"disease-{d}", f"compound-{comp}"])
        design = isa_designs[doc]
        g.add((design, RDF.type, OWL.Class))
        g.add((design, RDFS.label, Literal(f"CPMP ISA {doc} design")))
        g.add((design, CPMP.moduleRole, Literal("compound x disease state")))
        g.add((design, CPMP.compoundStated, Literal(comp)))
        g.add((design, CPMP.diseaseStated, Literal(d)))
        g.add((design, RDFS.subClassOf, CLINICAL_STUDY_DESIGN))
        for sup in (m_design, disease_designs[d]):
            g.add((design, RDFS.subClassOf, sup))
            annotate_axiom(g, design, RDFS.subClassOf, sup, [
                (CPMP.evidenceDoc, Literal(doc)),
                (CPMP.evidenceText, Literal(norm(gr["evidence"]))),
            ])
        rows = comps[comps["doc_list"].map(lambda ds: doc in ds)]
        own = rows[rows["class"] != "compound column"]
        for _, row in own.iterrows():
            declare_component(g, row)
        for _, row in rows.iterrows():
            has_part(g, design, row, doc)
        # Schedule: own cells, restated master cells, master defaults unless overridden.
        mine = sched[sched["doc_list"].map(lambda ds: doc in ds)]
        for _, s in mine.iterrows():
            if s["class"] != "compound column":
                declare_cell(g, s["activity_key"], s["visit"], ACTION, [
                    (CPMP.sharingClass, Literal(s["class"])), (CPMP.occursIn, Literal(s["docs"]))])
            ann = [(CPMP.allocation, Literal("own")), (CPMP.evidenceDoc, Literal(doc)),
                   (CPMP.evidenceSource, Literal(f"{SOA_SOURCE}, {nct_of[doc]}"))]
            if (doc, s["activity_key"]) in addition:
                text, names_dsa = addition[(doc, s["activity_key"])]
                ann.append((CPMP.additionStated, Literal(text)))
            has_part_cell(g, design, s["iri"], ann)
        for _, r in restated[restated["isa"] == doc].iterrows():
            has_part_cell(g, design, cell_iri(r["activity_key"], r["visit"]), [
                (CPMP.allocation, Literal("restated")), (CPMP.evidenceDoc, Literal(doc)),
                (CPMP.evidenceSource, Literal(f"{SOA_SOURCE}, {nct_of[doc]}"))])
        for cell in defaults:
            if (doc, cell) in override_master:
                annotate_axiom(g, design, CPMP.overrides, cell_iri(*cell), [
                    (CPMP.evidenceDoc, Literal(doc)), (CPMP.evidenceText, Literal(override_master[(doc, cell)]))])
                g.add((design, CPMP.overrides, cell_iri(*cell)))
            else:
                has_part_cell(g, design, cell_iri(*cell), [(CPMP.allocation, Literal("default"))])
        for isa_code, activity, text in override_beyond:
            if isa_code != doc:
                continue
            g.add((design, CPMP.overrides, disease_designs[d]))
            annotate_axiom(g, design, CPMP.overrides, disease_designs[d], [
                (CPMP.evidenceDoc, Literal(doc)), (CPMP.activityKey, Literal(activity)),
                (CPMP.visit, Literal("ED")), (CPMP.evidenceText, Literal(text))])
        for _, r in dep[dep["doc"] == doc].iterrows():
            g.add((design, CPMP.dependsOn, disease_designs[d]))
            annotate_axiom(g, design, CPMP.dependsOn, disease_designs[d], [
                (CPMP.evidenceSection, Literal(f"{r['section']} {r['section_title']}")),
                (CPMP.evidencePage, Literal(int(r["page"]), datatype=XSD.integer)),
                (CPMP.evidenceText, Literal(norm(r["sentence"]))),
            ])
        g.serialize(MODULES / f"isa-{doc}.ttl", format="turtle")
        log("isa", doc, "asserted: master + disease-state design; has part own components",
            f"{len(rows)} components ({len(own)} not compound-column); {len(dep[dep['doc'] == doc])} DSA references")

    # ---------------------------------------------------------------- ISAs with no documents (CT.gov)
    new_isas = []
    for f in sorted(CTGOV.glob("NCT*.json")):
        rec = json.loads(f.read_text())
        p = rec["protocolSection"]
        ident = p["identificationModule"]
        secondary = [s["id"] for s in ident.get("secondaryIdInfos", [])]
        if "H0P-MC-CPMP" not in secondary:
            raise SystemExit(f"{f.name}: H0P-MC-CPMP not among secondary IDs")
        study = [s for s in secondary if s.startswith("H0P-MC-") and s != "H0P-MC-CPMP"]
        if len(study) != 1:
            raise SystemExit(f"{f.name}: expected one ISA study ID, found {study}")
        code = study[0].replace("H0P-MC-", "")
        summary = norm(p["descriptionModule"]["briefSummary"])
        ds = re.findall(r"\((OA|CLBP|DPNP)\)", summary)
        if len(set(ds)) != 1:
            raise SystemExit(f"{f.name}: disease abbreviation not unique in brief summary: {ds}")
        d = ds[0]
        drugs = [i["name"] for i in p["armsInterventionsModule"]["interventions"] if i["name"] != "Placebo"]
        if len(drugs) != 1:
            raise SystemExit(f"{f.name}: expected one non-placebo intervention, found {drugs}")
        nct = ident["nctId"]
        g = new_graph()
        ontology(g, f"isa-{code}", ["master", f"disease-{d}"])
        design = CPMP[f"ISA_{code}"]
        g.add((design, RDF.type, OWL.Class))
        g.add((design, RDFS.label, Literal(f"CPMP ISA {code} design (registered, no documents posted)")))
        g.add((design, CPMP.moduleRole, Literal("compound x disease state")))
        g.add((design, CPMP.compoundStated, Literal(drugs[0])))
        g.add((design, CPMP.diseaseStated, Literal(d)))
        g.add((design, RDFS.subClassOf, CLINICAL_STUDY_DESIGN))
        for sup in (m_design, disease_designs[d]):
            g.add((design, RDFS.subClassOf, sup))
            annotate_axiom(g, design, RDFS.subClassOf, sup, [
                (CPMP.evidenceDoc, Literal(f"{nct} (ClinicalTrials.gov record, last update {p['statusModule']['lastUpdatePostDateStruct']['date']})")),
                (CPMP.evidenceText, Literal(summary)),
            ])
        for cell in defaults:
            has_part_cell(g, design, cell_iri(*cell), [(CPMP.allocation, Literal("default assumed, no document"))])
        g.serialize(MODULES / f"isa-{code}.ttl", format="turtle")
        new_isas.append(code)
        log("isa-new", code, "CT.gov: secondary ID H0P-MC-CPMP; disease from brief summary; compound from interventions", f"{nct} {d} {drugs[0]}")

    # ---------------------------------------------------------------- all + catalog
    all_names = (["cpmp-core", "master"] + [f"disease-{d}" for d in DISEASE_TERMS]
                 + [f"compound-{c}" for c in compounds] + [f"isa-{d}" for d in isas] + [f"isa-{c}" for c in new_isas])
    g = new_graph()
    ontology(g, "cpmp-all", all_names)
    g.serialize(MODULES / "cpmp-all.ttl", format="turtle")
    entries = [f'  <uri name="{NS}modules/{n}" uri="{n}.ttl"/>' for n in all_names + ["cpmp-all"]]
    entries.append(f'  <uri name="{NS}imports/upstream_import" uri="../imports/upstream_import.ttl"/>')
    (MODULES / "catalog-v001.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<catalog prefer="public" xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">\n'
        + "\n".join(entries) + "\n</catalog>\n")

    log("crosswalk", "decisions", "sources/crosswalk_decisions.csv",
        f"{int((dec['decision'] == 'merge').sum())} pairs merged, {int((dec['decision'] == 'keep apart').sum())} kept apart; band(s) {', '.join(sorted(set(dec['band'])))}")
    log("scope", "objective-endpoint pairing", "not represented", "objectives and endpoints are separate components")
    log("scope", "fepixnebart CHEBI_758046", "not used: BioPortal synonym of LY3016859, not document content", "")

    idx = comps[["kind", "class", "docs", "key"]].copy()
    idx.insert(0, "iri", comps["iri"].astype(str))
    idx.to_csv(OUTPUT / "components_index.csv", index=False)
    sidx = pd.concat([
        pd.DataFrame([{"iri": str(cell_iri(a, v)), "activity_key": a, "visit": v,
                       "class": "master default" if (a, v) in defaults else "master", "docs": "CPMP"}
                      for a, v in sorted(master_cells)]),
        sched[["iri", "activity_key", "visit", "class", "docs"]].astype({"iri": str}),
    ], ignore_index=True)
    sidx.to_csv(OUTPUT / "schedule_index.csv", index=False)
    with open(OUTPUT / "build_log.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["step", "item", "rule", "detail"])
        w.writeheader()
        w.writerows(log_rows)
    print(f"{len(all_names)} modules, {len(comps)} components, {len(slots)} slots, "
          f"{len(sidx)} schedule cells, {n_sched_slots} schedule slots, {len(log_rows)} log rows")


if __name__ == "__main__":
    main()
