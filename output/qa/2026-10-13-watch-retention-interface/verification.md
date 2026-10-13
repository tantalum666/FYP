# Terminal watch history maintenance interface

2026-10-13. Implemented frontend scope only in the existing cloud checkout after the parent's explicit source-freeze release at 08:37 UTC. Same ongoing task and inherited 186-document intake; relevant rereads recorded in `reading.json`. No user runtime database, API, provider, credentials, installation, Git publication or live irreversible action was used.

## Delivered

- Visible-owner Watch history and bounded Trash workspace, explicit exact-ID maintenance detail and action-specific read-only previews
- Separate English/Chinese permanent-removal confirmation identifies title/ID, definition/baseline/review counts, post-operation retained opaque receipt count and exactly one logical saved-watch slot; tasks and independently started Work remain separate. No automatic cleanup or restart
- Trash remains charged; Restore history preserves terminal state and spent budgets, never invokes resume. Lifetime identity usage and fixed 256 ceiling are displayed separately, with unknown/over-limit usage never rendered as zero
- Ordinary and hidden list capacity uses validated `maintenance_usage.retained_count`, not visible row length. Hidden mode renders no maintenance component and retains the existing safe list/stop path, never `/work/capacity` or maintenance requests
- Narrow in-memory maintenance retry queue retains exact path/body/operation ID for unknown transport, malformed successful responses and server failures. Only explicit retry resends it; committed same-operation recovery does not need a still-live preview. Identity/privacy changes clear its private queue; no fresh key is silently generated
- Strict response-union decoder rejects fabricated acknowledgment/full-resource data in removed dispositions, checks expected ID/operation ID/original action, and requires terminal visible retained results for maintenance
- Successful Trash/removal dispositions clear selected ordinary detail before the next refresh. New-selection read owns refresh, avoiding a request to ordinary detail after its record leaves that view
- Shared owner and local view fences handle hide/show, session replacement, offline/stale, snapshot changes, unmount and reordered authority denials. Preview cancellation invalidates captured final callbacks synchronously; expiry checks both wall-clock and bounded monotonic client deadline (server owns authoritative session/epochs/inventory and TTL)
- Independent auditor found an older overlapping ordinary list denial could leave a newer success active. `useResponsibilities` now treats any actual denial within its mounted authority epoch as decisive regardless request order, while ignoring old/unmounted epochs. Independent reproducer rerun passed

## Scope and verification

Owned changes: responsibilities `ResponsibilitiesPanel.tsx`, `useResponsibilities.ts`, `types.ts`, `labels.ts`, `responsibilities.css`; new `retention.ts`, `useWatchRetention.ts`, `WatchRetention.tsx`; two new retention test files and the existing watch callback test. No shared personal mutation helper changed. Parent owns root/shared product/handoff/contract documentation.

- Focused retention: 14 executed production-hook/queue/decoder tests and 4 bilingual React SSR cases
- Existing watch callback suite: 7 cases, including added removed-disposition selection clearing and captured callbacks after unmount
- Full frontend suite: **214/214 passed**, final result in `frontend-tests.log`
- TypeScript: `typecheck.log` (empty output on success)
- Production Vite build: `build.log`; existing >500 kB chunk warning remains, no install or package change
- Independent audit **15/15 added cases**, independent full **214/214** and typecheck passed; evidence is separate under `../2026-10-13-watch-retention-interface-audit/`

`source-manifest.json` pins the reviewed responsibility workspace and changed tests. Tests use synthetic responses/deferred promises and production callbacks; SSR validates actual bilingual markup and escaping. These are not mounted browser, native dialog, keyboard focus, narrow-screen or target-device acceptance. No real lifecycle mutation or reclaimed user capacity is claimed.
