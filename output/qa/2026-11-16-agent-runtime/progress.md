# HISTORICAL · Group 2 progress before Pi recovery

This checkpoint is superseded by [final QA](verification.md). Pi deployment and its Google consent were completed later in the same task.

Work continues in `codex/agent-runtime-20261116`. Preserve the recovery checkout, all original runtime data and private backups.

- PR123 merged as `7d7ab9fad96e2717f572f8dd5d997d0b03da1e33`. The application tree matches the locally tested candidate. No CI.
- Full local baseline: 2348 backend tests, 387 frontend tests, Ruff, types and build passed. Original-store rehearsal preserved all 102 original table contents while adding 22 tables; schema remains 3.
- Mac now runs the complete immutable release `~/.local/share/desk-companion/releases/20261116-7d7ab9fa/desk-companion` against the original data. Web endpoint remains `http://127.0.0.1:8831/`. A3/version9 and protected configuration were retained. New build-info and index were read back.
- Native iPhone17Pro/iOS26.5 Simulator rebuilt, installed and observed. Its embedded build-info/index match Mac. It uses a Mac8831 launch argument; no saved origin change or physical-iPhone acceptance is claimed.
- Pi remains unreachable. VPS service/443 and exact Pi relay credentials worked in an isolated Mac test; the Pi reverse listener is absent. No new Pi deployment. Same-source 93,739,434-byte bundle is prepared privately; SHA256 `337cacec9fd928034b5826fbac16069501acc1d8e802146733c899a4cb32a7d0`. Power diagnosis remains deferred.
- Owner completed Gmail reconnection and Calendar consent. FYP connection versions changed; actual Gmail profile and bounded Calendar events reads succeeded. No message bodies/calendar titles were collected, no mail sent.
- Microsoft personal-account login stopped at the owner's CAPTCHA difficulty. No client registration or FYP Graph authorization completed. Do not repeat/bypass the challenge or copy connector tokens.
- Official managed Agents browser trial used the newly authorized one-session/60-second/US$1 round. Four browser activities read the first two Books to Scrape products and selected the cheaper one. Results matched independent HTML readback. Elapsed 51.731 seconds; session DELETE succeeded and GET returned 404. No second cancellation trial fit the time cap. Usage was null: reserve the entire US$1, mark cost unknown, and close the round. No additional paid requests authorized.

Private receipts/logs: `~/.config/desk-companion/agent-runtime-20261116/` (including `managed-trial/verified-result.json`, `mac-activation.json`, `native-readback.json`, `google-provider-check.json`). Credentials, databases, browser histories and private logs stay outside Git.

In progress: integrate an opt-in managed public-browser executor with the existing JobService and local protocol tests. The operator trial is not yet a deployed FYP integration, merchant account flow, purchase or ticket acceptance.
