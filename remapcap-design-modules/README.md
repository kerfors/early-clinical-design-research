# REMAP-CAP design modules

Option B of the design-modules work: the method of `../cpmp-design-modules/` applied to REMAP-CAP, to test whether it generalises beyond one sponsor's template, and to add version binding (Core Protocol 4.0 / 4.1).

This README is the agreement record.

## Sources

The 20 current documents on remapcap.org (checked 2026-10-25), the same set as `../usdm-master-protocol/sources/remapcap/manifest.csv` (retrieved 2026-10-24). Core 4.0 is from the superseded listing.

No current DSA names a Core version: "Core Protocol Version n" occurs in none of the 10 current DSAs. All refer to "core protocol documents" without a version.

## Decisions (2026-10-25)

1. **Scope.**
   - Core 4.0 and 4.1, PANDA 1.0, and four DSAs:
     - Corticosteroid 6 (5 Nov 2024);
     - Antibiotic 4 (5 Nov 2024);
     - Tropical Antibiotic 1 (22 Apr 2026);
     - Influenza Antiviral 4 (5 Oct 2026, the only DSA issued after Core 4.1).
   - Extend to all 9 PANDA-era DSAs if the extraction rules hold. Done 2026-10-26: see "Nine PANDA-era DSAs".
   - Out of scope:
     - COVID-19 Antiviral (II), ASCOT: another template lineage, predates Core 4.0, never cites PANDA;
     - the RSAs (2019–2021);
     - the Statistical Analysis Appendix and Registry Appendix: candidates for a later master-layer extension.
2. **Component unit.**
   - Kinds of component:
     - domain-specific eligibility criteria;
     - interventions, with availability per stratum and state;
     - endpoints;
     - data-collection variables;
     - allocation parameters, as statements with value and source section.
   - A DSA is one factor, not a whole design. Regimens across domains are not enumerated, because the documents do not state them.
3. **Version representation.**
   - One module per Core version, each with an `owl:versionIRI`.
   - A component with identical section text in both versions keeps one IRI.
   - A changed component gets a version-independent parent class, with one revision subclass per version.
   - DSA statements carry the cdd v0.2 binding: bound / unversioned / noStatement.
   - Issue dates are an annotation only, never used to choose a revision.
4. **Home.**
   - This folder, with its own scripts.
   - Upstream imports and ROBOT settings are referenced from `cpmp-design-modules/` by path and sha256.
   - Shared machinery is factored out only after both builds work, as a separate proposal with a diff.
5. **Competency questions** R1–R7 (see "Competency questions").
6. **"Core Protocol documents"** is used by all four DSAs and defined nowhere.
   - The Core 4.1 glossary calls PANDA, each DSA and each RSA "an appendix to the Core Protocol".
   - It is modelled as a document-set individual with **no asserted membership**.
   - Each statement that points at it gets a separate, logged resolution to a specific section, as an `analyst-reading`. Example: DSA §8.1 Age Strata resolves to PANDA §2.
7. **A domain is a subclass of OBI_0000750 *study design independent variable*.** Its interventions are its values. If OBI has no value property, BFO_0000051 *has part* is used and logged.
8. **Endpoints stay under IAO_0000033, as in CPMP.** OBI_0000751 *study design dependent variable* is recorded as a later change to both builds, to make after the comparison, with a diff.
9. **Biological Sampling Appendix** (named in Core 4.1 §2.2, not posted). It becomes a stub module only if a Core or DSA statement delegates content to it. Otherwise it is recorded as a named, unposted layer with no module.

## Upstream terms (BioPortal, 2026-10-25)

Pinned releases as in CPMP: OBI 2026-07-27, MONDO 2026-10-06.

- MONDO_0024355 *respiratory tract infectious disorder*
- MONDO_0005249 *pneumonia*
- MONDO_0005812 *influenza*
- "community-acquired": no exact term in MONDO, NCIt or HP. Authored as a PANDA §4.1 category.
- OBI_0500001, OBI_0500026/27/28, IAO_0000005, IAO_0000033: as in CPMP.
- OBI_0000750 for the domain (decision 7).
- IAO_0000007 *action specification* for an intervention.
- Strata and states, data-collection variables and allocation parameters: authored under IAO_0000033. OBI has no stratification term or data-item term.

## Competency questions

| CQ | Question |
|---|---|
| R1 | Which components occur in all DSAs in scope but in no Core or PANDA section? |
| R2 | What does a DSA inherit from Core + PANDA before it states anything? Compared with what Tropical Antibiotic 1 states. |
| R3 | Which DSA pairs share components beyond Core? |
| R4 | Which Core delegations get no answer in a DSA? Which are circular? Which resolutions leave the Core? |
| R5 | Which Core defaults does a DSA take, override, or make state-dependent? |
| R6 | Which DSA statements depend on Core components that changed in 4.1? Grouped by binding kind, with both revisions. |
| R7 | For DSAs issued before 4.1 and still current, which unversioned statements now resolve to changed content? Does Influenza Antiviral 4 bind differently? |

## Step 1: sections and cross-layer statements

