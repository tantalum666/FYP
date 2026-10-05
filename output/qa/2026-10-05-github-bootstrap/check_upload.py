"""Check upload coverage without printing or saving credential values."""
import hashlib
import json
import re
import subprocess
import zipfile
from collections import Counter
from pathlib import Path

qa = Path(__file__).parent
paths = [Path(p.decode()) for p in subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0") if p]
untracked = [p.decode() for p in subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z"]).split(b"\0") if p]
assert not untracked, ("Untracked eligible project work", untracked)
assert not any(p.is_symlink() for p in paths)
assert not any(p.stat().st_size >= 100 * 1024 * 1024 for p in paths)
for p in paths:
    assert not any(s in {".runtime", ".venv", "node_modules", "python_packages", ".git", "__pycache__", "DerivedData"} for s in p.parts), p
    assert p.name != ".env" and (not p.name.startswith(".env.") or p.name == ".env.example"), p

values = set()
sources = set()

def collect(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if re.search(r"password|secret|token|api_key|device_key|console_key", k, re.I) and isinstance(v, str) and len(v) >= 12 and v != "REDACTED":
                values.add(v.encode())
            else:
                collect(v)
    elif isinstance(x, list):
        for v in x:
            collect(v)

for root in [Path(".runtime"), Path("desk-companion/.runtime")]:
    for p in root.rglob("*.json"):
        if not re.search(r"(?:credentials|config)[^/]*\.json$", p.name) or any(s.startswith("github-upload-scan") for s in p.parts):
            continue
        if p.stat().st_size > 2_000_000:
            continue
        try:
            obj = json.loads(p.read_text())
        except (ValueError, UnicodeError):
            continue
        sources.add(p.as_posix())
        collect(obj)

matches = []
archives = 0
archive_private = []
for p in paths:
    if any(value in p.read_bytes() for value in values):
        matches.append(p.as_posix())
    if p.suffix.lower() in {".zip", ".docx"} and zipfile.is_zipfile(p):
        if p.suffix.lower() == ".zip":
            archives += 1
        with zipfile.ZipFile(p) as archive:
            for info in archive.infolist():
                if re.search(r"(?:^|/)(?:\.runtime|\.env|credentials\.json)(?:/|$)", info.filename):
                    archive_private.append(p.as_posix() + "!" + info.filename)
                if not info.is_dir() and info.file_size < 30_000_000:
                    if any(value in archive.read(info) for value in values):
                        matches.append(p.as_posix() + "!" + info.filename)
assert not matches, ("Private runtime values found", matches)
assert not archive_private, ("Private archive entries found", archive_private)
protected = json.loads(Path("output/qa/task-enhancement-ux-2026-10-03/protected-after.json").read_text())["files"]
changed = [p for p, digest in protected.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest]
assert not changed, changed
inputs = json.loads(Path("inputs/manifest.json").read_text())["files"]
assert all(hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() == item["sha256"] for item in inputs)

report = {
    "date": "2026-10-05",
    "tracked_files": len(paths),
    "tracked_bytes": sum(p.stat().st_size for p in paths),
    "top_level": dict(sorted(Counter(p.parts[0] if len(p.parts) > 1 else "[root]" for p in paths).items())),
    "eligible_untracked_files": [],
    "files_over_100MiB": [],
    "symlinks": [],
    "private_paths_in_index": [],
    "archives_checked": archives,
    "private_archive_entries": [],
    "runtime_comparison": {"configuration_files_checked": len(sources), "distinct_private_values_checked": len(values), "matches": [], "values_recorded": False},
    "protected_originals_checked": len(protected),
    "protected_originals_changed": [],
    "input_original_copies_checked": len(inputs),
    "file_integrity": [{"path": p.as_posix(), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths if qa not in p.parents],
    "manifest_scope": "All indexed file counts; per-file SHA256 excludes this QA directory to avoid self-referential evidence hashes. Remote Git-tree verification covers every committed file including QA.",
}
(qa / "upload-manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "file_integrity"}, ensure_ascii=False, indent=2))
