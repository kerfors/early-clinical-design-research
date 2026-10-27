"""REMAP-CAP design modules, step 1: sections and cross-layer statements.

The rules are those of usdm-master-protocol/scripts/build_02_remapcap_structure_nb.py
(Plan 1 Step 2), copied, not imported, because that builder is a notebook generator.
Generalised only where it was specific to the three Step 2 documents:
  - running-header patterns: one pattern per document, from its own name;
  - self reference ("this DSA", "the <name> DSA"): per DSA;
  - layer rank: by layer, so Core 4.0 and 4.1 are both rank 0.
Gate 1: CORE40, PANDA, CS_DSA reproduce Step 2 sections.csv and cross_references.csv.
Gate 2: CORE40 vs CORE41 changed sections (exact text) equal Step 5 core_v40_v41_diff.csv.
"""
import hashlib
import re
from pathlib import Path

import pandas as pd
import pypdfium2 as pdfium

HERE = Path(__file__).resolve().parent.parent
PLAN1 = HERE.parent / "usdm-master-protocol"
SRC = PLAN1 / "sources" / "remapcap"
STEP2 = PLAN1 / "output_remapcap" / "step2"
STEP5 = PLAN1 / "output_remapcap" / "step5"
OUT = HERE / "output" / "step1"
OUT.mkdir(parents=True, exist_ok=True)

# role: (layer, header name, self name, file)
DOCS = {
    "CORE40": ("CORE", "Core Protocol", None, "superseded/REMAP-CAP-Core-Protocol-V4-05-November-2024_CLEAN-m9gf.pdf"),
    "CORE41": ("CORE", "Core Protocol", None, "current/REMAP-CAP-Core-Protocol-V41-29-MAY-2026_CLEAN.pdf"),
    "PANDA": ("PANDA", "Patient, Pathogen and Disease Appendix", None, "current/REMAP-CAP-Pathogen-ANd-Disease-Appendix-PANDA-V1-05-NOV-2024.pdf"),
    "CS_DSA": ("DSA", "Corticosteroid Domain-Specific Appendix", "corticosteroid", "current/REMAP-CAP-Corticosteroid-DSA-V6-05-NOV-2024_CLEAN.pdf"),
    "AB_DSA": ("DSA", "Antibiotic Domain-Specific Appendix", "antibiotic", "current/REMAP-CAP-Antibiotic-DSA-V4-05-NOV-2024_CLEAN.pdf"),
    "TAB_DSA": ("DSA", "Tropical Antibiotic Domain-Specific Appendix", "tropical antibiotic", "current/REMAP-CAP-Tropical-Antibiotic-DSA-V1-22-APR-2026.pdf"),
    "IAV_DSA": ("DSA", "Influenza Antiviral Domain-Specific Appendix", "influenza antiviral", "current/REMAP-CAP-Influenza-Antiviral-DSA-V4_CLEAN-05-OCT-2026.pdf"),
    "MD_DSA": ("DSA", "Macrolide Duration Domain-Specific Appendix", "macrolide duration", "current/REMAP-CAP-Macrolide-Duration-DSA-V4-05-NOV-2024_CLEAN.pdf"),
    "IG_DSA": ("DSA", "COVID-19 Immunoglobulin Therapy Domain-Specific Appendix", "covid-19 immunoglobulin therapy", "current/REMAP-CAP-COVID-19-Immunoglobulin-DSA-V4-05-NOV-2024_CLEAN.pdf"),
    "MV_DSA": ("DSA", "Mechanical Ventilation Domain-Specific Appendix", "mechanical ventilation", "current/REMAP-CAP-Mechanical-Ventilation-DSA-V20-05-NOV-2024_CLEAN.pdf"),
    "END_DSA": ("DSA", "Endothelial Modulation Domain-Specific Appendix", "endothelial modulation", "current/REMAP-CAP-Endothelial-DSA-V2-05-NOV-2024_CLEAN.pdf"),
    "IIM_DSA": ("DSA", "Influenza Immune Modulation Domain-Specific Appendix", "influenza immune modulation", "current/REMAP-CAP-Influenza-IM-DSA-V21-09-May-2025_CLEAN.pdf"),
}

