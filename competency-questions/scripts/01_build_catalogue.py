"""Competency question catalogue: general questions, with their case questions and findings.

Authored (reviewed by Kerstin): sources/questions.csv (general questions, requirements) and
sources/case_questions.csv (which case question, finding or open question belongs to which
general question, and review still pending: not yet reviewed, or the reviewer it waits for). Everything else is read from the committed outputs of the builds:

- CPMP case questions: answer and check from cpmp-design-modules/output/cq_results.csv.
- REMAP-CAP case questions: the query file must be run and asserted against pandas in
  remapcap-design-modules/notebooks/01_cq_check.ipynb; the answers are in the findings.
- Findings: expected, observed and check from evidence-matrix/output/findings_checked.csv;
  status from the evidence rows in evidence-matrix/output/evidence_matrix.csv; review of analyst
  readings from remapcap-design-modules/sources/reading_reviews.csv (decisions by Kerstin).
- Inheritance readings: remapcap-design-modules/sources/inheritance_reviews.csv must hold one review
  per reading in remapcap-design-modules/output/step5/inheritance_readings.csv, with the same
  resolution and rule as reviewed (a changed reading needs a new review).
- Earlier questions: the file they were answered in (row count for a CSV).
- Open questions: the file that states them.

Checks (fail fast): every finding is placed exactly once; every CPMP case question in
cq_results.csv and every query file in both queries/ folders is placed; every referenced
file exists.

Output: output/catalogue.csv and output/catalogue.md.
Run:    python3 competency-questions/scripts/01_build_catalogue.py   (from the repo root)
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = ROOT / "competency-questions"
OUT = HERE / "output"
RCAP_NB = ROOT / "remapcap-design-modules" / "notebooks" / "01_cq_check.ipynb"
KINDS = ["case question", "finding", "earlier", "open", "not asked"]

questions = pd.read_csv(HERE / "sources" / "questions.csv", dtype=str)
cases = pd.read_csv(HERE / "sources" / "case_questions.csv", dtype=str).fillna("")
cpmp = pd.read_csv(ROOT / "cpmp-design-modules" / "output" / "cq_results.csv", dtype=str)
findings = pd.read_csv(ROOT / "evidence-matrix" / "output" / "findings_checked.csv", dtype=str)
statements = pd.read_csv(ROOT / "evidence-matrix" / "sources" / "findings.csv", dtype=str).set_index("finding_id").finding
matrix = pd.read_csv(ROOT / "evidence-matrix" / "output" / "evidence_matrix.csv", dtype=str)
rcap_nb = RCAP_NB.read_text(encoding="utf-8")
reviews = pd.read_csv(ROOT / "remapcap-design-modules" / "sources" / "reading_reviews.csv", dtype=str)
inh = pd.read_csv(ROOT / "remapcap-design-modules" / "output" / "step5" / "inheritance_readings.csv", dtype=str).fillna("")
inh_reviews = pd.read_csv(ROOT / "remapcap-design-modules" / "sources" / "inheritance_reviews.csv", dtype=str).fillna("")

assert set(cases.q_id) == set(questions.q_id), "every general question needs at least one row"
assert set(cases.kind) <= set(KINDS), set(cases.kind) - set(KINDS)

cpmp["item_id"] = cpmp.question.str.split().str[0]
cpmp = cpmp[cpmp.item_id.str.startswith("CQ")].set_index("item_id")
findings = findings.set_index("finding_id")
matrix["status_kind"] = matrix.status.str.split(":").str[0].str.strip()
STATUS_ORDER = ["document fact", "document fact (identity decided by Kerstin)", "rule-derived",
                "rule-derived from analyst readings", "analyst-reading", "decision by Kerstin"]
assert set(matrix.status_kind) <= set(STATUS_ORDER), set(matrix.status_kind) - set(STATUS_ORDER)


def status_text(kinds):
    """Labels in a fixed order; counts per label only when a finding has more than one kind."""
    n = kinds.value_counts()
    labels = [k for k in STATUS_ORDER if k in n]
    return "; ".join(f"{k} {n[k]}" if len(labels) > 1 else k for k in labels)


status = matrix.groupby("finding_id").status_kind.agg(status_text)
n_rows = matrix.groupby("finding_id").size()

readings = matrix[matrix.status.str.startswith("analyst")]
reviewed = readings[readings.finding_id.isin(reviews.finding_id)]
assert not reviews.duplicated(["finding_id", "source_key"]).any(), "one review row per reading"
assert set(zip(reviews.finding_id, reviews.source_key)) == set(zip(reviewed.finding_id, reviewed.source_key)), \
    "every analyst reading of a reviewed finding needs exactly one review row"
INH_KEY = ["doc", "section", "sentence"]
assert not inh.duplicated(INH_KEY).any() and not inh_reviews.duplicated(INH_KEY).any(), "one row per inheritance reading"
inh_join = inh.merge(inh_reviews, on=INH_KEY, how="outer", suffixes=("", "_reviewed"), indicator=True)
assert (inh_join._merge == "both").all(), inh_join[inh_join._merge != "both"][INH_KEY + ["_merge"]].to_string()
changed = inh_join[(inh_join.resolution != inh_join.resolution_reviewed) | (inh_join.rule != inh_join.rule_reviewed)]
assert changed.empty, "reading changed since review:\n" + changed[INH_KEY + ["resolution", "resolution_reviewed"]].to_string()
assert set(inh_reviews.decision) <= {"confirmed", "confirmed: unresolved as decided"}, set(inh_reviews.decision)

review_summary = reviews.groupby("finding_id").decision.agg(
    lambda s: "readings: " + ", ".join(f"{n} {k}" for k, n in s.value_counts().items()))

placed = cases[cases.kind == "finding"].item_id
assert placed.is_unique, placed[placed.duplicated()].tolist()
assert set(placed) == set(findings.index), set(findings.index) ^ set(placed)
cq_placed = cases[(cases.case == "CPMP") & (cases.kind == "case question")].item_id
assert set(cq_placed) == set(cpmp.index), set(cpmp.index) ^ set(cq_placed)
rq_files = {str(p.relative_to(ROOT)) for p in ROOT.glob("*-design-modules/queries/*.rq")}
assert rq_files == set(cases[cases["query"].str.endswith(".rq")]["query"]), rq_files ^ set(cases["query"])
for q in cases[cases["query"] != ""]["query"]:
    assert (ROOT / q).is_file(), q



def rq_header(path):
    """The query's own question: its leading comment lines up to the first line ending a sentence.

    A header line ending in ":" followed by an indented column list ("#   name   description")
    gets the descriptions appended, so the question is not cut at the colon.
    """
    lines, items = [], []
    for ln in (ROOT / path).read_text(encoding="utf-8").splitlines():
        if not ln.startswith("#"):
            break
        if ln.startswith("#   "):
            items.append(re.split(r"\s{2,}", ln[1:].strip(), maxsplit=1)[-1])
            continue
        if items:
            break
        lines.append(ln.lstrip("# ").strip())
        if lines[-1].endswith(("?", ".")):
            break
    text = " ".join(lines)
    if items:
        text = f"{text} {'; '.join(items)}."
    return re.sub(r"^(R|CQ)\d[a-z]?( \(statement level\))?: ", "", text)


rows = []
for c in cases.itertuples():
    text, answer, check, stat, n_ev = "", "", "", "", ""
    if c.kind == "case question" and c.case == "CPMP":
        r = cpmp.loc[c.item_id]
        text, answer, check = rq_header(c.query), r.answer, f"{r.check} (against pandas, cq_results.csv)"
    elif c.kind == "case question" and c.case == "REMAP-CAP":
        assert Path(c.query).name in rcap_nb, c.query
        text, answer = rq_header(c.query), "in the findings"
        check = "asserted against pandas in notebooks/01_cq_check.ipynb"
    elif c.kind == "finding":
        f = findings.loc[c.item_id]
        text, answer, check, stat = statements[c.item_id], f.observed, f.check, status[c.item_id]
        assert int(f.evidence_rows) == n_rows[c.item_id], c.item_id
        n_ev = f.evidence_rows
    elif c.kind == "earlier":
        if c.query.endswith(".csv"):
            answer = f"{len(pd.read_csv(ROOT / c.query))} rows"
        stat = "earlier"
    elif c.kind == "open":
        answer, stat = "not answered", "open"
    rows.append({"q_id": c.q_id, "case": c.case, "kind": c.kind, "item_id": c.item_id, "text": text,
                 "review": "; ".join(x for x in [review_summary.get(c.item_id, ""), c.review] if x),
                 "query": c.query, "answer": answer, "check": check, "status": stat,
                 "evidence_rows": n_ev, "note": c.note})
cat = pd.DataFrame(rows)
cat = cat.merge(questions, on="q_id", how="left")
order = {q: i for i, q in enumerate(questions.q_id)}
cat["_q"] = cat.q_id.map(order)
cat["_k"] = cat.kind.map({k: i for i, k in enumerate(KINDS)})
cat = cat.sort_values(["_q", "case", "_k"], kind="stable")
cols = ["q_id", "question", "requirements", "case", "kind", "item_id", "text", "query", "answer", "check", "status", "evidence_rows", "review", "note"]
OUT.mkdir(exist_ok=True)
cat[cols].to_csv(OUT / "catalogue.csv", index=False)


def cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


md = ["# Competency questions", "",
      "Generated by `scripts/01_build_catalogue.py` from `sources/` and the committed outputs of the builds. "
      "Do not edit by hand.", "",
      "Columns: *Check* says how an answer was checked. *Status* gives the kinds of evidence behind a finding "
      "(labels as in the root README, Terms; with counts when a finding has more than one kind), and *Evidence rows* "
      "their total in `evidence-matrix/output/evidence_matrix.csv`. Case questions have no status or evidence rows: they are "
      "queries, and their answer is checked as the Check column says. *Review* gives what is reviewed and what "
      "still waits, and for whom.", ""]
for q in questions.itertuples():
    md += [f"## {q.q_id}. {q.question}", "", f"Requirements: {q.requirements.replace(';', ', ')}", "",
           "| Case | Kind | Item | Question or finding | Answer | Check | Status | Evidence rows | Review |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in cat[cat.q_id == q.q_id].itertuples():
        item = f"[{r.item_id}](../../{r.query})" if r.query else r.item_id
        text = r.text if r.text else r.note
        ans = r.answer
        md.append(f"| {r.case} | {r.kind} | {cell(item)} | {cell(text)} | {cell(ans)} | {cell(r.check)} | "
                  f"{cell(r.status)} | {cell(r.evidence_rows)} | {cell(r.review)} |")
    md.append("")
(OUT / "catalogue.md").write_text("\n".join(md), encoding="utf-8")

print(f"{len(questions)} questions, {len(cat)} rows:", cat.kind.value_counts().to_dict())
print(f"inheritance readings: {len(inh)}, all reviewed:", inh_reviews.decision.value_counts().to_dict())
