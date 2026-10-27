"""REMAP-CAP design modules, step 5 part 2: DSA responses to Core 4.1 delegations and defaults.

Input: output/step1/cross_references.csv (CORE41 -> DSA, delegates / default_overridable: 21),
output/step1/sections.csv, output/step2/components.csv (DSA 8.3.1 arms),
output/step5/statement_versions.csv (DSA dates), sources/template_map.csv,
sources/response_rules.csv, ../cdd-layer/output/cq2_pairing_draft.csv (comparison only).
Output (default output/step5, or the directory given as argument 1):
delegation_readings.csv, delegation_readings_by_state.csv, cq2_comparison.csv; stdout is the run log.

Rules (README, step 5 part 2, agreed 2026-10-25):
  M-map       each of the 21 Core 4.1 statements is matched by core_section + core_key to exactly
              one template_map row. Primary / secondary sections are resolved per DSA by
              num:<n>, prefix:<n>, title:<start of title> or exact:<whole title>
              (case-insensitive).
  M-topic     a row with topic_pattern reads only the sentences that match it; otherwise the
              whole primary section. Secondary sections: only sentences matching secondary_pattern.
  D-*         delegations, first match wins: no primary sentence -> no_answer
              (conditional row: condition_not_stated); negation -> fills_none; every sentence
              backref + defers_only -> defers_back; any backref -> fills_by_reference; else fills.
  F-*         defaults, first match wins: no topic sentence -> silent; overrides_pattern ->
              overrides; takes_pattern -> takes; modal -> ambiguous; else ambiguous.
  S-state     per_state = two_interventions: arms = DSA 8.3.1 items; an arm with "(X State only)"
              counts in X only, any other arm in every state named in DSA 8.1.2. Count != 2 ->
              condition_not_met in that state; count == 2 -> the text response.
  S-control   per_state = control_arm: not evaluated (trial-design); response ambiguous, with
              every sentence naming "control" in the secondary section as evidence.
  R-role      umbrella row: recorded, response umbrella_not_paired. descriptive row: response
              descriptive_no_slot, with its evidence sentences.
  V-core40    the Core 4.0 sentence of the same section and relation that is most similar is
              carried, with same_text_4_0.
  V-transition row 6 (primary outcome), DSA dated before Core 4.1: Core 7.6.2 transition noted.
Every row is an analyst-reading for Kerstin's review.
"""
import difflib
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent.parent
STEP1 = HERE / "output" / "step1"
STEP2 = HERE / "output" / "step2"
STEP5 = HERE / "output" / "step5"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else STEP5
OUT.mkdir(parents=True, exist_ok=True)
DRAFT = HERE.parent / "cdd-layer" / "output" / "cq2_pairing_draft.csv"
from rcap_docs import DSAS  # scripts/rcap_docs.py
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")  # as scripts/01_extract_structure.py

xr = pd.read_csv(STEP1 / "cross_references.csv", dtype=str, keep_default_na=False)
sections = pd.read_csv(STEP1 / "sections.csv", dtype=str, keep_default_na=False)
components = pd.read_csv(STEP2 / "components.csv", dtype=str, keep_default_na=False)
versions = pd.read_csv(STEP5 / "statement_versions.csv", dtype=str, keep_default_na=False)
tmap = pd.read_csv(HERE / "sources" / "template_map.csv", dtype=str, keep_default_na=False)
rules = pd.read_csv(HERE / "sources" / "response_rules.csv", dtype=str, keep_default_na=False).set_index("test").pattern
BACKREF = re.compile(rules["backref"], re.I)
DEFERS = re.compile(rules["defers_only"], re.I)
NEGATION = re.compile(rules["negation"], re.I)
MODAL = re.compile(rules["modal"], re.I)
STATE = re.compile(rules["state"])
STATE_ONLY = re.compile(rules["state_only"])

