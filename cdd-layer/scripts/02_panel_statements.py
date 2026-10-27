"""Panel-content statements from the CPMP ISA lab appendices.

Each ISA lab appendix opens with one sentence that allocates panel content
between the master protocol and the ISA ("... This table describes tests
unique for ISA ..."). This script takes that sentence for each ISA from the
lab-table page (page from cpmp-soa-join/output/lab_coverage.csv) and writes
cdd-layer/output/panel_statements.csv.

Sources, in order:
1. PDF text layer (pdftotext), matched by SENTENCE. method = text_layer.
2. cdd-layer/panel_statements_visual.csv, read from the rendered page, for
   pages where 1 finds nothing (letter-spaced or no text layer).
   - Page has a text layer: the transcription must match it letter for
     letter, whitespace ignored. method = visual_checked_against_text_layer.
   - Page has no text layer: method = visual_unchecked.
A page found by neither source stops the script.

Run on a machine with pdftotext:
    python3 cdd-layer/scripts/02_panel_statements.py [path to soa2usdm-collections]
The default path is ~/repos/GitHub/soa2usdm-collections.
"""

import csv
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COLLECTIONS_ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / 'repos' / 'GitHub' / 'soa2usdm-collections'
COLLECTION = COLLECTIONS_ROOT / 'collections' / 'cpmp' / 'protocols'
LAB_COVERAGE = REPO / 'cpmp-soa-join' / 'output' / 'lab_coverage.csv'
VISUAL = REPO / 'cdd-layer' / 'panel_statements_visual.csv'
OUT = REPO / 'cdd-layer' / 'output' / 'panel_statements.csv'
MASTER = 'CPMP'

SENTENCE = re.compile(
    r'(?:The\s+)?(?:master\s+protocol(?:\s+CPMP)?|CPMP\s+master\s+protocol)\s+describes\s+tests'
    r'.*?unique\s+for\s+(?:this\s+ISA|ISA\s+[A-Z0-9\-]+)\.',
    re.S | re.I,
)


def page_text(pdf, page):
    result = subprocess.run(
        ['pdftotext', '-f', str(page), '-l', str(page), str(pdf), '-'],
        check=True, capture_output=True, text=True,
    )
    return result.stdout


def despace(text):
    return re.sub(r'\s+', '', text)


def main():
    pages = {}
    with open(LAB_COVERAGE, newline='') as f:
        for row in csv.DictReader(f):
            if row['isa'] == MASTER:
                continue
            pages.setdefault((row['isa'], row['nct_id']), set()).add(int(row['pdf_page']))
    assert len(pages) == 12, f'expected 12 ISAs, found {len(pages)}'

    with open(VISUAL, newline='') as f:
        visual = {(r['isa'], r['nct_id'], int(r['pdf_page'])): r['text'] for r in csv.DictReader(f)}

    rows = []
    used_visual = set()
    for (isa, nct_id), page_set in sorted(pages.items()):
        assert len(page_set) == 1, f'{isa}: lab table on more than one page {sorted(page_set)}'
        page = page_set.pop()
        pdf = COLLECTION / nct_id / f'{nct_id}.pdf'
        assert pdf.exists(), f'missing {pdf}'
        text = page_text(pdf, page)
        match = SENTENCE.search(text)
        key = (isa, nct_id, page)
        if match:
            assert key not in visual, f'{isa}: found in text layer and also transcribed visually'
            sentence = ' '.join(match.group(0).split())
            method = 'text_layer'
        else:
            assert key in visual, f'{isa} p{page}: no text-layer match and no visual transcription'
            sentence = visual[key]
            used_visual.add(key)
            if text.strip():
                assert despace(sentence) in despace(text), f'{isa} p{page}: transcription does not match the text layer'
                method = 'visual_checked_against_text_layer'
            else:
                method = 'visual_unchecked'
        rows.append({'isa': isa, 'nct_id': nct_id, 'pdf_page': page, 'text': sentence, 'method': method})

    assert used_visual == set(visual), f'unused visual rows: {sorted(set(visual) - used_visual)}'

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['isa', 'nct_id', 'pdf_page', 'text', 'method'])
        writer.writeheader()
        writer.writerows(rows)

    for r in rows:
        print(r['isa'], r['pdf_page'], r['method'], '|', r['text'])


if __name__ == '__main__':
    main()
