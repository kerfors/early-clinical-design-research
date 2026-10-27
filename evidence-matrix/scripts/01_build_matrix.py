"""Evidence matrix: requirement x case x finding x document evidence (direction note, step 3).

Authored inputs (reviewed by Kerstin): sources/requirements.csv, sources/findings.csv (one line per finding,
its requirement, and the expected value as recorded in the builds' READMEs and status notes).
Generated: every evidence row, selected from committed outputs of the builds (read only):
  remapcap-design-modules/   output/step1-5, sources/crosswalk_decisions.csv
  cpmp-design-modules/       output/, sources/
  cpmp-soa-join/             output/, activity_crosswalk.csv
  usdm-master-protocol/      output_cpmp/step2, step4, step5; inventory.csv
  soa2usdm-collections       collections/cpmp at cf9541d (SoA page per activity; env SOA2USDM_COLLECTIONS)
Each selector returns its evidence rows and an observed value. The observed value must equal `expected`;
"*" marks a finding first counted here (observed is recorded, rows must exist). A mismatch stops the build.

Outputs: output/evidence_matrix.csv (one row per evidence item), output/findings_checked.csv.
Run: SOA2USDM_COLLECTIONS=/path/to/soa2usdm-collections python scripts/01_build_matrix.py
"""
import json
import os
import re
import subprocess
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parents[1]
RC = BASE / "remapcap-design-modules"
CP = BASE / "cpmp-design-modules"
JOIN = BASE / "cpmp-soa-join"
UMP = BASE / "usdm-master-protocol"
COLL = Path(os.environ.get("SOA2USDM_COLLECTIONS", BASE.parent / "GitHub" / "soa2usdm-collections"))
COLL_COMMIT = "cf9541d"
DSAS = ["CS_DSA", "AB_DSA", "TAB_DSA", "IAV_DSA", "MD_DSA", "IG_DSA", "MV_DSA", "END_DSA", "IIM_DSA"]
COLUMNS = ["requirement", "case", "finding_id", "finding", "evidence_kind", "role", "doc", "section", "page",
           "text", "scope", "source_file", "source_key", "status"]


