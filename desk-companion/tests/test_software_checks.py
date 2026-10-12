import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess


spec = importlib.util.spec_from_file_location(
    "check_assets", Path(__file__).resolve().parents[1] / "scripts" / "check_assets.py"
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def fixture_assets(tmp_path):
    body = b"fictional asset fixture"
    digest = hashlib.sha256(body).hexdigest()
    for directory, name in [("avatars", "sample.vrm"), ("companion", "a1.png")]:
        folder = tmp_path / "public" / directory
        folder.mkdir(parents=True)
        (folder / name).write_bytes(body)
        source = (
            {"asset": name, "sha256": digest}
            if directory == "avatars"
            else {"assets": [{"image": name, "sha256": digest}]}
        )
        (folder / "source.json").write_text(json.dumps(source))
    return tmp_path


def test_asset_check_accepts_both_exact_manifest_hashes(tmp_path):
    assert checker.check_assets(fixture_assets(tmp_path)) == []


def test_asset_check_reports_missing_and_changed_files(tmp_path):
    frontend = fixture_assets(tmp_path)
    (frontend / "public" / "avatars" / "sample.vrm").unlink()
    (frontend / "public" / "companion" / "a1.png").write_bytes(b"changed")
    assert checker.check_assets(frontend) == [
        "Missing bundled asset: public/avatars/sample.vrm",
        "Asset hash mismatch: public/companion/a1.png",
    ]


def test_asset_check_rejects_manifest_paths_outside_asset_directory(tmp_path):
    frontend = fixture_assets(tmp_path)
    manifest = frontend / "public" / "companion" / "source.json"
    manifest.write_text(json.dumps({"assets": [{"image": "../outside", "sha256": "0" * 64}]}))
    assert checker.check_assets(frontend) == [
        "Unreadable or invalid manifest: public/companion/source.json"
    ]


def test_asset_check_reports_bad_manifest_without_changing_files(tmp_path):
    frontend = fixture_assets(tmp_path)
    manifest = frontend / "public" / "avatars" / "source.json"
    manifest.write_text("not JSON")
    assert checker.check_assets(frontend) == [
        "Unreadable or invalid manifest: public/avatars/source.json"
    ]
    assert manifest.read_text() == "not JSON"


def check_script_fixture(tmp_path):
    project = tmp_path / "project"
    (project / "scripts").mkdir(parents=True)
    (project / "frontend" / "node_modules").mkdir(parents=True)
    (project / ".venv" / "bin").mkdir(parents=True)
    (project / ".venv" / "bin" / "python").touch(mode=0o755)
    source = Path(__file__).resolve().parents[1] / "scripts" / "check_software.sh"
    shutil.copyfile(source, project / "scripts" / "check_software.sh")
    bins = tmp_path / "bin"
    bins.mkdir()
    for name in ("uv", "node", "npm"):
        executable = bins / name
        executable.write_text(
            "#!/bin/bash\n"
            'echo "${0##*/} $*" >> "$CHECK_LOG"\n'
            'if [[ "${0##*/}" == uv ]]; then\n'
            '  [[ "$DESK_TEXT_PROVIDER" == none && "$DESK_VOICE_PROVIDER" == none ]] '
            "|| exit 13\n"
            '  [[ -z "${DESK_TEXT_API_KEY:-}" ]] || exit 14\n'
            '  [[ -n "$DESK_RUNTIME_DIR" && -d "$DESK_RUNTIME_DIR" ]] || exit 15\n'
            '  echo "$DESK_RUNTIME_DIR" > "$RUNTIME_LOG"\n'
            '  if [[ "$*" == *"ruff check"* && "${FAIL_RUFF:-0}" == 1 ]]; then exit 9; fi\n'
            "fi\n"
        )
        executable.chmod(0o755)
    env = {
        **os.environ,
        "PATH": str(bins) + os.pathsep + os.environ["PATH"],
        "CHECK_LOG": str(tmp_path / "commands.log"),
        "RUNTIME_LOG": str(tmp_path / "runtime.txt"),
        "DESK_TEXT_PROVIDER": "gemini",
        "DESK_TEXT_API_KEY": "fictional-unit-test-value",
    }
    return project / "scripts" / "check_software.sh", env


def test_check_script_uses_frozen_offline_dependencies_and_isolated_runtime(tmp_path):
    script, env = check_script_fixture(tmp_path)
    result = subprocess.run(
        ["bash", str(script), "--install", "--offline", "--skip-assets"],
        env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    commands = Path(env["CHECK_LOG"]).read_text()
    assert "uv sync --frozen --offline" in commands
    assert "npm ci --ignore-scripts --no-audit --no-fund --offline" in commands
    assert "uv run --no-sync pytest -q" in commands
    assert "npm test" in commands and "npm run build" in commands
    assert "PARTIAL CHECKOUT" in result.stdout
    assert not Path(Path(env["RUNTIME_LOG"]).read_text().strip()).exists()


def test_check_script_stops_on_failure_and_cleans_only_its_runtime(tmp_path):
    script, env = check_script_fixture(tmp_path)
    result = subprocess.run(
        ["bash", str(script), "--skip-assets"], env={**env, "FAIL_RUFF": "1"},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 9
    commands = Path(env["CHECK_LOG"]).read_text()
    assert "pytest" not in commands and "npm test" not in commands
    assert not Path(Path(env["RUNTIME_LOG"]).read_text().strip()).exists()
    assert script.exists()


def test_check_script_rejects_unknown_option_before_running_tools(tmp_path):
    script, env = check_script_fixture(tmp_path)
    result = subprocess.run(
        ["bash", str(script), "--unexpected"], env=env,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert not Path(env["CHECK_LOG"]).exists()
