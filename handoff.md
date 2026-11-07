# Group 2 · Current handoff

7 November 2026. Active checkout `/Users/tantalum/.codex/worktrees/live-agent-eval-20261107/FYP`, branch `codex/alice-home-wake-20261107`, [PR97](https://github.com/tantalum666/FYP/pull/97) open/unmerged. Current source **f2a33e9** is active on Mac/Pi. No CI. All agent test ledgers closed; red-LED investigation remains deferred.

## Current result

Shared dark Alice home remains: large phone avatar, full month, clock/weather, translucent composer and optional Plan/More. Location prompting and loopback-cookie reconnects are repaired. [Home contract](desk-companion/docs/alice-home.md).

The owner's real wake failure exposed full-catalog schema corruption: annotation cleanup also deleted business title properties. Old27-tool payload was rejected400; repaired same catalog accepted200. Previous restricted-query smoke test did not cover this. Complete browser acceptance now passes with production capture/wake/Live/Responses/tool/playback code and synthetic transmitted input. Three finalized sessions included idle/re-wake and a correct Alice identity/two-meeting answer from an actual calendar_query, with playback acknowledgement and no writes. [Repair QA](output/qa/2026-11-07-alice-wake-repair/verification.md).

The app now has one explicit Microphone selector shared by local test, keyword capture and conversation. Normal Mac Web is saved to the built-in MacBook Pro microphone; actual local meter activity was observed without sending/recording it. Final Web page visibly waits for Alice, cloud disconnected. GPT Live remains primary, Sol handles delegation/text/browser, Realtime remains explicit comparison. Live voice-only/image limits remain unchanged. Safe provider failure code/phase is retained; deliberate retry clears stale error notice.

## Evidence and operation

2054backend/343frontend, lint/types/build pass. Fresh engineering-capped USD0.50repair ledger is closed at conservative **USD0.1864995**; all three receipts finalized. Useful post-input audio6.393seconds remains above the approximate5second target. This is not a human-accent/noise/AEC accuracy result. Prior USD1UI trial (USD0.0518613333) and browser/text round (USD0.37970163) remain independently closed.

Mac Web5190/API8831 runs the active checkout. Pi release `/opt/desk-companion-releases/20261107-wake-repair` has292verified files, original keys/environment and active app/application services. [Activation](output/qa/2026-11-07-alice-wake-repair/activation-summary.json). Physical Pi audio acceptance remains separate.

Private repair evidence and22-file stopped/checkpointed/off-device-verified backup: `~/.config/desk-companion/alice-wake-failure-20261107/`, archive `20261107-before-wake-repair.tar.gz`. The closed browser fixture ledger and scripts must not be reused for new paid testing. Its temporary tab/server are stopped; no microphone interception was installed on the owner's normal page. Keep the20261106release backing the frozen environment symlink and the retained recovery checkout used by `~/.config/desk-companion/pi5-dorm-ethernet-20261104/pi_remote.py`. VPS route unchanged.

## One next step

Reduce the measured first useful voice answer delay toward5seconds without stripping the normal tool catalog or weakening authority. Start with offline profiling; any new paid acceptance needs fresh scope. Native background/human acoustics/physical Pi audio remain open. The subsequent personal-agent slice is explicit same-browser owner takeover at the observed JD verification boundary; real transactions and native sending are still not implemented.
