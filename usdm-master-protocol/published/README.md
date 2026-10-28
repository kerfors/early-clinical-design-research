# USDM v4 files without the section text

The most complete USDM v4.0.0 file of each case, with the whole-section text replaced, so the files can be
published and loaded into other tools:

- `cpmp_usdm_v2_without_text.json`: the Lilly Chronic Pain Master Protocol (CPMP) as one Study with 13 documents
  (master and 12 intervention-specific appendices), their versions and approval dates, section numbers and
  headings, and the 12 amendments with 204 changes, each pointing at the amended section. Built in Step 4.
- `remapcap_usdm_v3_without_text.json`: REMAP-CAP Core Protocol 4.0 and 4.1 (two study versions), the Patient,
  Pathogen and Disease Appendix and the Corticosteroid domain-specific appendix: document structure, section
  numbers and headings, eligibility criteria, objectives, endpoints, arms and interventions. Built in Step 6.

Written by `../scripts/20_usdm_without_text.py` from the files in `../output_cpmp/step4/` and
`../output_remapcap/step6/`, which are not published. The only change: every `NarrativeContentItem.text` and every
`StudyIntervention.description` is replaced by "[Section text not published here; see the source document.]".
Everything else is as built; the script checks that nothing else differs.

Validated with the usdm-rdf validator (`../scripts/04_run_usdm_rdf_validator.py`), as the originals: the structural
findings (missing required attributes, each logged in the mapping logs) are the same, row for row
(`validation_cpmp/`, `validation_remapcap/`).

Not in these files: a schedule of activities (CPMP's 13 schedules are in
[soa2usdm-collections](https://kerfors.github.io/soa2usdm-collections/collections/cpmp/protocols/index.html)), and
biomedical concepts. The CPMP study design was set aside; its design content is in `../../cpmp-design-modules/`.

Source documents: CPMP as posted on ClinicalTrials.gov; REMAP-CAP as posted on remapcap.org. They remain under
their owners' terms. The files here are derived from them and are not endorsed by the sponsors.
