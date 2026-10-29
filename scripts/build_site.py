"""Build the GitHub Pages site in docs/ from the committed catalogue and README.

Pages:
- docs/index.html: the README introduction (up to "## The questions"), then one card per area
  (questions, cases, templates) with counts from the data.
- docs/vision/index.html: VISION.md, linked from the landing page and the navigation.
- docs/questions/index.html: the README section "## The questions" (text before its table), then the
  ten questions as cards with, per case, the number of findings, case questions and open questions,
  and which reviewer still has readings to look at.
- docs/cases/index.html: the README section "## The two cases", then one card per case.
- docs/templates/index.html: the README section "## Templates as data", then one card per template family.
- docs/questions/<Q>/index.html: one page per question, the catalogue rows of that
  question by case, as in competency-questions/output/catalogue.md.
- docs/findings/index.html: the 36 findings by requirement (evidence-matrix/sources/requirements.csv,
  findings.csv), each with its observed value and check (evidence-matrix/output/findings_checked.csv) and its
  status and question (competency-questions/output/catalogue.csv).
- docs/modules/index.html: the design modules of both cases. Upstream terms (cpmp-design-modules and
  remapcap-design-modules imports/upstream_terms.csv; releases from cpmp-design-modules/sources/upstream/MANIFEST.csv),
  the gaps recorded in the module files (upstreamGap annotations; authored classes commented "Authored:"), the
  module files with their imports and the classes each declares (modules/*.ttl, read with rdflib), and the
  asserted and inferred memberships (output/design_hierarchy.csv).
- docs/examples/cp-11b/index.html: the README section "### One chain, end to end: CP-11b", one finding followed
  from the documents to the catalogue; linked from that finding's row on its question page and the Findings page.
- docs/cases/cpmp/index.html: the CPMP documents. The compound x disease grid of the 12 ISAs
  from usdm-master-protocol/output_cpmp/step5/grid.csv (read from each ISA's section 5);
  NCT ID, secondary ID and posted protocol (date, link) from the ClinicalTrials.gov records in
  usdm-master-protocol/sources/ctgov_api/cpmp_studies.json. The DSAs are not public: shown as
  dashed boxes, named only by disease. Records with a H0P-MC- secondary ID outside the grid are
  listed with what is posted for them.
- docs/cases/remapcap/index.html: the REMAP-CAP documents in scope (version and date as read
  from each document's header: remapcap-design-modules/output/documents.csv), the other current
  documents and the superseded listings on remapcap.org (usdm-master-protocol/sources/remapcap/manifest.csv).
- docs/usdm/index.html: the first round, USDM v4 as the carrier for both master protocols
  (usdm-master-protocol/): the five USDM files and what each step added, with the validator's own
  counts read from the committed executed validation notebooks; the mapping decisions per step from
  the mapping logs; the method with links to its scripts and notebooks; the breakpoint table
  (output_remapcap/step5/breakpoints.csv). The USDM JSON files themselves are not committed.
- docs/usdm/m11-cpmp/index.html, docs/usdm/m11-remapcap/index.html: each case's published USDM file as an ICH M11
  protocol, with a Protocol and a Deep-dive view (scripts/m11_page.py, from usdm-master-protocol/output_m11/
  <case>_m11.json written by usdm-master-protocol/scripts/21_m11_view.py); linked from the USDM page.
- docs/templates/remapcap-dsa/index.html: the DSA template REMAP-CAP uses but no document states,
  read from the headings of its nine DSAs (remapcap-design-modules/output/step1/headings.csv, no text):
  one row per title key found in two or more DSAs, one column per DSA with that DSA's section
  number(s); then the headings found in one DSA only.
- docs/templates/tpp/index.html: the four TPP templates and examples compared, from tpp-templates/output_tpp/:
  column models, labels shared across families, then per family its elements. FDA, PaVe-GT and NIH SEED are US
  government works and are shown with their prompts, guidance and example values; WOAH's terms do not allow its
  content to be copied by extraction tools, so only the structure of the WOAH template is shown (and kept).
- docs/templates/eupearl/index.html: the EU-PEARL templates as data, from eupearl-templates/output_eupearl/:
  the MPT and ISA side by side on the committed alignment (ISA-only sections placed after the ISA section
  they follow), the SAP and DMC heading trees, and the MPT and ISA field labels. Per section, the number of
  paragraphs of each text kind, not the text: the templates are copyright EU-PEARL Consortium (and
  TransCelerate for the CPT-based parts), with no open licence. A "show as data" switch reveals the keys.

Inputs (read only, all committed): README.md, competency-questions/sources/questions.csv,
competency-questions/output/catalogue.csv, evidence-matrix/sources/requirements.csv, and the
case inputs above. The build stops if any tracked file outside docs/ has uncommitted changes. Each page ends
with a provenance line: its input files, linked, and the last commit that changed them or this script. No
build time, so an unchanged input gives byte-identical pages. Commit the inputs first, then docs/.

Relative links in README.md and the catalogue point at files in the repo; on the site
they point at the same file on GitHub (main).

docs/ is generated; do not edit by hand.
Run:    python3 scripts/build_site.py   (from the repo root)
"""
import hashlib
import html
import json
import re
import shutil
import subprocess
from pathlib import Path

import markdown
import pandas as pd

import m11_page
import rdflib
from rdflib.namespace import OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
REPO = "https://github.com/kerfors/early-clinical-design-research"
BLOB = REPO + "/blob/main/"
SITE = "https://kerfors.github.io/early-clinical-design-research/"
SCRIPT = "scripts/build_site.py"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


dirty = git("status", "--porcelain", "--untracked-files=no", "--", ".", ":!docs")
assert not dirty, "uncommitted changes outside docs/; commit the inputs first:\n" + dirty

INPUTS = {
    "readme": "README.md",
    "questions": "competency-questions/sources/questions.csv",
    "catalogue": "competency-questions/output/catalogue.csv",
    "requirements": "evidence-matrix/sources/requirements.csv",
}
VISION = "VISION.md"
CPMP_INPUTS = {
    "grid": "usdm-master-protocol/output_cpmp/step5/grid.csv",
    "ctgov": "usdm-master-protocol/sources/ctgov_api/cpmp_studies.json",
}
RCAP_INPUTS = {
    "documents": "remapcap-design-modules/output/documents.csv",
    "manifest": "usdm-master-protocol/sources/remapcap/manifest.csv",
}
CTGOV_DOC = "https://cdn.clinicaltrials.gov/large-docs/{tail}/{nct}/{file}"
DISEASE_ORDER = ["OA", "CLBP", "DPNP"]
RDSA_INPUTS = {
    "headings": "remapcap-design-modules/output/step1/headings.csv",
    "documents": "remapcap-design-modules/output/documents.csv",
}
UMP = "usdm-master-protocol/"
USDM_FILES = [
    # case, step, file name, what the step added, mapping log, validation folder, building notebook
    ("REMAP-CAP", "Step 3", "remapcap_usdm.json",
     "Core 4.0, PANDA 1.0 and the Corticosteroid DSA 6 as three documents (Core childIds = PANDA, DSA); eligibility, objectives and endpoints, arms and interventions of the Corticosteroid domain; PANDA section text",
     "output_remapcap/step3/mapping_log.csv", "output_remapcap/step4", "notebooks/03_remapcap_usdm.ipynb"),
    ("REMAP-CAP", "Step 5", "remapcap_usdm_v2.json",
     "plus Core 4.1 as a new document version and StudyVersion 2 with a StudyAmendment",
     "output_remapcap/step5/mapping_log_step5.csv", "output_remapcap/step5/validation",
     "notebooks/05_remapcap_amendment_breakpoints.ipynb"),
    ("REMAP-CAP", "Step 6", "remapcap_usdm_v3.json",
     "plus the section text of Core 4.0, Core 4.1 and the Corticosteroid DSA 6 as NarrativeContent",
     "output_remapcap/step6/mapping_log_step6.csv", "output_remapcap/step6/validation", "notebooks/06_remapcap_narrative.ipynb"),
    ("CPMP", "Step 3", "cpmp_usdm.json",
     "one Study with 13 documents (master childIds = the 12 ISAs; the three DSAs logged as not public), document versions with approval dates, the section text of all 13 as NarrativeContent",
     "output_cpmp/step3/mapping_log.csv", "output_cpmp/step3/validation", "notebooks/12_cpmp_usdm.ipynb"),
    ("CPMP", "Step 4", "cpmp_usdm_v2.json",
     "plus the 12 amendments, one StudyChange per row of each Summary of Changes table, pointing at the amended section",
     "output_cpmp/step4/mapping_log_step4.csv", "output_cpmp/step4/validation", "notebooks/13_cpmp_amendments.ipynb"),
]
NOT_CARRIED = {
    "REMAP-CAP": "no schedule (REMAP-CAP has no schedule tables); no biomedical concepts",
    "CPMP": "no study design (set aside 2026-10-25: the design content went into cpmp-design-modules); "
            "no schedule (the 13 SoAs are in soa2usdm-collections); no biomedical concepts",
}
BREAKPOINTS = UMP + "output_remapcap/step5/breakpoints.csv"
RAW = "https://raw.githubusercontent.com/kerfors/early-clinical-design-research/main/"
PUBLISHED = [UMP + "published/cpmp_usdm_v2_without_text.json", UMP + "published/remapcap_usdm_v3_without_text.json"]
M11_CASES = {"cpmp": "CPMP", "remapcap": "REMAP-CAP"}
M11_PAGE = "scripts/m11_page.py"
M11_REVIEWED = UMP + "sources/m11_breakpoint_links.csv"
M11_STATUS = [("one", "one value"), ("several", "several values"), ("not-checked", "values, a condition not run"),
              ("filtered-out", "the condition finds nothing"), ("none", "no value in the file"),
              ("section-rule", "protocol text"), ("unmapped", "no mapping"), ("no-element", "no M11 element")]
USDM_METHOD = [
    ("Read the documents",
     "Table of contents, headings and section text from the PDF text layer; for CPMP, letter-spaced pages with word "
     "boundaries from OCR aligned line by line, and section numbers from the printed body heading. The cross-layer "
     "statements (\"as specified in the Core Protocol\", \"will be specified in the DSA\") by phrase rules, with "
     "direction and overridable defaults.",
     ["scripts/10_cpmp_page_text.py", "notebooks/02_remapcap_structure.ipynb", "notebooks/11_cpmp_structure.ipynb"]),
    ("Map to USDM v4.0.0",
     "Model and controlled terminology pinned from usdm-rdf (DDF-RA v4.0.0). A value only where the document states "
     "it; a required attribute with no source is left out and logged; one mapping-log row per decision, with evidence. "
     "Structure decisions by Kerstin, recorded in the README.",
     ["notebooks/03_remapcap_usdm.ipynb", "notebooks/12_cpmp_usdm.ipynb"]),
    ("Validate",
     "The usdm-rdf validator notebook, run unchanged: references, structural SHACL shapes, terminology. Every "
     "structural finding is checked against the absences the mapping logged.",
     ["scripts/04_run_usdm_rdf_validator.py"]),
    ("Amendments",
     "REMAP-CAP: Core 4.1 as a second study version, with a section-level diff of 4.0 and 4.1. CPMP: the Summary of "
     "Changes tables read cell by cell, with rules and redaction bars from the rendered page and every cell checked "
     "against OCR.",
     ["notebooks/05_remapcap_amendment_breakpoints.ipynb", "scripts/13_cpmp_amendment_tables.py",
      "notebooks/13_cpmp_amendments.ipynb"]),
    ("Section text", "One NarrativeContent per numbered section, in document order.",
     ["notebooks/06_remapcap_narrative.ipynb"]),
    ("Breakpoints",
     "What the mapping logs marked not expressible, or possible only by copying or convention, collected with evidence.",
     ["notebooks/05_remapcap_amendment_breakpoints.ipynb"]),
]
EUP_DIR = "eupearl-templates/output_eupearl/"
EUP_INPUTS = {
    "sections": EUP_DIR + "sections.csv",
    "alignment": EUP_DIR + "mpt_isa_alignment.csv",
    "fields": EUP_DIR + "field_labels.csv",
    "structure": EUP_DIR + "eupearl_structure.json",
}
EUP_KINDS = ["instruction", "common", "suggested", "example", "sample", "guidance", "field_label"]
EUP_RATIONALE = "https://doi.org/10.1186/s13063-024-08034-8"
EUP_FLAGS = ["refers_to_master", "extends_master", "either_location"]
TPP_DIR = "tpp-templates/output_tpp/"
TPP_INPUTS = {
    "elements": TPP_DIR + "tpp_elements.csv",
    "column_models": TPP_DIR + "tpp_column_models.csv",
    "inventory": TPP_DIR + "tpp_label_inventory.csv",
    "crosswalk": TPP_DIR + "crosswalk_review.csv",
    "metadata": TPP_DIR + "tpp_source_metadata.json",
}
TPP_FAMILIES = ["FDA2007", "WOAH2026", "PAVEGT", "SEED"]
TPP_SEED = ["SEED_SMALL_MOLECULE", "SEED_BIOLOGIC", "SEED_VACCINE", "SEED_CGT"]
WOAH_TERMS = "https://www.woah.org/en/terms-and-conditions/"
KIND_ORDER = ["finding", "case question", "earlier", "open", "not asked"]
KIND_PLURAL = {"finding": "findings", "case question": "case questions"}
CASE_ORDER = ["CPMP", "REMAP-CAP", "both"]
REVIEWERS = ["trial-design reviewer", "clinical reader", "statistical reader"]

