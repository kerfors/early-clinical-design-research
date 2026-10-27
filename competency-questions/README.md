# Competency questions

Ten general questions, each with the case questions (SPARQL), findings, earlier questions and open questions
that answer it for CPMP and REMAP-CAP.

- Authored, reviewed by Kerstin: `sources/questions.csv` (question, requirements) and
  `sources/case_questions.csv` (what belongs under each question; review still pending and who it waits for).
- Generated: `output/catalogue.csv` and `output/catalogue.md`, by `scripts/01_build_catalogue.py`, from the
  committed outputs of the builds. Nothing in the catalogue is typed.
- Checks (the build stops): every finding placed once; every case query placed; every analyst reading of a
  reviewed finding has a review row; every REMAP-CAP inheritance reading has a review that matches it.

Run from the repo root: `python3 competency-questions/scripts/01_build_catalogue.py`
