"""Publish the committed tree via GitHub Git Database after smart-HTTP resets.

Uses gh's existing authentication. Never reads/prints a token or rewrites main.
Only the new task branch is created, after every blob and tree hash is checked.
"""
import base64
import json
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QA = Path(__file__).parent
REPO = "tantalum666/FYP"
BASE = "8129775b641126ead9e11425ef604f0296ce2bc8"
ART = "50e174f50a4130b3c666f836f666f6aa4cde4b32"
BRANCH = "codex/assistant-a1-3d-20261017"
state_path = QA / "git-database-upload.json"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def api(path, body=None):
    args = ["gh", "api", "repos/" + REPO + "/" + path]
    if body is not None:
        args += ["--method", "POST", "--input", "-"]
    for attempt in range(3):
        try:
            response = subprocess.run(
                args,
                input=json.dumps(body).encode() if body is not None else None,
                capture_output=True,
                timeout=55,
            )
            if response.returncode == 0:
                return json.loads(response.stdout)
            status = re.search(r"HTTP ([0-9]{3})", response.stderr.decode(errors="replace"))
            reason = "HTTP " + status.group(1) if status else "transport error"
        except subprocess.TimeoutExpired:
            reason = "timeout"
        print(json.dumps({"retry": attempt + 1, "endpoint": path, "reason": reason}), flush=True)
        if attempt < 2:
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError("GitHub request failed for " + path + "; credentials/response suppressed")


def blob_exists(sha):
    try:
        result = subprocess.run(
            ["gh", "api", "repos/" + REPO + "/git/blobs/" + sha, "--jq", ".sha"],
            capture_output=True, timeout=55,
        )
        return result.returncode == 0 and result.stdout.decode().strip() == sha
    except subprocess.TimeoutExpired:
        return False


head = git("rev-parse", "HEAD").decode().strip()
assert git("branch", "--show-current").decode().strip() == BRANCH
assert git("rev-parse", "HEAD^").decode().strip() == BASE
tree = git("rev-parse", "HEAD^{tree}").decode().strip()
base_tree = git("rev-parse", BASE + "^{tree}").decode().strip()
state = json.loads(state_path.read_text()) if state_path.exists() else {
    "local_commit": head,
    "base": BASE,
    "tree": tree,
    "uploaded_blobs": [],
    "transport": "GitHub Git Database via gh; no force update",
    "preceding_smart_http_attempts": 3,
}
assert state["local_commit"] == head and state["tree"] == tree


def save():
    state_path.write_text(json.dumps(state, indent=2) + "\n")


novel = {
    line.split()[0]
    for line in git("rev-list", "--objects", head, "^" + BASE, "^" + ART).decode().splitlines()
}
uploaded = set(state["uploaded_blobs"])
entries = []
paths = git("diff", "--name-only", "-z", BASE, head).decode().split("\0")
for path in filter(None, paths):
    item = git("ls-tree", "-z", head, "--", path).decode().rstrip("\0")
    if not item:
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
        continue
    header, found_path = item.split("\t", 1)
    mode, kind, sha = header.split()
    assert found_path == path and kind == "blob"
    data = git("cat-file", "blob", sha)
    entry = {"path": path, "mode": mode, "type": "blob"}
    if sha not in novel or sha in uploaded:
        entry["sha"] = sha
    else:
        try:
            text = data.decode("utf-8")
            inline = "\0" not in text and len(data) <= 200000
        except UnicodeDecodeError:
            inline = False
        if inline:
            entry["content"] = text
        else:
            if not blob_exists(sha):
                try:
                    result = api("git/blobs", {"content": base64.b64encode(data).decode(), "encoding": "base64"})
                    assert result["sha"] == sha, "Blob content hash mismatch"
                except RuntimeError:
                    assert blob_exists(sha), "Blob upload not confirmed by independent readback"
            uploaded.add(sha)
            state["uploaded_blobs"] = sorted(uploaded)
            save()
            print(json.dumps({"uploaded": len(uploaded), "path": path, "bytes": len(data), "sha_verified": True}), flush=True)
            entry["sha"] = sha
    entries.append(entry)

result = api("git/trees", {"base_tree": base_tree, "tree": entries})
assert result["sha"] == tree, "Remote tree differs from committed local tree"
state["remote_tree_verified"] = True
save()
raw = git("cat-file", "commit", head).decode()
headers, message = raw.split("\n\n", 1)


def identity(label):
    line = next(line for line in headers.splitlines() if line.startswith(label + " "))
    match = re.fullmatch(r"[^ ]+ (.*) <(.*)> ([0-9]+) ([+-][0-9]{4})", line)
    assert match
    name, email, timestamp, offset = match.groups()
    minutes = (int(offset[1:3]) * 60 + int(offset[3:])) * (1 if offset[0] == "+" else -1)
    date = datetime.fromtimestamp(int(timestamp), timezone(timedelta(minutes=minutes))).isoformat()
    return {"name": name, "email": email, "date": date}


commit = api("git/commits", {
    "message": message, "tree": tree, "parents": [BASE],
    "author": identity("author"), "committer": identity("committer"),
})
assert commit["tree"]["sha"] == tree
assert [parent["sha"] for parent in commit["parents"]] == [BASE]
state["remote_commit"] = commit["sha"]
state["commit_sha_matches_local"] = commit["sha"] == head
save()
try:
    ref = api("git/refs", {"ref": "refs/heads/" + BRANCH, "sha": commit["sha"]})
except RuntimeError:
    # A lost successful response must be independently read back, not forced.
    ref = api("git/ref/heads/" + BRANCH)
assert ref["object"]["sha"] == commit["sha"]
state["branch_created"] = True
save()
print(json.dumps({"branch_created": True, "tree_verified": True, "remote_commit": commit["sha"], "same_commit": commit["sha"] == head}), flush=True)
