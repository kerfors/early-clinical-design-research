"""Build the GitHub Pages site in docs/ from the committed catalogue and README.

Pages (first slice):
- docs/index.html: the README introduction (up to "## The questions"), the README section
  "## The two cases", then the ten questions as cards with, per case, the number of findings, case questions and open
  questions, and which reviewer still has readings to look at.
- docs/questions/<Q>/index.html: one page per question, the catalogue rows of that
  question by case, as in competency-questions/output/catalogue.md.
- docs/cases/cpmp/index.html: the CPMP documents. The compound x disease grid of the 12 ISAs
  from usdm-master-protocol/output_cpmp/step5/grid.csv (read from each ISA's section 5);
  NCT ID, secondary ID and posted protocol (date, link) from the ClinicalTrials.gov records in
  usdm-master-protocol/sources/ctgov_api/cpmp_studies.json. The DSAs are not public: shown as
  dashed boxes, named only by disease. Records with a H0P-MC- secondary ID outside the grid are
  listed with what is posted for them.
- docs/cases/remapcap/index.html: the REMAP-CAP documents in scope (version and date as read
  from each document's header: remapcap-design-modules/output/documents.csv), the other current
  documents and the superseded listings on remapcap.org (usdm-master-protocol/sources/remapcap/manifest.csv).
- docs/templates/eupearl/index.html: the EU-PEARL templates as data, from eupearl-templates/output_eupearl/:
  the MPT and ISA side by side on the committed alignment (ISA-only sections placed after the ISA section
  they follow), the SAP and DMC heading trees, and the MPT and ISA field labels. Per section, the number of
  paragraphs of each text kind, not the text: the templates are copyright EU-PEARL Consortium (and
  TransCelerate for the CPT-based parts), with no open licence. A "show as data" switch reveals the keys.

Inputs (read only, all committed): README.md, competency-questions/sources/questions.csv,
competency-questions/output/catalogue.csv, evidence-matrix/sources/requirements.csv, and the
case inputs above. Each page ends with a provenance line: its input files and their sha256. No build time,
so an unchanged input gives byte-identical pages.

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
from pathlib import Path

import markdown
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
REPO = "https://github.com/kerfors/early-clinical-design-research"
BLOB = REPO + "/blob/main/"
SITE = "https://kerfors.github.io/early-clinical-design-research/"
SCRIPT = "scripts/build_site.py"

INPUTS = {
    "readme": "README.md",
    "questions": "competency-questions/sources/questions.csv",
    "catalogue": "competency-questions/output/catalogue.csv",
    "requirements": "evidence-matrix/sources/requirements.csv",
}
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
KIND_ORDER = ["finding", "case question", "earlier", "open", "not asked"]
KIND_PLURAL = {"finding": "findings", "case question": "case questions"}
CASE_ORDER = ["CPMP", "REMAP-CAP", "both"]
REVIEWERS = ["trial-design reviewer", "clinical reader"]

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
.side .colhead { font-size: 0.8rem; color: var(--muted); font-weight: 600; }
.side .box { font-size: 0.82rem; }
.side .rel { font-size: 0.75rem; color: var(--muted); align-self: center; }
.side .empty { border: 1.5px dashed var(--line); border-radius: 5px; }
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


def page(title, depth, body, wide=False, inputs=None):
    up = "../" * depth
    prov = "; ".join(f'<a href="{BLOB}{p}">{p}</a> sha256 <code>{sha256(p)[:12]}</code>' for p in (inputs or list(INPUTS.values())))
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
<nav><a href="{up}">Early clinical design research</a> · <a href="{up}cases/cpmp/">CPMP</a> · <a href="{up}cases/remapcap/">REMAP-CAP</a> · <a href="{up}templates/eupearl/">EU-PEARL templates</a> · <a href="{REPO}">repository</a></nav>
{body}
</main>
<footer{' class="wide"' if wide else ''}>Generated by <a href="{BLOB}{SCRIPT}">{SCRIPT}</a> from {prov}. Namespace for now:
<code>{SITE}</code>. Code MIT, derived content CC BY 4.0.</footer>
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

if DOCS.exists():
    shutil.rmtree(DOCS)
(DOCS / "questions").mkdir(parents=True)
(DOCS / "cases" / "cpmp").mkdir(parents=True)
(DOCS / "cases" / "remapcap").mkdir(parents=True)
(DOCS / "templates" / "eupearl").mkdir(parents=True)
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
<h3><span class="qid">{q.q_id}</span><a href="questions/{q.q_id}/">{esc(q.question)}</a></h3>
<p>{req_names}</p>
<p>{'<br>'.join(per_case)}</p>
{f'<p>{wait_html}</p>' if wait_html else ''}
</div>""")

