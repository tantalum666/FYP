# Group 2 · Initiative finding → follow-up → revisitable status

25 November 2026. Grok Bot. Independent branch from public `main` `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` (PR #157 workspace). Pull requests #158, #159 and #160 were not checked out, stacked, merged, or edited. Throwaway three-way tree `65eb854e` was not used as a build base.

## Chosen gap (current main)

On `main` after #157, Conversation already shows proactive findings with Sources and Got it. The owner could dismiss a finding, but could not explicitly open a bound private follow-up task from that finding and later reread accurate status on the same card. Mail-thread follow-up and memory follow-up are different journeys. This slice closes only that suggestion → sources → owner-chosen follow-up → revisitable status path inside existing Alice Conversation / Tasks.

## Reading scope

- `AGENTS.md`, `product.md`, `handoff.md`, recent `decision-log.md` / `work-log.md`
- [Nov 11 Grok review verification](../2026-11-11-grok-review/verification.md)
- [Proactive research contract](../../desk-companion/docs/proactive-research.md), [personal-agent status](../../desk-companion/docs/personal-agent-status.md), [ui-copy](../../desk-companion/docs/ui-copy.md)
- Current `initiative.py`, `InitiativeMessages.tsx`, Tasks listing, private mutation / MutationFeedback
- #160 suite-gate notes for reusable baseline expectation fixes only (fingerprint, reprice clarify, managed-browser `session_origin`, forget `home_archived`, Google composer mocks, `requestDeadline`, Today/`MomentCard` mount). No #158/#159 feature code.

## Implemented journey

1. Owner expands Conversation and opens Sources on a pending finding.
2. Owner chooses Follow up on this. Alice creates one private task bound by task id to that finding. Nothing is sent. External effects are not claimed.
3. The finding card shows live status (open / waiting / completed / cancelled / missing). Completing the bound task updates status; a same-title decoy task does not steal the binding.
4. Tasks lists the follow-up. Hide-private fences display of the private task; the id binding remains.
5. A failed write keeps the exact request for Retry the same request; recovery does not invent a second task.
6. Got it still dismisses without sending and without reopening a completed follow-up.

Local fake initiative + fixture login only. Not live mailbox, not paid model, not live external acceptance.

## Origin ports

Owned browser ports `5200` (Vite) and `8840` (API) are added to the existing loopback allowlist beside `5190`/`8831`/`5191`/`8832`. POST from those origins no longer fails `ORIGIN_NOT_ALLOWED`. Production HTTPS / Pi tunnel rules are unchanged.

## Local checks

Interpreter `/tmp/desk-venv/bin/python`. Chrome at `/usr/local/bin/google-chrome`. UI ports 8840/5200 owned by the test process group.

| Check | Result |
|---|---|
| Focused initiative API + UI | **24 passed** (`tests/test_initiative.py` 23 + `tests/test_initiative_followup_ui.py` 1) |
| Full backend | **3058 passed, 1 skipped, 0 failed**, 1004.33s. Skip: existing `tests/test_shop_basket.py` local PHP CLI unavailable |
| Frontend `npm test` | **438 passed, 0 failed** |
| `npx tsc --noEmit` | passed |
| `npm run build` | passed (existing chunk-size warning) |
| Ruff on edited Python | All checks passed |
| `git diff --check` | clean |

### Baseline suite gate (same class as #160; not feature import)

Main tip still had the nine known stale-expectation failures. “Baseline also fails” was not acceptance. Narrow expectation/fixture alignment + behavior-preserving `requestDeadline` extraction, citing #160 pointers, without #158 `momentView` / `BROWSER_PAGE_LOST` or #160 mail-reply features:

| Failure | Product-aligned fix |
|---|---|
| Office fingerprint ×3 | Assert fingerprint behavior, not rebuilt dump of absent review fields |
| Flight reprice ×2 | Stale old-fare agreement clarifies (`acted:false`); status stays `reprice` |
| Managed browser ×2 | Split `session_origin` (create allowlist) from challenge `origin` |
| Forget context | Assert `cleared` and `home_archived is False` |
| Browser timeout regex | Behavioral `requestDeadline` path checks |
| MomentCard in App | Assert single mount under `TodayView` |
| Google composer fixture | Add home transcript / caption mocks |

### Browser evidence (real controllable local Chrome)

- Desktop 1440×1000: [desktop-1440.png](desktop-1440.png)
- Narrow 320×740: [narrow-320.png](narrow-320.png)
- Fail-once follow-up POST → alert → Retry the same request → Follow-up open. Nothing was sent. → Tasks shows the bound title. Home / composer / Work & tools still load.

## Distinction of evidence

| Kind | This slice |
|---|---|
| API / simulation | Fake `TextConfig` findings; pytest owner/stranger/hide-private/idempotence |
| Real controllable local browser | Installed Chrome against owned 5200/8840 |
| Authorization | Owner session required; stranger denied; private task + hide_private |
| External result | None claimed. No send, purchase, booking, live mailbox, or paid model |

## Future merge conflicts

#158 / #159 / #160 independently carry overlapping baseline test repairs (`requestDeadline` / Moments / fingerprint / reprice / `session_origin` / forget / composer mocks). Treat those as duplicate baseline repair when landing. Do not pull their feature stacks into this journey. This branch also adds loopback origins `:5200` and `:8840`.

## Ancillary #160 EOF hygiene (parent closeout)

On `cursor/followed-reply-reminder-e853` tip `a4882b89697a4b8c47a6217e788161225761fdbd`: removed the trailing blank line after the final `_blank_body(item)` in `mail_reply_reminder.py` so `git diff --check` is clean. Notes-only + whitespace; no semantic change. Full suite evidence remains on product `87a38f48` / throwaway integration `65eb854e`, not re-run as a fake new head.

## Remaining gates (not this PR)

- GitHub merge / CI / deploy
- Live Gmail / paid model / runtime provider or A3 change
- Pi / hardware
- Merging or importing #158–#160 features
- Parent weekly-limit budget decision before further Auto slices
