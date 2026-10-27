# cdd-layer

A CDD-style allocation layer above USDM v4.0.0: which layer of a master protocol decides where an item of design content is specified or taken from. Sketch, not pipeline.
Parked 2026-10-25: its allocation kinds informed the design modules and the requirements. Seed data: `../usdm-master-protocol/output_remapcap/` (REMAP-CAP), `../cpmp-soa-join/output/` and `output/panel_statements.csv` (CPMP).

## Terminology

- "Core" = the REMAP-CAP Core Protocol (top layer of the REMAP-CAP master protocol). "V4.0" / "V4.1" are Core Protocol versions (5 Nov 2024; 29 May 2026, an amendment), not USDM versions.
- USDM throughout is v4.0.0 (DDF-RA v4.0.0, via usdm-rdf).
- Short forms (`CORE`, `CORE_41`, `CS_DSA`) are used only in file names, CSV values and IRIs.

## Scope (agreed 2026-10-24)

- Sketch only: small vocabulary (hand-written Turtle) + REMAP-CAP instances + one SPARQL query per competency question.
- Documents: REMAP-CAP Core Protocol V4.0 and V4.1, PANDA V1.0, Corticosteroid DSA (CS_DSA) V6. Nothing else.
- Instances are generated from the seed CSVs by script, never typed by hand. Every triple traces to a CSV row with document evidence.
- Out of scope: pipeline, other DSAs, CPMP, SHACL (unless a CQ needs it), rationale capture, usdm-overlay candidate findings, publishing.

## Scope, v0.2 (agreed 2026-10-25)

- Programmes: REMAP-CAP (as above) and Lilly CPMP (master protocol H0P-MC-CPMP and the 12 posted ISAs; the disease-state addenda are not public).
- The vocabulary refers to USDM objects only: `NarrativeContent`, `ScheduledActivityInstance`, `BiomedicalConceptCategory`, `BiomedicalConcept`. It does not refer to SoA extraction artefacts (rows, cells, panels). Interpreting an extracted SoA as USDM, including resolving panels to biomedical concepts, belongs to soa2usdm; the cdd-layer assumes it has been done.
- Instances can only point at USDM objects that exist. REMAP-CAP: `usdm-master-protocol/output_remapcap/step6/remapcap_usdm_v3.json` has NarrativeContent for all four document versions. CPMP: no USDM yet (the soa2usdm-collections `cpmp` collection holds SoA extractions only, schema `soa-tables-consolidated 1.6`).
- IAO parents for `Statement` and `Allocation`: later.

## Competency questions

1. Which CS_DSA statements depend on Core sections that changed in Core Protocol V4.1?
2. Which Core delegations (15) and overridable defaults (6) to DSAs does CS_DSA 6 take up, and which does it override?
3. Which decisions have no recorded rationale?

Added in v0.2 (2026-10-25):

- CQ-A (across programmes): which allocation kinds occur in REMAP-CAP and CPMP, at which level, with which version binding (bound, unversioned, no statement)?
- CQ-B (identity below the SoA row): which delegated biomedical concepts does each CPMP ISA carry? Expected result: `../cpmp-soa-join/output/delegated_test_level.csv`.
- CQ-C (event anchors): which delegations start at a scheduled activity instance inside an encounter (CPMP: randomisation inside Visit 3)?
- CQ3 is kept only as a test that the "rationale not available" record is honest.

## Modelling decisions (agreed 2026-10-24)

- Home: this folder; own repo when it stabilises.
- Statement (a sentence in a document version and section) and Decision (what it decides) are separate classes. 1:1 in the first sketch.
- Missing rationale is explicit: "rationale not available", with reason and sources checked. Not plain absence.
- PROV-O for evidence and attribution only (prov:wasDerivedFrom, prov:wasAttributedTo). Decisions are not prov:Activity.
- Evidence tiers, pattern copied from usdm-overlay (not its IRIs): document-stated, rule-derived (relation labels from the EU-PEARL phrase rules, Plan 1 Step 2), analyst-reading, analyst-reading-agreed.
- Version pointers: USDM StudyDefinitionDocumentVersion instances from `remapcap_usdm_v2.json` (instance namespace `https://kerfors.github.io/early-clinical-design-research/usdm/remapcap/`).
- Section pointers: not m11-rdf section IRIs (REMAP-CAP is not M11-structured). See open point 1.
- Namespace: `cdd:` = `https://kerfors.github.io/early-clinical-design-research/cdd/`.
- Test: each SPARQL result compared with an expected result computed with pandas from the seed CSVs; fail on difference.

- Core decisions are made in Core Protocol V4.0 (the seed extracted cross-references from Core Protocol V4.0 only). Whether Core Protocol V4.1 restates them is not checked in this sketch.
- Open readings stay open: response `ambiguous` with an `open_question`; tier stays `analyst-reading` (nothing reviewed). Row 138 is kept but excluded from the CQ2 expected results.

