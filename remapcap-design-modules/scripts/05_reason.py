"""Merge the modules, check the OWL 2 DL profile, classify with ELK (ROBOT), write the hierarchy.

Same steps as ../cpmp-design-modules/scripts/02_reason.py.
Inputs:  modules/rcap-all.ttl (+ catalog), imports/upstream_import.ttl
Outputs: output/merged.ttl, output/inferred.ttl, output/profile.txt,
         output/design_hierarchy.csv (design class, superclass, asserted/inferred)

Run: ROBOT_JAR=/path/to/robot.jar python scripts/05_reason.py
"""
import os
import subprocess
from pathlib import Path

import pandas as pd
import rdflib
from rdflib.namespace import OWL, RDF, RDFS

BASE = Path(__file__).resolve().parents[1]
MODULES = BASE / "modules"
OUTPUT = BASE / "output"
ROBOT_JAR = os.environ["ROBOT_JAR"]
NS = "https://kerfors.github.io/early-clinical-design-research/remapcap-design-modules/"
DESIGN_PREFIXES = ("CoreDesign", "DomainDesign_", "PandaDesign", "SharedDSA_")


def robot(*args):
    subprocess.run(["java", "-Xmx4G", "-jar", ROBOT_JAR, *args], check=True, cwd=MODULES)


def short(u):
    return str(u).replace(NS, "rcap:")


def main():
    OUTPUT.mkdir(exist_ok=True)
    merged, inferred, profile = OUTPUT / "merged.ttl", OUTPUT / "inferred.ttl", OUTPUT / "profile.txt"
    robot("merge", "--catalog", "catalog-v001.xml", "--input", "rcap-all.ttl", "--output", str(merged))
    robot("validate-profile", "--profile", "DL", "--input", str(merged), "--output", str(profile))
    if "in profile" not in profile.read_text():
        raise SystemExit(f"not OWL 2 DL: see {profile}")
    # ELK fails the run on an inconsistent ontology or an unsatisfiable class.
    robot("reason", "--input", str(merged), "--reasoner", "ELK",
          "--axiom-generators", "SubClass EquivalentClass",
          "--include-indirect", "true", "--exclude-tautologies", "structural",
          "--remove-redundant-subclass-axioms", "false",
          "--output", str(inferred))

    asserted = rdflib.Graph().parse(merged)
    g = rdflib.Graph().parse(inferred)

    obo = "http://purl.obolibrary.org/obo/"
    authored = {s for s in g.subjects(RDF.type, OWL.Class) if isinstance(s, rdflib.URIRef) and str(s).startswith(NS)}
    orphans = [s for s in authored
               if not any(isinstance(o, rdflib.URIRef) and str(o).startswith(obo)
                          for o in g.transitive_objects(s, RDFS.subClassOf))]
    if orphans:
        raise SystemExit(f"{len(orphans)} authored classes without an upstream ancestor, e.g. {orphans[:3]}")
    print(f"{len(authored)} authored classes, each with an upstream ancestor")

    designs = sorted(s for s in authored if str(s)[len(NS):].startswith(DESIGN_PREFIXES))
    rows = []
    for d in designs:
        for sup in g.objects(d, RDFS.subClassOf):
            if not isinstance(sup, rdflib.URIRef) or sup in (OWL.Thing, d) or sup not in designs:
                continue
            rows.append({"design": short(d), "superclass": short(sup),
                         "status": "asserted" if (d, RDFS.subClassOf, sup) in asserted else "inferred"})
    table = pd.DataFrame(rows).sort_values(["design", "superclass"])
    table.to_csv(OUTPUT / "design_hierarchy.csv", index=False)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
