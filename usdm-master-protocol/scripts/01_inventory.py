"""Step 1 of Plan 1: inventory of public CPMP documents on ClinicalTrials.gov.

Input:  sources/ctgov_api/cpmp_studies.json  (CT.gov API v2 records, H0P-MC-*)
        sources/pdf/<NCT>_<filename>.pdf     (large docs as posted on CT.gov)
Output: inventory.csv

All values come from the API JSON or from the PDF text layer. Nothing is filled in.
Values not found are left empty.
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pypdfium2 as pdfium

BASE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
API = BASE / "sources" / "ctgov_api" / "cpmp_studies.json"
PDF_DIR = BASE / "sources" / "pdf"
OUT = BASE / "inventory.csv"

DSA_BY_PREFIX = {"OA": "CPMP(1)", "BP": "CPMP(2)", "NP": "CPMP(3)"}


def collapse(text):
    """Remove all whitespace. Needed because many pages have a character-spaced text layer."""
    return re.sub(r"\s+", "", text).replace("￾", "-")


def read_pages(pdf_path):
    pdf = pdfium.PdfDocument(str(pdf_path))
    pages = [pdf[i].get_textpage().get_text_range() for i in range(len(pdf))]
    image_only = []
    for i in range(len(pdf)):
        if len(pages[i].strip()) < 40 and any(o.type == 3 for o in pdf[i].get_objects()):
            image_only.append(i + 1)
    return pages, image_only


def cover_title(cover):
    """Title as printed on the CT.gov cover page (page 1): lines between the protocol line and the NCT line."""
    lines = [l.strip() for l in cover.splitlines() if l.strip()]
    start = next(i for i, l in enumerate(lines) if re.match(r"^(Protocol|Clinical Study Protocol)", l))
    end = next(i for i, l in enumerate(lines) if re.match(r"^NCT\d{8}$", l))
    title = " ".join(lines[start + 1:end])
    return title.replace("�", "ti")


def title_page_fields(page):
    c = collapse(page)
    amend = re.search(r"AmendmentNumber:(.{0,30}?)(?:Compound|Brief|Acronym)", c)
    approval = re.search(r"ApprovalDate:(\d{1,2}-[A-Za-z]{3}-\d{4})", c) or re.search(r"Approvedon(\d{1,2}[A-Za-z]{3}\d{4})", c)
    doc_id = re.search(r"DocumentID:(VV-CLIN-\d+)", c)
    inds = re.findall(r"(LY\d+IND:?\d+|MasterProtocolIND:?\d+|^IND:\d+|IND:\d+)", c)
    return {
        "amendment_on_title_page": amend.group(1) if amend else "",
        "approval_date_on_title_page": approval.group(1) if approval else "",
        "lilly_document_id": doc_id.group(1) if doc_id else "",
        "ind_numbers": "; ".join(dict.fromkeys(inds)),
    }


def doc_history(all_c):
    m = re.search(r"DOCUMENTHISTORY(.{0,160})", all_c)
    if not m:
        return ""
    return m.group(1).split("OverallRationale")[0]


studies = json.load(open(API))
rows = []
for s in studies:
    p = s["protocolSection"]
    ident = p["identificationModule"]
    nct = ident["nctId"]
    sec_ids = [x["id"] for x in ident.get("secondaryIdInfos", [])]
    sponsor_no = next(x for x in sec_ids if x.startswith("H0P-MC-"))
    layer = "master" if sponsor_no == "H0P-MC-CPMP" else "ISA"
    prefix = sponsor_no.replace("H0P-MC-", "")[:2]
    base = {
        "layer": layer,
        "nct_id": nct,
        "sponsor_protocol_no": sponsor_no,
        "ctgov_secondary_ids": "; ".join(sec_ids),
        "ctgov_brief_title": ident["briefTitle"],
        "ctgov_status": p["statusModule"]["overallStatus"],
        "ctgov_first_submitted": p["statusModule"]["studyFirstSubmitDate"],
        "dsa_by_disease_prefix": DSA_BY_PREFIX.get(prefix, "") if layer == "ISA" else "",
    }
    docs = s.get("documentSection", {}).get("largeDocumentModule", {}).get("largeDocs", [])
    if not docs:
        rows.append({**base, "ctgov_doc_label": "(no documents posted)"})
        continue
    for d in docs:
        row = {
            **base,
            "ctgov_doc_label": d["label"],
            "ctgov_doc_date": d["date"],
            "ctgov_upload_date": d["uploadDate"],
            "ctgov_filename": d["filename"],
            "ctgov_size_bytes": d["size"],
        }
        if d["typeAbbrev"] == "Prot":
            pdf_path = PDF_DIR / f"{nct}_{d['filename']}"
            pages, image_only = read_pages(pdf_path)
            all_c = "".join(collapse(x) for x in pages)
            spaced = []
            for i, pg in enumerate(pages):
                toks = pg.split()
                if len(toks) > 50 and sum(len(t) == 1 for t in toks) / len(toks) > 0.4:
                    spaced.append(i + 1)
            dsa_refs = sorted(set(re.findall(r"CPMP\s*[\[(](\d)[\])]", all_c)))
            row.update({
                "document_title": cover_title(pages[0]),
                **title_page_fields(pages[1]),
                "document_history": doc_history(all_c),
                "dsa_numbers_cited_in_text": "; ".join(f"CPMP({x})" for x in dsa_refs),
                "pdf_pages": len(pages),
                "redaction_CCI_count": all_c.count("CCI"),
                "redaction_PPD_count": all_c.count("PPD"),
                "image_only_pages": "; ".join(map(str, image_only)),
                "char_spaced_text_pages": len(spaced),
            })
        rows.append(row)

# DSA layer: rows for each DSA identifier cited by the ISAs. No DSA document is posted on any record.
for prefix, dsa in DSA_BY_PREFIX.items():
    citing = sorted(r["sponsor_protocol_no"] for r in rows if dsa in r.get("dsa_numbers_cited_in_text", "").split("; "))
    rows.append({
        "layer": "DSA",
        "sponsor_protocol_no": f"H0P-MC-{dsa}",
        "ctgov_doc_label": "(not posted on any CT.gov record)",
        "dsa_by_disease_prefix": dsa,
        "cited_by": "; ".join(citing),
    })

df = pd.DataFrame(rows)
order = {"master": 0, "DSA": 1, "ISA": 2}
df = df.sort_values(["layer", "sponsor_protocol_no"], key=lambda c: c.map(order) if c.name == "layer" else c)
df.to_csv(OUT, index=False)
print(f"wrote {OUT} rows={len(df)}")
