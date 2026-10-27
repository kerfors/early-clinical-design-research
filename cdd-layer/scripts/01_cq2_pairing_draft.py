"""CQ2 pairing draft: each Core -> DSA delegation / overridable default,
paired with the CS_DSA 6 statement that answers it.

All pairings are analyst readings (tier analyst-reading), for review.
DSA evidence snippets are asserted to occur verbatim in sections.csv.
core_row = row position in cross_references.csv (0-based).
"""
from pathlib import Path

import pandas as pd

SEED = Path(__file__).resolve().parents[2] / "usdm-master-protocol" / "output_remapcap" / "step2"
OUT = Path(__file__).resolve().parents[1] / "output" / "cq2_pairing_draft.csv"

# Response vocabulary
#   takes_explicit  DSA states it uses the Core content
#   silent          DSA does not address it; the Core default applies by silence
#   fills           DSA specifies the delegated content
#   fills_none      DSA states explicitly that there is none / not applicable
#   defers_back     DSA refers the delegated content back to the Core
#   not_applicable  the condition in the Core statement does not hold for this domain
#   ambiguous       reading not settled; see note
PAIRS = [
    (51, "9.1", "no additional clinical testing is specified in this protocol", "fills_none",
     "Reads 'sampling' (Core) as covered by 'testing' (DSA)."),
    (75, "", "", "silent",
     "No statement on initial allocation. DSA 6 is not a domain initiation."),
    (76, "", "", "silent",
     "No statement on allocation for an added intervention."),
    (77, "10.1", "The decision regarding the reference control can only be made after having achieved a trigger for efficacy", "ambiguous",
     "Domain has a 'no corticosteroid' comparator now. After its removal (pre-specified in 10.1) the domain has no control arm, and the Core default would then apply. Is 'no corticosteroid' a control arm in the Core sense?"),
    (78, "10.3", "Response Adaptive Randomization may be applied.", "ambiguous",
     "Three interventions overall, but hydrocortisone is Severe State only (8.3.1), so the Moderate State has two. Does 'may be applied' override the two-intervention default for the Moderate State?"),
    (79, "8.5.1", "The primary endpoint for this domain is the primary outcome as specified in Core Protocol documents.", "takes_explicit",
     "Unversioned; resolves differently under Core 4.0 and 4.1 (see CQ1, Core 4.1 7.6.2)."),
    (90, "9.4", "All corticosteroids will be administered on an open-label basis.", "fills", ""),
    (112, "10.2", "The statistical model will permit borrowing between all strata as specified in Core Protocol documents.", "takes_explicit",
     "No alternative gamma; Core borrowing taken. 10.2 also fills the unit-of-analysis strata."),
    (114, "10.5", "Interactions with all other domains are either not evaluable or not considered possible and will not be incorporated into the statistical model", "fills_none", ""),
    (115, "10.6", "Nesting is not applicable to this domain.", "fills_none", ""),
    (117, "", "", "silent",
     "No statement on priors. Silence read as 'none used'; the Core sentence is conditional ('If informative priors are used')."),
    (124, "", "", "not_applicable",
     "Not an early phase or seamless Phase 2/3 domain (no statement either way). 10.8 sets an equivalence delta, which is not this delegation."),
    (133, "10.3", "the cap on the maximum or minimum proportion of patients assigned to an intervention that is specified in core protocol documents may be modified by the Statistical Analysis Committee (SAC)", "takes_explicit",
     "Takes the Core cap, but delegates further: SAC may modify it, as an operational decision in the Current State document. Applies to two-intervention domains: same Moderate State question as row 78."),
    (138, "", "", "ambiguous",
     "Generic delegation of 'individual processes'; no single answering statement. Proposal: keep out of CQ2."),
    (140, "8.3.1", "Patients will be randomly assigned to receive one of the following open-label study interventions.", "fills",
     "Also 9.4."),
    (142, "9.3", "Refer to relevant core protocol documents for criteria for the discontinuation of participation in this trial.", "defers_back",
     "Circular: Core 8.6 says domain-specific criteria are in the DSA; the DSA points back to the Core. Note: DSA speaks of discontinuation of participation in the trial, Core of discontinuation of an allocated intervention."),
    (143, "8.4", "All use of systemic corticosteroids is recorded and the reason for any new or additional administration will be documented.", "fills",
     "8.4 also: etomidate after enrollment not permitted."),
    (144, "9.2.1", "Additional domain-specific data will be collected.", "fills", ""),
    (148, "11.2", "Other SAEs should be reported only where, in the opinion of the site investigator, the event might reasonably have occurred as a consequence of a study intervention or study participation", "ambiguous",
     "Reporting requirement is stated; 'established safety profile' is not stated explicitly (11.3 says corticosteroids have been used for decades)."),
    (151, "8.5.2", "serious adverse events (SAE) as defined in the Core Protocol", "ambiguous",
     "Core sentence is descriptive rather than a delegation; Step 2 classification 'delegates' to be reviewed."),
    (153, "11.2", "Potential domain-specific harms related to corticosteroid therapy include hyperglycemia, nosocomial infections and ICU-acquired weakness.", "fills", ""),
]

