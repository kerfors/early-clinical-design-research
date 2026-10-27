"""Extract the upstream terms used by the CPMP design modules (ROBOT MIREOT).

Inputs: pinned OBI, MONDO and HP releases in sources/upstream/ (listed in
sources/upstream/MANIFEST.csv with version IRI and sha256; the .owl files are
git-ignored). Every term here was checked through BioPortal on 2026-10-25.

Output: imports/upstream_import.ttl (classes with their ancestors, labels and
definitions) and imports/upstream_terms.csv (term, source, label read from the
pinned file).

Run: ROBOT_JAR=/path/to/robot.jar python scripts/00_extract_upstream.py
"""
import csv
import hashlib
import os
import subprocess
from pathlib import Path

import rdflib
from rdflib.namespace import OWL, RDF, RDFS

BASE = Path(__file__).resolve().parents[1]
UPSTREAM = BASE / "sources" / "upstream"
IMPORTS = BASE / "imports"
ROBOT_JAR = os.environ["ROBOT_JAR"]

OBO = "http://purl.obolibrary.org/obo/"

# term, source file, kind
TERMS = [
    ("OBI_0500001", "obi.owl", "class"),   # clinical study design
    ("OBI_0500026", "obi.owl", "class"),   # eligibility criterion
    ("OBI_0500027", "obi.owl", "class"),   # inclusion criterion
    ("OBI_0500028", "obi.owl", "class"),   # exclusion criterion
    ("IAO_0000005", "obi.owl", "class"),   # objective specification
    ("IAO_0000033", "obi.owl", "class"),   # directive information entity
    ("IAO_0000007", "obi.owl", "class"),   # action specification (SoA cells, 2026-10-25)
    ("BFO_0000051", "obi.owl", "property"),  # has part
    ("IAO_0000136", "obi.owl", "property"),  # is about
    ("MONDO_0005178", "mondo.owl", "class"),  # osteoarthritis
    ("MONDO_0006626", "mondo.owl", "class"),  # diabetic neuropathy
    ("HP_0003419", "hp.owl", "class"),     # Low back pain
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_manifest():
    with open(UPSTREAM / "MANIFEST.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        actual = sha256(UPSTREAM / row["file"])
        if actual != row["sha256"]:
            raise SystemExit(f"sha256 mismatch for {row['file']}: {actual} != {row['sha256']}")
    return {row["file"] for row in rows}


def robot(*args):
    cmd = ["java", "-Xmx8G", "-jar", ROBOT_JAR, *args]
    subprocess.run(cmd, check=True)


def main():
    files = check_manifest()
    IMPORTS.mkdir(exist_ok=True)
    parts = []
    for source in sorted({t[1] for t in TERMS}):
        if source not in files:
            raise SystemExit(f"{source} not in MANIFEST.csv")
        lower = IMPORTS / f"_terms_{source}.txt"
        lower.write_text("".join(OBO + t[0] + "\n" for t in TERMS if t[1] == source and t[2] == "class"))
        out = IMPORTS / f"_mireot_{source}.ttl"
        robot("extract", "--input", str(UPSTREAM / source), "--method", "MIREOT",
              "--lower-terms", str(lower), "--intermediates", "all",
              "--annotate-with-source", "true", "--output", str(out))
        parts.append(out)

    merged = rdflib.Graph()
    for p in parts:
        merged.parse(p)

    # Object properties are declared from the pinned OBI file (label and definition copied).
    obi = rdflib.Graph()
    obi.parse(UPSTREAM / "obi.owl")
    definition = rdflib.URIRef(OBO + "IAO_0000115")
    for term, source, kind in TERMS:
        if kind != "property":
            continue
        iri = rdflib.URIRef(OBO + term)
        if (iri, RDF.type, OWL.ObjectProperty) not in obi:
            raise SystemExit(f"{term} is not an object property in {source}")
        merged.add((iri, RDF.type, OWL.ObjectProperty))
        for p in (RDFS.label, definition):
            for o in obi.objects(iri, p):
                merged.add((iri, p, o))

    rows = []
    for term, source, kind in TERMS:
        iri = rdflib.URIRef(OBO + term)
        labels = [str(o) for o in merged.objects(iri, RDFS.label)]
        if len(labels) != 1:
            raise SystemExit(f"{term}: expected one label in {source}, found {labels}")
        rows.append({"term": term, "iri": str(iri), "source": source, "kind": kind, "label": labels[0]})

    onto = rdflib.URIRef("https://kerfors.github.io/early-clinical-design-research/cpmp-design-modules/imports/upstream_import")
    merged.add((onto, RDF.type, OWL.Ontology))
    merged.serialize(IMPORTS / "upstream_import.ttl", format="turtle")
    with open(IMPORTS / "upstream_terms.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["term", "iri", "source", "kind", "label"])
        w.writeheader()
        w.writerows(rows)
    for p in parts:
        p.unlink()
    for p in IMPORTS.glob("_terms_*.txt"):
        p.unlink()
    print(f"upstream_import.ttl: {len(merged)} triples; {len(rows)} terms")


if __name__ == "__main__":
    main()
