# Evidence matrix

Direction note step 3: requirement × case × finding × document evidence, generated from the committed outputs of
`remapcap-design-modules/`, `cpmp-design-modules/`, `cpmp-soa-join/`, `usdm-master-protocol/` and the
soa2usdm-collections `cpmp` collection at `cf9541d` (SoA page per activity). All inputs are read only.

## Agreed 2026-10-26

- One row per piece of evidence; a finding has as many rows as it has evidence.
- Authored, reviewed by Kerstin: `sources/requirements.csv` (8 requirements) and `sources/findings.csv` (36 findings: one line, requirement, expected value as recorded in the builds' READMEs and status notes).
- Generated: every evidence row, by one selector per finding in `scripts/01_build_matrix.py`. Nothing in a row is typed.
- Check: each selector's observed value must equal `expected`. `*` marks a finding first counted here (RC-8, CP-12): the observed value is recorded and evidence rows must exist. A mismatch stops the build.
- Evidence kinds: *instance* (a sentence, item or cell), *count* (a number a build computed), *absence* (what was searched and where, with result zero).
- No CDISC/SDTM mapping.

## Columns (`output/evidence_matrix.csv`)

`requirement`, `case`, `finding_id`, `finding`, `evidence_kind`, `role` (what the row shows: parent statement, child response, occurrence, ...), `doc`, `section`, `page`, `text` (verbatim, whitespace collapsed), `scope` (the trials, DSAs or component the row applies to), `source_file`, `source_key`, `status` (document fact, rule-derived, analyst-reading, decision by Kerstin).

Page: from the source row. For REMAP-CAP rows with a section but no page, the page of the same sentence in step 1 cross-references, else the section's page range ("a-b (section)"). Rows with no single location (crosswalk pairs, counts, absences, unanswered delegations) have no page.

## Results (first build, 2026-10-26)

36 findings, all pass; 1,930 evidence rows. Finding statements reviewed with Kerstin 2026-10-26 (15 reworded, CP-11 split into CP-11a and CP-11b). `output/findings_checked.csv` has expected and observed per finding.

| requirement | CPMP | REMAP-CAP |
|---|---|---|
| R-ANCHOR | 5 | 0 |
| R-COMMON | 354 | 152 |
| R-DECISION | 243 | 11 |
| R-DOCSET | 3 | 223 |
| R-GAP | 141 | 219 |
| R-ID | 143 | 143 |
| R-LAYER | 49 | 14 |
| R-VERSION | 26 | 204 |

Row counts measure how much evidence a selector returns, not how strong a finding is.

Corrections made while building (from the documents):
- RC-18: the IAV appendix heading "APPENDIX 1: REGION-SPECIFIC MODIFICATIONS FOR JAPAN" has no number in the text layer and sits inside section 13 (References); only 14.1–14.2.2 are numbered. Expected value changed from "section 14".
- RC-20: REMAP-CAP is not silent on versions: 11 version-history sections give version, approving body and date, and no reason.
- CP-13: 2 of 26 CPMP cross-layer amendment texts name a master version (NP03(a), OA03(a): "Master protocol updates for CPMP amendment (a)").

Review of readings, 2026-10-27 (records in `../remapcap-design-modules/sources/reading_reviews.csv` and `inheritance_reviews.csv`):
- RC-6 reworded: whether the no-control-arm default applies is *not evaluated* (rule S-control leaves it to a trial-design reviewer); the 9 rows were labelled "ambiguous". The label in `rc6()` changed with it.
- RC-17 reworded: DSA 8.1 points at "Core Protocol documents"; the definitions are in PANDA, and whether PANDA is part of that set is not stated.
- Counts and evidence rows unchanged; 36 of 36 pass.

## Run

```
SOA2USDM_COLLECTIONS=/path/to/soa2usdm-collections python scripts/01_build_matrix.py
```

The script checks that soa2usdm-collections is at `cf9541d`.
