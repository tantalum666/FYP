# Group 2 — Grok PR integration review

11 November 2026. Owner authorized review, repair and merge. Source integrates **23 Grok PRs plus Alice #97**; exact heads, bases and file lists are in [pr-inventory.json](pr-inventory.json). Remote publication and merge are receipted after actual GitHub confirmation. This is not a runtime deployment.

## Scope and baseline

Main `855e60ee9f413de84474e3e0b9975b9b9a3d5fbc`; Alice baseline `ebf6d91751ff69f6acec0813f7eb69a1ed53dc5d`. Included #95, #96, #97, #98, #99, #101, #102, #103, #104, #105, #107, #108, #109, #110, #111, #112, #113, #114, #115, #116, #117, #118, #119 and #120. The four merge-guide PRs contain historical contributor rehearsals, not independently accepted results. All exact heads are ancestors of the integration tree; a fresh fetch confirmed no moving head and unchanged main before publication.

Work happened in `/Users/tantalum/.codex/worktrees/grok-reviewed-integration-20261111/FYP`, on `codex/grok-reviewed-integration-20261111`. Existing dirty recovery checkout and active runtime source/data were preserved. Ordinary local merges retain the contributor ancestry. No rebase/force-push, CI workflow, paid model call, account operation, payment or Pi restart was used.

## Findings and repairs

