"""Document and static-source checks only; does not build or run vendor code."""
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
QA = Path(__file__).resolve().parent
OWNED = [
    "README.md", "product.md", "handoff.md", "decision-log.md", "work-log.md",
    "desk-companion/docs/architecture.md", "desk-companion/docs/operator-guide.md",
    "research/2026-10-05-rig-arm/secondary-development-review.md",
]


def git(*args, cwd=ROOT):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def main():
    reading = json.loads((QA / "reading-record.json").read_text())
    assert reading["complete"] and len(reading["files"]) == 122
    assert reading["total_lines"] == 11376
    for f in reading["files"]:
        assert f["read_ranges"] == [[1, f["lines"]]], f["path"]
    links, missing = [], []
    for name in OWNED + [str(QA.relative_to(ROOT) / "verification.md")]:
        p = ROOT / name
        body = p.read_text()
        assert len(re.findall(r"^```", body, re.M)) % 2 == 0, name
        for target in re.findall(r"\]\((<[^>]+>|[^)]+)\)", body):
            target = target.strip("<>")
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target:
                continue
            resolved = p.parent / target
            links.append({"file": name, "target": target})
            if not resolved.exists():
                missing.append(links[-1])
    assert not missing, missing
    for name in ["product.md", "handoff.md", "research/2026-10-05-rig-arm/secondary-development-review.md"]:
        assert not re.search(r"Group\s*0?02\b|Group02\b", (ROOT / name).read_text())

    source = json.loads((ROOT / "research/2026-10-05-rig-arm/source-register.json").read_text())
    for row in source["sources"]:
        if "evidence" in row:
            assert (ROOT / "research/2026-10-05-rig-arm" / row["evidence"]).is_file()
    for row in source["screenshots"]:
        p = ROOT / "research/2026-10-05-rig-arm" / row["path"]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == row["sha256"]
    for repo in source["repository_snapshots"]:
        checkout = ROOT / ".runtime/rig-arm-research" / repo["repository"].split("/")[-1]
        assert git("rev-parse", "HEAD", cwd=checkout) == repo["commit"]
        for name, digest in repo["selected_code_files"].items():
            assert hashlib.sha256((checkout / name).read_bytes()).hexdigest() == digest

    local = ROOT / ".runtime/rig-arm-research/rig_local"
    omni = ROOT / ".runtime/rig-arm-research/rig_omni"
    http = (local / "main/mcp_http_server.cc").read_text()
    assert all(x in http for x in ['"/mcp"', '"tools/list"', '"tools/call"', "HTTP_POST"])
    assert "mcp_http_server.cc" in (local / "main/CMakeLists.txt").read_text()
    assert "McpHttpServer::GetInstance().Start()" in (local / "main/application.cc").read_text()
    omni_arm = (omni / "main/boards/arm/arm_board.cc").read_text()
    assert all(x in omni_arm for x in ["self.arm.node", "self.arm.shake", "self.arm.teach_play"])
    assert "保存本次轨迹但不自动回放" in omni_arm
    assert "退出示教模式并开始回放" in (local / "main/boards/arm/arm_board.cc").read_text()
    assert "static bool enabled = false;" in (omni / "main/boards/arm/idle_motion.cc").read_text()
    assert "static bool enabled = true;" in (local / "main/boards/arm/idle_motion.cc").read_text()
    audio = (omni / "main/protocols/websocket_protocol.cc").read_text()
    assert '"format", "opus"' in audio and '"sample_rate", 16000' in audio
    llm = (local / "main/cloud_api/llm_client.cc").read_text()
    assert '"tools"' in llm and '"tool_call_id"' in llm and '"enable_thinking"' in llm
    assert "Apache License, Version 2.0" in (omni / "README_CN.md").read_text()
    current_driver = (ROOT / "desk-companion/backend/desk/agents/outputs.py").read_text()
    assert 'choices=["simulator", "pca9685"]' in current_driver

    protected = json.loads((ROOT / "output/qa/task-enhancement-ux-2026-10-03/protected-after.json").read_text())["files"]
    changed = [name for name, expected in protected.items()
               if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected]
    assert not changed, changed
    base = "5b8ce5b81dd075cae3cef6787c964bf0406591e2"
    application_diff = git("diff", "--name-only", base, "--", "desk-companion/backend", "desk-companion/frontend",
                           "desk-companion/config", "desk-companion/scripts", "desk-companion/tests")
    assert not application_diff, application_diff
    assert git("check-ignore", ".runtime/rig-arm-research/rig_omni/README.md")
    for name in ["research-checkpoint.json", "reading-record.json"]:
        json.loads((QA / name).read_text())

    result = {
        "checked_at": datetime.now(ZoneInfo("Asia/Hong_Kong")).isoformat(),
        "status": "passed_document_and_static_source_checks",
        "updated_project_markdown": OWNED,
        "local_links_checked": len(links), "broken_links": missing,
        "initial_reading_complete": True,
        "protected_files_checked": len(protected), "protected_files_changed": changed,
        "current_application_code_changed": False,
        "repository_snapshots_and_source_hashes_verified": True,
        "static_interfaces_located": True,
        "screenshots_visually_reviewed": ["rig-arm-full-unit-shop.jpg", "rig-arm-makerworld.jpg"],
        "not_rerun": ["application tests", "DOCX/PDF rendering"],
        "not_performed": ["vendor code execution or build", "firmware flash", "physical motion", "paid API", "purchase", "supplier contact"],
        "tool_attempts_corrected": ["Wrong config.h read corrected to board_config.h", "Atomic patch with duplicate handoff path was rejected, then split successfully"],
    }
    (QA / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ["status", "local_links_checked", "protected_files_checked", "current_application_code_changed"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
