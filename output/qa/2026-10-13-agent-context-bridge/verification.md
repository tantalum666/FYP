# Personal-context bridge focused verification

Date: 13 October 2026. Local shared implementation workspace; inherited source checkpoint `91e6ed9` / parent-reported head `908b567`. No commit, push, live provider call, real browser launch, account change, hardware operation or runtime-data migration was performed by this workstream.

## Implemented files

- `desk-companion/backend/desk/agent_context.py`: strict selection/binding types, owner selection catalog, metadata-only selected record binding and bounded ephemeral projection
- `desk-companion/tests/test_agent_context.py`: 27 direct bridge cases
- `desk-companion/tests/test_agent_personal_context_integration.py`: 17 end-to-end coordinator cases
- `desk-companion/docs/agent-personal-context.md`: selection, consent, retention, limits and integration contract
- This QA record and supplemental reading ledger

No edits to existing `context.py`, `memory.py` or `conversations.py` were needed. Coordinator/schema/planner integration belongs to the separate run-tool workstream. Frontend, runtime/app wiring and root project documents belong to their respective integration owners.

## Commands and outcomes

Executed from `desk-companion` using the pre-existing `.venv`:

- `.venv/bin/ruff format backend/desk/agent_context.py tests/test_agent_context.py tests/test_agent_personal_context_integration.py`
- `.venv/bin/ruff check backend/desk/agent_context.py tests/test_agent_context.py tests/test_agent_personal_context_integration.py`
- `.venv/bin/pytest -q tests/test_agent_context.py`: 27 passed in 6.97 seconds
- `.venv/bin/pytest -q tests/test_agent_personal_context_integration.py`: 17 passed in 5.29 seconds, with the existing FastAPI/Starlette test-client deprecation warning

Combined final focused rerun is recorded in `focused-tests.log`. These are local software/protocol results only. Fixtures authenticate against a temporary SQLite store, inspect actual retained run rows and generated artifact files, and replace model/browser I/O with explicitly scripted fixtures. They do not demonstrate model intelligence or actual StackEdit usage.

## Established checks

- Default no-context path never includes enabled but unselected memory/history
- Exact selected memories and pre-start message watermarks, without unrelated or subsequently appended text
- Original session, run ID, destination and privacy/version/hash checks; owner-shaped dictionaries and expired sessions rejected
- Explicit strict-boolean derived-retention acknowledgement, with no automatic direct private input copy into run observations or cache
- Forget/correction excludes old history, even when its retained transcript remains owner-readable
- Off/on, hide/show, revoke/restore, correction, delete and endpoint changes cannot restore an earlier binding
- Late returned model text is discarded before persistence; a committed-but-not-applied model decision cannot be replayed after invalidation
- Unchanged binding survives pause/restart; invalid binding cannot be refreshed by resume or steering
- Remembered approval text cannot enable a disallowed local proposal
- Previously explicitly retained derived artifacts remain readable, without falsely claiming memory forget erased them
- Personal marker absent from the public-only browser prepare and dispatch payloads

## Integration review follow-through

Two additional coordinator review targets were reported directly to the run owner and root. They were not independently established as regressions by this focused suite: ensure a context change between run authorization and artifact publication cannot publish a stale private result; ensure confirming a pending run-derived business draft validates its personal binding rather than relying only on asynchronous worker cancellation. Root owns the independent integrated review and remaining acceptance.

The broader task continues. This workstream result is not publication evidence or a declaration that the complete personal-agent product is finished.