core = xr[(xr.doc == "CORE41") & (xr.target == "DSA") & xr.relation.isin(["delegates", "default_overridable"])]
assert len(core) == 21, f"expected 21 Core 4.1 statements, got {len(core)}"
core40 = xr[(xr.doc == "CORE40") & (xr.target == "DSA") & xr.relation.isin(["delegates", "default_overridable"])]
dates = versions.drop_duplicates("doc").set_index("doc")
assert set(DSAS) <= set(dates.index), "statement_versions.csv lacks a DSA date"

matched = {}
for c in core.itertuples():
    hit = tmap[(tmap.core_section == c.section) & tmap.core_key.map(lambda k: k in c.sentence)]
    assert len(hit) == 1, f"Core 4.1 {c.section}: {len(hit)} template rows match: {c.sentence}"
    row = hit.iloc[0]
    assert row["row"] not in matched, f"template row {row['row']} matches twice"
    kind = "delegation" if c.relation == "delegates" else "default"
    assert kind == row["kind"], f"template row {row['row']}: kind {row['kind']} but relation {c.relation}"
    matched[row["row"]] = c
assert len(matched) == 21, "not every template row matched"

sec = {d: sections[sections.doc == d] for d in DSAS}


def resolve(doc, spec):
    if not spec:
        return []
    out = []
    for part in spec.split(";"):
        how, val = part.split(":", 1)
        s = sec[doc]
        if how == "num":
            hit = s[s.number == val]
        elif how == "prefix":
            hit = s[(s.number == val) | s.number.str.startswith(val + ".")]
        elif how == "title":
            hit = s[s.title.str.lower().str.startswith(val.lower())]
        elif how == "exact":
            hit = s[s.title.str.strip().str.lower() == val.lower()]
        else:
            raise SystemExit(f"unknown section spec {part}")
        out += list(hit.itertuples())
    return out


def sentences(rows, pattern, case):
    flags = 0 if case == "s" else re.I
    out = []
    for r in rows:
        for t in SENTENCE_SPLIT.split(r.text):
            t = t.strip()
            if t and (not pattern or re.search(pattern, t, flags)):
                out.append((r.number, r.start_page, t))
    return out


def delegation_response(sents, conditional):
    if not sents:
        return ("condition_not_stated", "D-none-conditional") if conditional else ("no_answer", "D-none")
    texts = [t for _, _, t in sents]
    if any(NEGATION.search(t) for t in texts):
        return "fills_none", "D-negation"
    if all(BACKREF.search(t) and DEFERS.search(t) for t in texts):
        return "defers_back", "D-defers"
    if any(BACKREF.search(t) for t in texts):
        return "fills_by_reference", "D-backref"
    return "fills", "D-content"


def default_response(sents, takes, overrides):
    if not sents:
        return "silent", "F-none"
    texts = [t for _, _, t in sents]
    if overrides and any(re.search(overrides, t, re.I) for t in texts):
        return "overrides", "F-overrides"
    if takes and any(re.search(takes, t, re.I) for t in texts):
        return "takes", "F-takes"
    if any(MODAL.search(t) for t in texts):
        return "ambiguous", "F-modal"
    return "ambiguous", "F-other"


def evidence(sents):
    return " || ".join(f"[{n} p{p}] {t}" for n, p, t in sents)


def arms_by_state(doc):
    states = sorted(set(STATE.findall(sec[doc][sec[doc].number == "8.1.2"].text.iloc[0])))
    assert states, f"{doc}: no state in 8.1.2"
    arms = components[(components.doc == doc) & (components.section == "8.3.1") & (components.level == "1")]
    assert len(arms), f"{doc}: no 8.3.1 arms"
    count = {}
    for st in states:
        count[st] = [a.text for a in arms.itertuples()
                     if not STATE_ONLY.search(a.text) or STATE_ONLY.search(a.text).group(1) == st]
    return count