`scripts/01_extract_structure.py` applies the Plan 1 Step 2 rules (`../usdm-master-protocol/scripts/build_02_remapcap_structure_nb.py`, copied, not imported) to the seven documents.

It is generalised only in three places:
- running-header pattern, one per document;
- self reference, per DSA;
- layer rank by layer (Core 4.0 and 4.1 both rank 0).

The Core 4.1 TOC omits 7.6.3 and 7.6.4. They are split off from 7.6.2 by heading text, with Plan 1 Step 5's rule.

- **Gate 1:** Core 4.0, PANDA and CS_DSA reproduce Step 2 `sections.csv` and `cross_references.csv` cell for cell.
- **Gate 2:** Core 4.0 against 4.1 gives Step 5's 15 changes: 13 changed sections, plus 7.6.3 and 7.6.4, new in 4.1.
- All TOC headings were found in all seven documents.
- The `mention_only` sentences of the three new DSAs were read. They are §2 template boilerplate and authorisation lines; no inheritance wording is missed.

Observed:
- §8.1 of every DSA says the Age Strata and Illness Severity States are "defined in Core Protocol documents". They are defined in PANDA §2 and §4.3.
- Antibiotic and Tropical Antibiotic: Adult stratum, Severe State only.
- Corticosteroid and Influenza Antiviral: Paediatric, Adolescent and Adult strata; Moderate or Severe State.

Outputs: `output/step1/sections.csv`, `cross_references.csv`, `headings_not_found.csv` (empty), `run.log`.

Run from this folder: `python3 scripts/01_extract_structure.py` (pandas, pypdfium2).

## Step 2: components

`scripts/02_extract_components.py` cuts components from the sections mapped to component kinds (DSA §8.1–§10.8; Core 7.4.1, 7.4.2, 7.6.1–7.6.3, 7.8.7, 8.8.2; PANDA §2–§4.4). It uses line positions (`pdftotext -bbox-layout`), because the collapsed section text does not show where a list item ends.

Rules (the rule applied is logged per item):
- **R-row:** only the body band 60 < y < 775 is read. Lines on one row (|Δy| ≤ 4 pt) are joined in x order, so a bullet glyph and its text form one row.
- **R-glyph:** a list glyph (•, ●, ▪, ■, ◦, ☐, ☒, o) opens an item. Its level is the rank of the glyph's x, with positions within 3 pt counted as one level. The glyph is kept, because ☒ vs ☐ in an intervention list may carry meaning: IAV_DSA 8.3.1 checks "No antiviral agent", which all sites must offer.
- **R-number:** `n. ` (single integer) opens an item (Core numbered lists).
- **R-cont:** a line right of the item's glyph continues the item.
- **R-margin:** a line at the body margin ends the list. The body margin is the most frequent line x in the document, 72 pt in all seven.
- **R-group:** a line equal to an unnumbered TOC entry of the document is a group heading for the items after it (Core 8.8.2 "Inpatient data", …).
- **R-table:** a `Table n:` caption ends the list.
- **R-sentence:** section text outside list items is split into sentences (step 1 rule) as statement components.

Outputs:
- `output/step2/components.csv`: 269 items, none empty;
- `statements.csv`: 396 sentences;
- `section_text.csv`;
- `header_rows_in_band.csv`: 3 front-matter footers;
- `run.log`.

Known residue: Core 4.1 7.6.3 is not in its TOC, so its sub-heading "Respiratory Infection Ordinal Weighted Score" is not recognised and stays in the last 7.6.3 item.

Observed:
- Core 8.8.2 Post-discharge outcome data has 7 items in 4.0 and 6 in 4.1.
- RAR cap: 60% (Core 4.0 7.8.7) and 75% (Core 4.1 7.8.7), both "unless otherwise specified in a DSA".
- CS_DSA 10.3 and IAV_DSA 10.3 use the same unversioned sentence: the cap "specified in core protocol documents". IAV_DSA 4 was issued after Core 4.1.

## Upstream import

`scripts/00_extract_upstream.py` is the CPMP extract with the REMAP-CAP term list. It reads the sha256 of OBI and MONDO from `../cpmp-design-modules/sources/upstream/MANIFEST.csv` and checks the pinned files against them. ROBOT 1.9.8 (sha256 `6f518b02…`, same as CPMP), MIREOT.

- Output: `imports/upstream_import.ttl` (1900 triples, 13 terms) and `imports/upstream_terms.csv`. The labels read from the pinned files agree with BioPortal.
- ROBOT's Turtle output is not byte-stable (blank-node labels). A rerun is checked by graph isomorphism, not by file hash.
- Run where the pinned OWL files are: `ROBOT_JAR=… UPSTREAM_DIR=… python3 scripts/00_extract_upstream.py`. Run in the cloud workspace, 2026-10-25.

Decision 7 check: OBI has OBI_0001938 *has value specification*, whose range is *value specification*. A REMAP-CAP intervention is an action specification, so a domain *has part* (BFO_0000051) its interventions.

## Step 3: component identity

`scripts/03_identity.py`:

