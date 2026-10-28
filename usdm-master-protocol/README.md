# usdm-master-protocol

Plan 1: test USDM v4 against two public master protocols, the Lilly Chronic Pain Master Protocol (CPMP) and REMAP-CAP.

Status 2026-10-27: REMAP-CAP Steps 2–6 and CPMP Steps 2–5 done (sections below). The work first stopped after Step 1 (2026-10-24): the CPMP disease-state addenda (DSA) are not posted on CT.gov, and the search of other public sources found none ("DSA search" below). REMAP-CAP was then added as a fully public case, and CPMP was restarted for its posted documents.

Whole-document outputs (`output_cpmp/step2/page_text.csv` and `sections.csv`, `output_remapcap/step2/sections.csv`, and the USDM JSON files of both cases) are not in the public repo. The scripts and notebooks re-create them from the source PDFs (URLs and sha256 in `sources/`).

## Contents

- `sources/ctgov_api/cpmp_studies.json` – CT.gov API v2 full records for the 16 H0P-MC-* studies. `QUERY.txt` has the queries.
- `sources/pdf/` – all large documents posted on those records (13 protocols, 12 SAPs), as downloaded. File name = `<NCT>_<CT.gov filename>`.
- `scripts/01_inventory.py` – builds `inventory.csv` from the two folders above.
- `inventory.csv` – one row per posted document, plus one row per DSA and per record without documents.

## Inventory: protocol layer documents

Version and approval date are from the document title page. CT.gov file names (`Prot_000`, `Prot_004` …) are CT.gov upload numbering, not versions.

| Layer | Document | NCT | Title (from document) | Version | Approved | Pages |
|---|---|---|---|---|---|---|
| Master | H0P-MC-CPMP | NCT05986292 | A Master Protocol for Randomized, Placebo-Controlled, Phase 2 Clinical Trials of Multiple Interventions for the Treatment of Chronic Pain | Amendment (a) | 11-Dec-2020 | 93 |
| DSA | H0P-MC-CPMP(1) – OA | – | not posted | – | – | – |
| DSA | H0P-MC-CPMP(2) – CLBP | – | not posted | – | – | – |
| DSA | H0P-MC-CPMP(3) – DPNP | – | not posted | – | – | – |
| ISA | H0P-MC-OA01 | NCT04456686 | … LY3016859 for the Treatment of Osteoarthritis | (a) | 27-Mar-2020 | 40 |
| ISA | H0P-MC-NP01 | NCT04476108 | … LY3016859 for the Treatment of Diabetic Peripheral Neuropathic Pain | (a) | 27-Mar-2020 | 38 |
| ISA | H0P-MC-BP01 | NCT04529096 | … LY3016859 for the Treatment of Chronic Low Back Pain | original | 11-May-2020 | 40 |
| ISA | H0P-MC-OA02 | NCT05080660 | … LY3526318 for the Treatment of Osteoarthritis Pain | (a) | 10-Aug-2021 | 45 |
| ISA | H0P-MC-NP02 | NCT05177094 | … LY3526318 for the Treatment of Diabetic Peripheral Neuropathic Pain | (a) | 30-Sep-2021 | 44 |
| ISA | H0P-MC-BP02 | NCT05086289 | … LY3526318 for the Treatment of Chronic Low Back Pain | (a) | 10-Aug-2021 | 44 |
| ISA | H0P-MC-OA03 | NCT04627038 | … LY3556050 for the Treatment of Osteoarthritis Pain | (a) | 03-Mar-2021 | 41 |
| ISA | H0P-MC-NP03 | NCT04707157 | … LY3556050 for the Treatment of Diabetic Peripheral Neuropathic Pain | (b) | 01-Oct-2021 | 44 |
| ISA | H0P-MC-BP03 | NCT04874636 | … LY3556050 for the Treatment of Chronic Low Back Pain | original | 17-Mar-2021 | 36 |
| ISA | H0P-MC-OA05 | NCT05620563 | … LY3857210 for the Treatment of Osteoarthritis Pain | (a) | 14-Oct-2022 | 46 |
| ISA | H0P-MC-NP05 | NCT05620576 | … LY3857210 for the Treatment of Diabetic Peripheral Neuropathic Pain | (a) | 13-Oct-2022 | 47 |
| ISA | H0P-MC-BP05 | NCT05630196 | … LY3857210 for the Treatment of Chronic Low Back Pain | (a) | 13-Oct-2022 | 45 |
| ISA | H0P-MC-OA07 | NCT07641517 | (LY4065967) – no documents posted | – | – | – |
| ISA | H0P-MC-NP07 | NCT07285018 | (LY4065967) – no documents posted | – | – | – |
| ISA | H0P-MC-BP07 | NCT07641504 | (LY4065967) – no documents posted | – | – | – |

