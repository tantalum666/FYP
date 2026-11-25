# One reminder after a followed thread receives a reply

25 November 2026. Grok Bot. Source baseline `main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` (PR #157). Pull request #160 stays on `cursor/followed-reply-reminder-e853`. Pull requests #158 and #159 were not checked out, stacked, merged, or edited.

## What was read (closeout)

- `AGENTS.md`, `product.md`, `handoff.md`, recent `decision-log.md` / `work-log.md`.
- Prior slice verification on this path and the failing suite list from the previous head.
- Product contracts for each failure: `TextAssistant._fingerprint`, flight reprice clarify, managed-browser create allowlist vs challenge origin, voice forget `home_archived`, `AssistantPanel` home transcript/caption imports, `api.requestDeadline` paths, Today/`MomentCard` mount.
- Narrow remote diffs from #158/#159 used only as hypotheses for baseline expectation/fixture shape. Their feature commits were not cherry-picked.

## Implemented (unchanged product journey)

On a thread the owner has chosen to follow, one new incoming reply raises one reminder on that same task. Chat and the task show it. Inbox can open the task. Quiet hours hold publication until they end. The owner can reread the original message. That text is not stored as a memory, in task evidence, or in the read receipt. Draft a reply appears only after the owner asks. Saving the draft does not send. Check again does not send, including when an earlier send is unknown. Dismissing one reminder leaves another. A failed read is not a confirmed new reply. A message from another thread is refused.

The owner can complete this on Work & tools with the local mail sample. The sample is labeled “Not a live mailbox.” A synthetic Gmail provider uses the same reminder and returns a snippet only for an explicit read. Neither is live-mailbox acceptance. Models stay GPT-6.2 Sol, GPT-Live 1.1, and A3 v9.

## Closeout: previous suite failures

Previous reported gate on notes head `c31149e98688e120aedde6e5a5bf4f6f4acf8737` (product parent `3b2881a38a1355e53e600e4ce98f65df61d2e890`): backend **3059 passed / 9 failed / 1 skipped**; frontend **438 passed / 2 failed**. “Baseline also fails” was not acceptance. Each failure was rechecked against product on this tip:

| Failure | Root cause | Fix on #160 |
|---|---|---|
| `test_office_container_check_and_legacy_fingerprint` ×3 | Product omits absent review-screen fields from the fingerprint; the test rebuilt a dump that still carried those empty keys | Behavioral fingerprint asserts (same/different payload and `allow_memory`) |
| `test_quote_approval_reprice_and_terminal_readback` ×2 | Stale agreement against the old quoted fare returns `acted:false` / `kind:clarify` with no `flight_booking`; booking stays `reprice` on status | Expect clarify + status `reprice` |
| `test_unadmitted_origin_and_auth_are_never_auto_approved` ×2 | Fixture asserted create `allowed_domains` from the mutated challenge `origin`, so create raised `AssertionError` → job `unknown` instead of product deny → `failed` | Split `session_origin` (create allowlist) from challenge `origin` |
| `test_forget_context_route_requires_owner_session` | Forget returns `{cleared, home_archived}`; exact equality to `{cleared:true}` failed | Assert both fields; `home_archived is False` |
| `test_ordinary_composer_over_local_http` | Composer fixture missing `useHomeTranscript` / `HomeCaption` mocks under Node 22 | Add those mocks; keep ownership/privacy asserts |
| `browser-workflow` timeout regex | Source-string regex did not match the real multi-condition deadline | Export `requestDeadline` (same path rules) and assert deadlines behaviorally |
| `moments.test` MomentCard in App | Workspace redesign mounts `<MomentCard>` under `TodayView`, not `App` | Assert Today mount once; keep card copy checks |

No ownership, privacy, revocation, current-permission, idempotence, unknown-effect, or draft/send approval expectations were weakened. No failures were skipped. No #158/#159 feature code was merged.

### Codex conflict note (duplicate baseline fixes)

#158 (`c2cac2d8…`) and #159 (`90275bf0…`) independently contain overlapping baseline test/fixture adjustments (fingerprint, reprice clarify, managed-browser `session_origin`, forget `home_archived`, Google composer mocks, requestDeadline/timeout behavior, Today/`MomentCard`). #160 applied the same *class* of baseline fixes from product contracts only. #158 also extracts `momentView` and adds `BROWSER_PAGE_LOST` copy; those were **not** taken here. When landing, Codex should treat the overlapping test edits as duplicate baseline repair, not as a reason to pull #158/#159 features into this journey.

## Locally verified (this closeout tip)

Interpreter: `/tmp/desk-venv/bin/python`. Frontend Node suite via `npm test`. Ports **8832** (API) and **5191** (Vite `--strictPort`) owned by the UI test process group.

Focused followed-reply backend: `PYTHONPATH=backend … pytest tests/test_mail_reply_reminder.py tests/test_mail_followups.py tests/test_mail_reply_ui.py` → **47 passed** (UI includes failed-read recovery then successful read/draft/save at 1440×1000 and 320×740).

![Desktop task card after recovery and save](desktop-1440.png)

![Narrow task card](narrow-320.png)

Previously failing nine backend cases → **9 passed**.

Full backend: `PYTHONPATH=backend … pytest -q --tb=line -p no:cacheprovider` → **3068 passed, 1 skipped, 0 failed**, 1045.28s. The single skip is the suite’s existing skip, not this slice.

Frontend: `npm test` → **440 passed, 0 failed**. `npx tsc --noEmit` passed. `npm run build` passed (Vite; existing chunk-size warning). Ruff on the edited Python test files passed.

Exact tested product-and-test commit SHA is recorded in the notes commit that follows this closeout commit (or in the PR body once pushed). Suites above were run on the closeout working tree that became that product commit; they were not claimed for a later untested notes-only tip.

## Not claimed

Not merged. Not deployed. Not a live Gmail or Outlook acceptance. Not a sent message. Not shopping, booking, or automatic execution. Paid reasoning was not used. Extra paid credits were not used. The Pi update is a separate device step. #158 and #159 remain independent open work.