| Area | Actual defect or integration gap | Repair and evidence |
|---|---|---|
| Work continue (#96/#99) | The step happened before the continuation receipt was recorded; a crash in that interval could permit another step on retry. Refresh also cleared an executor lease. | Persist a reservation before dispatch; incomplete dispatch stays unknown. A returned no-op releases the reservation. An active worker cannot be reset, and model-mode runs cannot use this offline shortcut. Crash-after-step regression proves no second dispatch. |
| Next-step privacy (#114) | A paired request could fall through from filtered tasks to an unfiltered private owner goal. | Owner-only goal fallback; regression inspects the complete response for the private marker. |
| Reply obligations (#119) | Completed checklist steps still appeared as owed replies. Global matching could amend a different task despite the selected task. | Exclude done steps and scope lookup to the selected task. Regression checks the proposal target and unchanged unrelated task. |
| Attachments (#97 with #114/#116) | Local shortcut routes intercepted questions even when the conversation retained file context. | Preserve the file/provider route; five follow-up intents verified using real uploaded references and mock Responses transport. |
| Private feature access (#102/#103/#108/#110/#111/#112) | Memory/purchase routes did not honor private-hide; some writes only checked before entering their transaction; cached held-choice replies skipped owner validation. | Hide checks at routes/services, shared current-owner transaction gate, receipt checks before cache return. Regressions revoke the session between admission and write and verify no row is created. |
| Morning memory (#103) | Fact wording was copied into persisted/browser/push notices, remaining after later forgetting. Old operation receipts could repeat expired wording. | Store generic notices; project current active citations on owner reads. OS notifications stay generic. Forget/hide/expiry and repeated operation tests pass without leaking markers or creating another reminder. |
| Purchase approval (#110) | Confirm/update/approve did not bind the version on the owner's screen. Offer operation fingerprint omitted the target card. | Require `expected_version`; include card identity. A stale approval after a later recheck is rejected, and replay for a different card conflicts. |
| Substitute pricing (#110) | “Cheaper” meant cheaper than the budget, which could accept a substitute more expensive than the original. | Require the original item's total including shipping for substitution and compare against that total as well as budget. Regression uses an in-budget but more-expensive substitute. |
| Browser takeover (#101) | The production worker is headless and supplies no owner-control window; only the fake driver writes cleared-wall evidence. The UI still offered Take over. Cached handoff could bypass the admitting-session check. | Gate both API and UI on an explicitly capable driver; shipped headless transport remains unavailable. Check admitting session before cached results. Offline positive driver tests remain clearly synthetic. No real-account capability is claimed. |
| Public browsing (#101) | Any Sign in/Login text could stop a public shopping page, including a navigation link. | Restrict login-wall detection to actual password controls or a continuation prompt; navigation-link regression passes. |
| Trip quotes (#104/#105) | Event transition was computed before the write transaction and could overwrite a concurrent hold/revoke. Civil times silently accepted DST gaps/folds. | Recheck connection/current itinerary in the transaction and reject stale commits; use existing validated wall-time conversion. Trip tests and DST boundary regressions pass. |
| Interface integration | Old welcome markup and extra permanent composer controls conflicted with the current Alice baseline. New forms were mounted prominently ahead of task/memory content. | Keep #97 conversation/attachments/safe-area structure. Put optional forms in Work & tools or expandable Memory sections. Actual desktop/phone render and interactions checked. |
| Network compatibility | Contributor guides reported an IPv4-mapped public-address failure on Python3.12.3 and instructed leaving it. The current supported runtime should have consistent semantics. | Classify the embedded IPv4 endpoint before version-dependent IPv6 flags. All81transport checks pass, including private/link-local/multicast/reserved mapped forms. Seven extracted-function cases pass on installed3.12.13; that patched version already passed the old code, so the old3.12.3 failure was not reproduced locally. |
| Test integration | Two backend assertions expected pre-merge fallback kinds; four frontend tests matched obsolete implementation strings/welcome labels rather than user behavior. | Update the route expectations to the integrated kinds; remove those four label-string tests. Preserve actual render/state tests and add targeted regressions and browser flows. |

The standalone new services remain bounded local records/fixtures. Saved checklists are not an arbitrary skill executor; source briefs compare supplied notes; purchase/trip receipts are not orders or tickets. Their existing limitations and JSON-export exclusions remain explicit. Whole-database backups and portable exports are different products.

## Local validation

| Check | Result and scope |
|---|---|
| Initial integrated backend | 2319 passed / 2 failed: stale expectations in waiting/reply compatibility tests |
| Full repaired backend | **2342 passed**, 0 failed, Python3.14.5, 467.28seconds |
| Final network-policy suite | **81 passed** after the narrow mapped-IP change |
| Final memory suites/regressions | **40 passed** after current-fact receipt projection |
| Final combined regression/transport set | **100 passed** |
| Final handoff/jobs/regressions | **69 passed** after pre-cache admitting-owner validation |
| Frontend | **374 passed**, 0 failed; typecheck and production build pass |
| Ruff / diff | All checks pass; no unresolved merge markers or whitespace errors |
| Materials | No workflow changes, credential/database/audio/private-key file additions, or high-confidence secret patterns in the combined diff |
| Remote pin check | 24/24 heads unchanged and present as integration ancestors; main unchanged before publication |

Counts are separate runs, not additive. The full suite preceded the final narrow network, memory-receipt and cached-handoff follow-ups, which each have the targeted passing suites above. Existing Starlette/httpx and empty `pytest.raises` match warnings remain; the frontend has pre-existing large3D/runtime chunks. These are not failed tests. No dependency upgrade was made.

Representative commands: `.venv/bin/python -m pytest -q --tb=short`; targeted modules recorded in private logs; `.venv/bin/python -m ruff check`; `npm test`; `npm run build`; `git diff --check`. The Python environment and node_modules were reused by ignored symlinks, with commands run from this review checkout. No source from the active runtime was overwritten.

## Rendered acceptance

Flow: Alice home -> compact + menu -> actual file chooser -> local chip -> Send/upload -> mock-provider response; Tasks -> Work & tools -> Saved decisions -> save -> explicit approval -> changed assumption retaining the previous current choice; phone -> availability question -> readable bounded latest answer and usable input.

- Installed Chrome via Playwright1.62, isolated temporary profile and server `http://127.0.0.1:8832`.
- Desktop1440×1000, phone393×852 and320×740.
- Correct URL/title, nonblank Alice content, no framework overlay, zero page exceptions or failed responses in the final run, no horizontal overflow.
- Actual screenshots inspected: dark menu, file response, reviewed choice, two phone sizes. Existing Alice prominence, latest-caption surface, file entry and composer placement were retained.
- The first harness used8834, outside the product's allowed origins, and was corrected to already-allowed8832. No production origin protection was relaxed. Bundled Playwright headless-shell was absent, so installed Chrome was used without installing dependencies.
- The backend disabled schedulers, voice, real executors/connections and real provider transport; chat generation used `httpx.MockTransport` and synthetic local records. File transport/render success is not a fresh live-model understanding test.

Durable private evidence: `~/.config/desk-companion/grok-review-20261111/` (logs, harness and screenshots). [Validation summary and screenshot hashes](validation-summary.json). The QA browser was closed and the isolated server is stopped at closeout. No owner's tabs, microphone, camera, ordinary browser profile, runtime database or account sessions were used.

## Documentation and next step

Updated AGENTS current pointer, START_HERE_NEXT_CHAT, product, concise handoff, decision log, work log, research index, module map and affected feature contracts. Contributor merge guides are explicitly historical. The [reading/progress record](progress.md) distinguishes complete reading from focused/truncated ranges. Group remains Group2.

After verified remote merge, the next product gap is a real interactive owner browser transport and a scoped account journey using the existing job/permission system. Payment, ticketing, continuous real-mail monitoring, physical audio and runtime rollout remain separate from this merge. All old paid ledgers and the deferred Pi power investigation stay closed.