"…" = "Randomized, Placebo-Controlled, Phase 2 Clinical Trial to Evaluate". Full titles in `inventory.csv`.

Each ISA record also has one SAP (ISA SAP). The master record has no SAP. The master text says a DSA SAP will not be developed; DSA analyses go in the ISA SAPs (master p.57).

## Findings

1. **No DSA is posted.** The DSA identifiers come only from citations in the ISA texts: OA = H0P-MC-CPMP(1), CLBP = CPMP(2), DPNP = CPMP(3). No CT.gov record has a DSA document. The ISAs delegate objectives and endpoints, overall design, eligibility, discontinuation and statistics to "the Master Protocol and the DSA" (e.g. BP01 pp. 18, 19, 21, 26, 30). So the middle layer, where population and disease-specific endpoints sit, is missing.
2. **Master version is old.** Posted master = Amendment (a), 11-Dec-2020. The master record is still RECRUITING (last update 2026-09-23) and 2026 ISAs (07 series) exist, so later master amendments probably exist but are not posted. I don't know how many.
3. **ISA = intervention × disease.** The ISA number carries the disease (OA01, NP01, BP01 are all LY3016859). There is no single ISA per intervention.
4. **Registration mirrors FDA Appendix C.** Each ISA is its own NCT. The master NCT05986292 was registered only in 2023-08 (study start 2020-01-30). The 07-series records carry H0P-MC-CPMP as a secondary ID; older records do not. Some posted PDFs have a CT.gov cover sentence "This study … is a sub-study of Master Protocol H0P-MC-CPMP (NCT05986292)". This is naming/cover text only, no structured link.
5. **Redaction.** All posted documents are redacted with CCI / PPD markers (counts in `inventory.csv`; 10–43 CCI per document). Not yet checked which sections are affected.
6. **Text layer quality, relevant for Step 2.**
   - Character-spaced text layer ("P r o t o c o l") on 4–25 pages in 8 of 13 PDFs, including 16 master pages. Words can be found by removing whitespace, but word boundaries are lost.
   - OA05: pages 12–15, 31, 32, 34, 36–38 are image-only (e.g. the SoA). OCR needed.
   - OA02 has DPNP text in an appendix ("CPMP(3) DSA, and NP02 ISA", p.40): template carry-over, so DSA citations must be read with care.

## Stop

Plan 1 needs one master, one DSA and one ISA. The DSA layer is not public on CT.gov, so the plan as written cannot proceed. Options for decision:

- A. Two layers only: master (a) + one ISA, and record "DSA not public" as a finding in itself.
- B. Look for the DSAs in other public sources (EU CTIS, publications, FDA). Not searched yet.
- C. Choose another public master protocol where all layers are posted.

## DSA search (option B), 2026-10-24

Searched for the three DSA documents H0P-MC-CPMP(1) OA, (2) CLBP, (3) DPNP outside CT.gov.

| Source | Query | Result |
|---|---|---|
| EU CTIS (public API) | "H0P-MC", "CPMP", "Chronic Pain Master Protocol", LY3526318, LY3857210, LY3556050, LY4065967 | No CPMP trial. One LY3556050 hit is a different study (2023-506127-29-00, J2P-MC-LXBD). |
| EU Clinical Trials Register (EudraCT) | "H0P-MC", LY3526318, LY3556050, LY3016859, "chronic pain master protocol" | No CPMP trial (LY3016859 hit = I5V-MC-TGAB, diabetic nephropathy). |
| FDA | web search | One slide deck: `sources/publications/FDA_media_182237_CPMP_slides_2024-03-05.pdf` (Karen Price, Lilly, 5 Mar 2024). Names the DSAs CPMP(1)–(3) as "Pain Type 1/2/3" and the tier structure. No DSA content. |
| Europe PMC | CPMP title, NCT05986292, compound codes | 2 Lilly papers with CPMP content (below). Others are reviews/commentary. |
| Pain Reports 2024, design paper (PMC11487222) | full text + supplements | Describes DSA role in prose (disease-specific eligibility, cannot broaden master inclusion; secondary scales WOMAC for OA, Roland–Morris for CLBP, BPI-SF for DPNP). Supplements are video only. |
| PAIN vol. 166 (Europe PMC year 2024), LY3526318 results (PMC12168806) | full text + supplement | Supplement s001 (`sources/publications/PAIN_2025_LY3526318_PMC12168806_supplement_s001.pdf`, 5 pages) summarises CPMP-level exclusion criteria and DSA-level eligibility for OA, CLBP, DPNP in prose. Paper says data requests go via Vivli. |

**Conclusion.** No DSA document is public in the sources searched. The only DSA-level content is author summaries in two Lilly publications: secondary, paraphrased, no version or date, no section structure, no "as specified in" statements. It cannot stand in for the DSA layer in a USDM mapping without breaking the "document content only" rule. Access to the full documents would need a data request (Vivli) or Lilly.

