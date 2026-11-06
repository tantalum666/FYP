"""Replay the observed empty-file/already-run failure without touching real disks."""

import json
from pathlib import Path
import subprocess

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "pi"


@pytest.fixture
def bootstrap(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import network_bootstrap as module

    monkeypatch.setattr(module.os, "sync", lambda: None)
    return module


@pytest.fixture
def plan(bootstrap, tmp_path):
    import prepare_network_sd as prepare

    boot = tmp_path / "boot"
    boot.mkdir()
    user, meta = prepare.render("Fixture", "fixture-only", "192.168.0.7", "a" * 32)
    (boot / "user-data").write_text(user)
    (boot / "meta-data").write_text(meta)
    return bootstrap.read_plan(boot)


def test_empty_managed_files_and_old_semaphores_are_repaired_before_setup(
    bootstrap, plan, tmp_path
):
    root = tmp_path / "root"
    for row in plan["entries"]:
        path = root / row["path"].lstrip("/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    instances = tmp_path / "instances"
    instance = instances / ("desk-portable-network-" + plan["trial_id"])
    sem = instance / "sem"
    sem.mkdir(parents=True)
    for name in [
        "config_runcmd",
        "config_scripts_user",
        "config_ssh",
        "config_users_groups",
        "config_write_files",
    ]:
        (sem / name).touch()
    current = tmp_path / "instance"
    current.symlink_to(instance, target_is_directory=True)
    state = tmp_path / "complete.json"
    reports = []
    bootstrap.recover(
        plan,
        "boot",
        root=root,
        state=state,
        report=lambda *a, **kw: reports.append(a[1]),
        retry=lambda p: bootstrap.retry_this_instance(p, current, instances),
    )
    assert not (sem / "config_runcmd").exists() and not (sem / "config_scripts_user").exists()
    assert all(
        (sem / n).exists() for n in ["config_ssh", "config_users_groups", "config_write_files"]
    )
    assert not state.exists()
    calls = []

    def execute(command):
        assert all(
            (root / row["path"].lstrip("/")).read_text() == row["content"]
            for row in plan["entries"]
        )
        calls.append(command)

    bootstrap.recover(
        plan, "run", root=root, state=state, runner=execute, report=lambda *a, **kw: None
    )
    assert calls == plan["commands"] and bootstrap.completed(plan, state)


def test_failed_setup_never_marks_complete_and_next_boot_retries(bootstrap, plan, tmp_path):
    root = tmp_path / "root"
    state = tmp_path / "complete"

    def failed(command):
        raise subprocess.CalledProcessError(1, command)

    with pytest.raises(subprocess.CalledProcessError):
        bootstrap.recover(
            plan, "run", root=root, state=state, runner=failed, report=lambda *a, **k: None
        )
    assert not state.exists()
    retried = []
    bootstrap.recover(
        plan,
        "boot",
        root=root,
        state=state,
        report=lambda *a, **k: None,
        retry=lambda p: retried.append(True),
    )
    assert retried == [True]


def test_interrupted_write_preserves_previous_file_and_never_runs_setup(
    bootstrap, plan, tmp_path, monkeypatch
):
    root = tmp_path / "root"
    state = tmp_path / "complete"
    first = plan["entries"][0]
    target = root / first["path"].lstrip("/")
    target.parent.mkdir(parents=True)
    target.write_text("previous intact")

    def fail_sync(fd):
        raise OSError("fixture interrupted flush")

    monkeypatch.setattr(bootstrap.os, "fsync", fail_sync)
    executed = []
    with pytest.raises(OSError):
        bootstrap.recover(
            plan,
            "run",
            root=root,
            state=state,
            runner=lambda c: executed.append(c),
            report=lambda *a, **k: None,
        )
    assert target.read_text() == "previous intact" and not state.exists() and not executed


def test_completed_seed_does_not_overwrite_later_software_changes(bootstrap, plan, tmp_path):
    root = tmp_path / "root"
    state = tmp_path / "complete"
    bootstrap.recover(
        plan, "run", root=root, state=state, runner=lambda c: None, report=lambda *a, **k: None
    )
    target = root / plan["entries"][0]["path"].lstrip("/")
    target.write_text("later legitimate update")
    bootstrap.recover(
        plan,
        "boot",
        root=root,
        state=state,
        retry=lambda p: pytest.fail("must not reset completed seed"),
    )
    assert target.read_text() == "later legitimate update"


def test_wrong_instance_and_symlinks_never_reset_other_modules(bootstrap, plan, tmp_path):
    instances = tmp_path / "instances"
    other = instances / "another-instance"
    other.mkdir(parents=True)
    current = tmp_path / "instance"
    current.symlink_to(other, target_is_directory=True)
    with pytest.raises(ValueError):
        bootstrap.retry_this_instance(plan, current, instances)
    root = tmp_path / "root"
    target = root / plan["entries"][0]["path"].lstrip("/")
    target.parent.mkdir(parents=True)
    unrelated = tmp_path / "unrelated"
    unrelated.write_text("keep")
    target.symlink_to(unrelated)
    with pytest.raises(ValueError):
        bootstrap.restore_files(plan, root)
    assert unrelated.read_text() == "keep"


@pytest.mark.parametrize("corruption", ["empty", "unexpected_path", "duplicate", "wrong_instance"])
def test_corrupt_seed_cannot_start_restore(bootstrap, tmp_path, corruption):
    import prepare_network_sd as prepare

    boot = tmp_path / "boot"
    boot.mkdir()
    user, meta = prepare.render("Fixture", "fixture-only", "192.168.0.7", "a" * 32)
    data = json.loads(user.split("\n", 1)[1])
    if corruption == "empty":
        data["write_files"][0]["content"] = ""
    elif corruption == "unexpected_path":
        data["write_files"][0]["path"] = "/etc/shadow"
    elif corruption == "duplicate":
        data["write_files"].append(data["write_files"][0])
    else:
        meta = json.dumps({"instance-id": "different"})
    (boot / "user-data").write_text("#cloud-config\n" + json.dumps(data))
    (boot / "meta-data").write_text(meta)
    with pytest.raises(ValueError):
        bootstrap.read_plan(boot)


def test_empty_python_false_success_is_replaced_with_real_execution(bootstrap, plan, tmp_path):
    import sys

    root = tmp_path / "root"
    state = tmp_path / "complete"
    ran = tmp_path / "setup-actually-ran"
    target = root / bootstrap.NETWORK.lstrip("/")
    target.parent.mkdir(parents=True)
    target.touch()
    # This is why a successful shell exit alone missed the original failure.
    assert subprocess.run([sys.executable, str(target)], check=False).returncode == 0
    assert not ran.exists()
    for row in plan["entries"]:
        if row["path"] == bootstrap.NETWORK:
            row["content"] = (
                "from pathlib import Path\nPath("
                + repr(str(ran))
                + ').write_text("verified execution")\n'
            )

    def execute(command):
        subprocess.run([sys.executable, str(root / command[1].lstrip("/"))], check=True)

    bootstrap.recover(
        plan, "run", root=root, state=state, runner=execute, report=lambda *a, **k: None
    )
    assert ran.read_text() == "verified execution" and bootstrap.completed(plan, state)


@pytest.mark.parametrize("broken_reply", [False, True])
def test_progress_hint_contains_no_credentials_and_cannot_block_local_status(
    bootstrap, plan, tmp_path, monkeypatch, broken_reply
):
    import http.client

    plan = {**plan, "relay_host": "198.51.100.23"}
    output = tmp_path / "status.json"
    monkeypatch.setattr(bootstrap, "STATUS", output)
    requests = []

    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, *args):
            requests.append(args)

        def getresponse(self):
            if broken_reply:
                raise http.client.BadStatusLine("fixture bad response")
            return self

        def close(self):
            pass

    monkeypatch.setattr(bootstrap.http.client, "HTTPConnection", Connection)
    bootstrap.status(plan, "running_setup", component=Path(bootstrap.RELAY).name)
    assert json.loads(output.read_text())["phase"] == "running_setup"
    assert requests == [("GET", "/fyp-recovery/" + plan["trial_id"] + "/running_setup-relay")]
    assert "fixture-only" not in str(requests)


@pytest.mark.parametrize("receipt_kind", ["missing", "stale", "failed", "current"])
def test_zero_exit_without_current_setup_receipt_never_marks_success(
    bootstrap, plan, tmp_path, monkeypatch, receipt_kind
):
    root = tmp_path / "root"
    state = tmp_path / "complete"
    receipt = root / "var/lib/desk-companion/network-status.json"
    receipt.parent.mkdir(parents=True)
    if receipt_kind != "missing":
        receipt.write_text(
            json.dumps(
                {
                    "trial_id": "old" if receipt_kind == "stale" else plan["trial_id"],
                    "phase": "setup_failed" if receipt_kind == "failed" else "network_ready",
                }
            )
        )
    monkeypatch.setattr(bootstrap.subprocess, "run", lambda *args, **kwargs: None)
    if receipt_kind == "current":
        bootstrap.recover(plan, "run", root=root, state=state, report=lambda *a, **k: None)
        assert bootstrap.completed(plan, state)
    else:
        with pytest.raises((OSError, RuntimeError)):
            bootstrap.recover(plan, "run", root=root, state=state, report=lambda *a, **k: None)
        assert not state.exists()
