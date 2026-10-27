"""REMAP-CAP design modules, step 3: component identity.

Inputs: output/step2/components.csv (list items) and output/step2/statements.csv (sentences).

Rules (README, step 3):
  I-exact     identity = text with whitespace collapsed. Case and punctuation are kept:
              differences there go to review, not into identity.
  I-revision  Core 4.0 vs 4.1, per (section, group): a text in both versions is one component;
              a 4.0-only and a 4.1-only text in the same (section, group) with
              difflib ratio >= 0.85 are a revision pair (one version-independent parent);
              otherwise "only in 4.0" / "only in 4.1". Ties are not resolved: more than one
              candidate at the best ratio stops the script.
  I-move      a 4.0 text found word for word in 4.1 under another section is "moved"
              (section_41 says where); it is the same component in both versions.
  I-review    distinct texts with ratio in [0.85, 1.0) whose document sets are disjoint are
              written to crosswalk_review.csv with an empty decision column. Pairs that are
              Core 4.0/4.1 revisions are excluded (handled by I-revision).
  I-decide    sources/crosswalk_decisions.csv (Kerstin's decisions) is applied last: every review
              pair must have a row there and every row must be a review pair, else the script
              stops. "merge" pairs become one component (canonical member: the one in most
              documents, then the smaller id; other texts kept as variants); "keep apart" and
              open rows change nothing. The review itself stays on exact identity.
              After merging, a Core only_40 and only_41 row of one component become one row:
              "moved" (other section) or "same" (same section), with both texts.
Outputs in output/step3/: occurrences.csv (component = canonical, component_exact),
components_index.csv (variant_texts), core_revisions.csv, crosswalk_review.csv, run.log.
"""
import hashlib
import re
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent.parent
STEP2 = HERE / "output" / "step2"
DECISIONS = HERE / "sources" / "crosswalk_decisions.csv"
OUT = HERE / "output" / "step3"
OUT.mkdir(parents=True, exist_ok=True)
RATIO = 0.85

items = pd.read_csv(STEP2 / "components.csv", dtype=str, keep_default_na=False)
stmts = pd.read_csv(STEP2 / "statements.csv", dtype=str, keep_default_na=False)
occ = pd.concat([
    items.assign(unit="item", position=items["seq"], text=items["text"])[
        ["doc", "section", "section_title", "kind", "unit", "position", "item", "group", "glyph", "page", "text"]],
    stmts.assign(unit="sentence", position=stmts["part"] + ":" + stmts["n"], item="", group="", glyph="",
                 page="", text=stmts["sentence"])[
        ["doc", "section", "section_title", "kind", "unit", "position", "item", "group", "glyph", "page", "text"]],
], ignore_index=True)
occ["text"] = occ.text.str.replace(r"\s+", " ", regex=True).str.strip()
assert (occ.text != "").all(), "empty component text"


def cid(text):
    return "c" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


occ["component"] = occ.text.map(cid)
# I-exact collision check: distinct texts must not share an id
assert occ.groupby("component").text.nunique().max() == 1, "id collision"

# components index
idx = (occ.groupby("component")
       .agg(text=("text", "first"), kinds=("kind", lambda v: ";".join(sorted(set(v)))),
            units=("unit", lambda v: ";".join(sorted(set(v)))),
            docs=("doc", lambda v: ";".join(sorted(set(v)))), n_docs=("doc", "nunique"),
            n_occurrences=("doc", "size"))
       .reset_index())
print(f"occurrences={len(occ)} components (exact)={len(idx)}")
print("components by number of documents:", idx.n_docs.value_counts().sort_index().to_dict())
multi_kind = idx[idx.kinds.str.contains(";")]
print(f"components with more than one kind: {len(multi_kind)}")
for r in multi_kind.itertuples():
    print(f"  {r.component} [{r.kinds}] {r.text[:90]}")
within = occ.groupby(["doc", "component"]).size()
within = within[within > 1]
print(f"components occurring more than once in one document: {len(within)}")
for (d, c), n in within.items():
    print(f"  {d} {c} x{n} {idx.set_index('component').at[c, 'text'][:80]}")

