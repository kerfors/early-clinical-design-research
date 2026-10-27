# CPMP design modules

The Lilly Chronic Pain Master Protocol (CPMP) as a small OWL ontology of design modules that build on and reuse each other: master, disease state, compound, and compound × disease state (the ISA). Not a document model; USDM (`../usdm-master-protocol/output_cpmp/`) stays the document carrier.

Everything is generated from the Step 5 and Step 2 tables in `../usdm-master-protocol/output_cpmp/` and from three CT.gov records. Nothing is hand-typed.

## Agreed scope and decisions (2026-10-25)

| # | Decision |
|---|---|
| 1 | ROBOT (ODK conventions) for merge, profile check and classification (ELK); Python/rdflib generates the modules. Runs in the cloud workspace. |
| 2 | First build: criteria, objectives, endpoints. Intervention attributes (51 components, partly redacted) are not built. |
| 3 | "Women who are pregnant or breastfeeding" (6 ISAs, two compound columns) stays in each ISA module, flagged (`sharingClass` "other"); no fifth module (after the 2026-10-26 decisions: all 12 ISAs, see finding 8). |
| 4 | Crosswalk: only pairs decided "merge" in `sources/crosswalk_decisions.csv` are merged (decided 2026-10-25 for the 0.97–1.00 band: 34 pairs merged, 3 kept apart; 2026-10-26 for the 0.85–0.97 band and the low-ratio same-slot pairs: 51 merged, 27 kept apart, patterns P1–P8 in the `note` column). Review table: `scripts/06_crosswalk_review.py`; sensitivity: `scripts/03_crosswalk_sensitivity.py`. |
| 5 | OA07, BP07, NP07 placed from their CT.gov records (`sources/ctgov/`). |
| 6 | fepixnebart (CHEBI_758046, BioPortal synonym of LY3016859) not used: not document content. |
| 7 | Namespace `https://kerfors.github.io/early-clinical-design-research/cpmp-design-modules/`. |
| 8 | Schedule: one component per SoA cell (activity × visit) from the CPMP SoA join, same sharing rule as the criteria. |
| 9 | Overrides as master defaults: master cells overridden in an ISA are left out of the master definition (OWL is monotonic). |
| 10 | Activity identity from the SoA join's crosswalk (16 proposed equivalences); the join's own sensitivity run (case/typography only) found the compound columns unchanged. |
| 11 | ISAs with no documents inherit the master defaults, annotated "default assumed, no document". |
| 12 | Lab panel content ("tests unique for this ISA") is not built. |
| 13 | Slots split by rule into content gaps and role statements (`slotKind`): a sentence that describes the DSA's role ("specific study elements", "determines what DSA") names no content. |

## Layout

```
modules/
  cpmp-core.ttl            authored classes and annotation properties; imports upstream_import
  master.ttl               MasterDesign (defined class), 51 components, 8 delegated slots
  disease-{OA,CLBP,DPNP}   stubs: is about the upstream term, has part the slots, content not public
  compound-LY*.ttl x4      defined class over the compound-column components
  isa-{doc}.ttl x12        ISA design: asserted under master + disease state; has part its own components
  isa-{OA07,BP07,NP07}     registered ISAs with no documents: master + disease state only
  cpmp-all.ttl, catalog-v001.xml
imports/upstream_import.ttl, upstream_terms.csv    ROBOT MIREOT extract
queries/*.rq                                        competency questions
notebooks/01_cq_check.ipynb                         SPARQL answers checked against pandas
output/                                             build log, hierarchy, CQ results, sensitivity
sources/ctgov/*.json                                CT.gov records (NCT07641517, NCT07641504, NCT07285018)
sources/soa_statements.csv                          SoA delegation, override and addition statements with text (scripts/05)
sources/upstream/MANIFEST.csv                       pinned OBI, MONDO, HP (URL, version IRI, sha256); .owl git-ignored
```

## Upstream terms (checked through BioPortal, 2026-10-25)