manifest = pd.read_csv(SRC / "manifest.csv").set_index("file")
for role, (_, _, _, rel) in DOCS.items():
    digest = hashlib.sha256((SRC / rel).read_bytes()).hexdigest()
    assert digest == manifest.loc[rel, "sha256"], f"{role}: file differs from manifest"

COMMON_HEADERS = [r"^(CONFIDENTIAL )?Page \d+ of \d+$", r"^\d{1,3}$"]


def header_re(name):
    own = rf"^{re.escape(name)} Version [\d.]+ [Dd]ated \d{{1,2}} \w+ \d{{4}}$"
    return re.compile("|".join([own] + COMMON_HEADERS))


def read_pages(path, hre):
    pdf = pdfium.PdfDocument(str(path))
    pages, removed = [], 0
    for i in range(len(pdf)):
        page = pdf[i]
        textpage = page.get_textpage()
        raw = textpage.get_text_range().replace("\r", "").replace("\ufffe", "-")
        textpage.close()
        page.close()
        lines = raw.split("\n")
        kept = [ln for ln in lines if not hre.match(ln.strip())]
        removed += len(lines) - len(kept)
        pages.append("\n".join(kept))
    pdf.close()
    return pages, removed


pages = {}
for role, (_, name, _, rel) in DOCS.items():
    pages[role], removed = read_pages(SRC / rel, header_re(name))
    print(f"{role:8s} pages={len(pages[role]):3d} header lines removed={removed}")

TOC_END_RE = re.compile(r"(?:\.{2,}|\s)\s*(\d+)\s*$")
TOC_NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s*(.+)$")
# R-outline: DSA TOC lines carry the title text at a fixed x per level (checked on all nine DSAs);
# used to give a level, and then a counted number, to TOC entries whose number is not in the text layer.
TOC_LEVEL_X = {1: 106.5, 2: 116.8, 3: 150.0}
TOC_LEVEL_TOL = 4.0
TOC_UNNUMBERED_X = 72.5  # title at the left margin: not numbered in the document; left without a number
TOC_SKIP_ENTRY_RE = re.compile(r"(?i)^table of (tables|figures)$")


def toc_line_x(path, page_index):
    """(line text, x of the first title character after any printed number) for one TOC page."""
    pdf = pdfium.PdfDocument(str(path))
    textpage = pdf[page_index].get_textpage()
    out, chars = [], []
    for i in range(textpage.count_chars()):
        ch = textpage.get_text_range(i, 1).replace("\ufffe", "-")
        if ch in "\r\n":
            if chars:
                out.append(chars)
            chars = []
            continue
        chars.append((ch, textpage.get_charbox(i)[0]))
    if chars:
        out.append(chars)
    textpage.close()
    pdf.close()
    lines = []
    for cs in out:
        text = "".join(c for c, _ in cs)
        lead = len(text) - len(text.lstrip())
        m = re.match(r"^\d+(?:\.\d+)*\.?\s*", text[lead:])
        k = lead + (m.end() if m else 0)
        while k < len(cs) and cs[k][0].isspace():
            k += 1
        lines.append((text.strip(), cs[k][1] if k < len(cs) else None))
    return lines


def level_from_x(x):
    hits = [lvl for lvl, ref in TOC_LEVEL_X.items() if abs(x - ref) <= TOC_LEVEL_TOL]
    return hits[0] if len(hits) == 1 else None


def toc_pages(pp):
    idx = [i for i, p in enumerate(pp) if re.search(r"(?im)table of contents|^contents$", p)]
    assert idx, "no TOC page"
    start = idx[0]
    end = start
    while end + 1 < len(pp) and len(re.findall(r"\.{4,}\s*\d+\s*$", pp[end + 1], re.M)) >= 3:
        end += 1
    return list(range(start, end + 1))