rows, state_rows = [], []
for t in tmap.itertuples():
    c = matched[t.row]
    cands = core40[(core40.section == c.section) & (core40.relation == c.relation)]
    if len(cands):
        best = max(cands.sentence, key=lambda s: difflib.SequenceMatcher(None, s, c.sentence).ratio())
        c40, same40 = best, best == c.sentence
    else:
        c40, same40 = "", False
    for doc in DSAS:
        prim = resolve(doc, t.primary)
        psents = sentences(prim, t.topic_pattern, t.topic_case)
        ssents = sentences(resolve(doc, t.secondary), t.secondary_pattern, "i") if t.secondary else []
        if t.role == "umbrella":
            resp, rule = "umbrella_not_paired", "R-umbrella"
        elif t.role == "descriptive":
            resp, rule = "descriptive_no_slot", "R-descriptive"
        elif t.kind == "delegation":
            resp, rule = delegation_response(psents, t.conditional == "yes")
        else:
            resp, rule = default_response(psents, t.takes_pattern, t.overrides_pattern)
        if t.per_state == "control_arm":
            resp, rule = "ambiguous", "S-control"
        sresp = ""
        if ssents and t.kind == "delegation":
            sresp = delegation_response(ssents, False)[0]
        notes = []
        if t.row == "6" and dates.loc[doc, "dated_before_core_4_1"] == "True":
            notes.append("V-transition: DSA dated before Core 4.1; Core 7.6.2 additionally reports")
        rows.append({
            "row": t.row, "core_section": c.section, "core_page": c.page, "kind": t.kind,
            "topic": t.topic, "core_sentence_4_1": c.sentence, "core_sentence_4_0": c40,
            "same_text_4_0": same40, "dsa": doc, "dsa_date": dates.loc[doc, "doc_date"],
            "primary_sections": ";".join(r.number for r in prim), "response": resp, "rule": rule,
            "evidence": evidence(psents), "secondary_response": sresp, "secondary_evidence": evidence(ssents),
            "per_state": t.per_state, "conditional": t.conditional, "role": t.role,
            "reviewer": t.reviewer, "note": "; ".join(notes), "status": "analyst-reading"})
        if t.per_state == "two_interventions":
            for st, arms in arms_by_state(doc).items():
                sresp_state = resp if len(arms) == 2 else "condition_not_met"
                state_rows.append({"row": t.row, "core_section": c.section, "topic": t.topic, "dsa": doc,
                                   "state": st, "n_arms": len(arms), "arms": " | ".join(arms),
                                   "text_response": resp, "response": sresp_state,
                                   "rule": "S-state", "status": "analyst-reading"})

out = pd.DataFrame(rows)
by_state = pd.DataFrame(state_rows)
out.to_csv(OUT / "delegation_readings.csv", index=False)
by_state.to_csv(OUT / "delegation_readings_by_state.csv", index=False)

draft = pd.read_csv(DRAFT, dtype=str, keep_default_na=False)
assert len(draft) == 21, "cq2 draft: expected 21 rows"
cs = out[out.dsa == "CS_DSA"].reset_index(drop=True)
cmp_ = pd.DataFrame({"row": cs.row, "core_section": cs.core_section,
                     "draft_core_section": draft.core_section, "draft_dsa_section": draft.dsa_section,
                     "draft_response": draft.response, "new_sections": cs.primary_sections,
                     "new_response": cs.response, "new_secondary_response": cs.secondary_response})
assert (cmp_.core_section == cmp_.draft_core_section).all(), "cq2 draft order differs from the template map"
cmp_.to_csv(OUT / "cq2_comparison.csv", index=False)

print(f"pairings: {len(out)} ({out.role.value_counts().to_dict()})")
print("responses by DSA:")
print(pd.crosstab(out.response, out.dsa)[DSAS].to_string())
print("per state (two-intervention defaults):")
print(by_state[["row", "dsa", "state", "n_arms", "text_response", "response"]].to_string(index=False))
print("Core 4.0 sentence differs:", sorted(out[~out.same_text_4_0].row.unique(), key=int))
print("secondary responses:", out[out.secondary_response != ""].groupby(["row", "dsa"]).secondary_response.first().to_dict())
print("CS against the cq2 draft (Core 4.0), changed responses:")
print(cmp_[cmp_.draft_response != cmp_.new_response].to_string(index=False))