| Use | Term | Source release |
|---|---|---|
| every design | clinical study design OBI_0500001 | OBI 2026-07-27 |
| criteria | eligibility / inclusion / exclusion criterion OBI_0500026 / 0500027 / 0500028 | OBI |
| objectives | objective specification IAO_0000005 | OBI |
| endpoint, slot parent | directive information entity IAO_0000033 | OBI |
| relations | has part BFO_0000051; is about IAO_0000136 | OBI |
| SoA cells, schedule slots | action specification IAO_0000007 (definition source NCIt C132349 "Schedule of Activities") | OBI |
| OA | osteoarthritis MONDO_0005178 | MONDO 2026-10-06 |
| CLBP | Low back pain HP_0003419 (gap: phenotype term, no "chronic"; MONDO has no CLBP) | HP 2026-09-01 |
| DPNP | diabetic neuropathy MONDO_0006626 (gap: covers peripheral and/or autonomic; no "painful") | MONDO |

Not found: an endpoint class in OBI or IAO; LY3526318, LY3556050, LY3857210 in ChEBI or NCIt.

## Authored terms

- `cpmp:EndpointSpecification` ⊑ IAO_0000033 (definition source NCIt C25212 "End Point").
- `cpmp:DelegatedSlot` ⊑ IAO_0000033; slots from section 5 are also ⊑ eligibility criterion.
- One class per component (⊑ inclusion criterion, exclusion criterion, objective specification or endpoint specification) and one design class per module. Every authored class has an upstream ancestor (checked in `scripts/02_reason.py`; 148 classes).
- Annotation properties: `delegatesTo`, `dependsOn`, `moduleRole`, `contentStatus`, `sharingClass`, `textIdentical`, `occursIn`, `upstreamGap`, `compoundStated`, `diseaseStated`, `evidence*`, `note`. `delegatesTo` and `dependsOn` link classes to classes, so they are annotation properties (keeps OWL 2 DL), not object properties as first proposed.

## Rules

- **Component identity** = Step 5 key (template text with `{compound}`, `{disease}`, `{isa}`). Not the criterion number. The sharing class is recomputed from the documents and must equal Step 5's, or the build stops.
- **Module of a component**:
  - master class → master module;
  - compound column → compound module;
  - single ISA, compound column (part), other → each ISA it occurs in.
- **Master design and compound designs** are defined classes: clinical study design ⊓ has part some C, for each component.
- **ISA designs** are asserted ⊑ master design and ⊑ their disease-state design, with the ISA §5 sentence as axiom annotation. They have part every component of their own document; each has-part axiom carries document, number, page and verbatim text. **The compound design is inferred, not asserted.**
- **Disease-state designs** ≡ clinical study design ⊓ is about the upstream term. They have part the slots. `contentStatus` is "not public", since DSA CPMP(1)–(3) are cited but not posted.
- **Delegation**:
  - A master component whose own text says "will be specified in the ISAs" or "as described in the DSA / disease state addenda" delegates to the ISA or disease-state designs (3 components).
  - The master's other DSA delegation sentences (Step 2) become slots: 8 after excluding the §10.7 abbreviation list (Step 2 false positive) and the two objectives tables already carried by components, and merging one sentence repeated in 1.1 and 4.1.1.
  - Slots whose sentence also names the ISA delegate to the ISA designs too (4).
- **ISA → DSA references** (Step 2 `refers_to`, 117 sentences) are `dependsOn` axioms with the sentence, section and page.
- **Registered ISAs with no documents.** Membership: secondary ID H0P-MC-CPMP in the CT.gov record. Disease: the abbreviation in the brief summary. Compound: the non-placebo intervention.

- **Schedule:**
  - One component per SoA cell (activity key × visit), from `../cpmp-soa-join/output/layered_grid.csv` (commit `9ee4b8a`, collection `cf9541d`).
  - Master cells go to the master module.
  - A restated cell stays a master cell; the ISA's has-part is annotated "restated".
  - Other ISA cells follow the criteria rule: cells in all three ISAs of one compound, and in no ISA of another compound, go to the compound module. All others stay in each ISA.