- **I-exact:** identity is the text with whitespace collapsed. Case and punctuation are kept.
- **I-revision:** Core 4.0 against 4.1, per section and group. Ratio ≥ 0.85 makes a revision pair with a version-independent parent. A tie stops the script.
- **I-move:** a 4.0 text found word for word in 4.1 under another section is "moved". It is the same component.
- **I-review:** near matches (ratio 0.85–0.999) whose **document sets are disjoint** go to `crosswalk_review.csv` with an empty decision column. A document holding both texts is evidence of two components, not of variants of one.

Results:
- 665 occurrences, 487 components. 159 components occur in more than one document.
- Core 4.0 against 4.1: 86 same, 7 moved, 4 revised, 15 only in 4.0, 31 only in 4.1.
- **Gate:** the changed sections (7.6.1, 7.6.2, 7.6.3, 7.8.7, 8.8.2) equal the step 1 changed sections among the mapped Core sections.
- Moved:
  - five parts of the 4.0 primary endpoint (the ordinal scale) went from 7.6.1 to 7.6.3 *Exploratory outcomes*;
  - two definitions went from 7.6.2 to 7.6.1.
  
  So an endpoint's role (primary / secondary / exploratory) belongs to its occurrence in a module, not to the component.
- Revised:
  - 7.8.7 RAR cap, 60% → 75%;
  - 7.6.2 the sentence on DSAs dated before the amendment;
  - 7.6.1 high-flow oxygen definition;
  - 8.8.2 inpatient data window.
- Crosswalk: 46 pairs, no case-only pairs. Many are substantive (24 vs 48 h, 28 vs 90 days, ICU vs hospital, doses), so review is per pair. Until decided, the build uses exact identity only.

Step 2 fix found here: HTML entities are now decoded with `html.unescape`. Two sentences changed (`&apos;`).

## Step 4: modules and reasoning

`scripts/04_build_modules.py` generates the modules from the step 3 tables. Every rule application is in `output/build_log.csv`.

| File | Content |
|---|---|
| `rcap-core.ttl` | authored classes (each with an upstream parent) and annotation properties |
| `components.ttl` | 487 component classes, 4 revision parents |
| `about.ttl` | is_about axioms on inclusion items (B-about) |
| `core.ttl` | `CoreDesign`, version-independent: 93 stable components (86 same + 7 moved) + 4 revision parents |
| `core-4.0.ttl`, `core-4.1.ttl` | `CoreDesign_4_0` / `_4_1`, defined over each version's components, `owl:versionIRI` `core/4.0` and `core/4.1`, `dcterms:isVersionOf` `core` |
| `panda.ttl` | `PandaDesign`; `appendixTo CoreDesign` (annotation, Core 1.2 glossary) |
| `dsa-CS/AB/TAB/IAV.ttl` | `DomainDesign_X` ⊑ `CoreDesign` (asserted, `binding "unversioned"`); has part each component of its document, with evidence; `Domain_X` ⊑ `Domain` has part its §8.3.1 arms (☐/☒ kept) |
| `dsa-shared.ttl` | `SharedDSA_<set>`, defined for each set of ≥ 2 DSAs with components in no Core and no PANDA (7 sets) |

Rules:
- **B-parent:** parent by kind family; sentences are `DesignStatement`. The 3 organ-support items whose kinds span PANDA §4.3 and Core 7.6.1 go under IAO_0000033.
- **B-role:** an endpoint's role is annotated on the occurrence, not the component.
- **B-dsa:** evidence is the Core 1.2 glossary plus each DSA's own sentence "The Core Protocol contains all information that is generic to the trial …", located by exact text (E-locate: CS, AB, TAB and IAV; IAV's §2 is not a step 1 section).
- **B-domain:** a domain has part its arms through BFO_0000051. OBI_0001938's range is value specification, and an arm is an action specification.
- **B-shared:** shared modules are derived from the data. No document states these groupings, so their classification is not an independent test, unlike CPMP's §5 compound check.

Step 1 defects found here, none in a mapped section:
- IAV's TOC prints no top-level numbers in its text layer, so its §1, §2, §5 and §7 are not step 1 sections.
- IAV's 6.2.5 TOC line has no dot leaders, so 6.2.5 and 6.2.6 merge.

Decision 9: the Biological Sampling Appendix is named in Core 2.2 and 2.2.6 ("describes the strategy for biological sampling at participating sites"). No statement delegates content to it, so it has no module.

`scripts/05_reason.py` (ROBOT 1.9.8): merge, OWL 2 DL profile check, ELK. `output/inferred.ttl`, `profile.txt`, `design_hierarchy.csv`; `merged.ttl` is git-ignored and reproducible.
- In profile; consistent; 519 authored classes, each with an upstream ancestor.
- **`CoreDesign_4_0` and `CoreDesign_4_1` are both inferred ⊑ `CoreDesign`.**
- **No DSA design is inferred under either Core version.** Each sits only under the version-independent `CoreDesign`: the unversioned binding, made visible by classification.
- Each DSA design is inferred under the `SharedDSA` classes for its sets (by construction).

Run (Mac shell, from the repo root):
```
PYTHONPATH=.pydeps/lib python3 remapcap-design-modules/scripts/04_build_modules.py
PYTHONPATH=.pydeps/lib ROBOT_JAR=$PWD/.tools/robot.jar python3 remapcap-design-modules/scripts/05_reason.py
PYTHONPATH=.pydeps/lib python3 remapcap-design-modules/scripts/06_build_notebook.py   # then execute notebooks/01_cq_check.ipynb
```

