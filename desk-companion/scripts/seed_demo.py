"""Offline FYP demonstration workspace. Writes only a directory named .demo-runtime.

Does not call a hosted model. Computer notes are enabled for this process so the
seeded review jobs exist; the running server still needs DESK_COMPUTER_ENABLED=1.
Re-run with --refresh immediately before the computer-job minute: review expires
after five minutes, and this script does not extend that product limit.
"""

import argparse
import os
import shutil
import sys
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from desk.calendar import iso  # noqa: E402
from desk.jobs import JobInput  # noqa: E402
from desk.runtime import Runtime  # noqa: E402
from desk.schemas import CreateEvents, EventInput  # noqa: E402
from desk.store import DomainError, Store  # noqa: E402
from desk.tasks import TaskInput  # noqa: E402
from desk.workspace_data import PreferencesUpdate, WorkspacePreferences  # noqa: E402

ZONE = ZoneInfo("Asia/Hong_Kong")


def seed(runtime: Path, *, refresh: bool = False, clock=None) -> Path:
    runtime = runtime.expanduser().resolve()
    if runtime.name != ".demo-runtime":
        raise SystemExit("The demo seed only writes a directory named .demo-runtime.")
    if refresh and runtime.exists():
        shutil.rmtree(runtime)
    os.environ["DESK_COMPUTER_ENABLED"] = "1"
    store = Store(runtime, clock=clock)
    services = Runtime(store)

    def replay(action):
        try:
            return action()
        except DomainError as error:
            if error.code == "OPERATION_ID_CONFLICT":
                raise SystemExit(
                    "This demo directory was seeded with different data. Re-run with --refresh."
                ) from None
            raise

    local_now = store.clock().astimezone(ZONE).replace(second=0, microsecond=0, tzinfo=None)
    soon = local_now + timedelta(minutes=8)
    later = local_now + timedelta(hours=3)
    replay(
        lambda: store.create(
            CreateEvents(
                event=EventInput(
                    title="FYP presentation",
                    start_local=soon,
                    end_local=soon + timedelta(minutes=30),
                    calendar="study",
                    color="lavender",
                    visibility="displayable",
                    reminder_minutes=[10],
                    notes="Ten-minute offline demonstration. Example data, not a measured result.",
                )
            ),
            "demo/event/presentation",
            origin="sample",
        )
    )
    replay(
        lambda: store.create(
            CreateEvents(
                event=EventInput(
                    title="Project discussion",
                    start_local=later,
                    end_local=later + timedelta(minutes=45),
                    calendar="study",
                    color="blue",
                    visibility="displayable",
                    reminder_minutes=[10],
                )
            ),
            "demo/event/discussion",
            origin="sample",
        )
    )
    replay(lambda: services.memory.create("The owner studies at CUHK.", "demo/memory"))
    quiet = WorkspacePreferences(
        quiet_enabled=True,
        quiet_start="00:00",
        quiet_end="23:59",
        reminder_strength="chime",
    )
    current = services.data.preferences()
    if any(current[key] != value for key, value in quiet.model_dump().items()):
        replay(
            lambda: services.data.update(
                PreferencesUpdate(expected_version=current["version"], preferences=quiet),
                "demo/preferences",
            )
        )
    created = replay(
        lambda: services.tasks.create(
            TaskInput(
                title="Prepare the FYP demonstration",
                next_step="Open the demo note",
                visibility="displayable",
            ),
            "demo/task",
        )
    )
    with store.connection(write=True) as conn:
        conn.execute(
            "UPDATE tasks SET next_check_at=? WHERE id=?",
            (iso(store.clock() - timedelta(minutes=1)), created["task"]["id"]),
        )
    services.tasks.tick()
    replay(
        lambda: services.jobs.prepare(
            JobInput(
                action="save_note",
                title="FYP demo note",
                content="Offline demo note. Approve this job, then wait for the independent read-back.",
            ),
            "demo/job/approve",
        )
    )
    replay(
        lambda: services.jobs.prepare(
            JobInput(
                action="save_note",
                title="Scratch note",
                content="Cancel this job before it runs. Cancellation does not delete a file that was never written.",
            ),
            "demo/job/cancel",
        )
    )
    return runtime


def main():
    parser = argparse.ArgumentParser(description="Seed the offline Desk Companion demonstration.")
    parser.add_argument(
        "--runtime",
        default=str(Path(__file__).resolve().parents[1] / ".demo-runtime"),
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Replace the .demo-runtime directory so review jobs are new.",
    )
    args = parser.parse_args()
    runtime = seed(Path(args.runtime), refresh=args.refresh)
    print(f"Demo workspace: {runtime}")
    print(f"Sign in as owner. Password file: {runtime / 'credentials.json'}")
    print("Start the server with DESK_RUNTIME_DIR set to that directory,")
    print("DESK_TEXT_PROVIDER=fake, and DESK_COMPUTER_ENABLED=1.")
    print("Do not set DESK_TEXT_API_KEY. Review jobs expire five minutes after this seed.")


if __name__ == "__main__":
    main()
