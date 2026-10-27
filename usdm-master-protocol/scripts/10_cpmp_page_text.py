"""CPMP: page text of the 13 posted protocols, with OCR where the text layer is not usable.

Page kinds use the Step 1 rules (scripts/01_inventory.py):
- image_only: fewer than 40 characters of text and an image object on the page.
- letter_spaced: more than 50 tokens and more than 40% of them one character long.
- text_layer: all other pages.

Methods:
- text_layer: the PDF text layer as is (pypdfium2, as in Step 1 and Step 2).
- text_layer_letters_ocr_spacing: letter-spaced page. The letters and line breaks
  come from the text layer; OCR (tesseract) is used only to place word boundaries.
  Each text-layer line (whitespace removed) is aligned with the OCR letter
  stream of the whole page, order-free, by repeated longest match (difflib,
  runs of at least MIN_MATCH characters); a word boundary is taken over only
  inside an aligned run. `coverage` = share of the text layer's letters and digits
  (punctuation, e.g. TOC dot leaders, not counted) inside aligned blocks.
  Letters outside aligned blocks are kept, without word boundaries.
  By construction the output has exactly the text-layer letters (checked).
- ocr_unchecked: image-only page. Text from OCR, not checked against anything.

Output: output_cpmp/step2/page_text.csv, one row per page.
Needs: pypdfium2, pandas, tesseract on the PATH.
Run:   python3 scripts/10_cpmp_page_text.py
"""
import difflib
import re
import subprocess
import tempfile
from pathlib import Path

import pandas as pd
import pypdfium2 as pdfium

BASE = Path(__file__).resolve().parent.parent
PDF_DIR = BASE / "sources" / "pdf"
OUT_DIR = BASE / "output_cpmp" / "step2"
DPI = 300
MIN_MATCH = 4  # shortest aligned run taken over, unless the remaining part of the line is shorter


def page_kind(text, pdf_page):
    if len(text.strip()) < 40 and any(o.type == 3 for o in pdf_page.get_objects()):
        return "image_only"
    toks = text.split()
    if len(toks) > 50 and sum(len(t) == 1 for t in toks) / len(toks) > 0.4:
        return "letter_spaced"
    return "text_layer"


def ocr(pdf_page):
    image = pdf_page.render(scale=DPI / 72).to_pil()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "page.png"
        image.save(png)
        result = subprocess.run(["tesseract", str(png), "stdout", "-l", "eng"],
                                check=True, capture_output=True, text=True)
    return result.stdout


def respace(layer_text, ocr_text):
    """Text-layer letters and line breaks, word boundaries from OCR inside aligned blocks."""
    letters, line_break_after = [], set()
    for line in layer_text.split("\n"):
        chars = [c for c in line if not c.isspace()]
        if not chars:
            continue
        letters.extend(chars)
        line_break_after.add(len(letters) - 1)
    ocr_letters, ocr_boundary_after = [], set()
    for word in ocr_text.split():
        ocr_letters.extend(word)
        ocr_boundary_after.add(len(ocr_letters) - 1)
    # Per text-layer line, order-free: repeatedly take the longest match of a still
    # unmatched part of the line anywhere in the OCR stream (tables are read in a
    # different order by the text layer and by OCR).
    matcher = difflib.SequenceMatcher(None, autojunk=False)
    matcher.set_seq2(ocr_letters)
    space_after, matched = set(), 0
    starts = [0] + sorted(i + 1 for i in line_break_after)[:-1]
    for start, end in zip(starts, sorted(i + 1 for i in line_break_after)):
        line = letters[start:end]
        matcher.set_seq1(line)
        todo = [(0, len(line))]
        while todo:
            s, e = todo.pop()
            m = matcher.find_longest_match(s, e, 0, len(ocr_letters))
            if m.size < min(MIN_MATCH, e - s) or m.size == 0:
                continue
            for k in range(m.size):
                if line[m.a + k].isalnum():
                    matched += 1
                if m.b + k in ocr_boundary_after:
                    space_after.add(start + m.a + k)
            todo.extend(x for x in ((s, m.a), (m.a + m.size, e)) if x[1] > x[0])
    out = []
    for i, c in enumerate(letters):
        out.append(c)
        if i in line_break_after:
            out.append("\n")
        elif i in space_after:
            out.append(" ")
    text = "".join(out).strip()
    assert re.sub(r"\s+", "", text) == "".join(letters), "letters changed"
    return text, sum(1 for c in letters if c.isalnum()), matched


def main():
    inventory = pd.read_csv(BASE / "inventory.csv")
    protocols = inventory[inventory.ctgov_filename.fillna("").str.startswith("Prot")]
    assert len(protocols) == 13, f"expected 13 protocols, found {len(protocols)}"

    rows = []
    for doc in protocols.itertuples():
        (pdf_path,) = sorted(PDF_DIR.glob(f"{doc.nct_id}_Prot_*.pdf"))
        pdf = pdfium.PdfDocument(str(pdf_path))
        n_pages = len(pdf)
        n_spaced = n_image = 0
        for i in range(n_pages):
            pdf_page = pdf[i]
            layer = pdf_page.get_textpage().get_text_range().replace("\r", "").replace("￾", "-")
            kind = page_kind(layer, pdf_page)
            row = {"layer": doc.layer, "nct_id": doc.nct_id, "sponsor_protocol_no": doc.sponsor_protocol_no,
                   "file": pdf_path.name, "page": i + 1, "page_kind": kind}
            if kind == "text_layer":
                row.update(method="text_layer", letters=sum(1 for c in layer if c.isalnum()), matched="", coverage="", text=layer.strip())
            elif kind == "letter_spaced":
                n_spaced += 1
                text, n_letters, matched = respace(layer, ocr(pdf_page))
                row.update(method="text_layer_letters_ocr_spacing", letters=n_letters, matched=matched,
                           coverage=round(matched / n_letters, 4), text=text)
            else:
                n_image += 1
                text = ocr(pdf_page).strip()
                row.update(method="ocr_unchecked", letters=sum(1 for c in text if c.isalnum()), matched="", coverage="", text=text)
            rows.append(row)
        pdf.close()
        image_expected = [int(x) for x in str(doc.image_only_pages).split(";") if x.strip() and x.strip() != "nan"]
        assert n_spaced == int(doc.char_spaced_text_pages), f"{doc.nct_id}: {n_spaced} letter-spaced pages, inventory {doc.char_spaced_text_pages}"
        assert n_image == len(image_expected), f"{doc.nct_id}: {n_image} image-only pages, inventory {image_expected}"
        print(f"{doc.sponsor_protocol_no:12s} pages={n_pages:3d} letter_spaced={n_spaced:3d} image_only={n_image}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "page_text.csv", index=False)
    spaced = df[df.method == "text_layer_letters_ocr_spacing"]
    print("pages:", len(df), "| by method:", df.method.value_counts().to_dict())
    print("letter-spaced coverage: min", spaced.coverage.min(), "median", spaced.coverage.median(),
          "| pages below 0.95:", int((spaced.coverage < 0.95).sum()))


if __name__ == "__main__":
    main()
