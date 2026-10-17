"""Check authored links, preserved member data and deliverables without private data."""
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
QA = Path(__file__).parent
BASE = "8129775b641126ead9e11425ef604f0296ce2bc8"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


changed = set(git("diff", "--name-only", BASE).splitlines())
changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
norms = sorted(p for p in changed if p.endswith(".md") and not p.startswith("output/qa/"))
markdown = norms + [str((QA / "verification.md").relative_to(ROOT))]
broken = []
terms = []
rejected_spelling_quotes = []
for name in markdown:
    path = ROOT / name
    body = path.read_text()
    # Titles in links are not used by this task's authored documents.
    for target in re.findall(r"\[[^\]]*\]\((<[^>]+>|[^)]+)\)", body):
        target = target.strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme or not parsed.path:
            continue
        p = Path(unquote(parsed.path))
        if not p.is_absolute():
            p = path.parent / p
        if not p.exists():
            broken.append({"file": name, "target": target})
    for number, line in enumerate(body.splitlines(), 1):
        for bad in re.findall(r"\bGroup(?:0[0-9]+|[0-9]+|\s+02)\b", line):
            if name == "decision-log.md" and line == "1. **用户明确要求：** 所有组号使用 Group 2，取代 Group 02／Group02 写法。":
                rejected_spelling_quotes.append({"file": name, "line": number, "rejected_term": bad})
            else:
                terms.append({"file": name, "line": number, "term": bad})

member = "planning/2026-09-14/group-2-details.json"
original_member = subprocess.check_output(["git", "show", BASE + ":" + member], cwd=ROOT)
assert original_member == (ROOT / member).read_bytes()
assert not broken, broken
assert not terms, terms
assert not any(p.startswith(("inputs/", "output/submission/")) for p in changed)
primary = Path("/Users/tantalum/Documents/ChatGPT/FYP")
assert subprocess.run(["git", "diff", "--quiet"], cwd=primary).returncode == 0
assert subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=primary).returncode == 0
assert git("branch", "--show-current").strip() == "codex/assistant-a1-3d-20261017"

required = [
    "design/desk-companion/characters/2026-10-17-a1-3d/a1-v2.blend",
    "design/desk-companion/characters/2026-10-17-a1-3d/a1-v2.glb",
    "desk-companion/frontend/public/companion/source.json",
    "desk-companion/frontend/public/avatars/VRM-Public-License-1.0.txt",
    "desk-companion/frontend/public/avatars/pixiv-sample.vrm",
    "desk-companion/frontend/public/licenses/three-LICENSE.txt",
    "design/desk-companion/assistant-minimal-20261017/reference.png",
]
for name in required:
    assert (ROOT / name).is_file(), name
sample = ROOT / "desk-companion/frontend/public/avatars/pixiv-sample.vrm"
assert hashlib.sha256(sample.read_bytes()).hexdigest() == "12c2b97e95e700783a6a550dc0eee2d7880aeedccef9ae67bc4c5a2f0f2631a2"
refs = ROOT / "design/desk-companion/characters/2026-10-17-a1-3d/references"
primary_hashes = {
    hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (primary / "design/desk-companion/characters").rglob("*.png")
}
assert all(hashlib.sha256(p.read_bytes()).hexdigest() in primary_hashes for p in refs.glob("*.png"))

result = {
    "checked_at": datetime.now().astimezone().isoformat(),
    "updated_norms": norms,
    "internal_links_valid": True,
    "group_terms_valid": True,
    "historical_rejected_spellings_quoted_explicitly": rejected_spelling_quotes,
    "member_json_unchanged": True,
    "school_originals_and_submission_paths_unchanged": True,
    "primary_tracked_checkout_unchanged": True,
    "original_sample_byte_integrity": True,
    "references_match_primary_original_bytes": True,
    "deliverables_exist": required,
    "reading_supplement": [
        {
            "path": name,
            "lines": len((ROOT / name).read_text().splitlines()),
            "reviewed_ranges": [[1, len((ROOT / name).read_text().splitlines())]],
            "basis": "Fresh initial full read for existing text; complete new authored bodies and final changed hunks reviewed during this same task.",
        }
        for name in norms
    ],
}
(QA / "closeout-validation.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k not in ("reading_supplement", "deliverables_exist")}, indent=2))