def read(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def rel(path):
    return str(Path(path).relative_to(BASE)) if str(path).startswith(str(BASE)) else str(path)


def row(kind, role, doc, section, page, text, scope, source, key, status):
    return {"evidence_kind": kind, "role": role, "doc": doc, "section": section, "page": page,
            "text": re.sub(r"\s+", " ", str(text)).strip(), "scope": scope, "source_file": rel(source),
            "source_key": key, "status": status}


# ------------------------------------------------------------------ shared inputs
head = subprocess.run(["git", "-C", str(COLL), "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                      check=True).stdout.strip()
assert head == COLL_COMMIT, f"soa2usdm-collections at {head}, expected {COLL_COMMIT}"

OCC_F = RC / "output" / "step3" / "occurrences.csv"
occ = read(OCC_F)
docs_of = occ.groupby("component").doc.apply(set)
NOT_DSA = {"CORE40", "CORE41", "PANDA"}
INH_F = RC / "output" / "step5" / "inheritance_readings.csv"
inh = read(INH_F)
RI_F = RC / "output" / "step5" / "readings_index.csv"
ri = read(RI_F)
DR_F = RC / "output" / "step5" / "delegation_readings.csv"
dr = read(DR_F)
SEC_F = RC / "output" / "step1" / "sections.csv"
sec = read(SEC_F)
XR_F = RC / "output" / "step1" / "cross_references.csv"
xr = read(XR_F)
STM_F = RC / "output" / "step2" / "statements.csv"
stm = read(STM_F)

GRID_F = JOIN / "output" / "layered_grid.csv"
grid = read(GRID_F)
ISA_OF = grid.drop_duplicates("nct_id").set_index("nct_id").isa.to_dict()
COMPOUND_OF = grid.drop_duplicates("nct_id").set_index("nct_id").compound.to_dict()
MASTER_NCT = "NCT05986292"
ISA_OF[MASTER_NCT] = "CPMP"
CPX_F = UMP / "output_cpmp" / "step2" / "cross_references.csv"
cpx = read(CPX_F)
CPS_F = UMP / "output_cpmp" / "step2" / "sections.csv"
cps = read(CPS_F)
CRIT_F = UMP / "output_cpmp" / "step5" / "criteria.csv"
crit = read(CRIT_F)
OE_F = UMP / "output_cpmp" / "step5" / "objectives_endpoints.csv"
oe = read(OE_F)
SOAST_F = CP / "sources" / "soa_statements.csv"
soast = read(SOAST_F)

# SoA page per (nct, activity key): consolidated activity -> source_refs -> extraction source_page
xw = read(JOIN / "activity_crosswalk.csv")
xw["key"] = xw["activity_key"].where(xw["use"] == "yes", xw["name_as_printed"])
KEY = dict(zip(xw["name_as_printed"], xw["key"]))
soa_page = {}
for nct in set(grid.nct_id) | {MASTER_NCT}:
    base = COLL / "collections" / "cpmp" / "protocols" / nct / "SoA2USDM"
    con = json.loads((base / "consolidated" / f"{nct}_consolidated.json").read_text())
    pages = {}
    for f in sorted((base / "extracted").glob(f"{nct}_Table_*_extraction.json")):
        ext = json.loads(f.read_text())
        for a in ext["activities"]:
            pages[(a["table_number"], a["row_position"])] = a["source_page"]
    for a in con["unified_activities"]:
        key = KEY.get(a["activity_name"], a["activity_name"])
        for s in a["source_refs"]:
            soa_page.setdefault((nct, key), set()).add(pages[(s["table_num"], s["row_position"])])
SOA_SRC = COLL / "collections" / "cpmp" / "protocols"


def page_of(nct, key):
    p = soa_page.get((nct, key))
    assert p, f"no SoA page for {nct} {key}"
    return ";".join(str(x) for x in sorted(p))


# ------------------------------------------------------------------ REMAP-CAP selectors
def rc1():
    comps = [c for c, d in docs_of.items() if d == set(DSAS)]
    o = occ[occ.component.isin(comps) & occ.doc.isin(DSAS)]
    rows = [row("instance", "occurrence", r.doc, r.section, r.page, r.text, r.component, OCC_F,
                f"{r.doc}|{r.section}|{r.position}", "rule-derived") for r in o.itertuples()]
    return rows, f"{len(comps)} components in all {len(DSAS)} DSAs"


def rc2():
    comps = [c for c, d in docs_of.items() if {"AB_DSA", "TAB_DSA"} <= d and not d & NOT_DSA]
    o = occ[occ.component.isin(comps) & occ.doc.isin(["AB_DSA", "TAB_DSA"])]
    rows = [row("instance", "occurrence", r.doc, r.section, r.page, r.text, r.component, OCC_F,
                f"{r.doc}|{r.section}|{r.position}", "rule-derived") for r in o.itertuples()]
    return rows, f"{len(comps)} components"


UP = set(occ[occ.doc.isin(["CORE41", "PANDA"])].component)


def rc3():
    n = {d: len(set(occ[occ.doc == d].component) & UP) for d in DSAS}
    rows = [row("absence", "search", d, "", "", f"components of {d} that Core 4.1 or PANDA also has part of: {n[d]}",
                d, OCC_F, d, "rule-derived") for d in DSAS]
    return rows, f"{sum(n.values())} restated in {len(DSAS)} DSAs"


def reached(d):
    dep = set()
    for r in ri[(ri.doc == d) & (ri.resolution != "")].itertuples():
        for t in r.resolution.split(";"):
            layer, num = t.split(" ")
            docs = ["PANDA"] if layer == "PANDA" else (["CORE41", "CORE40"] if "4.0" in r.core_versions else ["CORE41"])
            dep |= set(occ[occ.doc.isin(docs) & (occ.section == num)].component)
    return UP & dep


def rc4():
    unreached = {d: UP - reached(d) for d in DSAS}
    first = occ[occ.doc.isin(["CORE41", "PANDA"])].drop_duplicates("component").set_index("component")
    rows = []
    for c in sorted(set().union(*unreached.values())):
        r = first.loc[c]
        scope = ";".join(d for d in DSAS if c in unreached[d])
        rows.append(row("instance", "inherited, not reached", r.doc, r.section, r.page, r.text, scope, OCC_F, c,
                        "rule-derived from analyst readings"))
    n = {d: len(v) for d, v in unreached.items()}
    others = sorted({v for d, v in n.items() if d != "IAV_DSA"})
    assert len(others) == 1, n
    return rows, f"{others[0]} in 8 DSAs; {n['IAV_DSA']} in IAV_DSA"


def delegation_rows(sel):
    rows = []
    for r in sel.itertuples():
        rows.append(row("instance", "parent statement", "CORE41", r.core_section, r.core_page, r.core_sentence_4_1,
                        r.dsa, DR_F, f"row {r.row}|{r.dsa}", "document fact"))
        rows.append(row("instance", f"child response: {r.response}" + (f" / {r.secondary_response}" if r.secondary_response else ""),
                        r.dsa, r.primary_sections, "", r.evidence or "(no section answers it)", r.dsa, DR_F,
                        f"row {r.row}|{r.dsa}", "analyst-reading"))
    return rows


def rc5():
    sel = dr[(dr.kind == "delegation") & (dr.role == "paired")
             & (dr.response.isin(["no_answer", "condition_not_stated", "defers_back"]) | (dr.secondary_response == "defers_back"))]
    unanswered = sel.response.isin(["no_answer", "condition_not_stated"])
    back = (sel.response == "fills") & (sel.secondary_response == "defers_back")
    assert (unanswered | back).all(), sel[~(unanswered | back)][["dsa", "topic", "response"]]
    return delegation_rows(sel), f"{int(unanswered.sum())} unanswered; {int(back.sum())} answered with a pointer back"


def rc6():
    bal = dr[(dr.kind == "default") & dr.topic.isin(["balanced allocation at domain start", "new intervention at 1/K"])
             & (dr.response == "silent")]
    amb = dr[(dr.kind == "default") & (dr.topic == "no control arm: no min/max") & (dr.response == "ambiguous")]
    return delegation_rows(pd.concat([bal, amb])), f"{len(bal)} silent (balanced allocation); {len(amb)} not evaluated (no control arm)"


def rc7():
    a = inh[(inh.doc == "END_DSA") & (inh.section == "10.8")]
    s = sec[(sec.doc == "CORE41") & (sec.number == "7.8.6")]
    b = re.findall(r"The Core Protocol does not specify a default Statistical Trigger for equivalence[^.]*\.", re.sub(r"\s+", " ", s.text.iloc[0]))
    assert len(a) == 1 and len(b) == 1
    rows = [row("instance", "child statement", "END_DSA", "10.8", "", a.sentence.iloc[0], "END_DSA", INH_F, "END_DSA|10.8", "document fact"),
            row("instance", "parent statement", "CORE41", "7.8.6", s.start_page.iloc[0], b[0], "all DSAs", SEC_F, "CORE41|7.8.6", "document fact")]
    return rows, "2 sentences"


def rc8():
    o = occ[(occ.doc == "MD_DSA") & occ.kind.isin(["domain_inclusion", "domain_exclusion"]) & occ.text.str.contains("Antibiotic Domain")]
    rows = [row("instance", r.kind, r.doc, r.section, r.page, r.text, "MD_DSA; AB_DSA", OCC_F, f"{r.doc}|{r.section}|{r.position}",
                "document fact") for r in o.itertuples()]
    return rows, f"{len(o)} eligibility items"


VERSION_NAMED = re.compile(r"(core protocol|core protocol documents?)\s*(,\s*)?(version|v\.?)\s*\d", re.I)


def rc9():
    s = inh[inh.target_phrase != "Statistical Analysis Appendix"]
    named = s[s.sentence.str.contains(VERSION_NAMED)]
    rows = [row("instance", f"binding: {r.binding}", r.doc, r.section, "", r.sentence, r.doc, INH_F, f"{r.doc}|{r.section}",
                "rule-derived") for r in s.itertuples()]
    return rows, f"{len(named)} statements name a Core version"


def rc10():
    sv = read(RC / "output" / "step5" / "statement_versions.csv")
    before = sv.drop_duplicates("doc").set_index("doc").dated_before_core_4_1
    dates = read(RC / "output" / "step5" / "statement_versions.csv").drop_duplicates("doc").set_index("doc").doc_date
    assert set(before.index) == set(DSAS), set(DSAS) - set(before.index)
    rows = [row("instance", f"resolves to Core {r.resolves_to_core_versions}", r.doc, r.section, "", r.sentence,
                f"{r.doc} dated {r.doc_date}", RC / "output" / "step5" / "statement_versions.csv", f"{r.doc}|{r.section}|{r.resolution}",
                "analyst-reading") for r in sv.itertuples()]
    return rows, f"{len(sv)} statements; {int((before == 'True').sum())} of {len(DSAS)} DSAs before Core 4.1"


def rc11():
    c = xr[xr.doc.isin(["CORE40", "CORE41"]) & (xr.section == "7.8.7") & xr.sentence.str.contains("capped at")]
    pct = {r.doc: re.search(r"capped at (\d+)\s*%", r.sentence).group(1) for r in c.itertuples()}
    assert set(pct) == {"CORE40", "CORE41"}, pct
    cs = inh[(inh.doc == "CS_DSA") & (inh.section == "10.3")]
    rows = [row("instance", "parent statement", r.doc, r.section, r.page, r.sentence, "two-intervention domains", XR_F,
                f"{r.doc}|7.8.7", "document fact") for r in c.itertuples()]
    rows += [row("instance", f"child statement, binding: {r.binding}", r.doc, r.section, "", r.sentence, "CS_DSA", INH_F,
                 f"{r.doc}|{r.section}", "document fact") for r in cs.itertuples()]
    return rows, f"{pct['CORE40']}% -> {pct['CORE41']}%"


TRANSITION = "DSAs dated before this Core Protocol amendment will additionally report"


def rc12():
    rows, found = [], {}
    for doc in ["CORE40", "CORE41"]:
        t = re.sub(r"\s+", " ", sec[(sec.doc == doc) & (sec.number == "7.6.2")].text.iloc[0]).replace("pre- specified", "pre-specified")
        m = re.search(re.escape(TRANSITION) + r"[^.]*\.", t)
        found[doc] = m.group(0)
        rows.append(row("instance", "transition sentence", doc, "7.6.2", "", m.group(0), "DSAs dated before the amendment",
                        SEC_F, f"{doc}|7.6.2", "document fact"))
    return rows, "identical in 4.0 and 4.1" if found["CORE40"] == found["CORE41"] else "differs"


def rc13():
    rv = read(RC / "output" / "step3" / "core_revisions.csv")
    sel = rv[rv.status.isin(["revised", "moved"])]
    rows = [row("instance", r.status, "CORE40 / CORE41", f"{r.section} / {r.section_41}", "",
                f"4.0: {r.text_40} | 4.1: {r.text_41}", "all DSAs", RC / "output" / "step3" / "core_revisions.csv",
                f"{r.section}|{r.group}", "rule-derived") for r in sel.itertuples()]
    return rows, f"{(sel.status == 'revised').sum()} revised; {(sel.status == 'moved').sum()} moved"


def rc14():
    d = read(RC / "sources" / "crosswalk_decisions.csv")
    rows = [row("instance", f"{r.decision} ({r.status})", "", "", "", f"A: {r.text_a} | B: {r.text_b}", f"{r.docs_a} | {r.docs_b}",
                RC / "sources" / "crosswalk_decisions.csv", f"{r.component_a}|{r.component_b}", "decision by Kerstin")
            for r in d.itertuples()]
    return rows, f"{len(d)} decisions; {d.status.str.startswith('tentative').sum()} tentative"


def rc15():
    kinds = occ.groupby("component").apply(lambda g: set(zip(g.doc, g.kind)))
    comps = [c for c, k in kinds.items() if any(kd == "domain_inclusion" for _, kd in k)
             and any(kd == "domain_exclusion" for _, kd in k) and "SARS-CoV-2" in occ[occ.component == c].text.iloc[0]]
    o = occ[occ.component.isin(comps)]
    rows = [row("instance", r.kind, r.doc, r.section, r.page, r.text, r.component, OCC_F, f"{r.doc}|{r.section}|{r.position}",
                "document fact") for r in o.itertuples()]
    return rows, f"{len(comps)} component"


def rc16():
    s = inh[inh.target_phrase == "document set: core protocol documents"]
    n = s.groupby("doc").size()
    rows = [row("instance", "points at the document set", r.doc, r.section, "", r.sentence, r.doc, INH_F, f"{r.doc}|{r.section}",
                "rule-derived") for r in s.itertuples()]
    return rows, f"{len(n)} DSAs; {n.min()}-{n.max()} statements each"


def rc17():
    s = inh[inh.resolution.str.startswith("PANDA") & inh.section.str.startswith("8.1")]
    rows = [row("instance", f"says: {r.target_phrase}; resolves to {r.resolution}", r.doc, r.section, "", r.sentence, r.doc,
                INH_F, f"{r.doc}|{r.section}", "analyst-reading") for r in s.itertuples()]
    p = sec[(sec.doc == "PANDA") & (sec.number == "4.3")]
    rows.append(row("instance", "where it is defined", "PANDA", "4.3", p.start_page.iloc[0], p.title.iloc[0], "all DSAs", SEC_F,
                    "PANDA|4.3", "document fact"))
    return rows, f"{s.doc.nunique()} DSAs"


APPENDIX_HEADING = re.compile(r"APPENDIX 1: REGION-SPECIFIC MODIFICATIONS FOR JAPAN[^.]*\.")


def rc18():
    iav = sec[sec.doc == "IAV_DSA"]
    held = iav[iav.text.str.contains(APPENDIX_HEADING)]
    assert len(held) == 1, held.number.tolist()
    h = held.iloc[0]
    rows = [row("instance", f"appendix heading, unnumbered, inside section {h.number} ({h.title})", "IAV_DSA", h.number, h.start_page,
                APPENDIX_HEADING.search(re.sub(r"\s+", " ", h.text)).group(0), "IAV_DSA", SEC_F, f"IAV_DSA|{h.number}", "document fact")]
    s = iav[iav.number.str.startswith("14.") & iav.text.str.contains("Japan")]
    rows += [row("instance", "section", r.doc, r.number, r.start_page, f"{r.title}: {r.text[:400]}", "IAV_DSA", SEC_F,
                 f"{r.doc}|{r.number}", "document fact") for r in s.itertuples()]
    return rows, f"IAV_DSA {';'.join(s.number)}; heading unnumbered, inside section {h.number}"


def rc19():
    rn = read(RC / "output" / "step1" / "reconstructed_numbers.csv")
    mv = rn[rn.doc == "MV_DSA"]
    allmv = sec[sec.doc == "MV_DSA"]
    rows = [row("instance", f"number from {r.number_source}", r.doc, r.number, r.toc_page, r.title, "MV_DSA",
                RC / "output" / "step1" / "reconstructed_numbers.csv", f"{r.doc}|{r.number}", "rule-derived") for r in mv.itertuples()]
    return rows, "all MV_DSA sections reconstructed" if set(allmv.number) <= set(mv.number) else f"{len(mv)} of {len(allmv)} MV_DSA sections reconstructed"


REASON = re.compile(r"\b(because|due to|reason|rationale|in order to|so that)\b", re.I)


def rc20():
    s = sec[sec.title.str.contains("version history", case=False)]
    rows, n = [], 0
    for r in s.itertuples():
        n += len(REASON.findall(r.text))
        rows.append(row("instance", "version history", r.doc, r.number, r.start_page, r.text, r.doc, SEC_F, f"{r.doc}|{r.number}",
                        "document fact"))
    return rows, f"{len(s)} sections; {n} reasons"


# ------------------------------------------------------------------ CPMP selectors
def crit_rows(cond, role, scope_fn=None, status="document fact"):
    rows = []
    for r in crit[cond].itertuples():
        rows.append(row("instance", role, r.doc, f"5 [{r.number}]", r.page, r.text, scope_fn(r) if scope_fn else r.doc, CRIT_F,
                        f"{r.doc}|{r.number}", status))
    return rows


def cp1():
    ci = read(CP / "output" / "components_index.csv")
    comp = ci[ci["class"] == "compound column"]
    g = read(UMP / "output_cpmp" / "step5" / "grid.csv")
    rows = [row("instance", "compound named in section 5", r.doc, "5", "", r.evidence, r.compound, UMP / "output_cpmp" / "step5" / "grid.csv",
                r.doc, "document fact") for r in g.itertuples()]
    for c in comp.itertuples():
        if c.kind == "criterion":
            src = crit[crit.template == c.key]
            rows += [row("instance", "compound component (criterion)", r.doc, f"5 [{r.number}]", r.page, r.text, c.docs, CRIT_F,
                         c.iri.rsplit("/", 1)[1], "rule-derived") for r in src.itertuples()]
        else:
            col = "objective_template" if c.kind == "objective" else "endpoint_template"
            src = oe[oe[col] == c.key].drop_duplicates(["doc", col])
            txt = "objective" if c.kind == "objective" else "endpoint"
            rows += [row("instance", f"compound component ({c.kind})", r.doc, "3", r.page, getattr(r, txt), c.docs, OE_F,
                         c.iri.rsplit("/", 1)[1], "rule-derived") for r in src.itertuples()]
    return rows, f"{len(comp)} components; {len(g)} ISAs name their compound"


def cp2():
    isa = grid[grid.isa_mark == "True"]
    n_isa = grid.nct_id.nunique()
    per = isa.groupby(["activity_key", "visit"]).nct_id.nunique()
    master = set(zip(grid[grid.master_mark == "True"].activity_key, grid[grid.master_mark == "True"].visit))
    cells = [c for c, n in per.items() if n == n_isa and c not in master]
    rows = []
    for (key, visit) in cells:
        for r in isa[(isa.activity_key == key) & (isa.visit == visit)].itertuples():
            rows.append(row("instance", "ISA SoA mark", r.isa, "1.3 SoA", page_of(r.nct_id, key), f"{key} at {visit}",
                            "all 12 ISAs; not in master", GRID_F, f"{r.nct_id}|{key}|{visit}", "rule-derived"))
    return rows, f"{len(cells)} cells"


def cp3():
    cond = crit.text.str.contains("pregnant or breastfeeding")
    rows = crit_rows(cond, "ISA exclusion criterion", status="document fact (identity decided by Kerstin)")
    m = cps[(cps.doc == "CPMP") & cps.text.str.contains("will be specified in the ISAs", regex=False)]
    for r in m.itertuples():
        s = re.search(r"[^.\]]*will be specified in the ISAs[^.]*\.", re.sub(r"\s+", " ", r.text)).group(0)
        rows.append(row("instance", "master delegation", "CPMP", r.number, r.start_page, s, "all ISAs", CPS_F, f"CPMP|{r.number}",
                        "document fact"))
    return rows, f"{crit[cond].doc.nunique()} ISAs; {len(m)} master sentence"


def cp4():
    k = read(JOIN / "output" / "kinds_per_isa.csv")
    m = grid[grid.master_mark == "True"].drop_duplicates(["activity_key", "visit"])
    rows = [row("count", "kinds of ISA marks", r.isa, "1.3 SoA", "", f"inherited {r.inherited}; restated {r.restated}; added {r.added}; "
                f"extended {r.extended}; ISA only {r.isa_only}; ED override {r.override_ed}", r.compound, JOIN / "output" / "kinds_per_isa.csv",
                r.isa, "rule-derived") for r in k.itertuples()]
    rs = k.restated.astype(int)
    return rows, f"restated {rs.min()}-{rs.max()} of {len(m)} master cells"


def cp5():
    o = read(JOIN / "output" / "override_ed_cells.csv")
    st = soast[soast.statement_kind == "override_ed"]
    rows = [row("instance", "ED override note", ISA_OF[r.nct_id], "1.3 SoA", page_of(r.nct_id, r.activity_key), r.text,
                f"{r.activity_key} at ED", SOAST_F, f"{r.nct_id}|{r.activity_key}", "document fact") for r in st.itertuples()]
    assert len(st) == len(o)
    return rows, f"{len(o)} cells; {int((o.in_master_soa == 'False').sum())} on activities not in the master SoA"


def cp6():
    st = soast[soast.statement_kind == "addition_stated"]
    rows = [row("instance", "stated addition", ISA_OF[r.nct_id], "1.3 SoA", page_of(r.nct_id, r.activity_key), r.text,
                r.activity_key, SOAST_F, f"{r.nct_id}|{r.activity_key}", "document fact") for r in st.itertuples()]
    comps = sorted({COMPOUND_OF[n] for n in st.nct_id})
    named = sorted({ISA_OF[n] for n in st[st.text.str.contains(r"\bDSA\b")].nct_id})
    return rows, (f"{len(st)} statements; {' '.join(comps)} only" if len(comps) == 1 else f"{len(st)} statements; {comps}") + \
        f"; DSA named in {', '.join(named)}"


def cp7():
    st = soast[soast.statement_kind == "delegation_activity"]
    filled = grid[(grid.delegated_by_master == "True") & (grid.isa_mark == "True")].activity_key.unique()
    rows = [row("instance", "master delegation", "CPMP", "1.3 SoA", page_of(MASTER_NCT, r.activity_key), r.text,
                f"filled as ISA SoA rows: {'yes' if r.activity_key in filled else 'no'}", SOAST_F, f"{MASTER_NCT}|{r.activity_key}",
                "document fact") for r in st.itertuples()]
    unfilled = sorted(set(st.activity_key) - set(filled))
    assert unfilled == ["Exploratory biomarker samples", "TSH"], unfilled
    lc = read(JOIN / "output" / "lab_coverage.csv")
    tsh = lc[(lc.test_as_printed == "TSH") & (lc.nct_id != MASTER_NCT)]
    rows += [row("instance", "TSH at test level", ISA_OF[r.nct_id], "lab appendix", r.pdf_page, f"{r.column_header} / {r.test_as_printed}",
                 COMPOUND_OF[r.nct_id], JOIN / "output" / "lab_coverage.csv", f"{r.nct_id}|{r.pdf_page}", "document fact") for r in tsh.itertuples()]
    bio = lc[lc.test_as_printed.str.contains("xploratory biomarker", case=False) & (lc.nct_id != MASTER_NCT)]
    rows.append(row("absence", "search", "", "", "", f"ISA lab tests named like 'exploratory biomarker': {len(bio)}; ISA SoA rows: 0",
                    "12 ISAs", JOIN / "output" / "lab_coverage.csv", "Exploratory biomarker samples", "rule-derived"))
    return rows, (f"{st.activity_key.nunique()} activities; {len(set(filled) & set(st.activity_key))} filled as rows; "
                  f"TSH at test level in {tsh.nct_id.nunique()} ISAs; exploratory biomarker samples in {'none' if bio.empty else len(bio)}")


def cp8():
    b = read(CP / "output" / "build_log.csv")
    slots = b[(b.step == "slot") & b.rule.str.startswith("master -> DSA delegation sentence")]
    rows = [row("instance", f"master slot: {r.rule.split(';')[0]}", "CPMP", r.detail.replace("sections ", ""), "", r.item,
                "CPMP(1)-(3), not public", CP / "output" / "build_log.csv", r.item[:40], "rule-derived") for r in slots.itertuples()]
    x = cpx[(cpx.layer == "ISA") & (cpx.target == "DSA") & (cpx.relation == "refers_to")]
    rows += [row("instance", "ISA sentence depends on the DSA", r.doc, r.section, r.page, r.sentence, "CPMP(1)-(3), not public", CPX_F,
                 f"{r.doc}|{r.section}|{r.page}", "rule-derived") for r in x.itertuples()]
    return rows, f"{len(slots)} slots; {len(x)} ISA sentences"


def cp9():
    rows = []
    for f in sorted((CP / "sources" / "ctgov").glob("*.json")):
        j = json.loads(f.read_text())
        ps = j["protocolSection"]
        ids = ps["identificationModule"]
        docs = j.get("documentSection", {}).get("largeDocumentModule", {}).get("largeDocs", [])
        rows.append(row("instance", "registered ISA", ids.get("orgStudyIdInfo", {}).get("id", ids["nctId"]), "", "",
                        f"{ids['nctId']}: {ids.get('briefTitle', '')}; documents posted: {len(docs)}", "LY4065967",
                        f, ids["nctId"], "document fact"))
    cq = read(CP / "output" / "cq_results.csv").set_index("question").answer
    rows.append(row("count", "CQ2", "", "", "", cq["CQ2 new ISA inherits"], "OA07, BP07, NP07", CP / "output" / "cq_results.csv",
                    "CQ2", "rule-derived"))
    return rows, f"{len(rows) - 1} ISAs; {cq['CQ2 new ISA inherits']}"


def cp10():
    s = cps[cps.text.str.contains("tests unique", regex=False)]
    rows = []
    for r in s.itertuples():
        t = re.search(r"[^.]*tests unique[^.]*\.", re.sub(r"\s+", " ", r.text)).group(0)
        rows.append(row("instance", "lab appendix sentence", r.doc, r.number, r.start_page, t, r.doc, CPS_F, f"{r.doc}|{r.number}", "document fact"))
    lc = read(JOIN / "output" / "lab_coverage.csv")
    t = lc[lc.test_as_printed == "TSH"]
    rows += [row("instance", "TSH heading", ISA_OF[r.nct_id], "lab appendix", r.pdf_page, f"{r.column_header} / {r.subgroup} / {r.test_as_printed}".replace(" /  /", " /"),
                 r.nct_id, JOIN / "output" / "lab_coverage.csv", f"{r.nct_id}|{r.pdf_page}", "document fact") for r in t.itertuples()]
    return rows, f"{len(s)} sentences; TSH under {t.column_header.nunique()} headings"


def cp11_rows():
    d = read(CP / "sources" / "crosswalk_decisions.csv")
    rev = pd.concat([read(f) for f in sorted((CP / "output").glob("crosswalk_review_*.csv"))])
    strip = lambda s: re.sub(r" p\d+$", "", s)
    texts = {frozenset((strip(r.a), strip(r.b))): (r.text_a, r.text_b) for r in rev.itertuples()}
    rows = []
    for r in d.itertuples():
        ta, tb = texts[frozenset((r.a, r.b))]
        rows.append(row("instance", r.decision, f"{r.a} / {r.b}", "5", "", f"A: {ta} | B: {tb}", r.band, CP / "sources" / "crosswalk_decisions.csv",
                        f"{r.a}|{r.b}", f"decision by Kerstin: {r.note}"))
    return d, texts, rows


def cp11a():
    d, texts, rows = cp11_rows()
    return rows, f"{len(d)} decisions"


def cp11b():
    d, texts, _ = cp11_rows()
    rows, vals = [], set()
    for r in d[d.note.str.startswith("P1")].itertuples():
        ta, tb = texts[frozenset((r.a, r.b))]
        v = [re.findall(r"(?:less than|<)\s*(\d+)\s*ml", x, re.I) for x in (ta, tb)]
        vals |= {int(x) for vv in v for x in vv}
        rows.append(row("instance", "keep apart: different value", f"{r.a} / {r.b}", "5", "", f"A: {ta} | B: {tb}", r.band,
                        CP / "sources" / "crosswalk_decisions.csv", f"{r.a}|{r.b}", f"decision by Kerstin: {r.note}"))
    return rows, f"eGFR values {'/'.join(map(str, sorted(vals)))}"


def cp12():
    s = cps[(cps.doc == "CPMP") & cps.text.str.contains("prior to randomization at Visit 3 will be used as baseline", regex=False)]
    rows = []
    for r in s.itertuples():
        t = re.search(r"[^.]*prior to randomization at Visit 3 will be used as baseline[^.]*\.", re.sub(r"\s+", " ", r.text)).group(0)
        rows.append(row("instance", "master baseline definition", "CPMP", r.number, r.start_page, t, "all ISAs", CPS_F, f"CPMP|{r.number}", "document fact"))
    v3 = grid[(grid.visit == "V3") & (grid.isa_mark == "True") & (grid.master_mark == "True")].drop_duplicates("activity_key")
    for r in v3.itertuples():
        rows.append(row("instance", "marked at V3 in master and ISA", "CPMP", "1.3 SoA", page_of(MASTER_NCT, r.activity_key), f"{r.activity_key} at V3",
                        "master and at least one ISA", GRID_F, f"{r.activity_key}|V3", "rule-derived"))
    return rows, f"{len(s)} master sentences; {len(v3)} activities marked at V3 in master and ISA"


def cp13():
    cl = read(UMP / "output_cpmp" / "step4" / "cross_layer_changes.csv")
    rows = [row("instance", f"{r.field}; names version: {r.names_version}", r.amendment, r.section, "", r.text, r.change, UMP / "output_cpmp" / "step4" / "cross_layer_changes.csv",
                r.change, "document fact") for r in cl.itertuples()]
    s = cps[cps.text.str.contains("tests unique", regex=False)]
    named = 0
    for r in s.itertuples():
        t = re.search(r"[^.]*tests unique[^.]*\.", re.sub(r"\s+", " ", r.text)).group(0)
        named += bool(re.search(r"amendment|version", t, re.I))
    return rows, f"{(cl.names_version == 'True').sum()} of {len(cl)} amendment texts; {named} of {len(s)} panel sentences"


def cp14():
    am = read(UMP / "output_cpmp" / "step4" / "amendment_changes.csv")
    j = json.loads((UMP / "output_cpmp" / "step4" / "cpmp_usdm_v2.json").read_text())
    n = [0]

    def walk(o):
        if isinstance(o, dict):
            n[0] += o.get("instanceType") == "StudyChange"
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(j)
    sh = read(UMP / "output_cpmp" / "step5" / "cq4_shared_rationale.csv")
    a = am[am.rationale != ""]
    rows = [row("instance", "change with brief rationale", r.doc, r.section_as_printed, r.page, f"{r.description} | rationale: {r.rationale}",
                f"amendment ({r.amendment})", UMP / "output_cpmp" / "step4" / "amendment_changes.csv", f"{r.amendment}|row {r.row}", "document fact") for r in a.itertuples()]
    rows += [row("count", "rationale in more than one document", "", r.sections, "", r.rationale, r.docs, UMP / "output_cpmp" / "step5" / "cq4_shared_rationale.csv",
                 r.rationale[:40], "rule-derived") for r in sh.itertuples()]
    return rows, f"{n[0]} changes; {len(sh)} shared rationales"


def cp15():
    inv = read(UMP / "inventory.csv")
    d = inv[inv.layer == "DSA"]
    rows = [row("absence", "cited, not posted", r.sponsor_protocol_no, "", "", f"{r.sponsor_protocol_no}: no NCT record, no posted document; cited by {r.cited_by}",
                "CT.gov, EU CTIS, EudraCT, FDA, publications (Plan 1)", UMP / "inventory.csv", r.sponsor_protocol_no, "document fact")
            for r in d.itertuples()]
    assert (d.ctgov_filename == "").all() and (d.nct_id == "").all()
    return rows, f"{len(d)} DSAs not posted"


SELECT = {re.sub(r"^(rc|cp)(\d+)(\w?)$", lambda m: f"{m.group(1).upper()}-{m.group(2)}{m.group(3)}", f.__name__): f for f in
          [rc1, rc2, rc3, rc4, rc5, rc6, rc7, rc8, rc9, rc10, rc11, rc12, rc13, rc14, rc15, rc16, rc17, rc18, rc19, rc20,
           cp1, cp2, cp3, cp4, cp5, cp6, cp7, cp8, cp9, cp10, cp11a, cp11b, cp12, cp13, cp14, cp15]}

req = read(HERE / "sources" / "requirements.csv")
fnd = read(HERE / "sources" / "findings.csv")
assert set(fnd.requirement) <= set(req.requirement), set(fnd.requirement) - set(req.requirement)
assert list(fnd.finding_id) == list(SELECT), (list(fnd.finding_id), list(SELECT))
allrows, checks, bad = [], [], []
for f in fnd.itertuples():
    rows, observed = SELECT[f.finding_id]()
    assert rows, f"{f.finding_id}: no evidence rows"
    ok = f.expected == "*" or observed == f.expected
    checks.append({"finding_id": f.finding_id, "case": f.case, "requirement": f.requirement, "expected": f.expected,
                   "observed": observed, "evidence_rows": len(rows), "check": "pass" if f.expected != "*" and ok else ("first counted here" if ok else "FAIL")})
    if not ok:
        bad.append((f.finding_id, f.expected, observed))
    for r in rows:
        allrows.append({"requirement": f.requirement, "case": f.case, "finding_id": f.finding_id, "finding": f.finding, **r})
checked = pd.DataFrame(checks)
print(checked.to_string(index=False, max_colwidth=70))
if bad:
    raise SystemExit(f"observed differs from expected: {bad}")
out = pd.DataFrame(allrows)[COLUMNS]
# REMAP-CAP rows with a section but no page: page of the same sentence in step 1 cross-references, else the
# section's page range (marked "a-b (section)")
xr_page = {(r.doc, r.section, re.sub(r"\s+", " ", r.sentence).strip()): r.page for r in xr.itertuples()}
sec_pages = {(r.doc, r.number): (r.start_page, r.end_page) for r in sec.itertuples()}
fill = []
for r in out.itertuples():
    if r.case != "REMAP-CAP" or r.page != "" or (r.doc, r.section) not in sec_pages:
        fill.append(r.page)
    elif (r.doc, r.section, r.text) in xr_page:
        fill.append(xr_page[(r.doc, r.section, r.text)])
    else:
        a, b = sec_pages[(r.doc, r.section)]
        fill.append(a if a == b else f"{a}-{b} (section)")
out["page"] = fill
(HERE / "output").mkdir(exist_ok=True)
out.to_csv(HERE / "output" / "evidence_matrix.csv", index=False)
checked.to_csv(HERE / "output" / "findings_checked.csv", index=False)
print(f"{len(out)} evidence rows; {len(fnd)} findings; {out.requirement.nunique()} requirements")
print(pd.crosstab(out.requirement, out.case).to_string())