def parse_toc(pp, path, hre):
    """TOC lines are read from the page itself, so that a bare page number that ends a wrapped entry
    is kept (read_pages drops bare numbers as page numbers); header lines are dropped as before."""
    rows = []
    buffer = ""
    start_x = None
    for i in toc_pages(pp):
        for ln, x in toc_line_x(path, i):
            if not ln or re.match(r"(?i)^(table of contents|contents|table of tables|table of figures)$", ln):
                continue
            if hre.match(ln) and not (buffer and re.fullmatch(r"\d{1,3}", ln)):
                continue
            if not buffer:
                start_x = x
            buffer = (buffer + " " + ln).strip()
            m = TOC_END_RE.search(buffer)
            if not m:
                continue
            entry = TOC_END_RE.sub("", buffer).strip()
            page = int(m.group(1))
            buffer = ""
            n = TOC_NUM_RE.match(entry)
            number, title = (n.group(1), n.group(2).strip()) if n else ("", entry)
            if re.match(r"(?i)^(table|figure) \d+", title):
                continue
            rows.append({"number": number, "title": title, "toc_page": page,
                         "level": number.count(".") + 1 if number else None, "title_x": start_x})
    return pd.DataFrame(rows)


def reconstruct_numbers(role, df):
    """R-outline: a DSA TOC entry with no number in the text layer gets its level from title_x and
    the next number at that level in TOC order. Printed numbers are kept and reset the counters."""
    df = df[~df.title.str.match(TOC_SKIP_ENTRY_RE)].reset_index(drop=True).copy()
    df["number_source"] = "printed"
    log = []
    counters = []
    after_references = False
    for k, r in df.iterrows():
        x_level = level_from_x(r.title_x)
        if not r.number and after_references:
            # back matter (appendices after REFERENCES): not numbered in any document; left without a number
            df.at[k, "number_source"] = "back_matter"
            log.append({"doc": role, "number": "", "title": r.title, "toc_page": r.toc_page,
                        "title_x": round(r.title_x, 1), "x_level": x_level, "number_source": "back_matter",
                        "check": "after_references"})
            continue
        if re.fullmatch(r"(?i)references", r.title):
            after_references = True
        if r.number:
            parts = [int(p) for p in r.number.split(".")]
            log.append({"doc": role, "number": r.number, "title": r.title, "toc_page": r.toc_page,
                        "title_x": round(r.title_x, 1), "x_level": x_level, "number_source": "printed",
                        "check": "x_level_equals_printed" if x_level == len(parts) else "x_level_differs"})
            counters = parts
            continue
        if abs(r.title_x - TOC_UNNUMBERED_X) <= TOC_LEVEL_TOL:
            df.at[k, "number_source"] = "unnumbered"
            log.append({"doc": role, "number": "", "title": r.title, "toc_page": r.toc_page,
                        "title_x": round(r.title_x, 1), "x_level": None, "number_source": "unnumbered",
                        "check": "left_margin"})
            continue
        assert x_level is not None, f"{role}: no level for unnumbered TOC entry {r.title!r} at x={r.title_x}"
        assert len(counters) >= x_level - 1, f"{role}: level {x_level} entry {r.title!r} has no parent"
        nxt = counters[:x_level - 1] + [counters[x_level - 1] + 1 if len(counters) >= x_level else 1]
        counters = nxt
        number = ".".join(map(str, nxt))
        df.at[k, "number"], df.at[k, "level"], df.at[k, "number_source"] = number, x_level, "reconstructed"
        log.append({"doc": role, "number": number, "title": r.title, "toc_page": r.toc_page,
                    "title_x": round(r.title_x, 1), "x_level": x_level, "number_source": "reconstructed",
                    "check": ""})
    # check: every entry whose number or whose parent's number was reconstructed sits under that parent
    nums = list(df.number)
    src = dict(zip(df.number, df.number_source))
    for k, n in enumerate(nums):
        if not n:
            continue
        parent = n.rsplit(".", 1)[0] if "." in n else None
        if parent is None or (src[n] == "printed" and src.get(parent) != "reconstructed"):
            continue
        prev = [m for m in nums[:k] if m and m.count(".") == n.count(".") - 1]
        assert prev and prev[-1] == parent, f"{role}: {n} {df.at[k, 'title']!r} not under {prev[-1] if prev else None}"
        for row in log:
            if row["doc"] == role and row["number"] == n and row["check"] == "":
                row["check"] = "under_parent"
    for row in log:
        if row["number_source"] == "reconstructed" and row["check"] == "":
            row["check"] = "no_child_or_parent_check"
    return df, log


