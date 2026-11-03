# Merge guide for the Grok offline-journey stack

Completed by Grok Bot via a Cursor cloud agent on 2026-11-03. This is a merge plan, not a merge. Codex merges. Do not merge drafts #73–#77 from this guide. Those stay on Codex's own stack.

The historical #20–#50 rehearsal is [merge-guide.md](merge-guide.md). Do not use that order for this set.

Checked against live GitHub on 2026-11-03, after `git fetch` of the heads below. None of #78, #79, or #80 was merged. Each is an open, non-draft pull request based on main `dac527b386c268caa96d9388d0c11d206b4f6856`, and GitHub reported each `MERGEABLE` / `CLEAN` against that base. A later push moves the tip. Re-run `git merge-tree --write-tree --name-only` before resolving if a tip changed.

| PR | State at check | Branch | Tip |
| --- | --- | --- | --- |
| [#78](https://github.com/tantalum666/FYP/pull/78) | open, not merged | `cursor/integration-acceptance-harness-dcc2` | `765b5fef1e7ad63ae4a595a964fa9467c1804c9e` |
| [#79](https://github.com/tantalum666/FYP/pull/79) | open, not merged | `cursor/mailbox-offline-journey-9739` | `5e1e72211ed528af71539285a0c54f255b190686` |
| [#80](https://github.com/tantalum666/FYP/pull/80) | open, not merged | `cursor/shopping-fixture-journey-0767` | `4a04770b0fdfd5589d58cdc41efba55afe175c2a` |

No calendar offline-journey pull request or remote branch was open at this check (`gh pr list --state open`, `git ls-remote --heads origin`). Do not invent a number for it. The placeholder is at the end.

This guide's own pull request only adds the guide, a pointer on the historical guide, a short handoff note, a short work-log note, and a QA record. It conflicts with #78, #79, and #80 on `handoff.md` and `work-log.md` because each appends those files. Keep every section. Merge this guide whenever; it does not change the code conflicts below.

## Order

Merge into `main`, top to bottom. Each step was simulated with `git merge-tree --write-tree --name-only` from the previous tip, parent before child. Both sides still branch from the same main, so the pairwise result is the merge after the earlier PR is in `main`.

1. [#78](https://github.com/tantalum666/FYP/pull/78) harness first. Tests and a checklist. No production redesign.
2. [#79](https://github.com/tantalum666/FYP/pull/79) mailbox, including the quiet-hour hold and portable backup cursors already on tip `5e1e722`.
3. [#80](https://github.com/tantalum666/FYP/pull/80) shopping fixtures.
4. Calendar offline journey when a real pull request exists. Until then, do not block 1–3.

#78 does not depend on #79 or #80. Merging #79 or #80 before #78 is code-clean against main, but #78's handoff still says the mailbox journey is the next step. Put #78 first so that sentence is overwritten by #79's real-account next step instead of being restored afterwards.

Leave #73–#77 unmerged here. Conflict files if someone later rebases them are listed only so a rebase does not drop either side.

## Log files

`handoff.md`, `work-log.md`, and `decision-log.md` conflict because each pull request appends at the same end. Keep every `##` section. Do not drop a section because another branch's "remaining" line still describes that work as future.

After steps 1–3 the work log must contain all three:

- `## 2026-11-03 · Integration acceptance harness`
- `## 2026-11-03 · Offline mailbox journey` and its `### Same day: quiet-hour delivery and portable mailbox backup`
- `## 2026-11-03 · Offline shopping fixtures`

The decision log must contain all three 2026-11-03 sections from #79 and #80. #79's first section still says mailbox rows are not in the portable JSON backup. The same-day follow-up on tip `5e1e722` supersedes that sentence: `mailbox_bundle` is in the backup. Keep the follow-up. Do not treat the earlier sentence as the tip contract. #80's shopping section says that slice did not edit the mailbox. That is scope for #80, not a reason to delete the mailbox sections.

## Codex review constraints still in force

These are the 28 October integration lessons. #78 locks them. #79 and #80 must not weaken them, and the calendar slice must not either. Source: [integration QA](../output/qa/2026-10-28-grok-review-merge/verification.md), [software-maintenance invariants](../desk-companion/docs/software-maintenance.md), and #78's [integration-acceptance.md](https://github.com/tantalum666/FYP/blob/cursor/integration-acceptance-harness-dcc2/desk-companion/docs/integration-acceptance.md) (that file is not on main until #78 merges).

- Login and task isolation. A tool cache or another login must not revive a deleted fact or replay another login's transcript.
- Owner permission on the final operation. A paired device cannot apply a backup, confirm a goal, confirm a `mailbox_reply`, or confirm a `shopping_advice`. Replay of the owner's operation id does not transfer that authority.
- Backup validation. Incomplete job rows and a rebound folder fingerprint are rejected. A good restore is visible on `GET /api/computer/jobs`. #79 adds the same rule for `mailbox_bundle`: preview validates before import, and restore does not rewrite an existing cursor. #80 does not put shopping cursor tables in the portable JSON backup.
- Field not provided. Omitted calendar notes, location, and reminders survive `execute_tool` and the HTTP confirm. #79 leaves omitted task notes, waiting reasons, and deadlines as saved. #80's confirm overlays only `provided_fields` (`status`, `waiting_for`, `next_step`, `title`); an omitted `next_step` stays.
- Stream interrupt is not success. Closing the assistant stream early does not complete it. Recovery is SSE, and the real client retries that path once. #79's mailbox interrupt leaves the attempt row and does not advance the history cursor. #80's `disconnect_after` leaves `completed` false and does not delete operation receipts.
- macOS names. Case-insensitive helper and component paths must stay distinct, including a missing `.ts` / `.tsx` suffix. #80 fixture ids are lowercase so two names cannot collide on a case-insensitive disk. Keep that if the calendar slice adds fixture files.
- Real-path tests. Assert through HTTP list, restore, `execute_tool`, and confirm. Do not prove the lesson by writing SQL or calling a private helper.

## 1. #78 integration-acceptance harness

Independent of the journeys. Eight files, all additions except two-line appends to `handoff.md` and `work-log.md`. No mailbox, shopping, Pi, Alice wake, desktop chat, or Work UI source.

What it adds: `desk-companion/tests/test_integration_acceptance.py` (seven tests) and Node fixtures that load the real `frontend/src/api.ts` recovery path. The checklist is `desk-companion/docs/integration-acceptance.md`.

Verify from `desk-companion/`, after `uv sync --frozen` (CPython 3.12.3). These are the commands in the pull request body:

```sh
uv run --no-sync ruff check tests/test_integration_acceptance.py tests/fixtures
uv run --no-sync pytest tests/test_integration_acceptance.py -q
```

Recorded result on that branch: Ruff clean, pytest **7 passed** in 4.09s, plus the existing Starlette/httpx test-client deprecation. The checklist doc's ruff line omits `tests/fixtures`. Run the pull request body's line.

Known gaps, from the pull request body:

- The full backend and frontend suites from the PR5 closeout were not re-run.
- No macOS bundle. Path collisions are caught by the source scan.
- Task updates that omit fields and replace the whole row were left alone. The reviewed failure was the calendar tool path.
- The client recovery check runs under pytest with Node's TypeScript transform. It is not in `npm test`, which uses `--experimental-strip-types` and cannot load `frontend/src/api.ts`.

Against #79: code is disjoint. `git merge-tree` of #79 onto #78 conflicted only in `work-log.md`. `handoff.md` auto-merged. After that auto-merge, keep #78's evidence paragraph and replace its stale sentence "This does not change the mailbox gate below." The section below is #79's offline mailbox slice, and the one next step is #79's real-account sentence, not main's "implement the mailbox journey".

Against #80: code is disjoint. Merge-tree conflicted only in `work-log.md`. `handoff.md` auto-merged and already keeps the harness paragraph, main's mailbox next step, and #80's shopping section. That handoff is right only if #79 has not landed yet. After #79 lands, use the #79/#80 handoff resolution below.

Against #73–#77: merge-tree conflicted only in `handoff.md` and `work-log.md`. Keep Codex's status paragraphs and #78's one evidence sentence. Do not merge those drafts from this guide.

## 2. #79 mailbox offline journey

Tip `5e1e722` includes the quiet-hour hold and the portable backup cursors. The earlier commit on the same branch did not. Review the tip, not the first commit message.

What it adds:

- Local `desk-mailbox-fixture-v1` files under `desk-companion/fixtures/mailbox/` for duplicates, out-of-order arrivals, interrupt/restart, revoke, and disconnect. The loader rejects a changed duplicate and path traversal before any row is written.
- `MailboxService` stores the connection, thread link, message fingerprint, and sync attempt in the same SQLite database, using `BEGIN IMMEDIATE` and an owner-session recheck. One sync reads one batch. The history cursor advances only when that batch finishes. An applied operation id replays the stored response. An interrupt leaves the attempt row and does not advance the cursor. Revoke and disconnect stop before later messages are read and are not success.
- One mail thread maps to one existing task. Omitted fields stay as saved, including owner notes, waiting reasons, and deadlines.
- `mailbox_reply` drafts cite the mail id and `observed_at`. Confirm and cancel use the existing proposal routes. Confirm writes a task note and sets `sent` to false. The kind is outside `SOFTWARE_PROPOSALS`, so full access does not auto-apply it.
- A meaningful notice during quiet hours is stored in `mailbox_notice_holds`. `Runtime.tick` publishes it through `Notifier` after quiet hours end. The hold stays until that publish is delivered or recognized as a duplicate.
- Portable JSON backup includes `mailbox_bundle`: connection cursor, read offset, thread-to-task link, message fingerprints, sync attempts, and quiet holds. Preview validates those records before import. Restore inserts a missing connection and does not rewrite an existing cursor. Snippets are not exported. A backup with no `mailbox_bundle` key still restores the older business data.

Verify from `desk-companion/`. The pull request body used `PYTHONPATH=/tmp/desk-py` for test dependencies that are not committed:

```sh
python3 -m pytest tests/test_mailbox_journey.py -q --tb=short
python3 -m pytest tests/test_exchange.py tests/test_backup_persona_jobs.py tests/test_memory_gaps.py tests/test_risk_gaps.py tests/test_tasks.py tests/test_integration_boundaries.py tests/test_notify.py tests/test_nudges.py -q --tb=line
python3 -m ruff check backend/desk/mailbox.py backend/desk/mailbox_fixture.py backend/desk/assistant.py backend/desk/assistant_routes.py backend/desk/runtime.py backend/desk/app.py backend/desk/exchange.py tests/test_mailbox_journey.py
```

Recorded result on that branch: mailbox file **9 passed** (5.30s); the eight adjacent files **64 passed** (15.58s); ruff clean on those paths. An earlier full backend run, after the same wheels were installed where `python -I` can import them, was **1693 passed, 1 failed**. The failure is pre-existing `tests/test_public_capture_transport.py::test_public_unicast[::ffff:93.184.216.34]`. On that interpreter `IPv6Address("::ffff:93.184.216.34").is_reserved` is true. That file was not edited. The quiet-hour and backup follow-up did not rerun the full suite. Do not treat 1693 as a result of the final tip.

Known gaps, from the pull request body:

- Not a real mailbox acceptance. No Gmail/Outlook, send, live push, or paid model.
- Confirm uses the existing task note action, which clears `check_in_local`. Due, waiting reason, next step, and evidence notes stay.
- Reconnect after revoke or disconnect is out of scope.
- Mailbox tables are created at runtime with `CREATE TABLE IF NOT EXISTS`. Schema version stays 3. Stores that only open `Store` and never construct `Runtime` do not create them. `mailbox_notice_holds` is one of those tables.

The quiet-hour retry gap and the portable mailbox backup gap are closed on this tip.

Rebase onto main if main moves, then onto #78. Code against #78 does not conflict. Resolve `work-log.md` by keeping both 2026-11-03 sections.

## 3. #80 shopping offline journey

Second acceptance journey. Offline cart, price, stock, and shipment fixtures land on the existing task, one paused Work run, notices, and drafts. No store account, no paid API, no checkout. Shopping files under `desk-companion/backend/desk/shopping/` do not overlap mailbox modules.

What it adds:

- One UTF-8 JSON fixture (`cart_change`, `price_drop`, `out_of_stock`, `order_shipped`, `order_delayed`) with a durable integer cursor. Sync is incremental and idempotent. One product or order subject keeps one task and one paused Work run.
- Advice is a `shopping_advice` draft that cites the fixture id and observation time. Confirm and cancel go through `POST /api/assistant/proposals/{id}/decisions`. The kind is outside `SOFTWARE_PROPOSALS`.
- Notices fire only for a threshold price drop, a shipment or delay change, or a decision. Unchanged carts, under-threshold drops, duplicates, and a second sync stay silent.
- Revoke returns before the fixture file is parsed. `disconnect_after` leaves `completed` false.

Verify from `desk-companion/`, after `uv sync --frozen --group dev` (CPython 3.12.3). These are the commands in the pull request body:

```sh
uv run --no-sync ruff check backend/desk/shopping backend/desk/assistant.py backend/desk/assistant_routes.py backend/desk/app.py backend/desk/runtime.py tests/test_shopping_fixtures.py
uv run --no-sync pytest tests/test_shopping_fixtures.py tests/test_permissions.py -q
```

Recorded result on that branch: Ruff clean, pytest **28 passed** in 12.03s (6 shopping HTTP tests plus 22 existing permission decisions). Shopping file alone: 6 passed in 3.90s. `desk-companion/docs/shopping-fixtures.md` has a shorter ruff line that omits `assistant.py`, `assistant_routes.py`, `app.py`, and `runtime.py`. Run the pull request body's line. After #79 is in the tree, also rerun #79's mailbox commands and #78's harness. Those shared files are why. This guide did not run that combined suite.

Known gaps, from the pull request body:

- No real merchant, inventory, shipping quote, address, payment, or order receipt. A fixture is not a purchase.
- Sync interruption is `disconnect_after` on the JSON body. It uses the same commit boundary as a dropped client. It is not a cancelled socket in the middle of a byte. Operation receipts are not cleared early. `completed` stays false.
- Portable JSON backup was not changed and does not include the shopping cursor tables. Whole-file SQLite copies do. Tasks created here are ordinary tasks, so they are in the existing task export.
- Full backend and frontend suites from the PR5 closeout were not re-run.
- `POST /api/shopping/checkout` is not a route. The SPA GET catch-all answers 405. The test asserts 405 and that the body does not report a performed checkout.

New tables (`shopping_connections`, `shopping_subjects`, `shopping_applied`, `shopping_buffer`) are created inside `ShoppingService` with `CREATE TABLE IF NOT EXISTS`. Schema version is not bumped. The Work run is created and paused in the same sync so the scheduler does not compose a purchase report.

### #80 against #78

Merge-tree conflicted only in `work-log.md`. `handoff.md` auto-merged. Keep both work-log sections. No shopping file overlaps the harness.

### #80 against #79

Merge-tree of either order conflicted in:

- `desk-companion/backend/desk/assistant_routes.py`
- `decision-log.md`
- `handoff.md`
- `product.md`
- `research/personal-agent-research-index.md`
- `work-log.md`

These auto-merged, and the merged tree already contains both sides. If a later tip conflicts, put both back. Do not keep one side:

- `desk-companion/backend/desk/app.py`. Both imports and both `include_router` calls. `shopping_routes(...)` stays with the Work routers. `mailbox_routes(...)` stays after `google_routes(...)`. Both must be registered before the `/{path:path}` catch-all.
- `desk-companion/backend/desk/runtime.py`. Construct both `self.shopping = ShoppingService(self)` and `self.mailbox = MailboxService(self)`. Keep `self.mailbox.release_quiet_notices()` inside `Runtime.tick`. #80 adds no tick line.
- `desk-companion/backend/desk/assistant.py`. Keep both decide paths. They are not the same shape. #80 runs before the kind chain and then falls through as `task_change`. #79 is an `elif` on the original kind. Also keep #79's `propose(..., ttl=)` signature. #80 does not edit it.
- `desk-companion/docs/modules.md`. Keep the mailbox table row and the 3 November shopping paragraph.

`app.py` at the simulated merge already has:

```python
from .mailbox import mailbox_routes
from .shopping.routes import shopping_routes
```

```python
    app.include_router(shopping_routes(services, owner, operation_id))
    app.include_router(voice_routes(services, authenticated, agent, allowed_origins, limit))
    app.include_router(exchange_routes(services, authenticated, owner, operation_id))
    app.include_router(google_routes(services, owner, operation_id))
    app.include_router(mailbox_routes(services, owner, operation_id))
```

`assistant.py` at the simulated merge already has both decide branches. Keep this shopping prelude, then the existing `apply_kind == "task_create"` / `"task_change"` / memory chain:

```python
            apply_kind = row["kind"]
            if apply_kind == "shopping_advice":
                from .shopping.service import prepare_shopping_confirmation

                payload = prepare_shopping_confirmation(self.runtime, payload)
                with self.store.connection(write=True) as conn:
                    fresh = conn.execute(
                        "SELECT state FROM assistant_proposals WHERE id=?", (proposal_id,)
                    ).fetchone()
                    if fresh and fresh["state"] == "pending":
                        conn.execute(
                            "UPDATE assistant_proposals SET data=? WHERE id=?",
                            (encode(payload), proposal_id),
                        )
                apply_kind = "task_change"
```

After `memory_delete`, keep the mailbox branch on `row["kind"]`, not on `apply_kind`. Shopping rewrites `apply_kind` to `task_change`. A check on `apply_kind` would either miss `mailbox_reply` or let a shopping draft enter the mailbox branch.

```python
            elif row["kind"] == "mailbox_reply":
                if payload.get("send") is not False:
                    raise DomainError("MAILBOX_SEND_FORBIDDEN", 409)
                for field in ("task_id", "mail_id", "observed_at"):
                    if not isinstance(payload.get(field), str) or not payload[field]:
                        raise DomainError("MAILBOX_DRAFT_INVALID", 422)
                with self.store.connection() as conn:
                    current = self.runtime.tasks.get(conn, payload["task_id"])
                note = (
                    f"Reviewed mailbox advice for {payload['mail_id']} "
                    f"observed at {payload['observed_at']}. Nothing was sent."
                )
                result = self.runtime.tasks.action(
                    payload["task_id"],
                    TaskAction(action="note", expected_version=current["version"], note=note),
                    internal_key,
                    origin="assistant_confirmed",
                )
                result = {
                    **result,
                    "sent": False,
                    "mail_id": payload["mail_id"],
                    "observed_at": payload["observed_at"],
                }
```

`assistant_routes.py` does not auto-merge. Keep both guards. Import `proposal_kind` and `visible_proposals` from `.mailbox`.

```python
        proposals = visible_proposals(
            runtime.assistant.proposals(allow_memory=principal["kind"] == "owner"), principal
        )
        proposals = runtime.agent_runs.filter_proposals(proposals, principal)
        if principal["kind"] != "owner" or not runtime.store.session_valid(principal.get("session")):
            proposals = [item for item in proposals if item.get("kind") != "shopping_advice"]
        return {"proposals": proposals}
```

```python
        if proposal_kind(runtime, proposal_id) == "mailbox_reply" and principal["kind"] != "owner":
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        if runtime.shopping.is_proposal(proposal_id):
            signed_in = principal["kind"] == "owner" and runtime.store.session_valid(
                principal.get("session")
            )
            if not signed_in:
                raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
```

Shopping's session check is stricter than mailbox's kind check. Do not weaken it to kind-only.

`product.md` is one bullet, edited by both. Keep both facts in that bullet: the offline mailbox sample is not a Gmail/Outlook acceptance, and the offline shopping fixtures can write a task, a paused Work run, and a notice without a store, payment, or checkout. Link both [the research index](../research/personal-agent-research-index.md) and [shopping-fixtures.md](https://github.com/tantalum666/FYP/blob/cursor/shopping-fixture-journey-0767/desk-companion/docs/shopping-fixtures.md). That shopping contract is on #80, not on main, until #80 merges.

`research/personal-agent-research-index.md` is the gap table. Keep #79's two mail rows (offline cursor and thread mapping exist; real Gmail/Outlook does not) and #80's tissue row (offline fixture maps one subject to one task and one paused Work run; it is not an order). Do not restore #80's older mail rows, which were written before #79.

`handoff.md`: keep #78's harness paragraph, #79's "Offline mailbox slice" section, and #80's "Offline shopping fixtures" section. The one next step becomes #79's real-account sentence. Delete #79's "Do not start shopping" clause once #80's section is in the same file. Shopping fixtures are that section. They are not a purchase. Do not start travel booking or a paid model round. Do not restore main's "implement the mailbox journey" as the next step.

`decision-log.md` and `work-log.md`: keep every 2026-11-03 section, including #79's quiet-hour and backup follow-up.

### #80 against #73–#77

Do not merge those drafts from this guide. If a later rebase hits them, merge-tree at these tips said:

| Draft | Tip | Conflict with #80 | Auto-merged wiring |
| --- | --- | --- | --- |
| #73 `codex/pi-home-resume-20261031` | `3150f3912b1719036cc5a043c8e98f8cee5931ce` | `decision-log.md`, `handoff.md`, `product.md`, `work-log.md` | no shared Python |
| #74 `codex/personal-agent-cross-app-20261031` | `89f215ec8af5f841072337cc9a17217d82a85e56` | `decision-log.md`, `handoff.md`, `work-log.md` | `runtime.py`, `product.md`, research index |
| #75 `codex/ui-copy-cleanup-20261031` | `34de1e790f7f0ba7b529523f6286034868dee0cc` | same as #74 | same as #74 |
| #76 `codex/conversation-desktop-20261102` | `17df07498ae67b4d9d1c50a8d00ca8af9e2dc9d4` | same as #74 | same as #74 |
| #77 `codex/openai-alice-wake-20261102` | `0d73f1cf6bd28f981793b4610425df58db7a6e48` | `decision-log.md`, `handoff.md`, `product.md`, `work-log.md` | `app.py`, `assistant.py`, `runtime.py`, research index |

#73 is a sibling of #74, not its parent. #75–#77 stack on #74's branch. #79 against this same stack also conflicts in `desk-companion/docs/pr5-integration.md` and the research index. #80 does not edit `pr5-integration.md`. For `product.md` against #73 and #77, keep Codex's Pi and OpenAI paragraphs and keep #80's shopping sentence in the personal-agent bullet.

## 4. Calendar offline journey

Not opened yet. Checked 2026-11-03: no open pull request and no remote head whose name is a calendar offline journey. When it opens, add its real number, branch, and tip here before merging it. Do not block #78, #79, or #80 on it.

Intended place: after #80, as its own package, the same way shopping stayed out of `mailbox.py`. If it lands first and does not touch shopping or mailbox modules, it can merge before them. Rebase whichever lands second.

Hotspots to expect, not observed:

- The same shared wiring #79 and #80 already share: `app.py` (`google_routes` is already included; add the new router, and do not drop `shopping_routes` or `mailbox_routes`), `assistant.py` (another decide branch beside `shopping_advice` and `mailbox_reply`), `assistant_routes.py` (another list filter and owner check), `runtime.py` (another service next to `self.shopping` and `self.mailbox`).
- Append-only `handoff.md`, `work-log.md`, `decision-log.md`, plus the personal-agent bullet in `product.md` and the gap table in `research/personal-agent-research-index.md`.
- `desk-companion/docs/modules.md`.
- Backup code only if that slice adds a bundle. #79's `mailbox_bundle` and #80's decision not to export shopping cursors must both survive.
- The harness test `test_shared_tool_validation_preserves_omitted_schedule_fields`. Omitted calendar notes, location, and reminders must still survive `execute_tool` and HTTP confirm. Use that path, not a private helper. Keep the macOS case-collision scan green if new files are added.

## After the last journey merge

Search the tree for `<<<<<<<`. There should be none.

From `desk-companion/`, run the three command blocks in this file: #78's ruff and pytest, #79's pytest and ruff, and #80's ruff and pytest. Do not set a paid provider. Do not start GitHub Actions. A failure in the pre-existing IPv6-mapped unicast test is the known interpreter gap named under #79, and only if that test was not edited.

This guide did not execute those suites. The pass counts above are the counts written on each pull request, not a combined rehearsal.
