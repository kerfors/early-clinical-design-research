"""Inventory of REMAP-CAP protocol documents (current + superseded).

Input:  sources/remapcap/manifest.csv and the PDFs it lists
Output: remapcap_inventory.csv

Document name, version and date are taken from the document's own page 1 text
(the "<name> Version <n> dated <date>" statement). Values not found stay empty
and are flagged in column parse_note.
"""
import re
from pathlib import Path

import pandas as pd
import pypdfium2 as pdfium

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "sources" / "remapcap"
OUT = BASE / "remapcap_inventory.csv"

LAYER_RULES = [
    ("Pandemic Appendix", "core-appendix"),
    ("Patient, Pathogen and Disease Appendix", "population-appendix"),
    ("Statistical Analysis Appendix", "core-appendix"),
    ("Registry Appendix", "core-appendix"),
    ("Region-Specific Appendix", "region-appendix"),
    ("Regional Specific Appendix", "region-appendix"),
    ("Domain-Specific Appendix", "domain-appendix"),
    ("Domain Specific Appendix", "domain-appendix"),
    ("Core Protocol", "core"),
    (" DSA", "domain-appendix"),
]
VERSION_RE = re.compile(
    r"(?P<name>[A-Za-z0-9 ,():/\-–]{3,160}?)\s+Version\s+(?P<version>\d+(?:\.\d+)*)\s+(?:Master\s+)?"
    r"(?:dated|Dated)\s+(?P<date>\d{1,2}\s*(?:st|nd|rd|th)?\s+[A-Za-z]+,?\s+\d{4})"
)


def clean(text):
    text = text.replace("￾", "-").replace("SUPERSEDED", " ")
    return re.sub(r"\s+", " ", text)


def layer_of(name):
    for key, layer in LAYER_RULES:
        if key.lower() in name.lower():
            return layer
    return ""


manifest = pd.read_csv(SRC / "manifest.csv")
rows = []
for m in manifest.itertuples():
    pdf = pdfium.PdfDocument(str(SRC / m.file))
    pages = [pdf[i].get_textpage().get_text_range() for i in range(len(pdf))]
    raw_all = " ".join(pages)
    first = clean(" ".join(pages[:2]))
    hit = VERSION_RE.search(first)
    name = hit.group("name").strip(" :-") if hit else ""
    name = re.sub(r"^.*?(REMAP-CAP|Randomized)", r"\1", name) if name else ""
    near_empty = [i + 1 for i, p in enumerate(pages) if len(p.strip()) < 40]
    spaced = sum(
        1 for p in pages if len(p.split()) > 50 and sum(len(t) == 1 for t in p.split()) / len(p.split()) > 0.4
    )
    core_refs = sorted(set(re.findall(r"Core Protocol,? [Vv]ersion\s*(\d+(?:\.\d+)*)", clean(raw_all))))
    rows.append({
        "listing": m.listing,
        "link_text": m.link_text,
        "file": m.file,
        "layer": layer_of(name) or layer_of(m.link_text),
        "document_name_on_page1": name,
        "version": hit.group("version") if hit else "",
        "dated": re.sub(r"\s+", " ", hit.group("date")) if hit else "",
        "pages": len(pages),
        "superseded_watermark": "SUPERSEDED" in raw_all,
        "near_empty_pages": len(near_empty),
        "char_spaced_pages": spaced,
        "core_protocol_versions_cited": "; ".join(core_refs),
        "trial_ids_cited": "; ".join(sorted(set(re.findall(r"NCT\d{8}|\d{4}-\d{6}-\d{2}", raw_all)))),
        "parse_note": "" if hit else "no 'Version n dated' statement on pages 1-2",
        "sha256": m.sha256,
    })

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)
print(f"wrote {OUT.name} rows={len(df)} unparsed={int((df.parse_note != '').sum())}")