The notebook's last cell writes `output/cq_results.csv` (question, answer, check), one row per query, only after every check has passed (added 2026-10-27; read by the competency-question catalogue).

## Step 2 fix and crosswalk decisions (2026-10-25)

**Table text** (`02_extract_components.py`, diff reviewed by Kerstin):
- The caption "Table 4: Organisms of interest …" was also an entry in the TOC's list of tables, so R-group took it as a group heading. The table rows then became sentences: crosswalk pairs #27 and #45 were table residue.
- Now: TOC table and figure captions are not group headings. R-table puts the caption, the rows and the table notes (margin lines starting with `*`) into `section_text.csv` `table_text`.
- Prose at the margin after a table ends the table, and a table breaks the section text, so no sentence runs across it.
- Effect: 269 items, unchanged. Statements 396 → 389:
  - table residue in AB/TAB §8.3.2 and §8.5.2 removed;
  - the §8.3.2 dosing lead-in ("… as follows:") and the sentence after the tables ("It is permitted to provide these antibiotics via intermittent, prolonged, or continuous infusion.") are separate statements.
- Four tables are in `table_text`: AB Tables 3–4, TAB Tables 5–8.

**Decisions:** `sources/crosswalk_decisions.csv`. One row per review pair, keyed by its two component IDs, with group, decision, status, reason, decider and date. Kerstin decided from the information-architecture side; Claude gave a reading per pair with reasons.

| Group | Pairs | Decision |
|---|---|---|
| A, wording only (punctuation, typo, article, case, abbreviation, synonym) | 27 | merge |
| B, substantive (threshold, population, drug, dose rule, trigger list, default vs not, opposite statement, CRRT added) | 12 | keep apart |
| C, same wording, different target: "Core Protocol documents" (set) vs "the Core Protocol" | 2 | keep apart |
| D, same definition in PANDA 4.3 and a Core 7.6.1 footnote ("nasal" only in PANDA); cross-layer duplication recorded | 2 | keep apart |
| E, needs a clinical reading ("one or more" vs "one or both"; "antibiotic therapy" vs "the allocated intervention") | 2 | keep apart, tentative, pending a clinical reader |

**I-decide** (`03_identity.py`, diff reviewed by Kerstin):
- Applied after the review, which stays on exact identity. The script stops unless every review pair has a decision row and every row is a review pair.
- Merged components keep one ID (the member in most documents, then the smaller ID) and their variant wordings (`components_index.csv` `variant_texts`, `occurrences.csv` `component_exact`). Each document keeps its own wording as has-part evidence.
- A Core 4.0-only and 4.1-only row of one merged component become one `moved` row: #05, the ordinal-scale item "…high-flow oxygen*" in 4.0 7.6.1 and without the marker in 4.1 7.6.3.
- Result: 27 merge pairs → 22 merged components; 481 → 456 components. Core 4.0/4.1: 86 same, 8 moved, 4 revised, 14 only in 4.0, 30 only in 4.1.

**R-hyphen** (`02_extract_components.py`, diff reviewed by Kerstin, 2026-10-25):
- A line ending in "word-" is joined to the next line without a space, unless the next word is *and / or / to* (suspended hyphen).
- 13 texts changed, all line-end splits ("pre- specified", "non- invasive", "all- cause", …).
- Found because Core 7.6.2 "DSAs dated before this Core Protocol amendment will additionally report the pre-specified endpoints …" was a false revision: 4.1 had "pre- specified". It is now one stable component in both versions.
- Its wording is identical, but its referent is not: "this Core Protocol amendment" is the version that contains it (reading, step 5).
- Decision #22 was re-keyed by the same rule (note column); the decision is unchanged.
- Core 4.0/4.1 now: 87 same, 8 moved, **3 revised** (RAR cap, high-flow oxygen definition, 8.8.2 inpatient window), 14 only in 4.0, 30 only in 4.1. 455 components; 95 stable Core components. R1 and R3 are unchanged.

## Competency questions answered so far (crosswalk decided)

`notebooks/01_cq_check.ipynb` runs `queries/*.rq` over `output/inferred.ttl` and checks every answer against pandas. A mismatch stops the notebook.

Classification is unchanged in shape: OWL 2 DL, ELK consistent, 486 authored classes with an upstream ancestor. Core 4.0 and 4.1 are inferred ⊑ `CoreDesign` (95 stable components + 3 revision parents). No DSA design is under either Core version.

| CQ | exact | decided | all pairs merged (upper bound) |
|---|---|---|---|
| R1 all four DSAs, no Core, no PANDA | 5 | **12** | 17 |
| R3 AB–TAB | 52 | **58** | 64 |
| R3 CS–IAV | 14 | **24** | 28 |
| R3 CS–AB | 12 | **18** | 22 |
| R3 CS–TAB | 11 | **17** | 22 |
| R3 AB–IAV | 8 | **17** | 21 |
| R3 TAB–IAV | 6 | **15** | 21 |