# Questions that would settle a reading; not settled from the documents (2026-10-24).
OPEN_QUESTIONS = {
    77: "Is 'no corticosteroid' a control arm in the Core 7.5.2 sense, and does the no-control-arm default apply after its removal?",
    78: "Does CS_DSA 10.3 'RAR may be applied' override the Core two-intervention default (no RAR) for the Moderate State, where two interventions are available?",
    133: "Does the Core 60% cap for two-intervention domains apply to the Moderate State, where two interventions are available?",
    148: "Does CS_DSA 11.2 answer the 'established safety profile' part of Core 8.12.1, or only the reporting part?",
    151: "Is Core 8.12.3 'as specified in DSAs' a delegation or a descriptive statement? (Step 2 classification kept.)",
}

# Generic delegation, names no specific content: kept in the table, not in CQ2 expected results.
EXCLUDE_FROM_CQ2 = {138}

xref = pd.read_csv(SEED / "cross_references.csv")
sections = pd.read_csv(SEED / "sections.csv", dtype={"number": str})
dsa = sections[sections["doc"] == "CS_DSA"].set_index("number")

core = xref[(xref["doc"] == "CORE") & (xref["target"] == "DSA")
            & xref["relation"].isin(["delegates", "default_overridable"])]
assert sorted(core.index) == sorted(p[0] for p in PAIRS), "PAIRS do not cover exactly the Core->DSA delegations/defaults"
assert core["relation"].value_counts().to_dict() == {"delegates": 15, "default_overridable": 6}
assert set(OPEN_QUESTIONS) <= set(core.index) and EXCLUDE_FROM_CQ2 <= set(core.index)

rows = []
for core_row, dsa_sec, snippet, response, note in PAIRS:
    c = xref.loc[core_row]
    if dsa_sec:
        text = dsa.loc[dsa_sec, "text"]
        assert snippet in text, f"snippet not verbatim in CS_DSA {dsa_sec}: {snippet}"
        dsa_page = int(dsa.loc[dsa_sec, "start_page"])
    else:
        assert snippet == "", f"row {core_row}: snippet without DSA section"
        dsa_page = None
    rows.append({
        "core_row": core_row,
        "core_doc_version": "CORE 4.0",
        "core_section": c["section"],
        "core_page": c["page"],
        "core_relation": c["relation"],
        "core_sentence": c["sentence"],
        "dsa_doc_version": "CS_DSA 6",
        "dsa_section": dsa_sec,
        "dsa_section_start_page": dsa_page,
        "dsa_evidence": snippet,
        "response": response,
        "note": note,
        "open_question": OPEN_QUESTIONS.get(core_row, ""),
        "in_cq2_expected": core_row not in EXCLUDE_FROM_CQ2,
        "tier": "analyst-reading",
    })

out = pd.DataFrame(rows)
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False)
print(out.groupby(["core_relation", "response"]).size().to_string())
print(f"wrote {OUT} ({len(out)} rows)")
