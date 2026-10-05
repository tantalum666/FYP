"""Compare every remote committed blob against the local Git tree."""
import argparse
import json
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

parser = argparse.ArgumentParser()
parser.add_argument("--report", required=True)
args = parser.parse_args()
repo = "tantalum666/FYP"

def api(path):
    return json.loads(subprocess.check_output(["gh", "api", path]))

metadata = api("repos/" + repo)
remote = api("repos/" + repo + "/git/ref/heads/main")["object"]["sha"]
local = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
assert metadata["private"] and metadata["visibility"] == "private"
assert metadata["default_branch"] == "main"
assert remote == local, ("Remote HEAD differs", remote, local)
remote_tree_sha = api("repos/" + repo + "/git/commits/" + remote)["tree"]["sha"]
local_tree_sha = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"]).decode().strip()
assert remote_tree_sha == local_tree_sha
tree = api("repos/" + repo + "/git/trees/" + remote_tree_sha + "?recursive=1")
assert tree["sha"] == remote_tree_sha
assert not tree.get("truncated"), "GitHub returned a truncated tree"
remote_files = {item["path"]: (item["mode"], item["type"], item["sha"]) for item in tree["tree"] if item["type"] != "tree"}
local_files = {}
for record in subprocess.check_output(["git", "ls-tree", "-r", "-z", "HEAD"]).split(b"\0"):
    if not record:
        continue
    header, raw_path = record.split(b"\t", 1)
    mode, kind, digest = header.decode().split()
    local_files[raw_path.decode()] = (mode, kind, digest)
missing = sorted(set(local_files) - set(remote_files))
extra = sorted(set(remote_files) - set(local_files))
changed = sorted(path for path in set(local_files) & set(remote_files) if local_files[path] != remote_files[path])
assert not missing and not extra and not changed, (missing, extra, changed)
assert all(kind == "blob" and mode in {"100644", "100755"} for mode, kind, _ in local_files.values())
report = {
    "verified_at": datetime.now(ZoneInfo("Asia/Hong_Kong")).isoformat(),
    "repository": repo,
    "url": metadata["html_url"],
    "private": metadata["private"],
    "default_branch": metadata["default_branch"],
    "local_head": local,
    "remote_head": remote,
    "head_matches": True,
    "git_tree_sha": tree["sha"],
    "tree_truncated": False,
    "local_files": len(local_files),
    "remote_files": len(remote_files),
    "missing_paths": missing,
    "unexpected_paths": extra,
    "content_or_mode_mismatches": changed,
    "top_level": dict(sorted(Counter(path.split("/")[0] if "/" in path else "[root]" for path in remote_files).items())),
    "remote_blob_bytes": sum(item.get("size", 0) for item in tree["tree"] if item["type"] == "blob"),
    "scope": "Every committed path, type, mode and Git blob hash; no inference from push exit alone.",
}
output = Path(args.report)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(report, ensure_ascii=False, indent=2))