# I-revision: Core 4.0 vs 4.1
core = occ[occ.doc.isin(["CORE40", "CORE41"])]
section_of_41 = core[core.doc == "CORE41"].groupby("text").section.apply(lambda v: ";".join(sorted(set(v)))).to_dict()
all40 = set(core[core.doc == "CORE40"].text)
rev_rows = []
for (section, group), g in core.groupby(["section", "group"]):
    t40 = list(dict.fromkeys(g[g.doc == "CORE40"].text))
    t41 = list(dict.fromkeys(g[g.doc == "CORE41"].text))
    s40, s41 = set(t40), set(t41)
    for t in t40:
        if t in s41:
            rev_rows.append({"section": section, "group": group, "status": "same", "text_40": t, "text_41": t,
                             "ratio": 1.0})
    only40 = [t for t in t40 if t not in s41]
    only41 = [t for t in t41 if t not in s40]
    # I-move: the same text in the other version under another section
    for t in [t for t in only40 if t in section_of_41]:
        rev_rows.append({"section": section, "group": group, "status": "moved", "text_40": t, "text_41": t,
                         "ratio": 1.0, "section_41": section_of_41[t]})
    only40 = [t for t in only40 if t not in section_of_41]
    only41 = [t for t in only41 if t not in all40]
    used41 = set()
    for t in only40:
        scored = sorted(((SequenceMatcher(None, t, u).ratio(), u) for u in only41 if u not in used41), reverse=True)
        if scored and scored[0][0] >= RATIO:
            best = [u for r, u in scored if r == scored[0][0]]
            assert len(best) == 1, f"I-revision tie in {section} for: {t[:60]}"
            used41.add(best[0])
            rev_rows.append({"section": section, "group": group, "status": "revised", "text_40": t,
                             "text_41": best[0], "ratio": round(scored[0][0], 3)})
        else:
            rev_rows.append({"section": section, "group": group, "status": "only_40", "text_40": t, "text_41": "",
                             "ratio": round(scored[0][0], 3) if scored else ""})
    for u in only41:
        if u not in used41:
            rev_rows.append({"section": section, "group": group, "status": "only_41", "text_40": "", "text_41": u,
                             "ratio": ""})
rev = pd.DataFrame(rev_rows)
rev["section_41"] = rev.get("section_41", pd.Series(dtype=str)).fillna("")
rev["component_40"] = rev.text_40.map(lambda t: cid(t) if t else "")
rev["component_41"] = rev.text_41.map(lambda t: cid(t) if t else "")
rev["parent"] = rev.apply(lambda r: "r" + hashlib.sha1((r.section + "|" + r.text_40).encode()).hexdigest()[:10]
                          if r.status == "revised" else "", axis=1)
print("Core 4.0/4.1:", rev.status.value_counts().to_dict())
changed_sections = sorted(set(rev[rev.status != "same"].section), key=lambda x: [int(p) for p in x.split(".")])
print("  sections with a change:", changed_sections)
# Gate: changed Core sections here = step 1 changed sections among those mapped to component kinds
s1 = pd.read_csv(HERE / "output" / "step1" / "sections.csv", dtype=str, keep_default_na=False)
mapped = set(core.section)
t40 = s1[s1.doc == "CORE40"].set_index("number").text
t41 = s1[s1.doc == "CORE41"].set_index("number").text
step1_changed = {n for n in mapped if n not in t40.index or n not in t41.index or t40[n] != t41[n]}
assert set(changed_sections) == step1_changed, f"gate: {sorted(set(changed_sections) ^ step1_changed)}"
print("  gate ok: equals step 1 changed sections among mapped Core sections")
for r in rev[rev.status != "same"].itertuples():
    print(f"  {r.section} {r.status} {r.ratio} | 4.0: {r.text_40[:70]!r} | 4.1: {r.text_41[:70]!r}")

# I-review: near matches across documents
revision_pairs = {frozenset((a, b)) for a, b in zip(rev.component_40, rev.component_41) if a and b and a != b}
docs_of = occ.groupby("component").doc.apply(set).to_dict()
text_of = idx.set_index("component").text.to_dict()
kinds_of = idx.set_index("component").kinds.to_dict()
pairs = []
for a, b in combinations(sorted(text_of), 2):
    if frozenset((a, b)) in revision_pairs:
        continue
    if docs_of[a] & docs_of[b]:
        continue  # a document holding both is evidence they are two components, not variants of one
    ta, tb = text_of[a], text_of[b]
    if abs(len(ta) - len(tb)) > 0.3 * max(len(ta), len(tb)):
        continue
    r = SequenceMatcher(None, ta, tb).ratio()
    if RATIO <= r < 1.0:
        pairs.append({"component_a": a, "component_b": b, "ratio": round(r, 3),
                      "case_only": ta.lower() == tb.lower(),
                      "kinds_a": kinds_of[a], "kinds_b": kinds_of[b],
                      "docs_a": ";".join(sorted(docs_of[a])), "docs_b": ";".join(sorted(docs_of[b])),
                      "text_a": ta, "text_b": tb, "decision": "", "note": ""})