CSS = """
:root { --bg: #ffffff; --fg: #1d1d1f; --muted: #5f6368; --line: #dadce0; --link: #1a5fb4;
        --code: #f3f4f6; --card: #f8f9fb; --chip: #eef1f5; --wait: #8a5a00; --wait-bg: #fff4dc; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --bg: #16181c; --fg: #e8eaed; --muted: #9aa0a6; --line: #3c4043;
    --link: #8ab4f8; --code: #23262b; --card: #1d2025; --chip: #2a2e35; --wait: #f2c46d; --wait-bg: #3a2f17; }
}
:root[data-theme="dark"] { --bg: #16181c; --fg: #e8eaed; --muted: #9aa0a6; --line: #3c4043;
  --link: #8ab4f8; --code: #23262b; --card: #1d2025; --chip: #2a2e35; --wait: #f2c46d; --wait-bg: #3a2f17; }
* { box-sizing: border-box; }
body { background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0; }
main { max-width: 64rem; margin: 0 auto; padding: 1.5rem 1rem 3rem; }
a { color: var(--link); }
nav { font-size: 0.9rem; color: var(--muted); margin-bottom: 1rem; }
h1 { font-size: 1.6rem; margin: 0.2rem 0 0.6rem; }
h2 { font-size: 1.15rem; margin-top: 2rem; border-bottom: 1px solid var(--line); padding-bottom: 0.2rem; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.88rem; background: var(--code);
       padding: 0.05rem 0.3rem; border-radius: 3px; overflow-wrap: anywhere; }
.muted { color: var(--muted); font-size: 0.9rem; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr)); gap: 0.8rem; }
.cards.four { grid-template-columns: repeat(auto-fill, minmax(13rem, 1fr)); }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 6px; padding: 0.8rem 1rem; }
.card h3 { margin: 0 0 0.3rem; font-size: 1rem; line-height: 1.35; }
.card h3 a { text-decoration: none; }
.card .qid { color: var(--muted); font-weight: 600; margin-right: 0.3rem; }
.card p { margin: 0.3rem 0; font-size: 0.88rem; }
.chip { display: inline-block; background: var(--chip); border-radius: 3px; padding: 0 0.35rem; margin: 0 0.25rem 0.2rem 0;
        font-size: 0.8rem; white-space: nowrap; }
.wait { background: var(--wait-bg); color: var(--wait); }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 0.88rem; }
th, td { border-bottom: 1px solid var(--line); padding: 0.4rem 0.5rem; text-align: left; vertical-align: top; }
th { color: var(--muted); font-weight: 600; }
td.item { white-space: nowrap; }
td .chip { white-space: normal; }
tr.answered td:first-child { border-left: 3px solid var(--fg); }
tr.unanswered td:first-child { border-left: 3px dashed var(--muted); }
tr.unanswered td { color: var(--muted); }
main.wide, footer.wide { max-width: 84rem; }
.layer { display: grid; gap: 0.5rem; margin: 0.6rem 0 1.2rem; }
.box { border: 1.5px solid var(--fg); border-radius: 5px; padding: 0.45rem 0.6rem; font-size: 0.85rem; background: var(--card); }
.box.dashed { border-style: dashed; border-color: var(--muted); color: var(--muted); background: transparent; }
.box b { display: block; font-size: 0.92rem; }
.box .muted { font-size: 0.8rem; }
.grid4 { display: grid; grid-template-columns: 9rem repeat(4, minmax(7rem, 1fr)); gap: 0.5rem; align-items: stretch; }
.grid4 .head { font-size: 0.8rem; color: var(--muted); font-weight: 600; align-self: end; }
.dsa3 { grid-template-columns: repeat(auto-fill, minmax(13rem, 1fr)); }
.core2 { grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr)); }
.switch { position: sticky; top: 0; background: var(--bg); padding: 0.5rem 0; border-bottom: 1px solid var(--line);
          z-index: 2; font-size: 0.9rem; }
.key { display: none; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.75rem; color: var(--link);
       background: var(--code); border-radius: 3px; padding: 0 0.3rem; margin-left: 0.3rem; }
body.data .key { display: inline-block; }
.rel .key { overflow-wrap: anywhere; max-width: 100%; }
.chip.change { background: transparent; border: 1px solid var(--line); }
.side { display: grid; grid-template-columns: minmax(0, 1fr) 9.5rem minmax(0, 1fr); gap: 0.3rem 0.5rem; min-width: 46rem; }
.side .colhead { font-size: 1.05rem; color: var(--fg); font-weight: 700; padding-bottom: 0.2rem; }
.side .box { font-size: 0.82rem; }
.side .rel { font-size: 0.75rem; color: var(--muted); align-self: center; }
.side .empty { border: 1.5px dashed var(--line); border-radius: 5px; }
th.area { text-align: left; background: var(--card); font-size: 0.85rem; }
td.num { text-align: right; white-space: nowrap; }
table.matrix td.num { text-align: center; white-space: nowrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.8rem; }
table.matrix td.miss { border-left: 1px dashed var(--line); border-right: 1px dashed var(--line); }
table.matrix td.miss span { display: block; border: 1.5px dashed var(--line); border-radius: 3px; height: 1.1rem; }
table.matrix th.dsa { text-align: center; font-size: 0.8rem; vertical-align: bottom; }
table.matrix th .dname { font-weight: 400; font-size: 0.72rem; color: var(--muted); }
table.matrix td.title { min-width: 16rem; }
details.own summary { cursor: pointer; font-weight: 600; margin: 0.4rem 0; }
.lead { border-left: 3px solid var(--link); background: var(--card); padding: 0.6rem 0.9rem; margin: 1rem 0; }
.lv2 { margin-left: 0.8rem; } .lv3 { margin-left: 1.6rem; } .lv4 { margin-left: 2.4rem; }
.tree .box { margin: 0.25rem 0; }
.slotbox { border: 1.5px dashed var(--muted); border-radius: 3px; min-height: 1.6rem; padding: 0.15rem 0.4rem;
           font-size: 0.8rem; color: var(--muted); }
.fields { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 0.3rem 0.8rem; align-items: center; font-size: 0.85rem; }
@media (max-width: 40rem) { .fields { grid-template-columns: 1fr; } }
footer { max-width: 64rem; margin: 0 auto; padding: 0 1rem 2rem; color: var(--muted); font-size: 0.8rem; overflow-wrap: anywhere; }
@media (max-width: 40rem) { main { padding: 1rem 1rem 2rem; } }
"""