Not searched: Vivli catalogue (request-based, not public), conference posters, FDA review documents (none expected for Phase 2 without approval).

## REMAP-CAP (chosen 2026-10-24 as public alternative)

Files:
- `scripts/02_remapcap_download.py` – downloads all PDFs listed on remapcap.org "protocol-documents" and "superseded-protocol-documents"; writes `sources/remapcap/manifest.csv` (URL, bytes, sha256, date).
- `scripts/03_remapcap_inventory.py` – writes `remapcap_inventory.csv`: layer, document name, version and date from each document's page 1, pages, text-layer checks, trial IDs cited.
- PDFs and HTML pages are git-ignored (`.gitignore` in this folder); re-create them with script 02.

Inventory (85 documents, all with a text layer, no image-only or character-spaced pages except 1 page in two Influenza Antiviral versions, no redaction found):

| Layer | Current | Superseded |
|---|---|---|
| Core Protocol | V4.1, 29 May 2026 | V1, 1.1, 2, 2.1, 3, 3.1, 4 (Nov 2016 – Nov 2024) |
| Patient, Pathogen and Disease Appendix (PANDA) | V1.0, 5 Nov 2024 | – |
| Pandemic Appendix to the Core Protocol | – | V1.0, 1.1, 2.0 (Jan – May 2020) |
| Domain-Specific Appendices | 10 domains | 55 versions, incl. 8 closed domains (e.g. Anticoagulation, Vitamin C, Statin, Antiplatelet, ACE2 RAS, Cysteamine) |
| Region-Specific Appendices | 6 regions (2019–2021) | – |
| Statistical Analysis Appendix / Registry Appendix | V4 / V2, 5 Nov 2024 | – |

One CT.gov record for the whole platform: NCT02735707 (EudraCT 2015-002340-14, CTIS 2023-507889-89-00); no documents posted there.

Findings relevant for USDM:
1. **Completeness.** The Core Protocol version history (§2.2) lists V1–V4.1; all 8 are posted. The Corticosteroid DSA version history lists V1–V6; all are posted. V4 is noted as publication supplement only, not for ethics submission.
2. **Versions are not linear.** Some DSA versions are regional branches with their own numbers: Immunoglobulin 2.2 Canada, 2.3 USA, 2.4.2 Australia, 2.5 NZ (all mid-2020); Core 3.1 and Corticosteroid 5 are marked "UK" in the file name. Corticosteroid 3.2 (20 Aug 2020) is dated after 4.0 (21 Jul 2020).
3. **No explicit version binding between layers.** DSAs refer to "the Core Protocol" without a version. PANDA says some active DSAs were approved before Core V4 and PANDA (continuity section).
4. **Website listing vs document content.** COVID-19 Antiviral (II): the "current" file is V1.1 (19 Mar 2024); the "superseded" list has V2 dated 8 Sep 2025 (link text says "V1"). Immunoglobulin 2.2: file name says 01 June 2020, document says 01 July 2020. Document page 1 is used as the authority in the inventory.
5. **Terminology.** "DSA" here = Domain-Specific Appendix (holds interventions). PANDA is the population/disease layer and is shared by all domains.

## Decision before Step 2 (REMAP-CAP), taken 2026-10-24

Proposed set: Core Protocol + PANDA V1.0 + Corticosteroid DSA V6 (5 Nov 2024). Open point: Core V4 (5 Nov 2024, same release date as PANDA V1 and Corticosteroid DSA V6) or current Core V4.1 (29 May 2026)?

**Decision 2026-10-24:** Core Protocol V4.0 (5 Nov 2024) + PANDA V1.0 + Corticosteroid DSA V6 for Steps 2–4. Core V4.1 (29 May 2026) only as amendment in Step 5.

## Step 2 – REMAP-CAP structure and cross-layer statements (done 2026-10-24)

- Generator: `scripts/build_02_remapcap_structure_nb.py` → notebook `notebooks/02_remapcap_structure.ipynb` (run from `notebooks/`).
- Outputs in `output_remapcap/step2/`: `toc.csv`, `headings.csv`, `sections.csv`, `cross_references.csv`.
- Test: executed with Jupyter (nbclient) in the cloud workspace, and its code run on this Mac; the four CSVs are byte-identical.

Structure: all numbered TOC entries found in the body (CORE 145, PANDA 17, CS_DSA 64). CORE has 35 unnumbered TOC sub-headings, kept in `toc.csv` but not used to split sections.

Relation rules: the EU-PEARL MPT/ISA phrase rules, adapted to REMAP-CAP wording (table in the notebook). Added: direction (up = takes content from a higher layer; down = hands content to a lower layer) and `default_overridable` ("unless otherwise specified in a DSA").