- **R1 (decided):** 12 components every DSA states and no Core or PANDA text does, in any of their wordings. By kind: domain eligibility 4, interactions with other domains 2, the equivalence and odds-ratio delta thresholds 2, and data collection, discontinuation, strata and secondary endpoints 1 each. A shared DSA layer that no document states, like CPMP's common SoA cells. The odds-ratio delta may be in the Statistical Analysis Appendix (out of scope).
- **R3:** AB–TAB is the strongest pair under every identity. The other pairs flatten under the decisions (15–24), so beyond the antibiotic pair the ranking depends on the crosswalk.
- **R6, module level:**
  - Every DSA inherits the 3 revised Core components only as version-independent parents: the RAR cap 60%/75%; the high-flow oxygen definition; the 8.8.2 inpatient data window. (The 7.6.2 transition sentence was a false revision, see R-hyphen.)
  - 8 components moved, each with a role change: six parts of the 4.0 primary endpoint (the ordinal scale) are exploratory in 4.1, and two 7.6.2 definitions moved to 7.6.1.
  - 44 Core components are in one version only.

Answered by the step 5 part 1 readings: R6 at statement level and R7 (below). By the part 2 readings: R4, R5 (below). By both: R2 (below).

## Step 5 part 1: inheritance readings (reviewed by Kerstin, 2026-10-25)

Scripts: `07_inheritance_readings.py` (resolution), `08_version_readings.py` (R6/R7 consequences), `09_readings_module.py` (`modules/readings.ttl`). Run order now `02 → 03 → 04 → 09 → 05 → 06`; `07` and `08` before `09`.

- **Statements:** every DSA → Core / PANDA / SAA statement in step 1 that is not mention-only: 62 (CS 21, AB 13, TAB 13, IAV 15).
- **T-target:** "core protocol documents" → the document set (decision 6), 35 statements; "Core Protocol" → the document, 26; the SAA, 1.
- **T-topic:** `sources/topic_rules.csv`, in order, first match wins, all matches logged.
  - Rules 1–11 are the CS_DSA readings agreed 2026-10-24. **Gate:** they are reproduced for all 12 agreed sections.
  - Rules 12–14 are title rules, accepted by Kerstin 2026-10-25. The term must be in the target title: DSMB → 8.11, Funding → 2.5, "SAEs should be reported" → 8.12.3.
  - IAV 10.2 matches rules 1 and 7. First match (7.8.3, borrowing) agreed.
- **Result:** 53 resolved. 5 unresolved and **left unresolved** (Kerstin): SAE "as defined" (CS, AB, TAB 8.5.2), the shock definition (CS 10.2), the reveal timing (CS 10.4). 3 version-scoped. 1 SAA (out of scope).
- **Binding:**
  - No statement names a Core version (unversioned).
  - The three §2 statements "The current version of the Core Protocol … is listed on the study website" are a floating pointer stated outright: `current (study website)`.
- **V-date:** document dates from each document's running header: Core 4.1 2026-05-29; CS and AB 2024-11-05; TAB 2026-04-22; IAV 2026-10-05.
- **V-current:** an unversioned statement resolves to Core 4.1.
- **V-transition:** Core 4.1 7.6.2 "DSAs dated before this Core Protocol amendment will additionally report the pre-specified endpoints as indicated in their respective documents and previous versions of the Core Protocol". "This amendment" is read as the containing version, "dated" as the header date. A DSA dated before Core 4.1 whose statement resolves to 7.6.1 or 7.6.2 resolves to 4.1 and, additionally, 4.0.
  - Accepted by Kerstin 2026-10-25 from the information-architecture side. What "additionally report" means for an analysis is for a trial-design reviewer.
  - The sentence is one component in both Core versions, annotated as referring to its own version.
- **Module:** one `InheritanceReading` (⊑ IAO_0000030) per statement, annotated with `readingOf`, `statement`, `resolvesToSection`, `dependsOn`, `targetPhrase`, `binding`, `resolvesToCoreVersions`, `sectionChangedIn41`, `rule`, `ruleSource`, `reviewStatus` and evidence.
  - **Coverage limit:** 33 readings link to their step 2 statement component (M-match), and 28 to the Core components of their target section.
  - The other 29 are statements in DSA sections not mapped to component kinds (§2, §7, §8.2, §10.1, §11, §12).
  - Six target sections are not mapped either (2.5, 7.8.3, 7.8.6, 8.6, 8.11, 8.12.3). These readings carry section and change status, without component links.

| DSA (date) | statements on Core sections changed in 4.1 (R6) | resolve to 4.1 only | 4.1 + 4.0 (R7, V-transition) |
|---|---|---|---|
| CS (2024-11-05) | 9 | 5 | 4 |
| AB (2024-11-05) | 4 | 2 | 2 |
| TAB (2026-04-22) | 4 | 2 | 2 |
| IAV (2026-10-05) | 8 | 8 | 0 |

**Finding:**
- The Core's transition rule protects the endpoints of DSAs dated before an amendment.
- Nothing protects their statistical parameters: triggers and stopping rules (7.8.6, 7.8.7), the RAR cap (7.8.7) and borrowing (7.8.3) resolve silently to 4.1.
- IAV, dated after Core 4.1, uses the same unversioned wording, so it will float again at the next Core amendment.

