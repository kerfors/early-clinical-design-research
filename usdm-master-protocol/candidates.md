# Alternative public master protocols (search 2026-10-24)

Why: the CPMP DSA layer is not public (see README). We need a master protocol where all document layers are posted.

Method: CT.gov API sweep (master protocol / platform / ISA / RSA / sub-study terms, plus "master protocol" etc. filtered to records with a posted protocol), then the documents themselves were downloaded and their front pages read. 158 records with posted protocols were screened.

## Candidates checked against the documents

| | REMAP-CAP | Lilly CWMM (LY900038) | HEALEY ALS | RECOVER (NIH) |
|---|---|---|---|---|
| Source | remapcap.org (current + "Superseded Protocol Documents" page, 65 PDF links, not yet de-duplicated) | CT.gov large docs | CT.gov large docs | CT.gov large docs + trials.recovercovid.org |
| Layers posted | Core Protocol V4.1 (29 May 2026); Patient, Pathogen and Disease Appendix (PANDA) V1; 10 Domain-Specific Appendices (interventions nested in domains); 6 Region-Specific Appendices; Statistical Analysis Appendix V4; Registry Appendix | Master W8M-MC-CWMM amendment (d), 12-Dec-2025 (NCT06143956); ISAs OXA1 (b), LAA1 (b), GN02 | Master Protocol (NCT04297683, posted 2024-10-14); Regimen-specific appendices A–G | 5 platform protocols + appendices; several appendices have only ICF posted |
| Number of layers | 3 (Core → PANDA → domain appendix), plus region and statistical overlays | 2 (master → ISA) | 2 (master → regimen) | 2 (platform → appendix) |
| Redaction | none found | master: 108 CCI markers | none found | not checked |
| Text layer | clean | GN02 ISA image-only (75 of 76 pages); master 19 near-empty pages | master is image-only (83/83 pages, needs OCR); Regimen F image-only | not checked |
| Registration | one NCT (NCT02735707) for the whole platform | master + each ISA own NCT (as CPMP) | master + each regimen own NCT | platform + each appendix own NCT |
| Layer relation statements | e.g. "as specified in the Core Protocol" (28 references to Core Protocol in the Corticosteroid DSA) | Lilly template, as CPMP | e.g. "Refer to NCT04297683 for the … Master Protocol document" (Regimen G cover) | not checked |

## Notes for choice

- **REMAP-CAP is the only one with three public layers.** The mapping to CPMP is not one-to-one:
  - REMAP-CAP "DSA" means *Domain*-Specific Appendix and holds the interventions (closest to an ISA). CPMP "DSA" means *Disease-State* Addendum.
  - PANDA defines patient, pathogen and disease categories that domains use for eligibility and analysis strata (Core §2.2.2). It is closest to the CPMP disease layer, but it is shared by all domains, not one document per population.
  - A participant can be randomised in several domains at once (multifactorial). That is a different stress on USDM than CPMP's one-ISA-per-participant-at-a-time.
  - Region-Specific Appendices and the site checkboxes in each domain appendix (which interventions a site selected) add a site/region variation layer that CPMP does not have.
- **Lilly CWMM** uses the same Lilly ISA template as CPMP and has a current master version, but only two layers and a heavily redacted master.
- **HEALEY** is clean and complete for two layers, but the master needs OCR.

Downloaded files are in the cloud scratch area only; not copied here until a candidate is chosen.
