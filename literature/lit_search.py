"""Themed Europe PMC searches, 2019-2026. Writes lit_hits.csv and prints the top hits per theme.

Usage: python3 lit_search.py <out_dir>
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

OUT = Path(sys.argv[1])
OUT.mkdir(exist_ok=True)
YEARS = "PUB_YEAR:[2019 TO 2026]"
QUERIES = {
    "programme_design": '(TITLE:"clinical development plan" OR TITLE:"clinical development program" OR TITLE:"clinical development programme" '
                        'OR TITLE:"drug development program" OR TITLE:"drug development programme" OR TITLE:"program design" '
                        'OR TITLE:"programme design" OR ABSTRACT:"clinical development plan")',
    "tpp": 'TITLE:"target product profile" OR TITLE:"target product profiles"',
    "master_protocol_data": '(TITLE:"master protocol" OR TITLE:"master protocols" OR TITLE:"platform trial" OR TITLE:"platform trials") AND '
                            '(ABSTRACT:"data" AND (ABSTRACT:"standard" OR ABSTRACT:"interoperability" OR ABSTRACT:"reporting" '
                            'OR ABSTRACT:"registry" OR ABSTRACT:"registration" OR ABSTRACT:"terminology"))',
    "digital_protocol": '(TITLE:"protocol" OR ABSTRACT:"protocol") AND (ABSTRACT:"machine-readable" OR ABSTRACT:"digital protocol" '
                        'OR ABSTRACT:"structured protocol" OR ABSTRACT:"Unified Study Definitions Model" OR ABSTRACT:"USDM" '
                        'OR ABSTRACT:"ICH M11" OR ABSTRACT:"Common Protocol Template")',
    "design_knowledge": '(TITLE:"trial design" OR TITLE:"study design" OR TITLE:"protocol design" OR TITLE:"clinical trial" '
                        'OR TITLE:"clinical trials") AND (TITLE:"ontology" OR TITLE:"knowledge graph" OR TITLE:"knowledge representation" '
                        'OR TITLE:"semantic" OR TITLE:"design rationale")',
    "decision_science": '(TITLE:"go/no-go" OR TITLE:"quantitative decision" OR TITLE:"decision making" OR TITLE:"decision-making") '
                        'AND (TITLE:"drug development" OR TITLE:"clinical development")',
}
FIELDS = ["pmid", "pmcid", "doi", "title", "authorString", "journalTitle", "pubYear", "citedByCount", "pubType"]

rows = []
for theme, q in QUERIES.items():
    params = {"query": f"({q}) AND {YEARS}", "format": "json", "pageSize": 100, "resultType": "lite",
              "sort": "CITED desc"}
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as resp:
        data = json.load(resp)
    hits = data["hitCount"]
    for r in data["resultList"]["result"]:
        rows.append({"theme": theme, "theme_hits": hits, **{f: r.get(f, "") for f in FIELDS}})
    print(f"== {theme}: {hits} hits")

df = pd.DataFrame(rows)
df.to_csv(OUT / "lit_hits.csv", index=False)
pd.set_option("display.width", 250)
for theme, g in df.groupby("theme", sort=False):
    print(f"\n######## {theme}")
    print(g.head(30)[["pubYear", "citedByCount", "title", "journalTitle"]].to_string(index=False, max_colwidth=110))
