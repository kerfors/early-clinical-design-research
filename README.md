# Early clinical design research

How the design content of a clinical trial programme can be identified, and its relations across documents
made explicit, as data; and what the documents carry today. Two public master protocols are the cases: the
Lilly Chronic Pain Master Protocol (CPMP) and REMAP-CAP. Programme-level design and Target Product Profiles
(TPP) are the wider frame, after the EFPIA Smart Program Design and PhUSE CDD Framework work (2013–2018).

**Status: early exploratory work.** Draft, not normative. It is published so the method and the evidence can
be followed and reused, not as a model to adopt. Built from public documents (ClinicalTrials.gov, remapcap.org,
EU-PEARL, FDA, WOAH, NIH SEED). The design classes are anchored in 16 terms from public ontologies (OBI with IAO
and BFO, MONDO, HP), imported from pinned releases; the gaps found are listed in the module READMEs. Analyst
readings are marked as such, and each carries its review state; what still waits for a trial-design reviewer or a
clinical reader is listed in the catalogue.

**Relation to usdm-rdf and m11-rdf.** [usdm-rdf](https://w3id.org/cdisc/usdm/v4/) gives USDM v4 an RDF/OWL
form, and [m11-rdf](https://w3id.org/m11-rdf/) gives every ICH M11 section and element its own identifier. Both
describe one study and one protocol. This repo explores what neither covers yet: design content that is shared
and handed over between the documents of a master protocol, across sub-studies and versions. USDM v4 stays the
document carrier here (`usdm-master-protocol/`, checked with the usdm-rdf validator), and the design modules sit
next to it. Pointing statements at m11-rdf section identifiers, rather than at section numbers, is an open choice.

**Identifiers, for now.** The design modules are OWL files whose IRIs sit in a namespace for now
(`https://kerfors.github.io/early-clinical-design-research/`), and those IRIs do not resolve yet.

**Where this is heading:** first the design content as Linked Data, as in m11-rdf, then the ontologies behind the
content. See [VISION.md](VISION.md).

## The questions

The work is organised by ten competency questions. Each is answered per case by SPARQL queries over the design
modules and by findings with document evidence. The catalogue gives the question, the case questions and
findings under it, the answer, how it was checked, and its status:
[competency-questions/output/catalogue.md](competency-questions/output/catalogue.md).

| | Question | Requirement |
|---|---|---|
| Q1 | When are two occurrences in different documents the same component? | Identity |
| Q2 | Which content is shared across sub-studies but stated as shared in no document? | Unstated sharing |
| Q3 | What does a new sub-study inherit before anything is written for it? | Layer relations, obligations |
| Q4 | What is specific to one sub-study only? | Layer relations |
| Q5 | Which hand-overs to a child are never answered, or point at content that is not available? | Obligations |
| Q6 | Which defaults does a child take, override or stay silent on? | Layer relations, obligations |
| Q7 | Which child statements are affected when a parent document changes? | Version binding |
| Q8 | Which documents make up the set a sub-study depends on, and is that set stated? | Documents as views |
| Q9 | Where does a schedule depend on an event inside a visit? | Event anchors |
| Q10 | Why was a design choice made, and what else was considered? | Decisions |

The requirements are defined in [evidence-matrix/sources/requirements.csv](evidence-matrix/sources/requirements.csv).
Some questions have no answer in the public documents (Q10 above all); the catalogue shows that as it is.

## The two cases

- **CPMP** (H0P-MC-CPMP): 4 compounds × 3 disease states. One master protocol, 3 disease-state addenda (DSA,
  not public) and 12 intervention-specific appendices (ISA), each posted on ClinicalTrials.gov under its own
  NCT ID. The 13 Schedules of Activities are extracted to USDM in
  [soa2usdm-collections](https://kerfors.github.io/soa2usdm-collections/collections/cpmp/protocols/index.html).
- **REMAP-CAP**: an adaptive platform trial in community-acquired pneumonia. A Core Protocol (versions 4.0 and
  4.1), the Patient, Pathogen and Disease Appendix (PANDA) and nine domain-specific appendices (DSA).

## Templates as data

Before the cases, two public template families were read as data, the same method on a template rather than a
protocol: [EU-PEARL](eupearl-templates/) (sections with keys, text categories from the template's own markers,
field labels, a TOC check, and the MPT ↔ ISA alignment) and [four TPP templates](tpp-templates/) (column models
compared, with concept matching left to a review file).

## How the work is done

- Questions first; each step produces evidence for a question or a requirement.
- Scripts read the documents (text layer, rendered page, OCR check). Every finding traces to document, section,
  page and sentence. Nothing in an output is typed by hand.
- Claude proposes rules, readings and identity candidates; Kerstin decides. Decisions are files the builds read:
  crosswalk decisions, topic and response rules, reading reviews.
- Every result is checked twice: SPARQL against pandas, and each finding's observed value against the value
  recorded when it was agreed. A mismatch stops the build.
- Status labels (see Terms): *document fact*, *rule-derived*, *analyst-reading*, *decision by Kerstin*, and two
  combined forms. Readings that wait for a trial-design reviewer or a clinical reader are marked in the catalogue.

### One chain, end to end: CP-11b

1. **Documents.** All 12 CPMP ISAs have an eGFR exclusion with the same CKD-EPI formula at Visit 1 or Visit 2.
   The threshold depends on the compound: less than 70 ml/min/1.73 m² for LY3016859 (OA01 [1004], BP01 [2003],
   NP01 [3003]), 60 for LY3556050 ([x030]), and 30 for LY3526318 and LY3857210 ([x052], [x077])
   (`usdm-master-protocol/output_cpmp/step5/criteria.csv`). OA01's number is shifted by its extra criterion [1003].
2. **Proposal.** The crosswalk pairs criteria with similar wording (difflib ratio ≥ 0.85) or in the same slot
   of the ISA numbering. Claude proposed a decision per pair, with a pattern: P1 "eGFR threshold differs (same
   rule, different value)", P3 and P8 for variants that differ only in wording.
3. **Decision.** Kerstin decided each pair in `cpmp-design-modules/sources/crosswalk_decisions.csv`: the 12 P1
   pairs are kept apart; the wording-only variants are merged (11 P3 pairs for < 30, 1 P8 same-slot pair for
   < 70). Three < 70 / < 60 pairs, kept apart in an earlier review group, are not P1 and are not counted: 27 eGFR
   rows in the decision file, 12 in this finding.
4. **Build.** `cpmp-design-modules/scripts/01_build_modules.py` merges only pairs decided "merge", and logs
   every pair kept apart (`output/build_log.csv`).
5. **Finding.** CP-11b in `evidence-matrix/sources/findings.csv`, with the expected value "eGFR values 30/60/70".
   The selector `cp11b()` in `evidence-matrix/scripts/01_build_matrix.py` reads the 12 P1 decisions and both
   texts of each pair, and extracts the thresholds. That gives 12 evidence rows, status *decision by Kerstin*.
6. **Check.** Observed "eGFR values 30/60/70" equals the expected value: pass (`output/findings_checked.csv`). A
   changed decision or threshold stops the build.
7. **Catalogue.** Q1, row CP-11b, with the answer, the check and the status (`competency-questions/output/catalogue.md`).

What it shows: text identity cannot say "the same rule with a different value". A design model needs the rule
as one component with a parameter that varies by compound.

## Terms (draft)

Working definitions for this early exploratory work, not definitions for reuse. They are how the terms are used
in this repo today, and they may change as the work goes on.

| Term | Working definition |
|---|---|
| Master protocol | One protocol for several sub-studies, holding what they share; the rest is in appendices |
| DSA | **CPMP:** disease-state addendum (what is specific to one disease; not public). **REMAP-CAP:** domain-specific appendix (one question, e.g. antivirals, with its interventions and rules) |
| ISA | Intervention-specific appendix (CPMP): one compound in one disease state; the sub-study protocol |
| Core, PANDA | REMAP-CAP Core Protocol (4.0, 4.1) and its Patient, Pathogen and Disease Appendix |
| Layer | A document level: master, DSA, ISA (CPMP); Core, PANDA, DSA (REMAP-CAP) |
| Component | One unit of design content (a criterion, an endpoint, an SoA cell, a statement), with one identity across documents |
| Module | An OWL class that groups the components of one layer or one shared set (for example the CPMP compound module, which has no document of its own) |
| Hand-over (delegation) | A parent statement that leaves content to a child ("will be specified in the relevant DSA"). An obligation: it can be answered, or not |
| Default (overridable) | A parent rule that holds unless a child states otherwise |
| Reading | Claude's reading of one statement by an agreed rule, marked *analyst-reading* and reviewed by Kerstin |
| Crosswalk decision | Kerstin's decision that two differently worded occurrences are, or are not, the same component |
| Status labels | As written in the evidence matrix: *document fact* (stated in the document); *document fact (identity decided by Kerstin)* (stated, with the component identity from a crosswalk decision); *rule-derived* (computed by an agreed rule); *rule-derived from analyst readings* (computed from reviewed readings); *analyst-reading* (as above); *decision by Kerstin* |

## Layout

| Folder | Content |
|---|---|
| `competency-questions/` | The ten questions and the generated catalogue |
| `evidence-matrix/` | Requirement × case × finding × document evidence, generated from the builds below |
| `cpmp-design-modules/` | CPMP as OWL design modules: master, disease state, compound, compound × disease state; CQ1–CQ8 |
| `remapcap-design-modules/` | REMAP-CAP as OWL design modules with version binding (Core 4.0 / 4.1); R1–R7; reading reviews |
| `cpmp-soa-join/` | CPMP master and ISA Schedules of Activities joined cell by cell: allocation kind per activity × visit |
| `usdm-master-protocol/` | Both cases in USDM v4: document structure, cross-layer statements, amendments, breakpoints |
| `cdd-layer/` | Sketch of an allocation layer above USDM (parked) |
| `eupearl-templates/` | The five EU-PEARL templates as data: sections, text categories, field labels, TOC check, MPT ↔ ISA alignment |
| `tpp-templates/` | Four TPP templates compared: elements, column models, attribute inventory, crosswalk for review |
| `literature/` | Europe PMC query script and hit list |
| `scripts/` | Notebook generators for the template and SoA-join notebooks |

Each build folder has its own README. In `remapcap-design-modules/` and `evidence-matrix/` the README is the
agreement record.

## Sources and reuse

Third-party documents are not redistributed, and neither is whole-document text extracted from them (page text,
section text, USDM NarrativeContent). The manifests and READMEs list each source URL with its sha256; the scripts
re-create the extracted files from them. What is published is the analysis: sentences, components, readings,
counts and decisions, each with its source location.

A fresh clone therefore runs the later steps only after the earlier ones have been re-run from the downloaded
sources. Python 3 with pandas, plus per folder: python-docx, pdfplumber, pypdfium2, tesseract, rdflib, pyshacl,
ELK via ROBOT. See each folder's README.

Upstream ontology terms are imported from OBI, MONDO and HP (versions and checksums in
`cpmp-design-modules/sources/upstream/MANIFEST.csv`); they remain under their own licences.

## Related

- [ICH M11 as linked data: why, and what I did](https://www.linkedin.com/pulse/ich-m11-linked-data-why-what-i-did-kerstin-forsberg-26b7e/)
  (article, 26 October 2026) and the pages
  [ICH M11 and USDM, coming together](https://kerfors.github.io/usdm-one-graph/m11/) and
  [the CDISC Pilot as an ICH M11 protocol](https://kerfors.github.io/usdm-one-graph/m11/protocol.html)
- [usdm-rdf](https://w3id.org/cdisc/usdm/v4/): USDM v4 as RDF/OWL
- [m11-rdf](https://w3id.org/m11-rdf/): ICH M11 sections and elements with identifiers, and the M11–USDM mappings
- [soa2usdm](https://github.com/kerfors/soa2usdm) and [soa2usdm-collections](https://kerfors.github.io/soa2usdm-collections):
  Schedules of Activities from protocol PDFs to USDM

## License

Code is licensed under the [MIT License](LICENSE). Derived content is shared under
[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). Source documents remain the property of their owners
and are not redistributed here.
