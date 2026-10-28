"""USDM files without the section text, for publication.

Input (not in the public repo): output_cpmp/step4/cpmp_usdm_v2.json and
output_remapcap/step6/remapcap_usdm_v3.json, the most complete file of each case.
Output: published/cpmp_usdm_v2_without_text.json, published/remapcap_usdm_v3_without_text.json.

Replaced by TEXT_MARK, because they hold whole section text: every NarrativeContentItem.text
(required, 1..1, so kept, not removed) and every StudyIntervention.description (REMAP-CAP: the
section 8.3 paragraphs). Everything else is kept as it is: identifiers, document structure,
section numbers and headings, amendments with their changes, and the design content at sentence
level (criteria, objectives, endpoints, arm and intervention names), all already public in this repo.

Checks (fail fast): same objects with the same ids in input and output; apart from the replaced
text, input and output are equal.
Run:    python3 scripts/20_usdm_without_text.py   (from usdm-master-protocol/)
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "published"
FILES = {
    "output_cpmp/step4/cpmp_usdm_v2.json": "cpmp_usdm_v2_without_text.json",
    "output_remapcap/step6/remapcap_usdm_v3.json": "remapcap_usdm_v3_without_text.json",
}
TEXT_MARK = "[Section text not published here; see the source document.]"


def objects(x, out):
    if isinstance(x, dict):
        if "instanceType" in x:
            out.append(x)
        for v in x.values():
            objects(v, out)
    elif isinstance(x, list):
        for v in x:
            objects(v, out)
    return out


OUT.mkdir(exist_ok=True)
for src, dst in FILES.items():
    data = json.loads((HERE / src).read_text(encoding="utf-8"))
    original = copy.deepcopy(data)
    items = [o for o in objects(data, []) if o["instanceType"] == "NarrativeContentItem"]
    descs = [o for o in objects(data, []) if o["instanceType"] == "StudyIntervention" and o.get("description")]
    chars = sum(len(o["text"]) for o in items) + sum(len(o["description"]) for o in descs)
    for o in items:
        o["text"] = TEXT_MARK
    for o in descs:
        o["description"] = TEXT_MARK
    before, after = objects(original, []), objects(data, [])
    assert [o["id"] for o in before] == [o["id"] for o in after], src
    for b, a in zip(before, after):
        diff = {k for k in set(b) | set(a) if b.get(k) != a.get(k) and not isinstance(b.get(k), (dict, list))}
        allowed = {"NarrativeContentItem": {"text"}, "StudyIntervention": {"description"}}.get(b["instanceType"], set())
        assert diff <= allowed, (src, b["id"], diff)
    (OUT / dst).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{dst}: {len(after)} objects; replaced {len(items)} NarrativeContentItem texts and "
          f"{len(descs)} StudyIntervention descriptions ({chars:,} characters)")