toc, outline_log = {}, []
for role, pp in pages.items():
    df = parse_toc(pp, SRC / DOCS[role][3], header_re(DOCS[role][1]))
    if DOCS[role][0] == "DSA" and (df.number == "").any():
        df, log = reconstruct_numbers(role, df)
        outline_log += log
    else:
        df["number_source"] = "printed"
    toc[role] = df
outline_log = pd.DataFrame(outline_log)
outline_log.to_csv(OUT / "reconstructed_numbers.csv", index=False)
print("R-outline:", outline_log.groupby(["doc", "number_source", "check"]).size().to_string())


def body_lines(pp, start_page):
    out = []
    for i in range(start_page, len(pp)):
        for ln in pp[i].split("\n"):
            if ln.strip():
                out.append((i + 1, ln.strip()))
    return out


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def locate_headings(role):
    pp = pages[role]
    first_body = toc_pages(pp)[-1] + 1
    lines_ = body_lines(pp, first_body)
    rows = []
    pos = 0
    for r in toc[role][toc[role].number != ""].itertuples():
        key = norm(r.title)[:25]
        num_re = re.compile(r"^" + re.escape(r.number) + r"\.?\s*")
        hit = None
        for j in range(pos, len(lines_)):
            page, ln = lines_[j]
            if r.number_source == "reconstructed":
                # the body heading has no number either: the line is the heading text alone
                # (or its first part, when the heading wraps)
                full, here = norm(r.title), norm(ln)
                nxt = norm(lines_[j + 1][1]) if j + 1 < len(lines_) else ""
                if here == full or (len(here) < len(full) and (here + nxt).startswith(full)):
                    hit = j
                    break
                continue
            if num_re.match(ln):
                rest = norm(num_re.sub("", ln))
                nxt = norm(lines_[j + 1][1]) if j + 1 < len(lines_) else ""
                if (rest + nxt).startswith(key):
                    hit = j
                    break
        rows.append({"doc": role, "number": r.number, "title": r.title, "level": r.level,
                     "toc_page": r.toc_page, "line_idx": hit,
                     "body_page": lines_[hit][0] if hit is not None else None,
                     "found": hit is not None})
        if hit is not None:
            pos = hit + 1
    return pd.DataFrame(rows), lines_


located, lines_by_doc = {}, {}
for role in DOCS:
    located[role], lines_by_doc[role] = locate_headings(role)
    df = located[role]
    print(f"{role:8s} TOC numbered={len(df)} found={int(df.found.sum())} not_found={int((~df.found).sum())}")
not_found = pd.concat(located.values()).query("not found")[["doc", "number", "title", "toc_page"]]
not_found.to_csv(OUT / "headings_not_found.csv", index=False)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def sections_for(role):
    df = located[role][located[role].found].sort_values("line_idx").reset_index(drop=True)
    lines_ = lines_by_doc[role]
    rows = []
    for k, r in df.iterrows():
        end = int(df.loc[k + 1, "line_idx"]) if k + 1 < len(df) else len(lines_)
        chunk = lines_[int(r.line_idx) + 1:end]
        text = re.sub(r"\s+", " ", " ".join(ln for _, ln in chunk)).strip()
        rows.append({"doc": role, "number": r.number, "title": r.title, "level": r.level,
                     "start_page": r.body_page, "end_page": chunk[-1][0] if chunk else r.body_page,
                     "n_chars": len(text), "text": text})
    return pd.DataFrame(rows)


sections = pd.concat([sections_for(role) for role in DOCS], ignore_index=True)