Both answers are SPARQL (`queries/r6s_statements_on_changed_core.rq`, `queries/r7_two_core_versions.rq`) checked against `output/step5/statement_versions.csv` in the notebook.

## Step 5 part 2: delegation and default readings (approved by Kerstin, 2026-10-25)

Scripts: `10_delegation_readings.py` (responses), `11_delegation_module.py` (`modules/delegations.ttl`). Run order now `02 → 03 → 04 → 07 → 08 → 09 → 10 → 11 → 05 → 06`.

- **Statements:** Core 4.1 → DSA, 15 `delegates` and 6 `default_overridable` (step 1), x four DSAs: 84 pairings.
- **Template map** (`sources/template_map.csv`, agreed 2026-10-25): each statement → a DSA template section by title key, resolved per DSA (numbers differ: Informative priors AB/TAB 10.9, IAV 10.10, CS none), plus a secondary section read only for a topic term.
  - Q1: Core 8 "Individual processes … in the relevant DSA documents" is an umbrella: recorded, not paired.
  - Q2: Core 8.6 (discontinuation of an *allocated intervention*) → DSA 8.3.x "Discontinuation of study intervention"; §9.3 (participation in the trial) is secondary.
  - Q3: Core 8.12.3 "trial endpoints … as specified in DSAs" is kept as a delegation in step 1 but read as descriptive, no slot.
  - Q4: AB 6.2.5 "All antibiotics used in CAP have a well-established safety profile" is merged into the 6.2.4 title in step 1 (logged, not fixed); the secondary section is matched on text.
- **Response rules** (`sources/response_rules.csv`): delegations no_answer / condition_not_stated (conditional rows) / fills_none / defers_back / fills_by_reference / fills; defaults silent / overrides / takes / ambiguous (modal "may" or no pattern). Negation wins over content in the same section (accepted for rows 19 and 21).
- **S-state:** the two-intervention defaults are answered per illness-severity state; arms from §8.3.1, an arm qualified "(X State only)" counts in X only, any other in every state of §8.1.2. Not exactly two arms → condition_not_met.
- **S-control:** "domains without a control arm" is not evaluated (trial-design question): ambiguous in all four.
- **V-core40:** the Core 4.0 sentence is carried; it differs for gamma (7.8.3) and the cap (60 % in 4.0, 75 % in 4.1).
- **Module:** one `DelegationReading` (⊑ IAO_0000030) per pairing plus 12 per-state readings (`refinesReading`, `state`, `armCount`).
  - **Coverage limit:** the Core statement links to a step 2 component for 7.6 and 7.8.7 only (8 pairings); the other Core sections carry no component kind. 36 pairings link to a DSA response component.
- **Comparison with the CS draft against Core 4.0** (`cdd-layer/output/cq2_pairing_draft.csv`): `output/step5/cq2_comparison.csv`.

| Response | CS | AB | TAB | IAV |
|---|---|---|---|---|
| fills | 4 | 9 | 9 | 8 |
| fills_by_reference | 3 | 0 | 0 | 1 |
| fills_none | 3 | 3 | 3 | 3 |
| no_answer / condition_not_stated | 3 | 1 | 1 | 1 |
| takes | 2 | 1 | 2 | 2 |
| overrides | 0 | 1 | 0 | 0 |
| silent | 2 | 3 | 3 | 2 |
| ambiguous | 2 | 1 | 1 | 2 |

**Findings:**
- No delegation is circular in its mapped section. All four DSAs' §9.3 refer back to the Core, but for participation in the trial. CS has no intervention-discontinuation section: Core 8.6 is unanswered there (revises cdd-layer session 1 finding 2).
- No DSA states separate triggers (Core 7.8.6): condition not stated in all four. CS states no informative priors.
- The balanced-allocation defaults (7.5.2) are silent in all four DSAs.
- Two-intervention defaults apply in two state-domains only: CS Moderate (RAR "may be applied": ambiguous; the cap is taken by an unversioned reference) and TAB Severe (RAR not applied: takes; the cap is silent, so 75 % applies with no word in the DSA). AB states RAR, but has four arms.

Both answers are SPARQL (`queries/r4_unanswered_delegations.rq`, `queries/r5_defaults.rq`) checked against `output/step5/delegation_readings*.csv` in the notebook.

## R2: what a DSA inherits before it states anything (2026-10-25)

From the modules and both sets of readings (`queries/r2a_inherited_by_kind.rq`, `r2b_slots_and_defaults.rq`, `r2c_tab_by_kind.rq`, `r2e_per_dsa.rq`), checked against pandas in the notebook. Core 4.1 by V-current.

- **Before it states anything, a DSA receives:**
  - 219 components from Core 4.1 and PANDA 1.0 (222 component-kind pairs): Core platform eligibility 8, endpoints 56, the RAR cap section 34, generic data collection 30; PANDA categories 94 (3 components in both).
  - 6 overridable defaults, which hold while it is silent.
  - 13 slots (paired delegations; 5 conditional), plus the umbrella (Core 8) and the descriptive Core 8.12.3 sentence.
  - Core content in sections with no component kind (7.8.3, 7.8.6, 8.6, 8.11, 8.12.3, 2.5) is inherited too, but only as sections.
