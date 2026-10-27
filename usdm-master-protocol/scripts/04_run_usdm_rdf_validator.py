"""Plan 1, Step 4: validate output_remapcap/step3/remapcap_usdm.json with usdm-rdf notebook 60.

The usdm-rdf notebook is not modified on disk. It is loaded, its two input
lines (STUDY_JSON, BASE_IRI) are replaced in memory, one cell is appended that
writes the findings to CSV, and it is executed with usdm-rdf/notebooks as
working directory. The executed copy is saved in output_remapcap/step4/.

Needs: nbformat, nbclient, ipykernel, rdflib, pyshacl.
Run:   python3 scripts/04_run_usdm_rdf_validator.py [STUDY_JSON [OUT_DIR [BASE_IRI]]]
       (defaults: step3 JSON, output_remapcap/step4, the REMAP-CAP instance namespace;
        USDM_RDF_DIR overrides the default ../../GitHub/usdm-rdf location)
"""
import os
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

BASE = Path(__file__).resolve().parent.parent
USDM_RDF = Path(os.environ.get("USDM_RDF_DIR", BASE.parent.parent / "GitHub" / "usdm-rdf"))
STUDY_JSON = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else BASE / "output_remapcap" / "step3" / "remapcap_usdm.json"
OUT_DIR = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else BASE / "output_remapcap" / "step4"
BASE_IRI = sys.argv[3] if len(sys.argv) > 3 else "https://kerfors.github.io/early-clinical-design-research/usdm/remapcap/"

SOURCE_NB = USDM_RDF / "notebooks" / "60_validate_study.ipynb"
assert SOURCE_NB.is_file(), SOURCE_NB
assert STUDY_JSON.is_file(), STUDY_JSON
OUT_DIR.mkdir(parents=True, exist_ok=True)

nb = nbformat.read(SOURCE_NB, as_version=4)
input_cell = nb.cells[2]
old_json = 'STUDY_JSON = "../downloads/CDISC_Pilot_Study.json"   # <-- point this at your own file'
old_iri = 'BASE_IRI = ""   # <-- required, e.g. "https://sponsor.example/studies/H2Q-MC-LZZT/"'
assert input_cell.source.count(old_json) == 1 and input_cell.source.count(old_iri) == 1, "notebook 60 input cell changed"
input_cell.source = (input_cell.source
                     .replace(old_json, f'STUDY_JSON = "{STUDY_JSON}"')
                     .replace(old_iri, f'BASE_IRI = "{BASE_IRI}"'))

nb.cells.append(nbformat.v4.new_code_cell(
    "import pandas as pd\n"
    f"_out = Path(r'{OUT_DIR}')\n"
    "pd.DataFrame(rows).to_csv(_out / 'shacl_findings.csv', index=False)\n"
    "pd.DataFrame([{'class': k, 'key': v} for k, vs in unmapped.items() for v in sorted(vs)],"
    " columns=['class', 'key']).to_csv(_out / 'context_unmapped_keys.csv', index=False)\n"
    "print('unknown types:', sorted(unknown_types))\n"
    "print('findings:', len(rows))\n"
))

NotebookClient(nb, timeout=900, kernel_name="python3",
               resources={"metadata": {"path": str(USDM_RDF / "notebooks")}}).execute()
nbformat.write(nb, OUT_DIR / "60_validate_remapcap.ipynb")

for cell in nb.cells:
    if cell.cell_type != "code":
        continue
    for o in cell.outputs:
        if o.output_type == "stream" and o.name == "stdout":
            print(o.text)
        elif o.output_type == "execute_result":
            print(o["data"].get("text/plain", ""))
print("wrote", OUT_DIR)
