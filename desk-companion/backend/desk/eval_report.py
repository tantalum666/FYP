"""One offline pass/fail table for the agent, conversation, and retrieval suites.

This module does not open a socket and does not read DESK_CONVERSATION_EVAL.
The optional live conversation script stays separate and is not called here.
"""

from dataclasses import dataclass

from .agent_eval import run_all as run_agent
from .conversation_eval import run_scripted
from .retrieval_eval import run_all as run_retrieval


SUITES = (
    ("agent", run_agent),
    ("conversation", run_scripted),
    ("retrieval", run_retrieval),
)


@dataclass(frozen=True)
class EvalRow:
    suite: str
    name: str
    passed: bool
    detail: str


def collect(new_runtime) -> list[EvalRow]:
    rows = []
    for suite, runner in SUITES:
        for result in runner(new_runtime):
            rows.append(EvalRow(suite, result.name, result.passed, result.detail))
    return rows


def format_table(rows: list[EvalRow]) -> str:
    lines = [f"{'suite':<14} {'name':<36} result"]
    for row in rows:
        outcome = "pass" if row.passed else "fail " + _one_line(row.detail)
        lines.append(f"{row.suite:<14} {row.name:<36} {outcome}")
    return "\n".join(lines)


def summary(rows: list[EvalRow]) -> str:
    failed = sum(1 for row in rows if not row.passed)
    return f"{len(rows) - failed} passed, {failed} failed"


def _one_line(detail: str) -> str:
    text = " ".join(str(detail or "failed").split())
    if len(text) > 120:
        return text[:117] + "..."
    return text
