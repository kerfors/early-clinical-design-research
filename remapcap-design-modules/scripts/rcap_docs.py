"""REMAP-CAP documents in scope: one shared definition for scripts 04, 06, 08, 09, 10, 11.

Scripts 01 and 02 keep their own DOCS tables (committed, gated, outputs byte-identical).
Version and issue date are read from each document's header (pages 2-3), not typed:
"Version <v> Dated <d Month yyyy>" (case-insensitive "dated"; IG writes "Version 4 dated ...").
Title = header name + " " + version.
"""
import subprocess
from collections import namedtuple
from datetime import datetime
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "usdm-master-protocol" / "sources" / "remapcap"
HEADER = re.compile(r"Version ([\d.]+)\s+[Dd]ated (\d{1,2} \w+ \d{4})")

Doc = namedtuple("Doc", "key layer short header_name file version date title date_text")

# key: (layer, short, header name, file)
_TABLE = {
    "CORE40": ("CORE", "CORE40", "Core Protocol", "superseded/REMAP-CAP-Core-Protocol-V4-05-November-2024_CLEAN-m9gf.pdf"),
    "CORE41": ("CORE", "CORE41", "Core Protocol", "current/REMAP-CAP-Core-Protocol-V41-29-MAY-2026_CLEAN.pdf"),
    "PANDA": ("PANDA", "PANDA", "Patient, Pathogen and Disease Appendix", "current/REMAP-CAP-Pathogen-ANd-Disease-Appendix-PANDA-V1-05-NOV-2024.pdf"),
    "CS_DSA": ("DSA", "CS", "Corticosteroid Domain-Specific Appendix", "current/REMAP-CAP-Corticosteroid-DSA-V6-05-NOV-2024_CLEAN.pdf"),
    "AB_DSA": ("DSA", "AB", "Antibiotic Domain-Specific Appendix", "current/REMAP-CAP-Antibiotic-DSA-V4-05-NOV-2024_CLEAN.pdf"),
    "TAB_DSA": ("DSA", "TAB", "Tropical Antibiotic Domain-Specific Appendix", "current/REMAP-CAP-Tropical-Antibiotic-DSA-V1-22-APR-2026.pdf"),
    "IAV_DSA": ("DSA", "IAV", "Influenza Antiviral Domain-Specific Appendix", "current/REMAP-CAP-Influenza-Antiviral-DSA-V4_CLEAN-05-OCT-2026.pdf"),
    "MD_DSA": ("DSA", "MD", "Macrolide Duration Domain-Specific Appendix", "current/REMAP-CAP-Macrolide-Duration-DSA-V4-05-NOV-2024_CLEAN.pdf"),
    "IG_DSA": ("DSA", "IG", "COVID-19 Immunoglobulin Therapy Domain-Specific Appendix", "current/REMAP-CAP-COVID-19-Immunoglobulin-DSA-V4-05-NOV-2024_CLEAN.pdf"),
    "MV_DSA": ("DSA", "MV", "Mechanical Ventilation Domain-Specific Appendix", "current/REMAP-CAP-Mechanical-Ventilation-DSA-V20-05-NOV-2024_CLEAN.pdf"),
    "END_DSA": ("DSA", "END", "Endothelial Modulation Domain-Specific Appendix", "current/REMAP-CAP-Endothelial-DSA-V2-05-NOV-2024_CLEAN.pdf"),
    "IIM_DSA": ("DSA", "IIM", "Influenza Immune Modulation Domain-Specific Appendix", "current/REMAP-CAP-Influenza-IM-DSA-V21-09-May-2025_CLEAN.pdf"),
}


def header(rel):
    text = subprocess.run(["pdftotext", "-f", "2", "-l", "3", str(SRC / rel), "-"], capture_output=True,
                          text=True, check=True).stdout
    found = set(HEADER.findall(text))
    assert len(found) == 1, f"{rel}: header version/date {found}"
    version, date = found.pop()
    return version, datetime.strptime(date, "%d %B %Y").date()


def _doc(key):
    layer, short, name, rel = _TABLE[key]
    version, date = header(rel)
    return Doc(key, layer, short, name, rel, version, date, f"{name} {version}", f"{date.day} {date:%b %Y}")


DOCS = {k: _doc(k) for k in _TABLE}
DSAS = [k for k, d in DOCS.items() if d.layer == "DSA"]
SHORT = {k: DOCS[k].short for k in DSAS}
TITLES = {k: DOCS[k].title for k in DSAS}

if __name__ == "__main__":
    for d in DOCS.values():
        print(f"{d.key:8} {d.short:6} {d.title:62} {d.date_text}")