cw = pd.DataFrame(pairs).sort_values("ratio", ascending=False)
cw.to_csv(OUT / "crosswalk_review.csv", index=False)
print(f"crosswalk review pairs (ratio {RATIO}-0.999, disjoint documents): {len(cw)}; case-only: {int(cw.case_only.sum())}")
print(cw.groupby(["docs_a", "docs_b"]).size().to_string())

# I-decide: apply Kerstin's crosswalk decisions
dec = pd.read_csv(DECISIONS, dtype=str, keep_default_na=False)
assert set(dec.decision) <= {"merge", "keep apart", ""}, f"unknown decisions: {set(dec.decision)}"
pair_key = lambda d: set(d.apply(lambda r: frozenset((r.component_a, r.component_b)), axis=1))
review_keys, decision_keys = pair_key(cw), pair_key(dec)
assert decision_keys <= review_keys, f"decision rows that are not review pairs: {len(decision_keys - review_keys)}"
assert review_keys <= decision_keys, f"review pairs without a decision row: {len(review_keys - decision_keys)}"
parent = {}


def find(k):
    parent.setdefault(k, k)
    while parent[k] != k:
        parent[k] = parent[parent[k]]
        k = parent[k]
    return k


for r in dec[dec.decision == "merge"].itertuples():
    parent[find(r.component_b)] = find(r.component_a)
members = {}
for k in list(parent):
    members.setdefault(find(k), set()).add(k)
canonical = {}
for group in members.values():
    best = sorted(group, key=lambda k: (-len(docs_of[k]), k))[0]
    for k in group:
        canonical[k] = best
occ["component_exact"] = occ.component
occ["component"] = occ.component.map(lambda k: canonical.get(k, k))
occ.to_csv(OUT / "occurrences.csv", index=False)
variants = {}
for k, c in canonical.items():
    if k != c:
        variants.setdefault(c, []).append(text_of[k])
idx = (occ.groupby("component")
       .agg(kinds=("kind", lambda v: ";".join(sorted(set(v)))),
            units=("unit", lambda v: ";".join(sorted(set(v)))),
            docs=("doc", lambda v: ";".join(sorted(set(v)))), n_docs=("doc", "nunique"),
            n_occurrences=("doc", "size"))
       .reset_index())
idx.insert(1, "text", idx.component.map(text_of))
idx["variant_texts"] = idx.component.map(lambda c: " || ".join(sorted(variants.get(c, []))))
idx.to_csv(OUT / "components_index.csv", index=False)
print(f"I-decide: {len(dec[dec.decision == 'merge'])} merge pairs -> {sum(1 for g in members.values())} merged components; "
      f"components {len(text_of)} -> {len(idx)}; open rows: {int((dec.decision == '').sum())}")
rev["component_40_exact"], rev["component_41_exact"] = rev.component_40, rev.component_41
rev["component_40"] = rev.component_40.map(lambda k: canonical.get(k, k) if k else "")
rev["component_41"] = rev.component_41.map(lambda k: canonical.get(k, k) if k else "")
o40 = rev[rev.status == "only_40"]
o41 = rev[rev.status == "only_41"]
joined = o40.merge(o41, left_on="component_40", right_on="component_41", suffixes=("", "_b"))
new_rows = []
for r in joined.itertuples():
    new_rows.append({"section": r.section, "group": r.group,
                     "status": "same" if r.section == r.section_b else "moved",
                     "text_40": r.text_40, "text_41": r.text_41_b,
                     "ratio": round(SequenceMatcher(None, r.text_40, r.text_41_b).ratio(), 3),
                     "section_41": r.section_b, "component_40": r.component_40, "component_41": r.component_41_b,
                     "parent": "", "component_40_exact": r.component_40_exact, "component_41_exact": r.component_41_exact_b})
merged_40 = set(joined.component_40)
rev = pd.concat([rev[~(((rev.status == "only_40") & rev.component_40.isin(merged_40)) |
                       ((rev.status == "only_41") & rev.component_41.isin(merged_40)))],
                 pd.DataFrame(new_rows)], ignore_index=True)
rev.to_csv(OUT / "core_revisions.csv", index=False)
print("Core 4.0/4.1 after decisions:", rev.status.value_counts().to_dict())
for r in new_rows:
    print(f"  merged across versions: {r['section']} -> {r['section_41']} {r['status']} | {r['text_40'][:60]!r} / {r['text_41'][:60]!r}")