| From → to | refers_to (up) | delegates (down) | default_overridable | mention_only |
|---|---|---|---|---|
| CS_DSA → CORE | 19 | – | – | 7 |
| CS_DSA → PANDA | 0 | – | – | 1 |
| CORE → DSA | – | 15 | 6 | 43 |
| CORE → PANDA | – | 3 | 0 | 7 |
| CORE → RSA | – | 4 | 0 | 20 |

Findings for Step 3 and the breakpoint table:
1. **Inheritance is explicit but unversioned.** The CS_DSA takes from the Core Protocol: platform eligibility (8.2), age strata (8.1.1), illness severity states (8.1.2), primary and secondary endpoints (8.5.1, 8.5.2), SAE definition, borrowing between strata (10.2), RAR cap (10.3), trigger thresholds (10.7, 10.8), stopping rules (10.1), discontinuation (9.3), DSMB (11.1), funding (12.1). None of these names a Core version or Core section number.
2. **"Core Protocol documents" is a document set.** The CS_DSA uses this phrase 13 times. Age strata and illness states are "defined in Core Protocol documents", but Core V4 does not define them; PANDA does (§2 age categories, §4.3 Moderate/Severe State). Core V4 §7.8.3 says "The current Strata utilized in the Platform are described in the PANDA". So the DSA → PANDA link exists only through the Core. The CS_DSA never cites PANDA directly.
3. **The Core defines extension points.** 15 delegations and 6 overridable defaults to DSAs, e.g. allocation balance and RAR (7.5.2), primary outcome "will apply to all domains, unless otherwise specified in a DSA" (7.6), RAR cap 60% (7.8.7), gamma/lambda per domain-strata and domain-domain pair (7.8.3), blinding (7.7.3, 8.5), discontinuation (8.6), co-interventions (8.7).
4. **The primary endpoint is an overridable default.** The CS_DSA takes the default (8.5.1). This is where Step 5 (Core V4.1 changes the primary endpoint) will bite.
5. **Site- and region-level choices.** The CS_DSA cover pages hold checkboxes for which interventions, age strata and pregnancy rule a site/jurisdiction selected. This is template content, not filled data; noted for Step 3.

Review status: all 7 remaining `mention_only` sentences CS_DSA → CORE were read; all are in §2 (description of the protocol structure).

## Step 3 – REMAP-CAP in USDM v4 JSON (done 2026-10-24)

Model and CT: `usdm-rdf` repo (`~/repos/GitHub/usdm-rdf`), pinned DDF-RA v4.0.0 (`dataStructure.yml`, `USDM_CT.xlsx`). The usdm-rdf repo is read only; nothing there was changed.

- Generator: `scripts/build_03_remapcap_usdm_nb.py` → `notebooks/03_remapcap_usdm.ipynb` (run from `notebooks/`; `USDM_RDF_DIR` overrides the usdm-rdf location).
- Outputs: `output_remapcap/step3/remapcap_usdm.json` (139 objects), `output_remapcap/step3/mapping_log.csv` (one row per mapping decision, with evidence).
- Test: executed with Jupyter in the cloud workspace and its code run on this Mac; both outputs byte-identical.

Decisions (2026-10-24): one study design = Corticosteroid domain; Core platform criteria as shared `EligibilityCriterionItem`s at `StudyVersion` level; Core objectives/endpoints copied into the design; PANDA strata/states kept as narrative only.

Rules: text taken from Step 2 `sections.csv` by section number; a value only where the document states it; a required attribute with no source is left out and logged. Codes: DDF-native value sets checked against `USDM_CT.xlsx` sheet 2; Inclusion Criteria C25532, Exclusion Criteria C25370, Interventional Study C98388 checked in NCIt (BioPortal) – codelist membership of these SDTM-backed codes not checked.

Content mapped: 3 `StudyDefinitionDocument`s (Core with `childIds` = PANDA, CS_DSA – Core §2.2), each with one approved version and approval date; 17 PANDA sections as `NarrativeContent`; 16 eligibility criteria (Core 3+3 platform, DSA 4+6 domain, document order kept); 3 objectives with 5 endpoints; 3 interventions and 3 arms; NCT02735707 with ClinicalTrials.gov as registry; official title and acronym.

Mapping log status counts: mapped 44, mapped_copy_from_core 7, derived 9, required_not_in_document 30, not_expressible 9.

## Step 4 – Validation (done 2026-10-24)

