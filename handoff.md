# Group 2 · Current handoff

13 November 2026. Current checkout `/Users/tantalum/.codex/worktrees/alice-motion-20261113/FYP`, branch `codex/alice-natural-motion-20261113`, based on main6153b41d. Existing [PR123](https://github.com/tantalum666/FYP/pull/123) remains open/unmerged. The owner rejected the first reversed-palm/stiff wave; current correction source is c65ac229. No CI or paid calls; all old budgets remain closed.

## Current result

Corrected **both** normalized wrist rolls, with palms facing forward and thumbs toward the face. Slower 4.8-second motion staggers elbow/wrist lift and return, with light rig-calibrated finger curls. Original model, Alice size, feet, A3 and business permissions retained. Tests use the real shipped bone hierarchy. 379 main-frontend tests and 358 runtime-compatible tests plus types/build pass. [Repair QA](output/qa/2026-11-13-alice-motion-repair/verification.md) supersedes the first-wave aesthetic acceptance.

## Actual endpoints

- **Mac web:** compatible frontend activated on the original live-agent-eval backend and work-ui-01 data. `http://127.0.0.1:8831/?page=assistant` is open and serves the normal account/voice environment. Greeting, palm-facing screenshot, return to idle and no console errors verified. A3/version9 and configuration retained. `?surface=phone` previews the same Mac workspace; it is not the native app's Pi backend.
- **Native phone:** original iPhone17Pro/iOS26.5 Simulator rebuilt/installed/launched, with its original Pi API origin `http://127.0.0.1:8891`. Actual recording shows initial greeting and return to idle. Native tap attempt was inconclusive; no physical iPhone or paid voice test. Its online services currently depend on restoring Pi connectivity.
- **Pi:** same 68-file compatible frontend atomically activated/read back under `/opt/desk-companion-releases/20261109-composer-attachments/frontend`. Backend PID1328, A3/version9 and 53 protected files unchanged at activation. Old frontend retained. Device page greeted from Mac, but that is not Pi GPU evidence. Original kiosk launched on the Pi display; optional browser keyring creation was cancelled. Real screen showed the new connected UI, then relay/VNC became unreachable before Alice finished loading. **Pi local animation/performance remains unverified.** No cause assigned and no power investigation resumed.

The native/runtime candidate overlays motion and the reviewed safe-area fix onto520ab563; it does not activate unrelated main/Grok features against the older backend. Private artifacts, receipts, backups and native video: `~/.config/desk-companion/alice-motion-20261113/`. Retain the live-agent-eval/native vendor worktree and original private runtime. Existing Mac-to-Pi forwarding launcher retains its normal reconnect behavior; no new network policy.

## Retained project state

All24 original Grok/Alice PRs were merged through121/122 on main6153b41d; [review evidence](output/qa/2026-11-11-grok-review/verification.md) preserves remaining real-browser/account gaps. That full integration still has not been rolled out to normal runtimes. Gmail Mac self-send was verified8November; FYP Microsoft/Calendar/Pi consent and real merchant takeover remain separate. A3 is selected. Pi power/red-LED diagnosis remains deferred.

## One next step

When Pi connectivity returns, inspect the kiosk renderer/logs and complete physical greeting/idle validation. Do not call the third endpoint accepted based on installed files or Mac rendering, and do not reopen paid budgets or the deferred power investigation. Mac web and native animation can already be inspected without a paid call.