- **Tropical Antibiotic 1 states:** 75 components, none of them a Core 4.1 or PANDA component (no verbatim restatement). 59 also occur in another DSA, 16 in TAB only: 7 interventions, 5 intervention exclusions, a nesting statement, an RAR statement, a domain inclusion criterion, a data collection item.
- **TAB points at** (13 inheritance statements: 11 resolved, 1 unresolved, 1 version-scoped) 109 of the 222 inherited pairs, through 6 of the resolved statements: all platform eligibility, all primary and secondary endpoints, 6 exploratory (the 4.0 primary-endpoint parts reached through V-transition), the RAR cap section, PANDA patient and illness-severity categories. The other 5 resolved statements point to sections without components (8.6, 7.8.6, 8.11, 8.12.3, 2.5).
- **TAB answers** the 13 slots: fills 9, fills_none 3, condition not stated 1 (separate triggers). The 6 defaults: takes 2 (primary outcome; no RAR, Severe State, two arms), silent 3 (both balanced-allocation defaults; the 75 % cap), ambiguous 1 (no control arm).

**Finding:** 113 of the 219 inherited components are reached by no TAB statement (corrected 2026-10-25 from 101, which left out the exploratory endpoints):
- the 30 Core 8.8.2 generic data-collection variables (TAB 9.2 says only "Additional domain-specific data will be collected", an extension with no pointer);
- the 12 Core 4.1 exploratory endpoint components (7.6.3; TAB's endpoint statements resolve to 7.6.1 and 7.6.2);
- 71 PANDA categories (pathogen, pathogen stratum, clinical feature, acquisition, disease entity).

No TAB sentence takes or rejects them; they reach TAB only as Core and PANDA content. With the 3 silent defaults, that is the part of TAB's design no TAB sentence states.

**R2e, all four DSAs:**

| DSA | components | restate Core 4.1 / PANDA | inherited reached | inherited not reached | silent defaults |
|---|---|---|---|---|---|
| CS | 86 | 0 | 106 | 113 | 2 |
| AB | 95 | 0 | 106 | 113 | 3 |
| TAB | 75 | 0 | 106 | 113 | 3 |
| IAV | 67 | 0 | 100 | 119 | 2 |

No DSA restates a Core 4.1 or PANDA component. In every DSA the same 71 PANDA categories are unreached; the Core part differs only for IAV (48 against 42).

## Nine PANDA-era DSAs (2026-10-25/26)

Scope extended (decision 1) to Macrolide Duration 4 (MD), COVID-19 Immunoglobulin 4 (IG), Mechanical Ventilation 2 (MV), Endothelial Modulation 2 (END) and Influenza Immune Modulation 2.1 (IIM), all from `usdm-master-protocol/sources/remapcap/manifest.csv` (sha256 checked; no download). Only IAV (5 Oct 2026) is dated after Core 4.1 (29 May 2026); the other eight are under the §7.6.2 transition rule.

**Steps 1–3** (commit `fedc9a1`; template map `dd243b9`):
- Step 1, R-outline: an unnumbered TOC entry gets its level from the title's x position and a counted number (log `output/step1/reconstructed_numbers.csv`). MV has no section numbers in its text layer; MD lacks level-2 numbers; END, IIM and IAV lack level-1 numbers. Side effects: the AB 6.2.5 heading split is fixed; IAV 55 → 69 sections.
- Step 2: DSA component kinds by title key (parent title, title); gate: equal to the number kinds for CS, AB, TAB, IAV.
- Step 3: crosswalk pairs 47–142 decided with Kerstin (52 merge, 40 keep apart, 4 tentative: #31, #33 statistical reader; #91, #92 clinical reader). 745 → 688 components.
- Template map row 1 (Core 2.2.6): `exact:Microbiology`. IG and MV have no Microbiology section.

**Decisions (2026-10-26):**

17. **Topic rules 15–18**, applied to all nine DSAs (`sources/topic_rules.csv`):
    - 15 "Severe State" → PANDA 4.3 (END, IIM 8.1.2);
    - 16 "Immediate Reveal" / "Deferred Reveal" → Core 7.8.3, which defines both (Core 8.3 cites "7.8.3.4", a level-4 heading that is no step 1 section);
    - 17 "Statistical Triggers and Platform Conclusions" → Core 7.8.6; 7.8.7 (MV 10.3.1);
    - 18 "SAE as defined" → Core 8.12.2 *Definitions* (8.5.2 lists, MD 9.2.1).

    Rules 16 and 18 also resolve four statements left unresolved under decision 13 (CS 10.4; CS, AB, TAB 8.5.2). Left unresolved, with the decision date, in `sources/left_unresolved.csv` (checked by `09`): CS 10.2, MV 10.3.8 (no section to point at), END 10.8 (see below).
18. **One shared document definition**, `scripts/rcap_docs.py`, for `04`, `06`, `08`, `09`, `10`, `11`. Version and issue date are read from each document's header ("Version n Dated …"; IG writes "dated"). `01` and `02` keep their own tables. The PANDA title literal follows its header: "Patient, Pathogen and Disease Appendix 1" (was "1.0"). The query `VALUES` lists stay; the notebook asserts that they, and the R1 count, equal `DSAS`.
19. **B-shared scope:** `SharedDSA_*` classes only for pairs and for all DSAs in scope, the shapes R3 and R1 ask about (module building only as far as the queries need). R2c stays the four-DSA TAB case; R2e covers all nine.

**Results** (commit `cfcebc1`; all checked against pandas in the notebook; analyst readings):

| DSA | components | R2e reached | R2e not reached | silent defaults | R6s statements on changed Core | R7 4.1 only | R7 4.1 + 4.0 |
|---|---|---|---|---|---|---|---|
| CS | 86 | 106 | 113 | 2 | 10 | 6 | 4 |
| AB | 95 | 106 | 113 | 3 | 4 | 2 | 2 |
| TAB | 75 | 106 | 113 | 3 | 4 | 2 | 2 |
| IAV | 67 | 100 | 119 | 2 | 8 | 8 | 0 |
| MD | 52 | 106 | 113 | 3 | 5 | 2 | 3 |
| IG | 65 | 106 | 113 | 3 | 5 | 2 | 3 |
| MV | 64 | 106 | 113 | 4 | 3 | 1 | 2 |
| END | 76 | 106 | 113 | 2 | 7 | 4 | 3 |
| IIM | 96 | 106 | 113 | 2 | 8 | 5 | 3 |

- **R1:** 4 components in all nine DSAs and in no Core or PANDA text (12 over the four): the clinician-belief domain exclusion, one other domain exclusion, the discontinuation refer-back, the interactions statement.
- **R3:** AB–TAB 58 remains the strongest pair, END–IIM 26 next; the other 34 pairs share 7–24.
- **R2e:** no DSA restates a Core 4.1 or PANDA component.
- **R4:** separate triggers unanswered in all nine; discontinuation no answer in CS, IG, MV; MV also gamma and unit of analysis (no answer) and informative priors; IG and MV domain-specific sampling.
- **R5:** balanced-allocation defaults silent and "no control arm" ambiguous in all nine. Two-intervention defaults live in CS Moderate, TAB, IG (both states), END, MD, MV. "No RAR": takes TAB, IG; overrides MD; ambiguous CS Moderate, END; silent MV. RAR cap: takes CS Moderate, END; silent TAB, IG, MD, MV.
- **§8.1** "as defined in Core Protocol documents" (defined in PANDA) holds in all nine DSAs.
- **END 10.8** points at "the relevant Core Protocol documents" for the equivalence odds ratio delta; Core 4.1 7.8.6 states it specifies no default equivalence trigger and that the margin is specified in individual DSAs. Statistical meaning for the trial-design reviewer.
- **Four-DSA results as a subset:** R1 over the four is still 12; readings differ only by the 4 from rules 16 and 18 and the 2 IAV §2 statements from the step 1 fix; delegation readings only by 5 evidence cells (step 1 fix). CS R6s/R7 9/5/4 → 10/6/4 (CS 10.4 → 7.8.3, changed in 4.1).
- **Logged, not fixed:** IIM 8.5.2 is one step 1 sentence for two (no full stop after "Core Protocol"), so its SAE pointer sits behind rule 9.

## Review of readings (2026-10-27)

Records: `sources/reading_reviews.csv` (the analyst readings behind RC-5, RC-6, RC-10 and RC-17, one row per evidence row) and `sources/inheritance_reviews.csv` (all 139 inheritance readings). Decisions by Kerstin. The catalogue build (`../competency-questions/`) checks that every reading has a review and that no reading has changed since.

- **Inheritance readings:** 64 (CS, AB, TAB, IAV) reviewed 2026-10-25; 75 (MD, IG, MV, END, IIM) reviewed 2026-10-27 by rule group, with a full-text search per DSA. 132 confirmed; 7 confirmed as unresolved by decision (§2 version and SAA pointers, MV 10.3.8, END 10.8).
- **Delegations (RC-5), five new DSAs:** absence readings checked by a full-text search of each DSA (references excluded). 11 confirmed, 3 open for a trial-design reviewer: MV 7.8.3 gamma and unit of analysis (10.3.1 borrowing across strata may partly answer it), 7.8.4 informative priors, 7.8.6 separate triggers (a preliminary phase with a fixed sample size, while 10.3.1 points at the Core triggers).
- **Row 16, discontinuation:** confirmed for all nine DSAs. Core 8.6 itself splits domain-specific criteria (DSA) from general criteria (Core), so DSA 8.3.x plus the 9.x pointer fits; "participation in this trial" against "allocated intervention" is the DSAs' imprecision.
- **Defaults (RC-6):** balanced allocation at domain start and for a new intervention, silent: confirmed (10). "No control arm" (rule S-control) is recorded as **not evaluated** for all nine DSAs, not as ambiguous: whether a domain has a control arm is a trial-design question.
- **Not changed:** the readings and the response labels in `output/step5/delegation_readings.csv`. The decisions are in the review files.