- Runner: `scripts/04_run_usdm_rdf_validator.py`. Executes usdm-rdf `notebooks/60_validate_study.ipynb` unchanged on disk; the two input lines are set in memory (`STUDY_JSON` = step 3 JSON, `BASE_IRI` = `https://kerfors.github.io/early-clinical-design-research/usdm/remapcap/`, an instance namespace chosen for this study – change if wanted).
- Outputs: `output_remapcap/step4/shacl_findings.csv`, `context_unmapped_keys.csv`, executed notebook `60_validate_study.ipynb` (local paths replaced by `<repo>` / `<repos>`).
- Needs rdflib + pyshacl + nbclient; run in the cloud workspace (the Mac VM has no free space for installs).

Results:
- Context conformance: 139 typed objects, 805 triples, no unknown types, no unmapped keys, 128 cross-references, 0 dangling.
- Structural SHACL: 30 violations, all `MinCount`. They are exactly the 30 `required_not_in_document` / `not_expressible` absences in the mapping log (checked per focus id and attribute) – no other structural problem.
- Terminology SHACL: conforms (25 DDF-native codelists checked). 17 coded values in 2 SDTM-backed codelists not checked (eligibility category, study type).

Input for the breakpoint table (Step 5), from `mapping_log.csv`:

| Kind | Item | Evidence |
|---|---|---|
| not expressible | Appendix documents have no `StudyDefinitionDocument.type`: value set C215477 has only "Protocol" | PANDA, CS_DSA title pages |
| not expressible | Inherited Core endpoint can only be copied into the domain design (`Endpoint` is composed, not referenced) | CS_DSA 8.5.1 |
| not expressible | Domain eligibility = platform + domain criteria; one flat list per design, the layer survives only in `identifier` | CS_DSA 8.2, Core 7.4 |
| not expressible | Intervention-level exclusion, conditional on site regulatory approval (pregnancy) | CS_DSA 8.2.3 |
| not expressible | Arm available only in one illness state (hydrocortisone, Severe State) | CS_DSA 8.3.3 |
| not expressible | Age strata and illness states (dynamic, re-randomisation) – no class; kept as narrative | PANDA 2, 4.3; CS_DSA 8.1 |
| model gap | `StudyVersion.versionIdentifier` for a platform = a set of document versions; no binding of DSA to a Core version | decision; CS_DSA 2 |
| model gap | `Code.codeSystemVersion` 1..1 – no CT package date in any source; value records the code's source instead | Step 3 code helper |
| content gap | Required but not stated in the documents: design model, rationale, epochs, cells; arm type; intervention role/type; endpoint purpose; objective level (domain objective); template name; registry identifier; governance date scope; version rationale | mapping log |

### M11 Master Protocol Indicator (checked 2026-10-24 in m11-rdf v0.3.0)

ICH M11 element "Master Protocol Indicator" (`m11:C217342.C218707`, §1.1.2, Required, one to one). Both published mappings in `m11-rdf/m11-usdm.sssom.tsv` sources – HL7 FHIR Clinical Study Protocol IG ballot (May 2026, row 83) and CDISC DDF-RA v4.0.0 M11 mapping (row 88) – map it to `StudyDefinitionDocumentVersion.children`. That attribute does not exist in USDM v4.0.0: the child link is `StudyDefinitionDocument.childIds`, on the document, not on the version. It is the location before DDF-RA issue #614 (closed) moved `children` from the document version to the document ("the versions are not children of each other but the documents itself are: like master versus sub-protocols"), so both mappings are behind #614. m11-rdf keeps both rows as residue ("attribute not on the class", `reports/d2-residue.csv`).

For REMAP-CAP: the indicator can only be derived from the Core document's `childIds`, and it is the same for every Core version. Which PANDA/DSA versions belong to Core 4.0 or 4.1 cannot be stated (see Step 3, version binding). Breakpoint table entry.

## Step 5 – Core V4.1 as amendment, and the breakpoint table (done 2026-10-24)

- Generator: `scripts/build_05_remapcap_amendment_breakpoints_nb.py` → `notebooks/05_remapcap_amendment_breakpoints.ipynb`. Reads Core V4.1 with the Step 2 code cells, unchanged (loaded from `02_remapcap_structure.ipynb`).
- Outputs in `output_remapcap/step5/`: `core_v40_v41_diff.csv`, `inherited_from_core.csv`, `remapcap_usdm_v2.json` (Step 3 JSON + Core 4.1 document version + StudyVersion 2 with StudyAmendment), `mapping_log_step5.csv`, **`breakpoints.csv` / `breakpoints.md`** (21 breakpoints), `validation/`.
- Validation: `python3 scripts/04_run_usdm_rdf_validator.py output_remapcap/step5/remapcap_usdm_v2.json output_remapcap/step5/validation` (runner now takes the JSON and output folder as optional arguments). 281 objects, 0 dangling references; 90 structural `MinCount` findings, all explained by the Step 3 and Step 5 logs; terminology conforms.
- Test: executed with Jupyter in the cloud workspace and its code run on this Mac; all outputs byte-identical.

