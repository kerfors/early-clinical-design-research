# Early clinical design research

How the design content of a clinical trial programme can be held as linked knowledge, and what the documents
carry today. Two public master protocols are the cases: the Lilly Chronic Pain Master Protocol (CPMP) and
REMAP-CAP. Programme-level design and Target Product Profiles (TPP) are the wider frame, after the EFPIA Smart
Program Design and PhUSE CDD Framework work (2013–2018).

**Status: early exploratory work.** Draft, not normative. It is published so the method and the evidence can
be followed and reused, not as a model to adopt. Built from public documents (ClinicalTrials.gov, remapcap.org,
EU-PEARL, FDA, WOAH, NIH SEED) and public ontologies (OBI, MONDO, HP). Analyst readings are marked as such, and
each carries its review state; what still waits for a trial-design reviewer or a clinical reader is listed in
the catalogue.

**Relation to usdm-rdf and m11-rdf.** [usdm-rdf](https://w3id.org/cdisc/usdm/v4/) gives USDM v4 an RDF/OWL
form, and [m11-rdf](https://w3id.org/m11-rdf/) gives every ICH M11 section and element its own identifier. Both
describe one study and one protocol. This repo explores what neither covers yet: design content that is shared
and handed over between the documents of a master protocol, across sub-studies and versions. USDM v4 stays the
document carrier here (`usdm-master-protocol/`, checked with the usdm-rdf validator), and the design modules sit
next to it. Pointing statements at m11-rdf section identifiers, rather than at section numbers, is an open choice.

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

## How the work is done

- Questions first; each step produces evidence for a question or a requirement.
- Scripts read the documents (text layer, rendered page, OCR check). Every finding traces to document, section,
  page and sentence. Nothing in an output is typed by hand.
- Claude proposes rules, readings and identity candidates; Kerstin decides. Decisions are files the builds read:
  crosswalk decisions, topic and response rules, reading reviews.
- Every result is checked twice: SPARQL against pandas, and each finding's observed value against the value
  recorded when it was agreed. A mismatch stops the build.
- Status labels: *document fact*, *rule-derived*, *analyst reading*, *decision by Kerstin*. Readings that wait
  for a trial-design reviewer or a clinical reader are marked in the catalogue.

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
| `eupearl-templates/`, `tpp-templates/` | Structure of the EU-PEARL master protocol templates and of TPP templates |
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

- [usdm-rdf](https://w3id.org/cdisc/usdm/v4/): USDM v4 as RDF/OWL
- [m11-rdf](https://w3id.org/m11-rdf/): ICH M11 sections and elements with identifiers, and the M11–USDM mappings
- [soa2usdm](https://github.com/kerfors/soa2usdm) and [soa2usdm-collections](https://kerfors.github.io/soa2usdm-collections):
  Schedules of Activities from protocol PDFs to USDM

## License

Code is licensed under the [MIT License](LICENSE). Derived content is shared under
[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). Source documents remain the property of their owners
and are not redistributed here.
