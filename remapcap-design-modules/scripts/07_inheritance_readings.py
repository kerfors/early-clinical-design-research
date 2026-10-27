"""REMAP-CAP design modules, step 5 part 1: resolution of DSA inheritance statements.

Input: output/step1/cross_references.csv (DSA -> CORE / PANDA / SAA statements that are not
mention_only), output/step1/sections.csv, sources/topic_rules.csv, the agreed CS_DSA readings
(../usdm-master-protocol/output_remapcap/step5/inherited_from_core.csv, 2026-10-24).
Output: output/step5/inheritance_readings.csv, output/step5/run.log (stdout).

Rules (README, step 5):
  T-target    the phrase the statement points at: "core protocol documents" (any case,
              with or without "relevant") -> document set (decision 6); otherwise "Core Protocol"
              -> the Core Protocol document.
  T-topic     sources/topic_rules.csv, in order, first match wins (case-insensitive). All
              matching rules are logged. No match -> unresolved (not guessed).
              A rule with a title_term must find that term in its target section's title
              (Core 4.1 / PANDA); otherwise the script stops.
  T-binding   no statement names a Core version -> "unversioned"; a version_scoped statement
              that points at "the current version" -> "current (study website)".
  T-changed   a resolved target section is "changed in 4.1" if its step 1 text differs between
              Core 4.0 and 4.1 (PANDA has one version).
  Gate        the rules reproduce the 12 agreed CS_DSA readings (section -> location).
Every row is an analyst-reading for Kerstin's review.
"""
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent.parent
STEP1 = HERE / "output" / "step1"
OUT = HERE / "output" / "step5"
OUT.mkdir(parents=True, exist_ok=True)
AGREED = HERE.parent / "usdm-master-protocol" / "output_remapcap" / "step5" / "inherited_from_core.csv"

xr = pd.read_csv(STEP1 / "cross_references.csv", dtype=str, keep_default_na=False)
sections = pd.read_csv(STEP1 / "sections.csv", dtype=str, keep_default_na=False)
rules = pd.read_csv(HERE / "sources" / "topic_rules.csv", dtype=str, keep_default_na=False).sort_values(
    "order", key=lambda s: s.astype(int))

title = {}
for r in sections.itertuples():
    if r.doc == "CORE41":
        title["CORE " + r.number] = r.title
    elif r.doc == "PANDA":
        title["PANDA " + r.number] = r.title
for r in rules.itertuples():
    for t in r.targets.split(";"):
        assert t in title, f"rule {r.order}: no section {t}"
    if r.title_term:
        assert all(r.title_term.lower() in title[t].lower() for t in r.targets.split(";")), \
            f"rule {r.order}: title term {r.title_term!r} not in {[title[t] for t in r.targets.split(';')]}"

t40 = sections[sections.doc == "CORE40"].set_index("number").text
t41 = sections[sections.doc == "CORE41"].set_index("number").text


def changed(target):
    doc, num = target.split(" ")
    if doc != "CORE":
        return ""
    if num not in t40.index:
        return "new in 4.1"
    return "changed in 4.1" if t40[num] != t41[num] else ""


stm = xr[(xr.layer == "DSA") & xr.target.isin(["CORE", "PANDA", "SAA"]) & (xr.relation != "mention_only")].copy()
rows = []
for s in stm.itertuples():
    low = s.sentence.lower()
    hits = [r for r in rules.itertuples() if re.search(r.pattern.lower(), low)]
    if s.target == "SAA":
        target_phrase, res, rule, src = "Statistical Analysis Appendix", "", "", "out of scope (SAA not in scope)"
    else:
        target_phrase = "document set: core protocol documents" if re.search(r"core protocol documents?", low) \
            else "document: Core Protocol"
        if s.relation == "version_scoped":
            res, rule, src = "", "", "version_scoped: names the current version, no section"
        elif hits:
            res, rule, src = hits[0].targets, hits[0].order, hits[0].source
        else:
            res, rule, src = "", "", "unresolved: no topic rule matches"
    binding = "current (study website)" if s.relation == "version_scoped" and "current version" in low else (
        "unversioned" if s.target != "SAA" else "")
    rows.append({"doc": s.doc, "section": s.section, "relation": s.relation, "target_phrase": target_phrase,
                 "binding": binding, "resolution": res, "rule": rule, "rule_source": src,
                 "all_matching_rules": ";".join(r.order for r in hits),
                 "target_titles": " | ".join(title[t] for t in res.split(";")) if res else "",
                 "target_change": ";".join(c for c in (changed(t) for t in res.split(";")) if c) if res else "",
                 "status": "analyst-reading", "sentence": s.sentence})
out = pd.DataFrame(rows)

# Gate: the agreed CS_DSA readings are reproduced
agreed = pd.read_csv(AGREED, dtype=str, keep_default_na=False)
cs = out[out.doc == "CS_DSA"]
for a in agreed.itertuples():
    got = set(cs[cs.section == a.dsa_section].resolution)
    want = a.core_location.replace("; ", ";")
    assert want in got, f"gate: CS_DSA {a.dsa_section}: agreed {want}, rules give {got}"
print(f"gate ok: {len(agreed)} agreed CS_DSA readings reproduced")

out.to_csv(OUT / "inheritance_readings.csv", index=False)
print(f"statements: {len(out)}")
print(out.groupby(["doc", "target_phrase"]).size().unstack(fill_value=0).to_string())
print("resolved:", int((out.resolution != "").sum()), " unresolved/other:", int((out.resolution == "").sum()))
print(out[out.resolution == ""][["doc", "section", "rule_source", "sentence"]].to_string(max_colwidth=90))
multi = out[out.all_matching_rules.str.contains(";")]
print("statements matching more than one rule (first wins):")
print(multi[["doc", "section", "all_matching_rules", "resolution", "sentence"]].to_string(max_colwidth=80))
print("resolved targets changed in Core 4.1:")
print(out[out.target_change != ""].groupby(["resolution", "target_change"]).doc.apply(lambda v: ";".join(sorted(set(v)))).to_string())