Core V4.0 → V4.1: 15 changed sections. Two (7.6.3 Exploratory outcomes, 7.6.4 Adaptations to the primary endpoint in a pandemic) are new headings in the body that are **not in the V4.1 TOC**. Of the 12 CS_DSA inheritance statements, 8 point to Core sections that changed (primary and secondary endpoints, borrowing between strata, triggers, RAR cap); platform eligibility (7.4.1, 7.4.2) and the PANDA-defined strata and states did not change. The `core_location` column in `inherited_from_core.csv` is an analyst reading, to be reviewed.

Endpoint under V4.1 (reading, logged): CS_DSA §8.5.1's unversioned "primary outcome as specified in Core Protocol documents" resolves to the V4.1 primary endpoint; per the V4.1 §7.6.2 transition rule the DSA (dated before V4.1) additionally reports the V4.0 primary endpoint "Survival and Recovery Trajectory". Its level is not stated (`ambiguous_in_document`); V4.1 lists it as exploratory (§7.6.3).

Breakpoints by area and kind (model = USDM v4.0.0 cannot express it; mapping = only by copying or convention; content = not stated in the protocol text):

| area | model | mapping | content |
|---|---|---|---|
| substudy unit | 1 | | |
| three layers | 2 | 1 | |
| inherited content | 4 | 1 | |
| version granularity | 5 | 1 | 2 |
| substudy identity | 1 | | 1 |
| codes | 1 | | |
| content gaps | | | 1 |

