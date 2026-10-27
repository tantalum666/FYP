"""What a hosted model may see for one turn. Secrets and deleted facts stay out."""

from datetime import timedelta

from .calendar import iso
from .workspace_data import owner_style


def pack_conversation(runtime, task_id=None, *, include_memory=True):
    now = runtime.store.clock()
    tasks = runtime.tasks.listing(include_closed=bool(task_id))
    selected = runtime.tasks.detail(task_id) if task_id else None
    window = runtime.store.snapshot(now, now + timedelta(days=7))
    return {
        "now": iso(now),
        "timezone": tasks["timezone"],
        "memory": runtime.memory.for_model() if include_memory else [],
        "profile": runtime.profile.text() if include_memory else "",
        "tasks": tasks["tasks"][:30],
        "more_tasks": len(tasks["tasks"]) > 30,
        "selected_task": selected,
        "calendar": window["occurrences"][:80],
        "style": owner_style(runtime.data.preferences()),
    }