# Core 4.1 body has 7.6.3 and 7.6.4 headings that its TOC omits. Same split rule as
# usdm-master-protocol/scripts/build_05_remapcap_amendment_breakpoints_nb.py (Plan 1 Step 5).
i762 = sections.index[(sections.doc == "CORE41") & (sections.number == "7.6.2")]
assert len(i762) == 1
i762 = i762[0]
m = re.search(r"\s7\.6\.3\.\s*Exploratory outcomes\s(.*?)\s7\.6\.4\.\s*(Adaptations to the primary endpoint in the event of a pandemic)\s(.*)$",
              sections.at[i762, "text"])
assert m, "7.6.3 / 7.6.4 headings not found inside V4.1 7.6.2"
base = sections.loc[i762].to_dict()
new_rows = [dict(base, number="7.6.3", title="Exploratory outcomes", level=3, start_page=None, end_page=None,
                 text=m.group(1), n_chars=len(m.group(1))),
            dict(base, number="7.6.4", title=m.group(2), level=3, start_page=None, end_page=None,
                 text=m.group(3), n_chars=len(m.group(3)))]
sections.at[i762, "text"] = sections.at[i762, "text"][:m.start()].strip()
sections.at[i762, "n_chars"] = len(sections.at[i762, "text"])
sections = pd.concat([sections.iloc[:i762 + 1], pd.DataFrame(new_rows), sections.iloc[i762 + 1:]], ignore_index=True)
sentences = (sections.assign(sentence=sections.text.map(SENTENCE_SPLIT.split))
             .explode("sentence")[["doc", "number", "title", "start_page", "sentence"]])
sentences = sentences[sentences.sentence.str.len() > 0].reset_index(drop=True)

TARGETS = {
    "CORE": r"core protocol",
    "PANDA": r"\bpanda\b|patient, pathogen and disease appendix",
    "DSA": r"\bdsas?\b|domain[- ]specific appendi(?:x|ces)",
    "RSA": r"\brsas?\b|region(?:al)?[- ]specific appendi(?:x|ces)",
    "SAA": r"statistical analysis appendix",
    "CURRENT_STATE": r"current state",
    "PANDEMIC": r"pandemic appendix",
}


def self_dsa(name):
    return (r"\bthis (?:version of the )?(?:dsa|domain[- ]specific appendix)\b"
            rf"|\bthe {re.escape(name)} (?:dsa|domain[- ]specific appendix)\b")


def relation_patterns(t):
    rel = r"(?:the\s+)?(?:relevant\s+)?(?:current version of the\s+)?"
    return {
        "refers_to": [rf"\b(?:as|is|are|be|that is|those)\s+(?:specified|defined|described|outlined)\s+in\s+{rel}(?:{t})",
                      rf"\brefers?\s+to\s+{rel}(?:{t})",
                      rf"\bsee\s+{rel}(?:{t})",
                      rf"\bguidance provided in the\s+(?:{t})",
                      rf"\binformation is contained in the\s+(?:{t})",
                      rf"\b(?:outcome|endpoint|endpoints|triggers?)\s+(?:as\s+)?(?:specified|described|defined)\s+in\s+{rel}(?:{t})"],
        "extends": [rf"\badditional to those specified in (?:the\s+)?(?:{t})",
                    rf"\bin addition to\b[^.]*\b(?:{t})"],
        "modifies": [rf"\bmodifications?\s+to\b[^.]*\bspecified in (?:the\s+)?(?:{t})"],
        "delegates": [rf"\b(?:will be|are|is|be)\s+specified\s+(?:only\s+)?in\s+(?:each|the|a|that)\s+(?:{t})"],
        "default_overridable": [rf"\bunless\s+(?:otherwise\s+)?specified\s+in\s+(?:a|the|each)\s+(?:{t})"],
        "version_scoped": [rf"\b(?:this|the current|the previous|previous|earlier)\s+versions?\s+of\s+(?:the\s+)?(?:{t})",
                           rf"\bdated before this\s+(?:{t})\s+amendment"],
    }


