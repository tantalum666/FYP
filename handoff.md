# Group 2 · Current handoff

16 November2026. Continue in `/Users/tantalum/.codex/worktrees/agent-runtime-20261116/FYP`, branch `codex/agent-runtime-20261116`. Preserve all recovery checkouts, original data and private backups. [QA](output/qa/2026-11-16-agent-runtime/verification.md), [capability map](desk-companion/docs/personal-agent-status.md), [managed-browser contract](desk-companion/docs/managed-browser.md).

## Delivered baseline

PR123 merged as `7d7ab9fad96e2717f572f8dd5d997d0b03da1e33`. Complete Mac/Pi backends and native Simulator frontend now share this baseline, including reviewed Grok features and Alice motions. Original-store migration rehearsals left all old tables unchanged (Mac102→124, Pi101→123, schema3). Verified stopped-service backups preceded activation; protected data, app accounts and A3/version9 were retained. Normal URLs: Mac `http://127.0.0.1:8831/`, phone browser `?surface=phone`, Pi relay `http://127.0.0.1:8891/`. Native uses a Mac8831 launch argument, not a saved origin change or a physical-iPhone claim.

The Pi returned through the existing VPS during this task. The old listener had been absent; VPS and exact relay credentials were independently healthy. No SD-card/network replacement, hotspot request or power investigation. Full release files/API/index were activated/read back. Device rendering and final feature-release receipts are tracked in QA; do not infer physical animation/performance from asset delivery.

## Accounts

Owner completed Mac Gmail Reconnect and Calendar Connect. FYP connection versions and actual Gmail profile/bounded Calendar GET both passed; no mail bodies/calendar titles or send operations were used. Owner subsequently completed Pi's separate Gmail/Calendar consent; both actual provider GETs also passed from Pi. Microsoft personal-account login was blocked by CAPTCHA difficulty; no FYP client registration/Graph grant exists. Do not repeat/bypass CAPTCHA, reuse the expired device code, or transfer Codex connector grants.

## Official execution work

An actual one-session managed Agents browser trial read two public book prices and chose the cheaper one; independent HTML readback matched. Four browser activities,51.731seconds, DELETE then GET404. Usage was null: **USD1 round closed, entire reservation retained, no further paid calls**. Live cancellation did not fit the cap and remains untested.

New opt-in FYP managed research adapter reuses JobService and owner/privacy/provider/permission checks; no new planner/queue or dependencies. It has local lifecycle, cancellation, uncertain-resource, legacy backup and desktop/phone UI checks. Ordinary runtimes keep `DESK_MANAGED_BROWSER_ENABLED` off. This FYP integration has not received another paid end-to-end trial; it is not voice-to-shopping autonomy, actual owner takeover, payment or ticketing. See QA for exact publication/activation status.

## Evidence and next step

Baseline2348backend/387frontend tests; new execution slice154focused backend/388frontend tests, Ruff/types/build and actual desktop/phone UI passed. No CI. Private evidence/scripts/bundles/backups: `~/.config/desk-companion/agent-runtime-20261116/`; Pi backup: `~/.local/state/desk-companion/release-20261116/`. Never commit those private contents.

Next product slice: connect a trusted conversation/voice admission to the existing browser-job review flow, then implement actual owner browser control/return before authenticated merchant acceptance. Keep managed execution opt-in until an integrated provider/cancellation trial has a fresh budget. Continuous inbox follow-up, real purchase/payment/ticket receipts and Microsoft registration/consent remains an explicit gap.