Next: Step 7 – draft DDF-RA discussion post or worked example (Issue #467 promised IG examples).

Review 2026-10-24: Kerstin agreed with the three analyst readings – one arm per randomized intervention (Step 3), `core_location` in `inherited_from_core.csv` (Step 5), and the domain endpoint under Core V4.1 (Step 5).

## Step 6 – section text of all document versions as NarrativeContent (done 2026-10-25)

Why: the cdd-layer (`../cdd-layer/`) points statements and allocations at USDM `NarrativeContent`. Until Step 5 only PANDA 1.0 had section content.

- Generator: `scripts/build_06_remapcap_narrative_nb.py` → `notebooks/06_remapcap_narrative.ipynb` (run from `notebooks/`; `USDM_RDF_DIR` overrides the usdm-rdf location).
- Outputs in `output_remapcap/step6/`: `remapcap_usdm_v3.json` (Step 5 JSON + NarrativeContent for Core V4.0, Core V4.1 and CS_DSA V6; nothing else changed), `mapping_log_step6.csv`, `validation/`.
- Sources: Core V4.0 and CS_DSA V6 from Step 2 `sections.csv`; Core V4.1 read with the Step 2 code unchanged, as in Step 5, with 7.6.3 and 7.6.4 split from 7.6.2. The notebook re-reads Core V4.0 and CS_DSA V6 and checks they equal `sections.csv`.
- Same pattern as Step 3 for PANDA: one `NarrativeContent` per numbered section, `previousId`/`nextId` in document order, `childIds` from the section number; text in `NarrativeContentItem`s at `StudyVersion` level. Headings without text of their own get no item (`contentItemId` 0..1).
- The text is kept as read from the documents: no `<usdm:ref>` tags link it into the structured data (none in any of the five USDM files, REMAP-CAP or CPMP). Possible later step.
- Counts: Core V4.0 145 sections (124 with text), Core V4.1 147 (126), CS_DSA V6 64 (53). 940 objects in the JSON.
- Validation: `python3 scripts/04_run_usdm_rdf_validator.py output_remapcap/step6/remapcap_usdm_v3.json output_remapcap/step6/validation`. 0 dangling references; 90 structural `MinCount` findings, row for row identical to Step 5; terminology conforms.
- Test: executed with Jupyter in the cloud workspace and its code run on this Mac; JSON and log byte-identical.

Observation (logged, candidate breakpoint, version granularity): `NarrativeContentItem` sits at `StudyVersion` level, but a document version can be shared by two StudyVersions (CS_DSA V6, PANDA 1.0). The CS_DSA items are placed in StudyVersion 1 only. For PANDA, Step 5 copied the items into StudyVersion 2 (`_v41` ids), but the shared PANDA `NarrativeContent` still points at the StudyVersion 1 items, so the StudyVersion 2 copies are not referenced.

## CPMP restart – page text (2026-10-25)

Plan 1 restarted on CPMP for the non-SoA content (the DSAs stay not public). `scripts/10_cpmp_page_text.py` → `output_cpmp/step2/page_text.csv`: one row per page of the 13 posted protocols. Page kinds follow the Step 1 rules. Letter-spaced pages (133) keep the text-layer letters and line breaks, with word boundaries from tesseract OCR aligned per line (`coverage` per page; median 0.99; the 9 pages below 0.9 are SoA tables). OA05's 10 image-only pages are OCR only, unchecked. Runs in the cloud workspace only (needs tesseract); not re-run on the Mac.

**Step 2 – structure** (`notebooks/11_cpmp_structure.ipynb`, from `scripts/build_11_cpmp_structure_nb.py`): TOC, sections and cross-layer statements from `page_text.csv`. Headings are located by title. The section number is the one printed on the body heading, because TOC numbers are unreliable on letter-spaced pages. Every TOC entry is found or shown redacted. Cross-layer rules follow the REMAP-CAP Step 2, adapted to CPMP wording (targets MASTER, DSA, ISA, SAP; adds `overrides` for "not needed for ED per the CPMP SoA").

**Step 3 – USDM first pass** (`notebooks/12_cpmp_usdm.ipynb`): structure A (decision 2026-10-25): one Study, 13 documents, master `childIds` = ISAs, DSAs logged as not public. Content: document versions (current with approval date; earlier versions from Document History), NarrativeContent, titles, identifiers, organizations. Study designs and amendments deferred. 1,716 objects; 55 required absences, all logged and equal to the validator's 55 MinCount findings. Validation: `python3 scripts/04_run_usdm_rdf_validator.py output_cpmp/step3/cpmp_usdm.json output_cpmp/step3/validation https://kerfors.github.io/early-clinical-design-research/usdm/cpmp/` (cloud workspace).

**Step 4 – amendments** (decisions D1–D4, 2026-10-25). Two parts:

- `scripts/13_cpmp_amendment_tables.py` → `output_cpmp/step4/amendment_cells.csv`, `amendment_changes.csv`, `amendment_headers.csv`, `amendment_redactions.csv`. Reads the Protocol Amendment Summary of Changes tables cell by cell: column starts from the header line, rules and redaction bars from the rendered page, text from the text layer with word spacing from `page_text.csv`, every cell checked against tesseract OCR. Rules for merged section cells, the newer open layout (BP05, NP05, OA05: rules between section groups only, rows split at each rationale paragraph) and rows that run across a page break are in the docstring. 12 amendments (11 documents; NP03 (a) is in its Appendix 5), 25 pages, 211 table rows.
- `notebooks/13_cpmp_amendments.ipynb` (from `scripts/build_13_cpmp_amendments_nb.py`) → `cpmp_usdm_v2.json` (Step 3 JSON + 12 `StudyAmendment` on the one StudyVersion), `mapping_log_step4.csv`, `cross_layer_changes.csv`. Executes the setup, helper and code cells of notebook 12 unchanged. One `StudyChange` per table row (204): description → `summary`, brief rationale → `rationale`, section → `DocumentContentReference` (number and title by pattern, `appliesToId` = the amended document; each number checked against the Step 2 TOC).
- Decisions: D1 all amendments on the one StudyVersion; D2 `primaryReason` not coded in the documents, left out and logged; D3 new file, Step 3 unchanged; D4 "Throughout the protocol" rows kept, `sectionNumber` left out and logged.
- Validation: `python3 scripts/04_run_usdm_rdf_validator.py output_cpmp/step4/cpmp_usdm_v2.json output_cpmp/step4/validation https://kerfors.github.io/early-clinical-design-research/usdm/cpmp/`. 2,158 objects, 3,305 references, 0 dangling; 102 structural `MinCount` findings = the 55 of Step 3 + 47 logged in this step (`primaryReason` ×12, `StudyAmendment.geographicScopes` ×12, `GovernanceDate.geographicScopes` ×11, `sectionNumber` ×10, one `summary`, one `rationale`); terminology conforms.
- Run on this Mac (tesseract is now on the shell; rdflib, pyshacl, nbclient installed in `../.pydeps/`, excluded from git; `PYTHONPATH=../.pydeps/lib`). Test: script run twice, CSVs byte-identical; notebook executed with nbclient and its code cells run with plain Python, outputs byte-identical.

Observations (logged):

- The text layer is not always the printed page. CPMP p5: the section cell and the first description line of two "3.0 Objectives and Endpoints" rows are printed but not in the text layer; the OCR check found them (4 cells). Only the missing part is taken from OCR, checked visually. The reverse also occurs (NP03 p41, OA05 p5: glyphs not rendered, text layer complete).
- Redaction: 6 table rows hidden whole (CPMP 3, NP02 1, NP05 1, OA05 1); one BP05 row keeps its rationale ("Per regulatory feedback.") with the description redacted, so its `summary` is absent; bars inside the Overall Rationale of CPMP (one list item) and OA03.
- Tracked-change markup in BP05, NP05, OA05 §5.2: "have ~~completed~~ participated in" with the insertion underlined. The text layer keeps both words; a USDM string cannot say which is deleted.
- Section references and the TOC: 125 rows match a TOC entry, 39 match the number only (e.g. BP02/OA02 "5.1. Study Population", TOC 5.1 "Inclusion Criteria"), 30 are not in the TOC (OA03 prints no section numbers; CPMP level-4 sections and "3.0"), 10 have no number.
- Model (candidate breakpoints): `StudyAmendment` has no reference to the document or document version it produces; `number` ("a" for 11 amendments) identifies an amendment only within one document; `DocumentContentReference.appliesToId` points to the document, not the version.
- Cross-layer: 26 descriptions or rationales name another layer (`cross_layer_changes.csv`), e.g. CPMP (a) 1.3 "Vital sign procedures for these visits will be detailed in the ISAs" (delegation stated as the reason for a change), NP01 (a) "Covered by the master Protocol H0P-MC-CPMP". Two name the other layer's version: NP03 (a) and OA03 (a) §5.3 "Master protocol updates for CPMP amendment (a)", the first explicit version binding between CPMP layers.

**Step 5 – design components across the ISA grid** (`d67e9e8`, 2026-10-25). Two parts:

- `scripts/14_cpmp_design_text.py` → `output_cpmp/step5/eligibility_items.csv`, `table_cells.csv`, `section_redactions.csv` and the long tables `criteria.csv`, `objectives_endpoints.csv`, `interventions.csv`. Reads eligibility criteria, the Objectives and Endpoints tables and the Study Intervention(s) Administered tables from the page layout (text and geometry functions of script 13; rules in the docstring). Four documents (BP02, NP02, OA02, OA05) carry their text layer in an invisible font, so bold (section and category headings) is read from the rendered page there. Redaction bars are items of their own: hidden criteria are counted, not filled.
- `notebooks/14_cpmp_components.ipynb` (from `scripts/build_14_cpmp_components_nb.py`) → `grid.csv`, `components.csv`, `crosswalk_proposals.csv`, `cq1_`–`cq4_*.csv`. Identity: same text after whitespace is collapsed; a weaker `template` key replaces the document's own compound code, ISA number and disease name. Grid class per component from the documents it occurs in (master, compound column, disease row, single ISA, other). Content common across a disease row is not called DSA content.
- Run: `python3 scripts/14_cpmp_design_text.py`, then build and execute the notebook.

Results:

- Grid: read from each ISA's §5 sentence ("The master protocol CPMP and OA DSA CPMP(1) provide eligibility criteria … LY3016859 specific inclusion and exclusion criteria are listed here."); 12 ISAs, 4 compounds × 3 disease states.
- Criteria: 121 (master 32; ISAs 3–17 each), plus 27 statements and 23 redaction bars (BP02, BP05, NP02, NP05, OA02, OA05). ISA criterion numbering = disease digit (1 OA, 2 CLBP, 3 DPNP) × 1000 + compound block (00 LY3016859, 25 LY3556050, 50 LY3526318, 75 LY3857210); tested against the §5 grid, holds for all 12. Same number is not the same criterion (OA01 inserts [1003] hyaluronic acid injection, shifting its numbers); identity comes from the text.
- Objectives and endpoints: master 1 primary + 13 secondary endpoints; ISA objectives in the LY3016859 and LY3526318 ISAs only. The tables of all LY3556050 and LY3857210 ISAs are redacted whole (`section_redactions.csv`; also one bar in the master table, p27).
- Interventions: 146 attribute values in 12 ISAs, 17 redacted (dosage levels 9, unit dose strengths 8; LY3526318 ISAs 4 each, LY3556050 ISAs 1–2 each). The LY3526318 intervention sections also have a redaction bar.
- Components: 166 (84 criteria, 21 endpoints, 10 objectives, 51 intervention attributes): master 51, compound column 33, compound column (part) 21, single ISA 52, other 9. No disease-row class occurs. One criterion crosses compound columns: "Women who are pregnant or breastfeeding." word-identical in the LY3526318 and LY3857210 ISAs (class other); all other ISA criteria worded the same in more than one document stay within one compound column.
- Disease-specific content inside ISAs: OA01 [1003] hyaluronic acid; NP01 megaloblastic anaemia or combined degeneration of the spinal cord; NP03 six criteria under "Additional Considerations for Participants Taking Metformin" and a metformin exception in [3034].
- Shared stated reasons (CQ4, from Step 4): 40 brief rationales occur in more than one document; 39 within one compound column, 1 includes the master.
- Crosswalk proposals: 115 pairs (81 `similar` at difflib ratio ≥ 0.85, 34 `same_slot`); nothing merged here. Decided later in `../cpmp-design-modules/sources/crosswalk_decisions.csv`.
- Not done: USDM `StudyDesign` per ISA (set aside 2026-10-25; the design modules build took over).
- Not done: joining the 13 CPMP schedules from soa2usdm-collections into the CPMP Study (open, not started).
