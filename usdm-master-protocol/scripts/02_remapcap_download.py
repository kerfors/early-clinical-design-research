"""Download all REMAP-CAP protocol documents listed on remapcap.org (current + superseded).

Output:
    sources/remapcap/html/<page>.html          the two listing pages as retrieved
    sources/remapcap/<current|superseded>/*.pdf
    sources/remapcap/manifest.csv              one row per PDF: page, link text, URL, file, bytes, sha256
"""
import hashlib
import html
import re
import subprocess
from datetime import date
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent / "sources" / "remapcap"
SITE = "https://www.remapcap.org"
PAGES = {"current": "protocol-documents", "superseded": "superseded-protocol-documents"}
UA = "Mozilla/5.0"


def curl(url, out):
    subprocess.run(["curl", "-s", "-L", "-f", "-m", "180", "-A", UA, "-o", str(out), url], check=True)


rows = []
for status, page in PAGES.items():
    html_path = BASE / "html" / f"{page}.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    curl(f"{SITE}/{page}", html_path)
    text = html_path.read_text()
    links = re.findall(r'<a[^>]+href="(/s/[^"]+\.pdf)"[^>]*>(.*?)</a>', text, re.S)
    assert links, f"no PDF links found on {page}"
    out_dir = BASE / status
    out_dir.mkdir(parents=True, exist_ok=True)
    for href, label in links:
        label = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", label))).strip()
        out = out_dir / Path(href).name
        curl(SITE + href, out)
        data = out.read_bytes()
        assert data[:5] == b"%PDF-", f"not a PDF: {out}"
        rows.append({
            "listing": status,
            "link_text": label,
            "url": SITE + href,
            "file": f"{status}/{out.name}",
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "retrieved": date.today().isoformat(),
        })
        print(status, out.name, len(data))

pd.DataFrame(rows).to_csv(BASE / "manifest.csv", index=False)
print("documents:", len(rows))