index_body = f"""<h1>Early clinical design research</h1>
{md_to_html(intro)}
<h2>The two cases</h2>
{md_to_html(cases_md)}
<p>The documents of each case, as layers: <a href="cases/cpmp/">CPMP</a> · <a href="cases/remapcap/">REMAP-CAP</a>.</p>
<h2>Templates as data</h2>
{md_to_html(templates_md)}
<p>The EU-PEARL templates as data, with the MPT and ISA side by side: <a href="templates/eupearl/">EU-PEARL templates</a>.</p>
<h2>The questions</h2>
<p class="muted">Each card counts what the catalogue holds per case: findings with document evidence, case questions
answered by SPARQL over the design modules, and questions still open. Earlier answers (before the modules) are on
the question pages.</p>
<div class="cards">
{chr(10).join(cards)}
</div>
"""
(DOCS / "index.html").write_text(page("Early clinical design research", 0, index_body), encoding="utf-8")

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
            cls = "unanswered" if r.kind in ("open", "not asked") else "answered"
            wait_html = "".join(f'<span class="chip wait">waits for {w}</span>' for w in waits(r.review))
            trs.append(f"""<tr class="{cls}"><td>{esc(r.kind)}</td><td class="item">{item}</td><td>{esc(r.text)}</td><td>{esc(r.answer)}</td>
<td>{esc(r.check)}</td><td>{status_chips(r.status)}</td><td>{esc(r.evidence_rows)}</td><td>{esc(r.review)}{(' ' + wait_html) if wait_html else ''}</td></tr>""")
        sections.append(f"""<h2>{case}</h2>
<div class="table-wrap"><table>
<thead><tr><th>Kind</th><th>Item</th><th>Question or finding</th><th>Answer</th><th>Check</th><th>Status</th><th>Evidence rows</th><th>Review</th></tr></thead>
<tbody>
{chr(10).join(trs)}
</tbody></table></div>""")
    body = f"""<h1>{q.q_id}. {esc(q.question)}</h1>
<ul>{req_html}</ul>
<p class="muted">Solid left edge: answered (finding, case question or earlier answer). Dashed: open or not asked.
Status gives the kinds of evidence behind a finding, with counts when there is more than one kind; evidence rows are
in <a href="{BLOB}evidence-matrix/output/evidence_matrix.csv">evidence_matrix.csv</a>. Same rows as the
<a href="{BLOB}competency-questions/output/catalogue.md">catalogue</a>.</p>
{chr(10).join(sections)}
"""
    out = DOCS / "questions" / q.q_id
    out.mkdir()
    (out / "index.html").write_text(page(f"{q.q_id}. {q.question}", 2, body, wide=True), encoding="utf-8")


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
cells = ['<div></div>'] + [f'<div class="head">{html.escape(c)}</div>' for c in compounds]
for dis in DISEASE_ORDER:
    cond = sorted({reg[d]["conditions"][0] for d in grid[grid.disease == dis].doc})
    cells.append(f'<div class="box dashed"><b>{dis} DSA</b><span class="muted">not public; '
                 f'{html.escape(", ".join(cond))}</span></div>')
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
<div class="table-wrap"><div class="grid4">
{chr(10).join(cells)}
</div></div>
<p class="muted">The 13 Schedules of Activities (master and 12 ISAs) are extracted to USDM in
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
            f'<span class="muted">{esc(r.date)} · <a href="{esc(r.url)}">remapcap.org</a> · {esc(r.short)}</span></div>')


layer_html = {lay: "".join(rbox(r) for r in rdocs[rdocs.layer == lay].itertuples()) for lay in ["CORE", "PANDA", "DSA"]}
out_scope = manifest[(manifest.listing == "current") & ~manifest.url.isin(rdocs.url)]
sup = manifest[manifest.listing == "superseded"].copy()
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
<h2>Other current documents on remapcap.org (not read here)</h2>
<div class="table-wrap"><table><tbody>{out_rows}</tbody></table></div>
<h2>Superseded versions listed on remapcap.org</h2>
<p class="muted">Names as the listing gives them.</p>
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
templates' own styles and markers. The text itself is not shown: the templates are © EU-PEARL Consortium, the MPT, ISA
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

print(f"docs/: index.html, {len(questions)} question pages, 2 case pages, 1 template page")