RANK = {"CORE": 0, "PANDA": 1, "SAA": 1, "CURRENT_STATE": 1, "PANDEMIC": 1, "DSA": 2, "RSA": 2}
DOWNWARD_ONLY = {"delegates", "default_overridable"}
FLAGS = list(relation_patterns("x").keys())
rows = []
for s in sentences.itertuples():
    layer, _, self_name, _ = DOCS[s.doc]
    low = s.sentence.lower()
    for target, tpat in TARGETS.items():
        if not re.search(tpat, low):
            continue
        if target == "DSA" and layer == "DSA":
            without_self = re.sub(self_dsa(self_name), "", low)
            if not re.search(tpat, without_self):
                target = "SELF"
        flags = {f: any(re.search(p, low) for p in pats) for f, pats in relation_patterns(tpat).items()} \
            if target != "SELF" else {f: False for f in FLAGS}
        if target == "SELF":
            direction = "self"
        elif RANK[target] > RANK[layer]:
            direction = "down"
            if flags["refers_to"]:
                flags["refers_to"] = False
                flags["delegates"] = True
        else:
            direction = "up" if RANK[target] < RANK[layer] else "same_rank"
            flags.update({f: False for f in DOWNWARD_ONLY})
        label = "+".join(f for f in FLAGS if flags[f]) or "mention_only"
        rows.append({"doc": s.doc, "layer": layer, "section": s.number, "section_title": s.title, "page": s.start_page,
                     "target": target, "direction": direction, "relation": label, **flags, "sentence": s.sentence})
xrefs = pd.DataFrame(rows)

# Gate 1: Step 2 reproduced
step2_sec = pd.read_csv(STEP2 / "sections.csv", dtype=str, keep_default_na=False)
step2_x = pd.read_csv(STEP2 / "cross_references.csv", dtype=str, keep_default_na=False)
ren = {"CORE40": "CORE"}
mine_sec = sections[sections.doc.isin(["CORE40", "PANDA", "CS_DSA"])].assign(doc=lambda d: d.doc.replace(ren))
mine_sec = mine_sec[step2_sec.columns].astype(str).reset_index(drop=True)
assert len(mine_sec) == len(step2_sec), f"gate 1 sections: {len(mine_sec)} != {len(step2_sec)}"
assert (mine_sec.values == step2_sec.values).all(), "gate 1: sections differ from Step 2"
mine_x = xrefs[xrefs.doc.isin(["CORE40", "PANDA", "CS_DSA"])].assign(doc=lambda d: d.doc.replace(ren))
mine_x = mine_x[step2_x.columns].astype(str).reset_index(drop=True)
assert len(mine_x) == len(step2_x), f"gate 1 xrefs: {len(mine_x)} != {len(step2_x)}"
assert (mine_x.values == step2_x.values).all(), "gate 1: cross references differ from Step 2"
print("gate 1 ok: Step 2 sections and cross references reproduced")

# Gate 2: Core 4.0 vs 4.1 changed sections
c40 = sections[sections.doc == "CORE40"].set_index("number").text
c41 = sections[sections.doc == "CORE41"].set_index("number").text
common = c40.index.intersection(c41.index)
changed = sorted(n for n in common if c40[n] != c41[n])
only40 = sorted(set(c40.index) - set(c41.index))
only41 = sorted(set(c41.index) - set(c40.index))
step5 = pd.read_csv(STEP5 / "core_v40_v41_diff.csv", dtype=str)
print(f"gate 2: changed={len(changed)} only_in_4.0={only40} only_in_4.1={only41}; step5 rows={len(step5)}")
print("  step5 sections:", sorted(step5.section))
print("  mine changed:  ", changed)
assert set(changed) | set(only41) == set(step5.section) and not only40, "gate 2: Core 4.0/4.1 changes differ from Step 5"
print("gate 2 ok")

sections.to_csv(OUT / "sections.csv", index=False)
xrefs.to_csv(OUT / "cross_references.csv", index=False)
cross = xrefs[(xrefs.target != "SELF") & (xrefs.target != xrefs.layer.where(xrefs.layer != "DSA", "-"))]
print(pd.crosstab([cross.doc, cross.target], cross.relation, margins=True).to_string())