- **Master defaults:**
  - The three master ED cells (NRS for pain, PGI, rescue medication reporting) that the LY3016859 ISAs override ("not needed for ED per the CPMP SoA") are outside the MasterDesign definition.
  - The other 9 ISAs have part them. OA01, BP01 and NP01 carry `overrides` with the sentence. OA07, BP07 and NP07 have part them as "default assumed, no document".
  - The master protocol does not call these cells defaults.
- **Overrides on activities not in the master SoA** (WOMAC, RMDQ, BPI at ED) point at the disease-state design. "CPMP SoA" there must include non-public content.
- **Master SoA delegations** become 9 schedule slots of the master design, delegating to the ISA designs: post-randomization ECG, Hematology, Chemistry, Lipid panel, Urinalysis, TSH, HbA1c, Exploratory biomarker samples, and "Visits after V7".
- **Stated additions** ("in addition to schedule described in …", LY3857210) are annotations on the ISA's has-part axioms.
- "Post randomization" lies inside V3 and is not modelled; that needs a timing anchor.

Every rule application is in `output/build_log.csv`.

## Run

```
ROBOT_JAR=/path/to/robot.jar python scripts/00_extract_upstream.py   # needs sources/upstream/*.owl, checked against MANIFEST.csv
python scripts/01_build_modules.py
ROBOT_JAR=/path/to/robot.jar python scripts/02_reason.py              # merge, DL profile, ELK, hierarchy
python scripts/03_crosswalk_sensitivity.py 0.97 1.0
python scripts/04_build_notebook.py                                   # then execute notebooks/01_cq_check.ipynb
python scripts/05_extract_soa_statements.py                           # Mac shell: needs git and soa2usdm-collections at cf9541d
python scripts/06_crosswalk_review.py 0.97 1.0                         # review table, decision column for Kerstin
```

ROBOT 1.9.8 (sha256 `6f518b02…`).

## Results (`output/cq_results.csv`; all checks pass against pandas)

| Question | Answer |
|---|---|
| Reasoner: inferred compound design = compound in ISA §5 | 12 of 12; no ISA under a second compound. OA07, BP07, NP07: no compound design |
| CQ1a disease-independent by module | 77 components (master 51, compound 26) |
| CQ1b disease-independent by occurrence | 80: CQ1a plus three criteria shared across compounds: the pregnancy exclusion (all 12 ISAs), the reproductive pointer to each ISA's Section 10.2 (LY3016859, LY3526318), eGFR < 30 (LY3526318, LY3857210) |
| CQ2 what a new ISA inherits (OA07/BP07/NP07) | 51 master components + 8 disease-state slots; nothing from a compound |
| CQ3 ISA-specific components | 41 (single ISA 11, compound column (part) 6, other 24). Same set within the column: BP02/NP02/OA02 and BP05/NP05/OA05 (all three), BP03/OA03: they differ only in the disease-state module |
| CQ4 delegation to a module with no public content | 2 master endpoints (physical functioning "as described in the DSA") + 8 slots, each to all three disease-state designs. Of the slots, 4 name content (age, stratification, discontinuation data, additional SoAs) and 4 are role statements |
| CQ4b ISA sentences that depend on the DSA | 117 (most in §5, §8, §9, §1.1, §1.3) |
| CQ5 what schedule a new ISA inherits | 148 master cells + 9 schedule slots + 3 master defaults ("default assumed, no document") |
| CQ6 overrides | 12: 9 on master defaults (NRS, PGI, rescue medication at ED in OA01/BP01/NP01); 3 on WOMAC/RMDQ/BPI, pointing at the disease state (not public) |
| CQ7 compound schedule modules | LY3016859 50, LY3526318 0, LY3556050 26, LY3857210 33 cells. With restated master cells and cross-compound cells this reconciles exactly with the join's compound columns (95/57/81/95) |
| CQ8 delegated activities filled by ISAs | 6 of 8 activities, 255 ISA cells; TSH and Exploratory biomarker samples have no ISA cell (join finding 5) |