def sha256(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def repo_link(target):
    """A repo-relative path (optionally with ../ prefixes) as a GitHub link; other links unchanged."""
    if re.match(r"^[a-z]+:", target) or target.startswith("#"):
        return target
    path = re.sub(r"^(\.\./)+", "", target)
    assert (ROOT / path.split("#")[0]).exists(), f"link target not in repo: {target}"
    return BLOB + path


def md_to_html(text):
    text = re.sub(r"\]\(([^)]+)\)", lambda m: "](" + repo_link(m.group(1)) + ")", text)
    return markdown.markdown(text, extensions=["tables"])


def esc(x):
    return "" if pd.isna(x) else html.escape(str(x))


def provenance(paths):
    prov = "; ".join(f'<a href="{BLOB}{p}">{p}</a>' for p in paths)
    stamp = git("log", "-1", "--format=%h", "--", SCRIPT, *paths)
    return f"""Generated by <a href="{BLOB}{SCRIPT}">{SCRIPT}</a> from {prov}; inputs as of
commit <a href="{REPO}/commit/{stamp}">{stamp}</a>. Namespace for now:
<code>{SITE}</code>. Code MIT, derived content CC BY 4.0; headings, field labels and short quotations from the source
documents remain their owners'."""


def page(title, depth, body, wide=False, inputs=None):
    up = "../" * depth
    paths = inputs or list(INPUTS.values())
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<main{' class="wide"' if wide else ''}>
<nav><a href="{up}">Early clinical design research</a> · <a href="{up}questions/">Questions</a> · <a href="{up}findings/">Findings</a> · <a href="{up}modules/">Modules</a> · <a href="{up}cases/">Cases</a> · <a href="{up}usdm/">USDM</a> · <a href="{up}templates/">Templates</a> · <a href="{up}vision/">Vision</a> · <a href="{REPO}">repository</a></nav>
{body}
</main>
<footer{' class="wide"' if wide else ''}>{provenance(paths)}</footer>
</body>
</html>
"""


def status_chips(status):
    if pd.isna(status) or status in ("earlier", "open"):
        return ""
    return "".join(f'<span class="chip">{html.escape(s)}</span>' for s in status.split("; "))


def waits(review):
    return [r for r in REVIEWERS if not pd.isna(review) and r in review]


readme = (ROOT / INPUTS["readme"]).read_text(encoding="utf-8")
FINDINGS = "evidence-matrix/sources/findings.csv"
finding_line = {}
for i, ln in enumerate((ROOT / FINDINGS).read_text(encoding="utf-8").splitlines(), start=1):
    fid = ln.split(",", 1)[0]
    if re.fullmatch(r"(CP|RC)-\d+[a-z]?", fid):
        assert fid not in finding_line, fid
        finding_line[fid] = i
questions = pd.read_csv(ROOT / INPUTS["questions"], dtype=str)
cat = pd.read_csv(ROOT / INPUTS["catalogue"], dtype=str)
reqs = pd.read_csv(ROOT / INPUTS["requirements"], dtype=str).set_index("requirement")

assert list(questions.q_id) == [f"Q{i}" for i in range(1, 11)], list(questions.q_id)
assert set(cat.q_id) == set(questions.q_id), set(cat.q_id) ^ set(questions.q_id)
assert set(cat.kind) <= set(KIND_ORDER), set(cat.kind) - set(KIND_ORDER)
assert set(cat.case) <= set(CASE_ORDER), set(cat.case) - set(CASE_ORDER)
req_ids = {r for q in questions.requirements for r in q.split(";")}
assert req_ids <= set(reqs.index), req_ids - set(reqs.index)
title_line, intro = readme.split("\n", 1)
assert title_line == "# Early clinical design research", title_line
intro = intro.split("\n## The questions", 1)[0]
cases_md = readme.split("\n## The two cases\n", 1)[1].split("\n## ", 1)[0]
templates_md = readme.split("\n## Templates as data\n", 1)[1].split("\n## ", 1)[0]
EXAMPLES = {"CP-11b": "One chain, end to end: CP-11b"}
examples_md = {fid: readme.split(f"\n### {title}\n", 1)[1].split("\n## ", 1)[0] for fid, title in EXAMPLES.items()}
questions_md = readme.split("\n## The questions\n", 1)[1].split("\n## ", 1)[0].split("\n|", 1)[0]

if DOCS.exists():
    shutil.rmtree(DOCS)
(DOCS / "questions").mkdir(parents=True)
(DOCS / "vision").mkdir(parents=True)
(DOCS / "usdm").mkdir(parents=True)
for c in M11_CASES:
    (DOCS / "usdm" / f"m11-{c}").mkdir()
(DOCS / "cases" / "cpmp").mkdir(parents=True)
(DOCS / "cases" / "remapcap").mkdir(parents=True)
(DOCS / "templates" / "eupearl").mkdir(parents=True)
(DOCS / "templates" / "remapcap-dsa").mkdir(parents=True)
(DOCS / "templates" / "tpp").mkdir(parents=True)
(DOCS / ".nojekyll").write_text("")

# Landing page
cards = []
for q in questions.itertuples():
    rows = cat[cat.q_id == q.q_id]
    req_names = "".join(f'<span class="chip">{esc(reqs.loc[r, "name"])}</span>' for r in q.requirements.split(";"))
    per_case = []
    for case in CASE_ORDER:
        sub = rows[rows.case == case]
        if sub.empty:
            continue
        counts = sub.kind.value_counts()
        parts = [k if k == "not asked" else f"{counts[k]} {KIND_PLURAL[k] if counts[k] > 1 and k in KIND_PLURAL else k}"
                 for k in KIND_ORDER if k in counts and k != "earlier"]
        per_case.append(f"<b>{case}</b>: {', '.join(parts)}")
    who = sorted({w for r in rows.review for w in waits(r)}, key=REVIEWERS.index)
    wait_html = "".join(f'<span class="chip wait">waits for {w}</span>' for w in who)
    cards.append(f"""<div class="card">
<h3><span class="qid">{q.q_id}</span><a href="{q.q_id}/">{esc(q.question)}</a></h3>
<p>{req_names}</p>
<p>{'<br>'.join(per_case)}</p>
{f'<p>{wait_html}</p>' if wait_html else ''}
</div>""")

questions_body = f"""<h1>The questions</h1>
{md_to_html(questions_md)}
<p class="muted">Each card counts what the catalogue holds per case: findings with document evidence, case questions
answered by SPARQL over the design modules, and questions still open; "both" is a question asked of the two cases
together. Earlier answers (before the modules) are on the question pages.</p>
<div class="cards">
{chr(10).join(cards)}
</div>
"""
(DOCS / "questions" / "index.html").write_text(page("The questions", 1, questions_body), encoding="utf-8")

# Question pages
for q in questions.itertuples():
    rows = cat[cat.q_id == q.q_id]
    req_html = "".join(f"<li><b>{esc(reqs.loc[r, 'name'])}</b> ({r}): {esc(reqs.loc[r, 'what design modules must represent'])}</li>"
                       for r in q.requirements.split(";"))
    sections = []
    for case in CASE_ORDER:
        sub = rows[rows.case == case]
        if sub.empty:
            continue
        trs = []
        for r in sub.itertuples():
            item = esc(r.item_id)
            if not pd.isna(r.query):
                item = f'<a href="{repo_link(r.query)}">{item}</a>'
            elif r.kind == "finding":
                item = f'<a href="{BLOB}{FINDINGS}#L{finding_line[r.item_id]}">{item}</a>'
            cls = "unanswered" if r.kind in ("open", "not asked") else "answered"
            wait_html = "".join(f'<span class="chip wait">waits for {w}</span>' for w in waits(r.review))
            if r.item_id in EXAMPLES:
                item += f' · <a href="../../examples/{r.item_id.lower()}/">worked example</a>'
            trs.append(f"""<tr class="{cls}"><td>{esc(r.kind)}</td><td class="item">{item}</td><td>{esc(r.text if not pd.isna(r.text) else r.note)}</td><td>{esc(r.answer)}</td>
<td>{esc(r.check)}</td><td>{status_chips(r.status)}</td><td>{esc(r.evidence_rows)}</td><td>{esc(r.review)}{(' ' + wait_html) if wait_html else ''}</td></tr>""")
        sections.append(f"""<h2>{case}</h2>
<div class="table-wrap"><table>
<thead><tr><th>Kind</th><th>Item</th><th>Question or finding</th><th>Answer</th><th>Check</th><th>Status</th><th>Evidence rows</th><th>Review</th></tr></thead>
<tbody>
{chr(10).join(trs)}
</tbody></table></div>""")
    body = f"""<h1>{q.q_id}. {esc(q.question)}</h1>
<ul>{req_html}</ul>
<p class="muted">Item: <b>CP-</b> and <b>RC-</b> are findings for CPMP and REMAP-CAP, each with document evidence
(<a href="{BLOB}{FINDINGS}">findings.csv</a>; the link opens the finding's row); <b>CQ</b> and <b>R</b> are the case
questions of the CPMP and REMAP-CAP design modules, each a SPARQL query (the link opens the query); <i>earlier</i>
rows are answers from before the modules, and cdd-layer items are questions stated in the parked cdd-layer sketch.
Case "both": a question asked of the two cases together.
Solid left edge: answered (finding, case question or earlier answer). Dashed: open or not asked.
Status gives the kinds of evidence behind a finding, with counts when there is more than one kind; evidence rows are
in <a href="{BLOB}evidence-matrix/output/evidence_matrix.csv">evidence_matrix.csv</a>. Same rows as the
<a href="{BLOB}competency-questions/output/catalogue.md">catalogue</a>.</p>
{chr(10).join(sections)}
"""
    out = DOCS / "questions" / q.q_id
    out.mkdir()
    (out / "index.html").write_text(page(f"{q.q_id}. {q.question}", 2, body, wide=True), encoding="utf-8")


# Findings page
FIND_INPUTS = [INPUTS["requirements"], FINDINGS, "evidence-matrix/output/findings_checked.csv", INPUTS["catalogue"]]
fsrc = pd.read_csv(ROOT / FINDINGS, dtype=str)
fchk = pd.read_csv(ROOT / FIND_INPUTS[2], dtype=str)
fq = cat[cat.kind == "finding"].set_index("item_id")
assert set(fsrc.finding_id) == set(fchk.finding_id) == set(fq.index), "finding ids differ between the inputs"
assert fchk.check.isin(["pass", "first counted here"]).all(), fchk[~fchk.check.isin(["pass", "first counted here"])]
first = fchk[fchk.check == "first counted here"].finding_id.tolist()
fall = fsrc.merge(fchk[["finding_id", "observed", "evidence_rows", "check"]], on="finding_id", validate="1:1")
fsections = []
for req, rq in reqs.iterrows():
    sub = fall[fall.requirement == req].sort_values("case", kind="stable")
    assert len(sub), req
    trs = "".join(
        f'<tr><td class="item"><a href="{BLOB}{FINDINGS}#L{finding_line[r.finding_id]}">{esc(r.finding_id)}</a>'
        + (f'<br><a href="../examples/{r.finding_id.lower()}/">worked example</a>' if r.finding_id in EXAMPLES else "")
        + '</td>'
        f'<td>{esc(r.case)}</td><td>{esc(r.finding)}</td><td>{esc(r.observed)}</td><td>{esc(r.check)}</td>'
        f'<td>{esc(fq.loc[r.finding_id, "status"])}</td><td>{esc(r.evidence_rows)}</td>'
        f'<td><a href="../questions/{fq.loc[r.finding_id, "q_id"]}/">{fq.loc[r.finding_id, "q_id"]}</a></td></tr>'
        for r in sub.itertuples())
    fsections.append(f"""<h2>{esc(rq['name'])} <span class="muted">({req})</span></h2>
<p>{esc(rq['what design modules must represent'])}</p>
<div class="table-wrap"><table><thead><tr><th>Finding</th><th>Case</th><th>Finding</th><th>Value</th><th>Check</th>
<th>Status</th><th>Evidence rows</th><th>Question</th></tr></thead><tbody>{trs}</tbody></table></div>""")
ncase = fall.case.value_counts()
findings_body = f"""<h1>Findings</h1>
<p>The {len(fall)} findings with document evidence (CPMP {ncase['CPMP']}, REMAP-CAP {ncase['REMAP-CAP']}), grouped by
the requirement they bear on. Each finding's value is recomputed from the builds. For {len(fall) - len(first)} it is checked
against the value recorded when the finding was agreed; {len(first)} ({", ".join(first)}) were first counted in the evidence
matrix, so only the presence of their evidence rows is checked. The question page gives the case questions and
review state around it; the evidence rows are in <a href="{BLOB}evidence-matrix/output/evidence_matrix.csv">evidence_matrix.csv</a>.</p>
{''.join(fsections)}"""
(DOCS / "findings").mkdir(parents=True, exist_ok=True)
(DOCS / "findings" / "index.html").write_text(page("Findings", 1, findings_body, wide=True, inputs=FIND_INPUTS),
                                             encoding="utf-8")

# Design modules page
MOD = {"CPMP": "cpmp-design-modules", "REMAP-CAP": "remapcap-design-modules"}
MOD_KIND = {"CPMP": [("cpmp-core", "authored vocabulary"), ("master", "master protocol"),
                     ("disease-", "disease state (DSA, not public)"), ("compound-", "compound (no document of its own)"),
                     ("isa-", "ISA (compound × disease state)"), ("cpmp-all", "imports all modules")],
            "REMAP-CAP": [("rcap-core", "authored vocabulary"), ("components", "components"),
                          ("core-4.", "Core Protocol version"), ("core", "Core Protocol, version-independent"),
                          ("panda", "PANDA"), ("dsa-shared", "shared between DSAs (no document states it)"),
                          ("dsa-", "domain-specific appendix"), ("about", "what components are about"),
                          ("readings", "analyst readings"), ("delegations", "analyst readings"),
                          ("rcap-all", "imports all modules")]}
UP_MANIFEST = "cpmp-design-modules/sources/upstream/MANIFEST.csv"
MOD_INPUTS = [UP_MANIFEST] + [f"{d}/imports/upstream_terms.csv" for d in MOD.values()] + \
             [f"{d}/output/design_hierarchy.csv" for d in MOD.values()] + [f"{d}/modules/" for d in MOD.values()]


def mod_kind(case, stem):
    for prefix, kind in MOD_KIND[case]:
        if stem.startswith(prefix):
            return kind
    raise AssertionError(f"no kind rule for {case} {stem}")


release = pd.read_csv(ROOT / UP_MANIFEST, dtype=str).set_index("file").version_iri
terms = []
for case, d in MOD.items():
    t = pd.read_csv(ROOT / d / "imports" / "upstream_terms.csv", dtype=str)
    t["case"] = case
    terms.append(t)
terms = pd.concat(terms)
term_rows = ""
for term, sub in terms.groupby("term", sort=False):
    r = sub.iloc[0]
    assert sub.label.nunique() == 1 and sub.source.nunique() == 1, term
    marks = "".join(f"<td>{'✓' if c in set(sub.case) else ''}</td>" for c in MOD)
    term_rows += (f'<tr><td class="item"><a href="{esc(r.iri)}">{esc(term)}</a></td><td>{esc(r.label)}</td>'
                  f'<td>{esc(r.kind)}</td><td><code>{esc(release[r.source])}</code></td>{marks}</tr>')
n_terms = terms.term.nunique()
gap_rows, file_sections, hier_rows = "", "", ""
for case, d in MOD.items():
    files = sorted((ROOT / d / "modules").glob("*.ttl"))
    allg = rdflib.Graph()
    frows = ""
    for f in files:
        g = rdflib.Graph().parse(f)
        allg += g
        assert len(set(g.subjects(RDF.type, OWL.Ontology))) == 1, f
        imps = sorted(str(o).rsplit("/", 1)[-1] for o in g.objects(None, OWL.imports))
        ncls = len(set(g.subjects(RDF.type, OWL.Class)))
        if case == "REMAP-CAP" and f.stem.startswith("dsa-") and f.stem != "dsa-shared":
            assert ncls == 2, (f.name, ncls)
        if case == "CPMP" and f.stem.endswith("07"):
            assert ncls == 1, (f.name, ncls)
        frows += (f'<tr><td class="item"><a href="{BLOB}{d}/modules/{f.name}">{f.name}</a></td>'
                  f'<td>{esc(mod_kind(case, f.stem))}</td><td>{esc(", ".join(imps))}</td>'
                  f'<td class="num">{ncls}</td></tr>')
    file_sections += f"""<h3>{case}: {len(files)} module files</h3>
<div class="table-wrap"><table><thead><tr><th>File</th><th>Kind (by file name)</th><th>Imports</th>
<th>Classes declared</th></tr></thead><tbody>{frows}</tbody></table></div>"""
    for p in {p for p in allg.predicates() if str(p).endswith("upstreamGap")}:
        for s, o in sorted(allg.subject_objects(p)):
            gap_rows += (f"<tr><td>{case}</td><td>{esc(allg.value(s, RDFS.label))}</td><td>{esc(o)}</td>"
                         f"<td>upstreamGap</td></tr>")
    for s, o in sorted(allg.subject_objects(RDFS.comment)):
        if str(o).startswith("Authored:"):
            gap_rows += (f"<tr><td>{case}</td><td>{esc(allg.value(s, RDFS.label))}</td><td>{esc(o)}</td>"
                         f"<td>authored class</td></tr>")
    h = pd.read_csv(ROOT / d / "output" / "design_hierarchy.csv", dtype=str)
    for status, n in h.status.value_counts().items():
        hier_rows += f"<tr><td>{case}</td><td>{esc(status)}</td><td class=\"num\">{n}</td></tr>"
assert gap_rows, "no gaps found in the module files"
cp1_n = int(re.match(r"(\d+) components", fchk.set_index("finding_id").observed["CP-1"]).group(1))
modules_body = f"""<h1>Design modules</h1>
<p><b>Early exploratory work.</b> The design modules are the second round of this work, after USDM. The design
content of each case is read from its documents and held as OWL classes, so that a reasoner can tell designs apart
and find what they share.</p>
<ul>
<li>A <i>component</i> is one unit of design content: an eligibility criterion, an objective, an endpoint, a Schedule
of Activities cell (CPMP), a statement (REMAP-CAP). It has one identity wherever it occurs; where the wording
differs, that identity is a decision (<a href="../questions/Q1/">Q1</a>).</li>
<li>A <i>module</i> groups the components of one layer or one shared set. CPMP: the master protocol, three disease
states (not public, so only what is handed over to them), four compounds and twelve ISAs; each ISA module imports
the master, its disease state and its compound. REMAP-CAP: the Core Protocol (one module per version, 4.0 and 4.1,
under a version-independent Core), PANDA and nine DSAs.</li>
<li>The reasoner then shows what no document states: in CPMP, a compound module of {cp1_n} components shared by the
three ISAs of each compound (<a href="../findings/">CP-1</a>); in REMAP-CAP, that no DSA sits under either Core
version, because no DSA names one (<a href="../questions/Q7/">Q7</a>).</li>
</ul>
<p>What this is not: a design ontology. The modules reuse {n_terms} upstream terms and pass an OWL 2 DL check, but no
ontologist has reviewed them, and they were built only for the competency questions of two cases. A foundation that
scales takes more. For every kind of content it has to be decided what a term denotes, the act performed, the
information it produces or the plan for either, and that choice has to be aligned with BFO and the ontologies
reused. The modules here are test cases for what such a model must represent (<a href="../findings/">Findings</a>,
<a href="../vision/">Vision</a>).</p>
<h2>Upstream terms: {n_terms}</h2>
<p class="muted">Imported from pinned releases (ROBOT, MIREOT); every authored class has one of them as an ancestor.</p>
<div class="table-wrap"><table><thead><tr><th>Term</th><th>Label</th><th>Kind</th><th>Release</th>
{''.join(f'<th>{c}</th>' for c in MOD)}</tr></thead><tbody>{term_rows}</tbody></table></div>
<h2>Gaps found</h2>
<p class="muted">As recorded in the module files: what the upstream term does not represent, and classes authored
because no upstream class was found.</p>
<div class="table-wrap"><table><thead><tr><th>Case</th><th>Class</th><th>Gap</th><th>Recorded as</th></tr></thead>
<tbody>{gap_rows}</tbody></table></div>
<h2>Module files</h2>
<p class="muted">A REMAP-CAP DSA file declares only its domain and design classes; its components are declared in
components.ttl. The CPMP files for OA07, BP07 and NP07 declare one class each: these ISAs are registered with no
protocol posted.</p>
{file_sections}
<h2>Classification</h2>
<p class="muted">Memberships of the design classes after reasoning: stated in the module files (asserted) or found by
the reasoner (inferred). The compound module of CPMP is found this way (<a href="../findings/">finding CP-1</a>).</p>
<div class="table-wrap"><table><thead><tr><th>Case</th><th>Status</th><th>Memberships</th></tr></thead>
<tbody>{hier_rows}</tbody></table></div>"""
(DOCS / "modules").mkdir(parents=True, exist_ok=True)
(DOCS / "modules" / "index.html").write_text(page("Design modules", 1, modules_body, wide=True, inputs=MOD_INPUTS),
                                            encoding="utf-8")

# Worked examples (README sections)
for fid, title in EXAMPLES.items():
    assert fid in fq.index, fid
    q = fq.loc[fid, "q_id"]
    body = (f"<h1>{esc(title)}</h1>\n<p class=\"muted\">A worked example: one finding followed from the documents "
            f"to the catalogue, as the README gives it. The finding on the <a href=\"../../findings/\">Findings</a> "
            f"page; its question <a href=\"../../questions/{q}/\">{q}</a>.</p>\n" + md_to_html(examples_md[fid]))
    (DOCS / "examples" / fid.lower()).mkdir(parents=True, exist_ok=True)
    (DOCS / "examples" / fid.lower() / "index.html").write_text(page(title, 2, body, inputs=[INPUTS["readme"]]),
                                                               encoding="utf-8")

# CPMP case page
grid = pd.read_csv(ROOT / CPMP_INPUTS["grid"], dtype=str)
studies = json.loads((ROOT / CPMP_INPUTS["ctgov"]).read_text(encoding="utf-8"))
assert len(grid) == 12 and grid.doc.is_unique, len(grid)
assert set(grid.disease) == set(DISEASE_ORDER), set(grid.disease)
reg = {}
for st in studies:
    ident = st["protocolSection"]["identificationModule"]
    sec = [x["id"] for x in ident.get("secondaryIdInfos", []) if x["id"].startswith("H0P-MC-")]
    assert sec, ident["nctId"]
    prots = [d for d in st.get("documentSection", {}).get("largeDocumentModule", {}).get("largeDocs", [])
             if d["label"] == "Study Protocol"]
    assert len(prots) <= 1, ident["nctId"]
    prot = prots[0] if prots else None
    url = CTGOV_DOC.format(tail=ident["nctId"][-2:], nct=ident["nctId"], file=prot["filename"]) if prot else None
    code = sec[0][len("H0P-MC-"):]
    assert code not in reg, code
    reg[code] = {"nct": ident["nctId"], "title": ident["briefTitle"], "secondary": sec,
                 "date": prot["date"] if prot else None, "url": url,
                 "conditions": st["protocolSection"]["conditionsModule"]["conditions"],
                 "interventions": [i["name"] for i in st["protocolSection"].get("armsInterventionsModule", {}).get("interventions", [])]}
assert set(grid.doc) <= set(reg), set(grid.doc) - set(reg)
assert "CPMP" in reg and reg["CPMP"]["url"], "master record or its protocol missing"
compounds = (grid.assign(n=grid.doc.str[2:]).sort_values("n").drop_duplicates("compound").compound.tolist())
assert len(compounds) == 4, compounds


def ctgov_link(code):
    r = reg[code]
    return f'<a href="https://clinicaltrials.gov/study/{r["nct"]}">{r["nct"]}</a>'


def protocol_line(code):
    r = reg[code]
    return f'<a href="{r["url"]}">protocol</a> {r["date"]}' if r["url"] else "no protocol posted"


m = reg["CPMP"]
prefix = grid.assign(p=grid.doc.str[:2]).groupby("disease").p.unique()
assert all(len(v) == 1 for v in prefix), prefix
prefix = prefix.str[0]
suffix = grid.assign(n=grid.doc.str[2:]).groupby("compound").n.unique()
assert all(len(v) == 1 for v in suffix), suffix
suffix = suffix.str[0]
dis_name = {dis: sorted({reg[d]["conditions"][0] for d in grid[grid.disease == dis].doc}) for dis in DISEASE_ORDER}
assert all(len(v) == 1 for v in dis_name.values()), dis_name
cells = (['<div class="head">Disease state</div>', f'<div class="head" style="grid-column: span {len(compounds)}; '
          'text-align: center">Compound (one ISA per compound and disease state)</div>']
         + ['<div></div>'] + [f'<div class="head">{html.escape(c)}</div>' for c in compounds])
for dis in DISEASE_ORDER:
    cells.append(f'<div class="box dashed"><b>{dis} DSA</b><span class="muted">{html.escape(dis_name[dis][0])}; '
                 f'not public</span></div>')
    for c in compounds:
        hit = grid[(grid.disease == dis) & (grid.compound == c)]
        assert len(hit) == 1, (dis, c)
        d = hit.doc.iloc[0]
        cells.append(f'<div class="box"><b>{d}</b>{ctgov_link(d)}<br><span class="muted">{protocol_line(d)}</span></div>')
others = sorted(k for k in reg if k != "CPMP" and k not in set(grid.doc))
other_rows = "".join(
    f"<tr><td>{k}</td><td>{ctgov_link(k)}</td><td>{esc('; '.join(reg[k]['secondary']))}</td>"
    f"<td>{esc('; '.join(reg[k]['interventions']))}</td><td>{esc('; '.join(reg[k]['conditions']))}</td><td>{protocol_line(k)}</td></tr>"
    for k in others)
cpmp_body = f"""<h1>CPMP: the documents</h1>
<p>Lilly Chronic Pain Master Protocol (H0P-MC-CPMP). One master protocol; one disease-state addendum (DSA) per disease,
not public; one intervention-specific appendix (ISA) per compound and disease, each registered on ClinicalTrials.gov
under its own NCT ID with the ISA posted as its protocol.</p>
<p class="muted">Solid box: posted document. Dashed box: a layer the ISAs refer to, not public. The grid is read from
each ISA's section 5 sentence naming the master protocol and its DSA
(<a href="{BLOB}{CPMP_INPUTS['grid']}">grid.csv</a>); registry data from the ClinicalTrials.gov records
(<a href="{BLOB}{CPMP_INPUTS['ctgov']}">cpmp_studies.json</a>, query in
<a href="{BLOB}usdm-master-protocol/sources/ctgov_api/QUERY.txt">QUERY.txt</a>).</p>
<h2>Master protocol</h2>
<div class="layer"><div class="box"><b>CPMP master protocol</b>{ctgov_link('CPMP')} · {html.escape(m['title'])}<br>
<span class="muted">{protocol_line('CPMP')}</span></div></div>
<h2>Disease-state addenda and ISAs</h2>
<p class="muted">Rows: the disease states, each with its disease-state addendum (DSA). Columns: the compounds. Disease
names as the ISAs' ClinicalTrials.gov records give them:
{'; '.join(f'<b>{dis}</b> {html.escape(dis_name[dis][0])}' for dis in DISEASE_ORDER)}. ISA codes: a disease prefix
({', '.join(f'{prefix[dis]} = {dis}' for dis in DISEASE_ORDER)}) and a compound number
({', '.join(f'{suffix[c]} = {c}' for c in compounds)}).</p>
<div class="table-wrap"><div class="grid4">
{chr(10).join(cells)}
</div></div>
<p class="muted">The 13 Schedules of Activities (master and 12 ISAs) are extracted as tables, not yet as USDM, in
<a href="https://kerfors.github.io/soa2usdm-collections/collections/cpmp/protocols/index.html">soa2usdm-collections</a>.</p>
<h2>Other records with a H0P-MC- secondary ID</h2>
<p class="muted">Registered under the programme but not in the grid above (not among the 12 ISAs read here).</p>
<div class="table-wrap"><table>
<thead><tr><th>Code</th><th>NCT</th><th>Secondary IDs</th><th>Interventions</th><th>Conditions</th><th>Protocol</th></tr></thead>
<tbody>{other_rows}</tbody></table></div>
"""
(DOCS / "cases" / "cpmp" / "index.html").write_text(
    page("CPMP: the documents", 2, cpmp_body, wide=True, inputs=list(CPMP_INPUTS.values())), encoding="utf-8")

# REMAP-CAP case page
rdocs = pd.read_csv(ROOT / RCAP_INPUTS["documents"], dtype=str)
manifest = pd.read_csv(ROOT / RCAP_INPUTS["manifest"], dtype=str)
assert set(rdocs.url) <= set(manifest.url), set(rdocs.url) - set(manifest.url)
assert set(manifest.listing) == {"current", "superseded"}, set(manifest.listing)
assert list(rdocs.layer.unique()) == ["CORE", "PANDA", "DSA"], list(rdocs.layer.unique())


def rbox(r):
    return (f'<div class="box"><b>{esc(r.header_name)} {esc(r.version)}</b>'
            f'<span class="muted">{esc(r.date)} · <a href="{esc(r.url)}">remapcap.org</a> · key in the data: {esc(r.short)}</span></div>')


layer_html = {lay: "".join(rbox(r) for r in rdocs[rdocs.layer == lay].itertuples()) for lay in ["CORE", "PANDA", "DSA"]}
out_scope = manifest[(manifest.listing == "current") & ~manifest.url.isin(rdocs.url)]
sup = manifest[manifest.listing == "superseded"].copy()
sup_read = sup[sup.url.isin(rdocs.url)]
parts = sup.link_text.str.extract(r"^(.*?)\s*-?\s*(?:Version|V)\s*([\d.]+)$")
assert parts.notna().all().all(), sup.link_text[parts.isna().any(axis=1)].tolist()
sup["family"], sup["version"] = parts[0], parts[1]
fam = sup.groupby("family", sort=False).version.apply(lambda v: ", ".join(v))
out_rows = "".join(f'<tr><td><a href="{esc(r.url)}">{esc(r.link_text)}</a></td></tr>' for r in out_scope.itertuples())
sup_rows = "".join(f"<tr><td>{esc(f)}</td><td>{esc(v)}</td></tr>" for f, v in fam.items())
rcap_body = f"""<h1>REMAP-CAP: the documents</h1>
<p>REMAP-CAP is an adaptive platform trial in community-acquired pneumonia. Its protocol is a set of documents posted
on remapcap.org: a Core Protocol, the Patient, Pathogen and Disease Appendix (PANDA), and one domain-specific appendix
(DSA) per domain, plus region-specific and other appendices. All are public.</p>
<p class="muted">The documents read in this work: {len(rdocs)}. Version and date as each document's page header states them
(<a href="{BLOB}{RCAP_INPUTS['documents']}">documents.csv</a>, written by
<a href="{BLOB}remapcap-design-modules/scripts/rcap_docs.py">rcap_docs.py</a>); listings as on remapcap.org when retrieved
(<a href="{BLOB}{RCAP_INPUTS['manifest']}">manifest.csv</a>, with sha256 per file).</p>
<h2>Core Protocol</h2>
<div class="layer core2">{layer_html['CORE']}</div>
<h2>Patient, Pathogen and Disease Appendix</h2>
<div class="layer core2">{layer_html['PANDA']}</div>
<h2>Domain-specific appendices</h2>
<div class="layer dsa3">{layer_html['DSA']}</div>
<p>The structure the nine DSAs share: <a href="../../templates/remapcap-dsa/">the DSA template no document states</a>.</p>
<h2>Other current documents on remapcap.org (not read here)</h2>
<div class="table-wrap"><table><tbody>{out_rows}</tbody></table></div>
<h2>Superseded versions listed on remapcap.org</h2>
<p class="muted">Names as the listing gives them. Read here: {esc("; ".join(sup_read.link_text))}.</p>
<div class="table-wrap"><table><thead><tr><th>Listed as</th><th>Versions</th></tr></thead><tbody>{sup_rows}</tbody></table></div>
"""
(DOCS / "cases" / "remapcap" / "index.html").write_text(
    page("REMAP-CAP: the documents", 2, rcap_body, wide=True, inputs=list(RCAP_INPUTS.values())), encoding="utf-8")


# EU-PEARL templates page
sec = pd.read_csv(ROOT / EUP_INPUTS["sections"], dtype=str)
aln = pd.read_csv(ROOT / EUP_INPUTS["alignment"], dtype=str)
fld = pd.read_csv(ROOT / EUP_INPUTS["fields"], dtype=str)
struct = json.loads((ROOT / EUP_INPUTS["structure"]).read_text(encoding="utf-8"))
assert list(sec.doc.unique()) == ["MPT", "ISA", "SAP", "DMC"], list(sec.doc.unique())
assert set(aln.match) == {"both", "mpt_only", "isa_only"}, set(aln.match)
assert sec.section_key.is_unique
for k in EUP_KINDS:
    sec["n_" + k] = sec["n_" + k].astype(int)
sec["para_idx"] = sec.para_idx.astype(int)
skey = sec.set_index("section_key")
assert set(aln.section_key_mpt.dropna()) == set(sec[sec.doc == "MPT"].section_key), "MPT sections and alignment differ"
assert set(aln.section_key_isa.dropna()) == set(sec[sec.doc == "ISA"].section_key), "ISA sections and alignment differ"


def counts_html(key):
    r = skey.loc[key]
    chips = "".join(f'<span class="chip">{k.replace("_", " ")} {r["n_" + k]}</span>' for k in EUP_KINDS if r["n_" + k])
    ch = int(float(r.eupearl_change_chars))
    if ch:
        chips += f'<span class="chip change">EU-PEARL change {ch} chars</span>'
    return chips


def sec_box(key):
    r = skey.loc[key]
    num = "" if pd.isna(r.number) else f"{esc(r.number)} "
    return (f'<div class="box lv{r.level}"><b>{num}{esc(r.title)}<span class="key">{esc(key)}</span></b>'
            f'{counts_html(key)}</div>')


# order: MPT order, each ISA-only section placed after the ISA section that precedes it in the ISA
isa_order = sec[sec.doc == "ISA"].sort_values("para_idx").section_key.tolist()
rows = aln[aln.match != "isa_only"].to_dict("records")
isa_only = aln[aln.match == "isa_only"].set_index("section_key_isa")
for k in isa_order:
    if k not in isa_only.index:
        continue
    prev = isa_order[: isa_order.index(k)]
    placed = [i for i, r in enumerate(rows) if r.get("section_key_isa") in prev]
    pos = max((i for i in placed if prev.index(rows[i]["section_key_isa"]) == max(prev.index(rows[j]["section_key_isa"]) for j in placed)), default=-1)
    rows.insert(pos + 1, dict(isa_only.loc[k], section_key_isa=k))
assert len(rows) == len(aln), (len(rows), len(aln))

side = ['<div class="colhead">Master Protocol Template (MPT)</div><div class="colhead">ISA relation</div>'
        '<div class="colhead">Intervention Specific Appendix (ISA)</div>']
for r in rows:
    left = sec_box(r["section_key_mpt"]) if r["match"] != "isa_only" else '<div class="empty"></div>'
    right = sec_box(r["section_key_isa"]) if r["match"] != "mpt_only" else '<div class="empty"></div>'
    if r["match"] == "both":
        flags = [f.replace("_", " ") for f in EUP_FLAGS if r[f] == "True"]
        refs = "" if pd.isna(r["master_section_refs"]) else f"<br>master § {esc(r['master_section_refs'])}"
        rel = (", ".join(flags) if flags else "no explicit master reference") + refs
    else:
        rel = "MPT only" if r["match"] == "mpt_only" else "ISA only"
    side.append(f'{left}<div class="rel" title="alignment key: {esc(r["align_key"])}">{rel}</div>{right}')

n_match = aln.match.value_counts()
n_rel = aln[aln.match == "both"].isa_relation.value_counts()


def tree(doc):
    return "".join(sec_box(k) for k in sec[sec.doc == doc].sort_values("para_idx").section_key)


def fields(doc):
    out = []
    for r in fld[fld.doc == doc].itertuples():
        slot = esc(r.inline_value) if not pd.isna(r.inline_value) else ""
        out.append(f'<div>{esc(r.label)}<span class="key">{esc(r.doc)} ¶{esc(r.para_idx)} · {esc(r.section_path)}</span></div>'
                   f'<div class="slotbox">{slot}</div>')
    return "".join(out)


tot = sec.groupby("doc", sort=False).size()
docs_list = "".join(f"<li><b>{d}</b>: {esc(struct['documents'][d]['file'])}"
                    f"{f' ({tot[d]} sections)' if d in tot else ' (no heading tree; not rendered here)'}</li>"
                    for d in struct["documents"])
eup_body = f"""<h1>EU-PEARL templates as data</h1>
<p>The EU-PEARL suite of platform-trial templates (<a href="{esc(struct['source'])}">eu-pearl.eu</a>; the rationale is
published in <a href="{EUP_RATIONALE}">Trials, 2024</a>), read by script as documents with their own structure. What is
shown is the structure: headings, field labels, and per section the number of paragraphs of each text kind, from the
templates' own styles and markers. No paragraph text is shown: the templates are © EU-PEARL Consortium, the MPT, ISA
and SAP based on TransCelerate templates, all rights reserved.</p>
<ul>{docs_list}</ul>
<p class="muted">Text kinds: <i>instruction</i> (instruction style), <i>common</i>, <i>suggested</i>, <i>example</i>,
<i>sample</i> (the templates' start and end markers), <i>guidance</i> (DMC charter), <i>field label</i>. EU-PEARL change:
characters highlighted as changed from the TransCelerate template. How they were read:
<a href="{BLOB}eupearl-templates/README.md">README</a>.</p>
<div class="switch"><label><input type="checkbox" id="sw"> Show as data</label>
<span class="muted"> section keys (document:paragraph) and field positions; the alignment key shows on hover over the relation</span></div>
<h2>MPT and ISA side by side</h2>
<p class="muted">Sections matched on the exact normalised title path, no fuzzy matching: {n_match['both']} in both,
{n_match['mpt_only']} in the MPT only, {n_match['isa_only']} in the ISA only (placed after the ISA section they follow).
For a matched section, the ISA relation is set only where an explicit phrase occurs in the ISA section:
{'; '.join(f'{esc(k.replace("_", " ").replace("+", " + "))} {v}' for k, v in n_rel.items())}. The phrase is kept as
evidence in <a href="{BLOB}{EUP_INPUTS['alignment']}">mpt_isa_alignment.csv</a>.</p>
<div class="table-wrap"><div class="side">
{chr(10).join(side)}
</div></div>
<h2>Title page and synopsis fields</h2>
<p class="muted">Field labels as the templates print them; a dashed box is where the value goes, with the template's
own placeholder where it has one.</p>
<h3>MPT ({(fld.doc == 'MPT').sum()})</h3><div class="fields">{fields('MPT')}</div>
<h3>ISA ({(fld.doc == 'ISA').sum()})</h3><div class="fields">{fields('ISA')}</div>
<h2>Statistical Analysis Plan (SAP)</h2>
<div class="tree">{tree('SAP')}</div>
<h2>Data Monitoring Committee charter (DMC)</h2>
<div class="tree">{tree('DMC')}</div>
<script>
const sw = document.getElementById('sw');
sw.addEventListener('change', () => document.body.classList.toggle('data', sw.checked));
</script>
"""
(DOCS / "templates" / "eupearl" / "index.html").write_text(
    page("EU-PEARL templates as data", 2, eup_body, wide=True, inputs=list(EUP_INPUTS.values())), encoding="utf-8")


# REMAP-CAP DSA template page
hd = pd.read_csv(ROOT / RDSA_INPUTS["headings"], dtype=str)
rd = pd.read_csv(ROOT / RDSA_INPUTS["documents"], dtype=str)
dsa_keys = rd[rd.layer == "DSA"].key.tolist()
short = rd.set_index("key").short
dh = hd[hd.doc.isin(dsa_keys)].copy()
assert set(dh.doc) == set(dsa_keys), set(dsa_keys) - set(dh.doc)
dh["pos"] = dh.groupby("doc").cumcount() / dh.groupby("doc").doc.transform("size")
n_docs = dh.groupby("title_key").doc.nunique()
japan = dh[(dh.doc == "IAV_DSA") & dh.number.str.startswith("14.")]
n_japan_shared = int(japan.title_key.isin(dh[(dh.doc == "IAV_DSA") & ~dh.number.str.startswith("14.")].title_key).sum())
assert len(japan) == 5 and n_japan_shared == 3, (len(japan), n_japan_shared)
shared = n_docs[n_docs >= 2].index
order = (dh[dh.title_key.isin(shared)].groupby(["title_key", "doc"]).pos.min()
         .groupby("title_key").mean().sort_values(kind="stable").index)


def label(key):
    titles = dh[dh.title_key == key].title
    counts = titles.value_counts()
    return counts[counts == counts.max()].index[0] if (counts == counts.max()).sum() == 1 else titles.iloc[0]


mrows = []
for key in order:
    sub = dh[dh.title_key == key]
    lvl = int(sub.level.astype(int).min())
    cells = []
    for d in dsa_keys:
        nums = sub[sub.doc == d].number.tolist()
        cells.append(f'<td class="num">{" · ".join(esc(x) for x in nums)}</td>' if nums
                     else '<td class="miss"><span></span></td>')
    mrows.append(f'<tr><td class="title lv{lvl}">{esc(label(key))}<span class="key">{esc(key)}</span></td>'
                 f'{"".join(cells)}<td class="num">{n_docs[key]}</td></tr>')
own = []
for d in dsa_keys:
    sub = dh[(dh.doc == d) & dh.title_key.isin(n_docs[n_docs == 1].index)]
    items = "".join(f"<li>{esc(r.number)} {esc(r.title)}</li>" for r in sub.itertuples())
    own.append(f'<details class="own"><summary>{esc(short[d])}: {len(sub)} of {(dh.doc == d).sum()} headings</summary>'
               f'<ul>{items}</ul></details>')
dist = n_docs.value_counts().sort_index(ascending=False)
rdoc = rd.set_index("key")
dname = {d: rdoc.loc[d, "header_name"].replace(" Domain-Specific Appendix", "") for d in dsa_keys}
heads = "".join(f'<th class="dsa" title="{esc(rdoc.loc[d, "header_name"])} {esc(rdoc.loc[d, "version"])}">'
                f'{esc(short[d])}<br><span class="dname">{esc(dname[d])}</span></th>' for d in dsa_keys)
legend = " · ".join(f"<b>{esc(short[d])}</b> {esc(dname[d])} {esc(rdoc.loc[d, 'version'])} ({esc(rdoc.loc[d, 'date'])})"
                    for d in dsa_keys)
rdsa_body = f"""<h1>REMAP-CAP: the DSA template no document states</h1>
<p>Each REMAP-CAP domain-specific appendix (DSA) follows a common structure, but no REMAP-CAP document gives that
structure as a template. Here it is read from the headings of the nine DSAs read in this work: {len(dh)} headings
under {len(n_docs)} distinct titles. The heading-level counterpart of finding RC-1 (components every DSA states).</p>
<p class="muted">IAV's headings {", ".join(japan.number)} belong to its Japan region-specific modification, which sits
inside the DSA (RC-18). {n_japan_shared} of their titles also occur at IAV 8.x, so they show as a second number in
IAV's cells and the counts per title do not change.</p>
<p class="muted">Titles matched exactly: lower case, characters other than a–z ignored; no fuzzy matching and no domain
names masked, so "Corticosteroid Domain Governance" and "Antibiotic Domain Governance" stay apart. A cell holds the
section number(s) of that heading in that DSA; a dashed cell: the DSA has no heading with that title. Rows ordered by
the mean relative position of the heading's first occurrence in each DSA. Number of DSAs per title:
{'; '.join(f'{k} DSAs: {v}' for k, v in dist.items() if k > 1)}; one DSA only: {dist.get(1, 0)}.
Headings and numbers as each document's table of contents gives them
(<a href="{BLOB}{RDSA_INPUTS['headings']}">headings.csv</a>, written by
<a href="{BLOB}remapcap-design-modules/scripts/12_headings.py">12_headings.py</a>); documents on the
<a href="../../cases/remapcap/">REMAP-CAP page</a>.</p>
<div class="switch"><label><input type="checkbox" id="sw"> Show as data</label>
<span class="muted"> the title key each row is matched on</span></div>
<h2>Headings in two or more DSAs ({len(order)})</h2>
<p>Rows: one heading title. Columns: the nine domain-specific appendices (DSA), one per REMAP-CAP domain, by version
and date: {legend}. Last column: in how many of the nine the heading occurs.</p>
<div class="table-wrap"><table class="matrix">
<thead><tr><th></th><th colspan="{len(dsa_keys)}" class="dsa">Domain-specific appendix (DSA): section number of the heading</th><th></th></tr>
<tr><th>Heading</th>{heads}<th class="dsa">DSAs</th></tr></thead>
<tbody>{''.join(mrows)}</tbody></table></div>
<h2>Headings in one DSA only ({dist.get(1, 0)})</h2>
<p class="muted">The domain-specific part of each appendix, and headings that would match with a different
wording or with the domain name masked.</p>
{''.join(own)}
<script>
const sw = document.getElementById('sw');
sw.addEventListener('change', () => document.body.classList.toggle('data', sw.checked));
</script>
"""
(DOCS / "templates" / "remapcap-dsa" / "index.html").write_text(
    page("REMAP-CAP: the DSA template", 2, rdsa_body, wide=True, inputs=list(RDSA_INPUTS.values())), encoding="utf-8")

# USDM page
VAL_PATTERNS = {
    "objects": r"typed objects:\s+(\d+)",
    "triples": r"instance triples:\s+(\d+)",
    "refs": r"cross-references:\s+(\d+), dangling: (\d+)",
    "structural": r"structural\s+conforms=(\w+)\s+findings=(\d+)",
    "terminology": r"terminology\s+conforms=(\w+)",
}


def validator_output(folder):
    nb = json.loads((ROOT / UMP / folder / "60_validate_study.ipynb").read_text(encoding="utf-8"))
    text = "".join("".join(o.get("text", [])) for c in nb["cells"] for o in c.get("outputs", []))
    out = {}
    for k, pat in VAL_PATTERNS.items():
        m = re.findall(pat, text)
        assert len(m) == 1, (folder, k, m)
        out[k] = m[0]
    return out


for p in PUBLISHED:
    assert (ROOT / p).is_file(), p
usdm_inputs = [BREAKPOINTS] + PUBLISHED
file_rows, log_rows = [], []
log_status = set()
logs = {}
for case, step, name, added, log, val, nbk in USDM_FILES:
    v = validator_output(val)
    sf = pd.read_csv(ROOT / UMP / val / "shacl_findings.csv", dtype=str)
    assert len(sf) == int(v["structural"][1]) and set(zip(sf.layer, sf.constraint)) <= {("structural", "MinCount")}, val
    lg = pd.read_csv(ROOT / UMP / log, dtype=str)
    logs[(case, step)] = lg.status.value_counts()
    log_status |= set(lg.status)
    usdm_inputs += [UMP + log, UMP + val + "/60_validate_study.ipynb"]
    file_rows.append(f"""<tr><td>{case}</td><td>{step}</td><td><code>{name}</code><br><span class="muted">built by
<a href="{BLOB}{UMP}{nbk}">{nbk.split('/')[-1]}</a></span></td><td>{esc(added)}</td>
<td class="num">{int(v['objects']):,}</td><td class="num">{int(v['triples']):,}</td>
<td class="num">{int(v['refs'][0]):,} / {v['refs'][1]}</td>
<td class="num"><a href="{BLOB}{UMP}{val}/shacl_findings.csv">{v['structural'][1]}</a></td>
<td>{'conforms' if v['terminology'] == 'True' else 'does not conform'}</td>
<td class="muted">{esc(NOT_CARRIED[case])}</td></tr>""")
STATUS_ORDER = ["mapped", "mapped_copy_from_core", "derived", "required_not_in_document", "not_in_document",
                "not_expressible", "ambiguous_in_document", "redacted_in_document", "deferred", "not_a_change"]
assert log_status <= set(STATUS_ORDER), log_status - set(STATUS_ORDER)
used_status = [x for x in STATUS_ORDER if x in log_status]
log_head = "".join(f'<th class="dsa">{x.replace("_", " ")}</th>' for x in used_status)
for case, step, name, added, log, val, nbk in USDM_FILES:
    c = logs[(case, step)]
    log_rows.append(f'<tr><td>{case}</td><td><a href="{BLOB}{UMP}{log}">{step}</a></td>'
                    + "".join(f'<td class="num">{c.get(x, "")}</td>' for x in used_status)
                    + f'<td class="num">{c.sum()}</td></tr>')
method_items = "".join(
    f'<li><b>{esc(t)}.</b> {esc(d)} <span class="muted">'
    + " · ".join(f'<a href="{BLOB}{UMP}{x}">{x.split("/")[-1]}</a>' for x in links) + "</span></li>"
    for t, d, links in USDM_METHOD)
for _, _, links in USDM_METHOD:
    for x in links:
        assert (ROOT / UMP / x).exists(), x
bp = pd.read_csv(ROOT / BREAKPOINTS, dtype=str).fillna("")
assert bp.id.is_unique
bp_kinds = bp.groupby(["area", "kind"], sort=False).size().unstack(fill_value=0)
bp_rows = []
for area, sub in bp.groupby("area", sort=False):
    bp_rows.append(f'<tr><th colspan="5" class="area">{esc(area)}</th></tr>')
    for r in sub.itertuples():
        note = f'<br><span class="muted">{esc(r.cpmp_note)}</span>' if r.cpmp_note else ""
        bp_rows.append(f'<tr id="{esc(r.id)}"><td class="item">{esc(r.id)}</td><td><span class="chip">{esc(r.kind)}</span></td>'
                       f'<td>{esc(r.breakpoint)}</td><td><code>{esc(r.usdm_element)}</code></td>'
                       f'<td>{esc(r.evidence_remapcap)}{note}</td></tr>')
kinds_line = "; ".join(f"{k} {int((bp.kind == k).sum())}" for k in ["model", "mapping", "content"])

# M11 view of each case's published USDM file
m11_rows = []
for c, name in M11_CASES.items():
    src = UMP + f"output_m11/{c}_m11.json"
    d = json.loads((ROOT / src).read_text(encoding="utf-8"))
    assert d["case"] == c and d["study_file"] in [p[len(UMP):] for p in PUBLISHED], (c, d["study_file"])
    bp_cols = ["id", "area", "kind", "breakpoint", "usdm_element", "cpmp_note"]
    assert [{k: b[k] for k in bp_cols} for b in d["breakpoints"]] == bp[bp_cols].to_dict("records"), \
        f"{src}: breakpoints differ from {BREAKPOINTS}, re-run 21_m11_view.py"
    assert d["study_sha256"] == sha256(UMP + d["study_file"]), f"{src}: built from another {d['study_file']}"
    flds = [f for sec in d["sections"] for f in sec["fields"]]
    assert len(d["sections"]) == 160 and len(flds) == 281, (len(d["sections"]), len(flds))
    n_st = pd.Series([m11_page.field_status(f) for f in flds]).value_counts()
    assert set(n_st.index) <= {k for k, _ in M11_STATUS}, set(n_st.index)
    n_bp = len({b for f in flds for r in f["routes"] for b in r.get("breakpoints", [])})
    n_rev = sum(len(f.get("breakpoints_reviewed", [])) for f in flds)
    paths = [src, M11_PAGE, UMP + d["study_file"], BREAKPOINTS, M11_REVIEWED] + [UMP + x for x in d["logs"]]
    (DOCS / "usdm" / f"m11-{c}" / "index.html").write_text(m11_page.page_html(d, {
        "title": f"{name} as an ICH M11 protocol", "up": "../", "blob": BLOB, "footer": provenance(paths)}),
        encoding="utf-8")
    m11_rows.append(f'<tr><td><a href="m11-{c}/">{name}</a></td>'
                    + "".join(f'<td class="num">{int(n_st.get(k, 0))}</td>' for k, _ in M11_STATUS)
                    + f'<td class="num">{n_bp}</td><td class="num">{n_rev}</td></tr>')
    usdm_inputs.append(src)
usdm_body = f"""<h1>USDM v4 and master protocols</h1>
<p>The first round of this work asked whether USDM v4 can carry a master protocol. Both cases were built as USDM v4.0.0
JSON from their documents, step by step, and checked with the <a href="https://w3id.org/cdisc/usdm/v4/">usdm-rdf</a>
validator. What USDM could not express is collected as a table of breakpoints. The design modules were built next to
USDM for what it cannot carry.</p>
<p class="muted">Folder: <a href="{BLOB}{UMP}README.md">usdm-master-protocol/</a> (its README records each step and
decision). The USDM JSON files as built hold whole-document text and are not published; the notebooks re-create them
from the source documents. The most complete file of each case is published without the section text (below). The
counts below are the validator's own, read from the executed validation notebooks.</p>
<h2>What we have</h2>
<div class="table-wrap"><table>
<thead><tr><th>Case</th><th>Step</th><th>File</th><th>What the step added</th><th>Objects</th><th>Triples</th>
<th>References / dangling</th><th>Structural findings</th><th>Terminology</th><th>Not in this file</th></tr></thead>
<tbody>{''.join(file_rows)}</tbody></table></div>
<p class="muted">Structural findings are all missing required attributes (MinCount); each one is an absence the mapping
logged (required but not in the document, or not expressible), not an error in the file.</p>
<p>The section text is kept as read from the documents: it carries no usdm:ref links into the structured data.</p>
<p><b>Published without the section text:</b> the most complete file of each case, with every section text and the
REMAP-CAP intervention descriptions replaced by a marker, everything else as built, and validated with the same
findings as the originals:
{' · '.join(f'<a href="{BLOB}{p}">{p.split("/")[-1]}</a> (<a href="{RAW}{p}">raw</a>)' for p in PUBLISHED)}
· <a href="{BLOB}{UMP}published/README.md">what is in them</a>.</p>
<p>The Schedules of Activities are the other half. The 13 CPMP schedules (master and 12 ISAs) are extracted as tables (extraction, resolution, consolidation), not yet as USDM, by
<a href="https://github.com/kerfors/soa2usdm">soa2usdm</a>, in
<a href="https://kerfors.github.io/soa2usdm-collections/collections/cpmp/protocols/index.html">soa2usdm-collections</a>,
kept separate and not yet joined into the CPMP Study above. REMAP-CAP has no schedule tables.</p>
<p class="muted">Open, not started: join the 13 CPMP schedules from soa2usdm-collections into the CPMP Study.</p>
<h2>Seen as an ICH M11 protocol</h2>
<p>Each published file laid out in the ICH M11 Template: every value is found by a query that follows the published
HL7 and CDISC M11-to-USDM mappings, the method of <a href="https://kerfors.github.io/usdm-one-graph/m11/">usdm-one-graph</a>.
M11 describes one protocol. Where a master protocol's documents and versions give several values, each value says where
it sits. The deep dive shows, for each mapping route, the condition and query, the mapping-log rows for the same
object and attribute, and the breakpoints that name the same USDM element.</p>
<div class="table-wrap"><table class="matrix">
<thead><tr><th>Case (M11 Template fields)</th>{''.join(f'<th class="dsa">{esc(t)}</th>' for _, t in M11_STATUS)}<th class="dsa">breakpoints named</th><th class="dsa">reviewed links</th></tr></thead>
<tbody>{''.join(m11_rows)}</tbody></table></div>
<p class="muted">281 Template fields in 160 sections. "Protocol text": the mappings take the value from the protocol
section with the M11 section number; neither case is numbered as M11, and the published files carry no section
text. "Breakpoints named": breakpoints whose USDM element names the same class and attribute as a route. "Reviewed
links": links from an M11 field to a breakpoint that the name match cannot find, each with its evidence
(<a href="{BLOB}{M11_REVIEWED}">m11_breakpoint_links.csv</a>). Lift:
<a href="{BLOB}{UMP}scripts/21_m11_view.py">21_m11_view.py</a>, with one row per field and route for review in
<code>output_m11/&lt;case&gt;_m11_routes.csv</code>.</p>
<h2>Method</h2>
<ol>{method_items}</ol>
<p class="muted">Every notebook is generated by a script. The folder README records for each step where it was run
and how its outputs were compared.</p>
<h3>Mapping decisions per step</h3>
<div class="table-wrap"><table class="matrix">
<thead><tr><th>Case</th><th>Mapping log</th>{log_head}<th class="dsa">rows</th></tr></thead>
<tbody>{''.join(log_rows)}</tbody></table></div>
<h2>What it showed: {len(bp)} breakpoints</h2>
<p>Where USDM v4.0.0 could not carry the master protocols. Kind: <i>model</i>, USDM cannot express it; <i>mapping</i>,
only by copying or convention; <i>content</i>, the protocol does not state it. {kinds_line}. Evidence from REMAP-CAP,
with the CPMP counterpart where there is one (<a href="{BLOB}{BREAKPOINTS}">breakpoints.csv</a>). Collected in the
first round from Core Protocol 4.0 and 4.1, PANDA 1.0 and the Corticosteroid DSA 6; candidate breakpoints from CPMP
are recorded in the folder README, not yet in the table.</p>
<div class="table-wrap"><table>
<thead><tr><th>Id</th><th>Kind</th><th>Breakpoint</th><th>USDM element</th><th>Evidence</th></tr></thead>
<tbody>{''.join(bp_rows)}</tbody></table></div>
"""
(DOCS / "usdm" / "index.html").write_text(
    page("USDM v4 and master protocols", 1, usdm_body, wide=True, inputs=usdm_inputs), encoding="utf-8")

# Area pages and landing page
def area_card(href, title, lines):
    return (f'<div class="card"><h3><a href="{href}">{html.escape(title)}</a></h3>'
            + "".join(f"<p>{x}</p>" for x in lines) + "</div>")


n_kind = cat.kind.value_counts()
cases_cards = [
    area_card("cpmp/", "CPMP: the documents",
              [f"1 master protocol, {grid.disease.nunique()} disease-state addenda (not public), {len(grid)} ISAs "
               f"({grid.compound.nunique()} compounds × {grid.disease.nunique()} diseases)",
               f"{len(others)} further records registered with no protocol posted"]),
    area_card("remapcap/", "REMAP-CAP: the documents",
              [f"Core Protocol ({(rdocs.layer == 'CORE').sum()} versions), PANDA ({(rdocs.layer == 'PANDA').sum()}) and "
               f"{(rdocs.layer == 'DSA').sum()} DSAs read here",
               f"{len(out_scope)} other current and {len(sup)} superseded documents listed on remapcap.org"]),
]
(DOCS / "cases" / "index.html").write_text(page("The two cases", 1, f"""<h1>The two cases</h1>
{md_to_html(cases_md)}
<div class="cards">{''.join(cases_cards)}</div>
""", inputs=[INPUTS["readme"]] + list(CPMP_INPUTS.values()) + list(RCAP_INPUTS.values())), encoding="utf-8")

# TPP templates page
tel = pd.read_csv(ROOT / TPP_INPUTS["elements"], dtype=str)
tcm = pd.read_csv(ROOT / TPP_INPUTS["column_models"], dtype=str)
tinv = pd.read_csv(ROOT / TPP_INPUTS["inventory"], dtype=str)
tcw = pd.read_csv(ROOT / TPP_INPUTS["crosswalk"], dtype=str)
tmeta = json.loads((ROOT / TPP_INPUTS["metadata"]).read_text(encoding="utf-8"))
tel["family"] = tel.source.str.replace(r"^SEED_.*$", "SEED", regex=True)
assert list(tel.family.unique()) == TPP_FAMILIES, list(tel.family.unique())
assert list(tel[tel.family == "SEED"].source.unique()) == TPP_SEED
assert "guidance_comments" not in tel.columns, "WOAH Comments text must not be in tpp_elements.csv"
woah_text = [c for c in tel.columns if c.startswith(("guidance_", "example_value_", "target_", "annotation_"))
             and tel.loc[tel.family == "WOAH2026", c].notna().any()]
assert not woah_text, f"WOAH text columns: {woah_text}"
n_tkind = tel.element_kind.value_counts()
assert len(tel) == 172 and dict(n_tkind) == {"attribute": 134, "label_section": 17, "label_subsection": 14,
                                              "milestone": 7}, dict(n_tkind)
n_fam = tinv.n_families.astype(int).value_counts()
assert len(tinv) == 99 and dict(n_fam) == {1: 95, 2: 3, 3: 1}, (len(tinv), dict(n_fam))
assert len(tcw) == 109 and tcw.concept.isna().all(), "crosswalk concept column is no longer empty"


def tpp_url(key):
    return tmeta["sources"][key]["url"]


def tpp_text(label, text):
    return "" if pd.isna(text) else f"<p><b>{label}</b> {esc(text)}</p>"


def tpp_rows(df, cols):
    out = []
    for r in df.itertuples():
        texts = "".join(tpp_text(lab, getattr(r, c)) for lab, c in cols)
        lab = esc(r.element_label)
        cell = f"<details><summary>{lab}</summary>{texts}</details>" if texts else lab
        out.append(f"<tr><td class=\"num\">{esc(r.element_id)}</td><td>{cell}</td>"
                   f"<td class=\"num\">{esc(r.page)}</td></tr>")
    return "".join(out)


# column models per family
cm_rows = []
for fam in TPP_FAMILIES:
    sub = tcm[tcm.source.str.replace(r"^SEED_.*$", "SEED", regex=True) == fam]
    models = sub.groupby("columns", dropna=False, sort=False).n_elements.apply(lambda s: s.astype(int).sum())
    cm_rows.append(f"<tr><td><b>{fam}</b></td><td>" + "<br>".join(
        f"{esc(c) if not pd.isna(c) else '<i>no columns of its own</i>'} <span class=\"muted\">({n})</span>"
        for c, n in models.items()) + f"</td><td class=\"num\">{(tel.family == fam).sum()}</td></tr>")

# shared labels
inv_cols = ["FDA2007", "WOAH2026", "PAVEGT", "SEED"]
shared = tinv[tinv.n_families.astype(int) > 1]
sh_rows = "".join("<tr><td>" + esc(r["norm_label"]) + "</td>"
                  + "".join(f"<td class=\"num\">{esc(r[c])}</td>" for c in inv_cols) + "</tr>"
                  for _, r in shared.iterrows())

# FDA
fda = tel[tel.source == "FDA2007"]
fda_cols = [("Target:", "target_prompt"), ("Annotations:", "annotation_prompt"), ("Guidance:", "guidance_text")]
fda_sec = []
for r in fda[fda.element_kind == "label_section"].itertuples():
    subs = fda[(fda.element_kind == "label_subsection") & (fda.group == r.element_id)]
    texts = "".join(tpp_text(lab, getattr(r, c)) for lab, c in fda_cols)
    sublist = "".join(f"<li>{esc(x.element_id)} {esc(x.element_label)}</li>" for x in subs.itertuples())
    body = texts + (f"<ul>{sublist}</ul>" if sublist else "")
    lab = esc(r.element_label)
    fda_sec.append(f"<tr><td class=\"num\">{esc(r.element_id)}</td><td>"
                   + (f"<details><summary>{lab}</summary>{body}</details>" if body else lab)
                   + f"</td><td class=\"num\">{esc(r.spl_loinc)}</td><td class=\"num\">{esc(r.page)}</td></tr>")
fda_ms = ", ".join(esc(x) for x in fda[fda.element_kind == "milestone"].element_label)
ms_cols = fda[fda.element_kind == "milestone"]["columns"].iloc[0]

# WOAH: structure only
woah = tel[tel.source == "WOAH2026"]
woah_rows = []
for g, sub in woah.groupby("group", sort=False):
    woah_rows.append(f"<tr><th class=\"area\" colspan=\"3\">{esc(g)}</th></tr>" + tpp_rows(sub, []))

# PaVe-GT
pave = tel[tel.source == "PAVEGT"]
assert pave.page.isna().all()
pave_rows = []
for r in pave.itertuples():
    same = r.minimum_equals_ideal == "True"
    texts = (tpp_text("Minimum acceptable result and ideal result (the same):", r.guidance_minimum_acceptable_result) if same
             else tpp_text("Minimum acceptable result:", r.guidance_minimum_acceptable_result)
             + tpp_text("Ideal result:", r.guidance_ideal_result))
    pave_rows.append(f"<tr><td class=\"num\">{esc(r.element_id)}</td><td><details><summary>{esc(r.element_label)}"
                     f"</summary>{texts}</details></td></tr>")

# SEED: labels across the four examples, values per example
seed = tel[tel.family == "SEED"]
seed_meta = tmeta["SEED"]
seed = seed.assign(grp=seed.group.fillna(""))
lab_order = list(dict.fromkeys(zip(*[seed.sort_values(["source", "element_id"], key=lambda c: c.map(
    {k: i for i, k in enumerate(TPP_SEED)}) if c.name == "source" else c.astype(int))[c] for c in ("grp", "element_label")])))
seed_head = "".join(f"<th class=\"dsa\">{esc(seed_meta[k]['Product Type'])}<br><span class=\"dname\">"
                    f"{esc(seed_meta[k]['Indication'])}</span></th>" for k in TPP_SEED)
seed_rows = []
for grp, lab in lab_order:
    cells = []
    for k in TPP_SEED:
        hit = seed[(seed.source == k) & (seed.grp == grp) & (seed.element_label == lab)]
        assert len(hit) <= 1, (k, lab)
        if hit.empty:
            cells.append('<td class="num miss"><span></span></td>')
            continue
        h = hit.iloc[0]
        texts = (tpp_text("Minimal:", h.example_value_minimal_acceptance_criteria)
                 + tpp_text("Preferred:", h.example_value_preferred_acceptance_criteria)
                 + tpp_text("", h.example_value_description))
        cells.append(f"<td><details><summary>{esc(h.element_id)}</summary>{texts}</details></td>")
    seed_rows.append(f"<tr><td class=\"title\">{esc(lab)}<br><span class=\"muted\">{esc(grp)}</span></td>"
                     + "".join(cells) + "</tr>")
n_seed_all = sum(1 for grp, lab in lab_order
                 if seed[(seed.grp == grp) & (seed.element_label == lab)].source.nunique() == 4)

tpp_body = f"""<h1>TPP templates compared</h1>
<p>Four public Target Product Profile templates and examples, read by script into one table of 172 elements
({n_tkind['attribute']} attributes, {n_tkind['label_section']} label sections, {n_tkind['label_subsection']} label
subsections, {n_tkind['milestone']} milestones). How they were read:
<a href="{BLOB}tpp-templates/README.md">README</a> and the
<a href="{BLOB}tpp-templates/tpp_template_comparison.ipynb">notebook</a>.</p>
<div class="table-wrap"><table>
<tr><th>Key</th><th>Source</th><th>What is shown</th></tr>
<tr><td><b>FDA2007</b></td><td>FDA draft guidance <i>Target Product Profile — A Strategic Development Process Tool</i>,
Appendix C, March 2007 (<a href="{tpp_url('FDA2007')}">copy on fda.report</a>; no longer on fda.gov)</td>
<td>Labels, prompts and guidance: a work of the US government</td></tr>
<tr><td><b>WOAH2026</b></td><td>WOAH <i>Target Product Profile – Template for animal vaccines</i>, February 2026
(<a href="{tpp_url('WOAH2026')}">woah.org</a>)</td>
<td>Structure only: numbers, labels, groups, columns. WOAH's <a href="{WOAH_TERMS}">terms of use</a> do not allow its
content to be copied or stored by extraction tools without written permission; the text of its Comments column is not
shown and not kept in the repository.</td></tr>
<tr><td><b>PAVEGT</b></td><td>NCATS PaVe-GT <i>TPP Template</i> for AAV gene therapy, 2025
(<a href="{tpp_url('PAVEGT')}">pave-gt.ncats.nih.gov</a>)</td>
<td>Labels and guidance: public domain per the PaVe-GT terms, which ask that NIH be acknowledged</td></tr>
<tr><td><b>SEED</b></td><td>NIH SEED example TPPs: {', '.join(f'<a href="{tpp_url(k)}">{esc(seed_meta[k]["Product Type"])}</a>' for k in TPP_SEED)}</td>
<td>Labels and example values: a work of the US government. Each example opens: "This information should not be
considered to represent advice or guidance on behalf of the U.S. Department of Health and Human Services or any
agency or office thereof."</td></tr>
</table></div>
<h2>Column models</h2>
<p class="muted">The columns each element is filled in, with the number of elements in brackets. This is what
distinguishes the families: a target with its evidence (FDA), ideal and minimum (WOAH), minimum acceptable and ideal
result (PaVe-GT), minimal and preferred acceptance criteria (SEED).</p>
<div class="table-wrap"><table>
<tr><th>Family</th><th>Columns</th><th>Elements</th></tr>
{''.join(cm_rows)}
</table></div>
<h2>Labels shared across families</h2>
<p class="muted">Labels matched only on exact normalised text: {len(tinv)} labels, {n_fam[1]} in one family,
{n_fam[2]} in two, {n_fam[3]} in three, none in all four. Cells give each family's element number. Related labels with
different wording are not merged: the <a href="{BLOB}{TPP_INPUTS['crosswalk']}">crosswalk for review</a> has
{len(tcw)} rows with an empty <code>concept</code> column, left for a human decision.</p>
<div class="table-wrap"><table>
<tr><th>Label (normalised)</th>{''.join(f'<th class="num">{c}</th>' for c in inv_cols)}</tr>
{sh_rows}
</table></div>
<h2>FDA 2007: the TPP as draft labeling</h2>
<p class="muted">{(fda.element_kind == 'label_section').sum()} label sections in the order of the drug label, each with
its SPL section LOINC code; open a section for its Target and Annotations prompts, guidance and subsections. The TPP is
also versioned: a milestone box records, for {fda_ms}, the columns {esc(ms_cols)}.</p>
<div class="table-wrap"><table>
<tr><th class="num">#</th><th>Label section</th><th class="num">SPL LOINC</th><th class="num">Page</th></tr>
{''.join(fda_sec)}
</table></div>
<h2>WOAH 2026: animal vaccines</h2>
<p class="muted">{len(woah)} attributes in {woah.group.nunique()} groups, each with the columns Ideal, Minimum and
Comments ({esc(tmeta['WOAH2026']['table_title'])}). Structure only, see above.</p>
<div class="table-wrap"><table>
<tr><th class="num">#</th><th>Attribute</th><th class="num">Page</th></tr>
{''.join(woah_rows)}
</table></div>
<h2>PaVe-GT 2025: AAV gene therapy</h2>
<p class="muted">{len(pave)} attributes with a minimum acceptable and an ideal result; for
{(pave.minimum_equals_ideal == 'True').sum()} of them the template gives the same text for both. A Word table, so no
page numbers.</p>
<div class="table-wrap"><table>
<tr><th class="num">#</th><th>Attribute</th></tr>
{''.join(pave_rows)}
</table></div>
<h2>NIH SEED: four worked examples</h2>
<p class="muted">The same frame filled in for four products: {len(lab_order)} labels across the four, {n_seed_all} in all
four (a label counted once per group). The first rows carry minimal and preferred acceptance criteria, the rest a
description. A dashed cell: the label is
not in that example. Open a number for the example's values.</p>
<div class="table-wrap"><table class="matrix">
<tr><th>Label<br><span class="dname">group</span></th>{seed_head}</tr>
{''.join(seed_rows)}
</table></div>
"""
(DOCS / "templates" / "tpp" / "index.html").write_text(
    page("TPP templates compared", 2, tpp_body, wide=True, inputs=list(TPP_INPUTS.values())), encoding="utf-8")

templates_cards = [
    area_card("eupearl/", "EU-PEARL templates as data",
              [", ".join(f"{d} {n}" for d, n in tot.items()) + " sections",
               f"MPT and ISA side by side: {n_match['both']} in both, {n_match['mpt_only']} MPT only, "
               f"{n_match['isa_only']} ISA only; {len(fld)} field labels"]),
    area_card("remapcap-dsa/", "REMAP-CAP: the DSA template no document states",
              [f"{len(dh)} headings of the nine DSAs under {len(n_docs)} titles: {dist.get(len(dsa_keys), 0)} in all nine, "
               f"{len(order)} in two or more"]),
    area_card("tpp/", "TPP templates compared",
              [f"{len(tel)} elements from FDA 2007, WOAH 2026, PaVe-GT and four NIH SEED examples",
               f"Four column models; {len(tinv)} labels, {(tinv.n_families.astype(int) > 1).sum()} shared by two or more "
               f"families"]),
]
(DOCS / "templates" / "index.html").write_text(page("Templates as data", 1, f"""<h1>Templates as data</h1>
{md_to_html(templates_md)}
<div class="cards">{''.join(templates_cards)}</div>
""", inputs=[INPUTS["readme"]] + list(EUP_INPUTS.values()) + [RDSA_INPUTS["headings"]] + [TPP_INPUTS["elements"],
           TPP_INPUTS["inventory"]]), encoding="utf-8")

landing_cards = [
    area_card("questions/", "The questions",
              [f"{len(questions)} competency questions; the catalogue holds {n_kind.get('finding', 0)} findings, "
               f"{n_kind.get('case question', 0)} case questions and {n_kind.get('open', 0)} open questions"]),
    area_card("cases/", "The two cases",
              [f"CPMP: master and {len(grid)} ISAs", f"REMAP-CAP: {len(rdocs)} documents read"]),
    area_card("usdm/", "USDM v4 and master protocols",
              [f"Both cases as USDM v4 JSON, validated; {len(bp)} breakpoints where USDM could not carry them"]),
    area_card("templates/", "Templates as data",
              [f"EU-PEARL: {len(tot)} templates with their heading trees, MPT and ISA side by side",
               f"REMAP-CAP: the DSA template read from {len(dsa_keys)} DSAs"]),
]
vision_md = (ROOT / VISION).read_text(encoding="utf-8")
vision_title, vision_rest = vision_md.split("\n", 1)
assert vision_title == "# Where this is heading", vision_title
(DOCS / "vision" / "index.html").write_text(page("Where this is heading", 1, f"""<h1>Where this is heading</h1>
{md_to_html(vision_rest)}
""", inputs=[VISION]), encoding="utf-8")
intro_html = md_to_html(intro)
heading_p = re.findall(r'<p><strong>Where this is heading:</strong>(.*?) See <a href="' + re.escape(BLOB + VISION) + r'">VISION\.md</a>\.</p>',
                       intro_html, flags=re.S)
assert len(heading_p) == 1, "README intro must end with one 'Where this is heading:' paragraph linking VISION.md"
intro_html = re.sub(r'<p><strong>Where this is heading:</strong>.*?</p>',
                    f'<p class="lead"><a href="vision/"><b>Where this is heading</b></a>:{heading_p[0]}</p>', intro_html, flags=re.S)
index_body = f"""<h1>Early clinical design research</h1>
{intro_html}
<div class="cards four">{''.join(landing_cards)}</div>
"""
(DOCS / "index.html").write_text(page("Early clinical design research", 0, index_body), encoding="utf-8")

print(f"docs/: index.html, vision, 3 area pages, {len(questions)} question pages, 2 case pages, 3 template pages, 2 M11 pages")