## Modelling decisions, v0.2 (agreed 2026-10-25)

- `cdd:Decision` renamed `cdd:Allocation`. Seven kinds: Delegation, OverridableDefault, Inheritance, Restatement, Addition, Extension, Override. Cell kinds of the CPMP join map as: inherited → Inheritance, restated → Restatement, added and isa_only → Addition, extended and isa_only_extended → Extension, override_ed → Override; whether the counterpart schedules the activity at all is `cdd:activityInCounterpart`.
- `cdd:allocates` points at a USDM object. Levels (SKOS scheme): narrative content, scheduled activity, biomedical concept category content. One allocation per scheduled activity instance.
- `cdd:counterpartLayer` replaces `cdd:delegatesTo` and `cdd:inheritsFrom`; its meaning is given by the kind. The deciding layer follows from `cdd:decidedIn` (document version → document → layer).
- Version binding sits on the allocation, with three values: bound, unversioned, no statement (rule-derived).
- Layers are individuals per programme, with full name (`skos:prefLabel`) and abbreviation (`skos:altLabel`), and a role from a fixed SKOS scheme: master, population / disease, intervention. "DSA" is not an identifier: Domain-Specific Appendix in REMAP-CAP (intervention layer), disease-state addendum in CPMP (population layer).
- `cdd:DocumentSection` removed; sections are `usdm:NarrativeContent`.
- Event anchors: `cdd:scopeStartsAt` points at the scheduled activity instance a delegation starts from. The order of other instances relative to it is USDM `Timing`.
- Panel content: an ISA's "tests unique for this ISA" statement gives an Inheritance of the master's category and one Addition per concept, `cdd:withinCategory` the master's category. Statements in `output/panel_statements.csv` (`scripts/02_panel_statements.py`): 6 from the PDF text layer, 5 read from the rendered page and checked letter by letter against a letter-spaced text layer, 1 (OA05, no text layer) read from the rendered page only. Transcriptions in `panel_statements_visual.csv`.

## Checks on the seed (2026-10-24)

- `remapcap_usdm_v2.json` has NarrativeContent only for PANDA 1.0 (17 sections). Core Protocol V4.0, Core Protocol V4.1 and CS_DSA 6 have no section-level content in the JSON. (2026-10-25: added in Plan 1 Step 6, `remapcap_usdm_v3.json`.)
- Core 7.6.3 and 7.6.4 are headings added in the Core Protocol V4.1 body, missing from both TOCs (README Step 5, BP16). They are new in V4.1, not removed.
- CQ2 pairing: the seed has both sides (Core→DSA delegates/default_overridable in `cross_references.csv`; CS_DSA→Core in `inherited_from_core.csv`), but no table pairing a Core delegation or default with the CS_DSA statement that answers it. Overrides (CS_DSA states its own value) are not in the seed at all.

- Revision scope: Plan 1 Step 5 compared every TOC-numbered Core section (plus 7.6.3 and 7.6.4 split from 7.6.2) by exact text; a section not in `core_v40_v41_diff.csv` has identical text in Core Protocol V4.0 and V4.1.
- Core 7.8.7 is listed with similarity 1.000 but one sentence changed: "capped at 60% for two-intervention domains" (V4.0) became "capped at 75% for two-intervention domains" (V4.1) (pdftotext of both PDFs, 2026-10-24). CS_DSA 10.3 takes "the cap ... specified in core protocol documents" without a version, so the cap it takes changes from 60% to 75% under Core Protocol V4.1 with no DSA change. Similarity is not a signal of materiality.

## Open points

1. Section IRIs (agreed 2026-10-24): minted for all four documents in the cdd instance namespace, keyed by document version + section number; PANDA ones linked to the existing USDM NarrativeContent. Superseded 2026-10-25: sections are the USDM NarrativeContent of `remapcap_usdm_v3.json`.
2. CQ2 pairing table (done 2026-10-24): `output/cq2_pairing_draft.csv` from `scripts/01_cq2_pairing_draft.py`. Five open questions (rows 77, 78, 133, 148, 151) not settled from the documents.

## Proposals for session 2 (2026-10-24; 1 and 2 agreed 2026-10-25, 3 deferred)

Focus is the structural part of the 2018 CDD Framework (who decides where, inheritance, version binding), not the rationale part.

1. Rename `cdd:Decision` to `cdd:Allocation` (who decides, where), with Delegation, OverridableDefault and Inheritance as its kinds. Reason: the sketch records allocation of authority between layers, not design decisions with alternatives in the 2018 sense; `Decision` would claim more than it holds.
2. Keep CQ3 (rationale) only as a test that the "rationale not available" record is honest.
3. Add CQ4, crossing into USDM objects: which USDM content items (Endpoint, EligibilityCriterion, StudyIntervention, ...) in the REMAP-CAP USDM instance are governed by a Core Protocol section that changed in V4.1? Needs a link from Statement/Allocation to USDM objects, which the sketch does not have yet.