## Findings

1. The four-module reading holds under classification. The compound module has no document. It is recovered by the reasoner from the components the three ISAs of a compound share, and agrees with the compound named in each ISA §5 for all 12.
2. A new ISA (LY4065967 in OA, CLBP, DPNP) inherits the master and a disease-state module whose 8 slots have no public content. Its compound module cannot exist from public sources.
3. After all crosswalk decisions (2026-10-25/26), the LY3526318 and LY3857210 ISAs are identical in all three disease states, and BP03/OA03 an identical pair. What still separates designs in a column is disease content (NP03: 7 criteria on metformin, diabetes medication, lactic acidosis; OA01 hyaluronic acid; NP01 megaloblastic anaemia) or an abbreviation variant in an objective and an endpoint (BP01 "PK and PD", "IV" against NP01/OA01 "pharmacokinetics and pharmacodynamics", "intravenous"). Step 5 proposed crosswalk pairs for criteria only, so these two were never reviewed.
4. The 0.97–0.999 crosswalk band is not only text-layer variants (`output/crosswalk_sensitivity_0.97-1.00.csv`, 37 proposals → 13 groups):
   - 7 groups would move criteria into compound modules;
   - 1 case-only pair ("are" / "Are men or women …") would take the reproductive criterion out of two compound modules and make it cross-compound;
   - 1 pair is a different threshold: eGFR < 70 (BP01) against < 60 (BP03/NP03/OA03).

   The groups need review one by one, not by band. Decided 2026-10-25 (`sources/crosswalk_decisions.csv`): 12 groups merged, the eGFR < 70 / < 60 group kept apart. In group 6, OA03 lacks an "and" before "must agree"; it was read as the same requirement and logged.

5. In the SoA, 71 of the 185 ISA cells are marked in ISAs of more than one compound but not in the master. 22 of them are in all 12 ISAs: post-randomization Chemistry, ECG and HbA1c, PK samples V3–V7 and ED, vital signs V3–V7, physical examination, urine pregnancy at V3. This is a de facto common schedule that no document states. It is much larger than the single criterion of its kind ("Women who are pregnant or breastfeeding").
6. LY3526318 has no compound schedule module: every cell its ISAs mark is shared with ISAs of other compounds. Its compound design is still found from its criteria, objectives and endpoints.
7. Overrides need defaults. In OWL an ISA under the master design cannot lose a master cell, so a cell any ISA overrides cannot sit in the master definition. Its status as a default is read from the ISA, not from the master.
8. The pregnancy exclusion is one component in all 12 ISAs, worded three ways ("Women who …", "are women who …", and "are pregnant or breastfeeding" under "Other Exclusions" in the LY3556050 ISAs), and in no master text: the master says only that reproductive and contraceptive requirements "will be specified in the ISAs". A common exclusion every ISA states and no document states as common, the criterion counterpart of the 22 common SoA cells (finding 5).
9. eGFR exclusions are one rule with three values by compound: < 70 (LY3016859), < 60 (LY3556050), < 30 (LY3526318, LY3857210), same formula and visits. Text identity keeps them apart; "same rule, different value" needs a parameterised criterion (open below).

## Open for Kerstin

- Whether the 71 cross-compound schedule cells (finding 5) should form a module of their own ("common across ISAs"), as the 22 in all 12 ISAs suggest, or stay in each ISA as now.

- Crosswalk: all proposed pairs decided (2026-10-26). Not proposed by Step 5, so not reviewed: the BP01 objective and endpoint abbreviation variants (finding 3).
- A parameterised criterion (e.g. eGFR exclusion with threshold < 30 / < 60 / < 70 by compound) instead of text identity, so "same rule, different value" is explicit.
- Intervention attributes (decision 2) and override statements (none at component level in Step 5).
- Landscape note section (handoff point 6).
