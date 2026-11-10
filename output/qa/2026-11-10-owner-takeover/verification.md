# Owner takeover on the same browser job

10 November 2026. Offline. No live JD or merchant login, no paid model call, no Pi or VPS change, and no GitHub Actions run.

## Read for this task

- `AGENTS.md`, `START_HERE_NEXT_CHAT.md`, `handoff.md`, the 7 November decision in `decision-log.md`, and the current computer-use sections of `product.md`.
- `desk-companion/docs/computer-use.md` and the job/permission implementation: `jobs.py`, `permissions.py`, `computer_use.py`, `computer_use_worker.py`, `computer_use_models.py`, `browser_supervisor.py`, and the job card in `JobActionCard.tsx`.
- The 7 November live QA only for the JD verification boundary. The raw JD page was not reopened.

## Scope

The existing computer-use job pauses at a login, SMS/OTP, captcha, or payment wall. Takeover and return stay on that job id, require the admitting owner session, and use operation ids. A fake browser driver reads `fixtures/browser/verification-wall.html` and `verification-cleared.html`.

## Checks

- `desk-companion/.venv/bin/pytest -q --tb=line` with `PYTHONPATH` including the project root: **2042 passed, 2 failed**.
- The two failures are the known main failures: `test_public_unicast[::ffff:93.184.216.34]` and `test_restart_runs_only_the_approved_folder_job`. The latter is handled separately in PR #98. This branch does not change them.
- Frontend `npm test`: **331 passed**. `npm run typecheck` passed.
- Ruff on the edited Python files passed.
- No live browser, merchant, or model request was made.

## Docs updated

`handoff.md`, `work-log.md`, `decision-log.md`, `product.md`, `START_HERE_NEXT_CHAT.md`, `AGENTS.md`, and `desk-companion/docs/computer-use.md`.
