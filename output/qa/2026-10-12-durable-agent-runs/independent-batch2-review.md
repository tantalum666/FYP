# Independent batch 2 review

Review frozen at 15:29 UTC, 12 October 2026. Scope: durable work-package design and actual implementation contracts, private immutable sources/artifacts, supervised experimental public browser workflow, frontend control/recovery/privacy behavior, and Runtime/app/AssistantPanel wiring. Implementation source was authored by other workers; this reviewer changed no implementation files.

Base source checkpoint: `546734273c9c8305cf6226e96a8e07854ba5c0b1`. Reviewed local additions are not represented as published or live-accepted here.

## Final verdict

Go for the documented implementation checkpoint on the hashed reviewed snapshot. No open reproduced code blocker remains. This is a source/contract verdict, subject to the parent's final aggregate verification, and does not establish live model quality, live StackEdit compatibility, deployed UI acceptance or hard network egress isolation.

The final negative probes verify that mismatched recovered effects cannot be adopted or marked achieved, unrelated drafts remain untouched, owner/private authorization covers linked and orphan run drafts, stale observation claims cannot publish, privacy revocation does not lose valid cleanup evidence, and browser cancellation remains available at capacity.

## Findings and changes verified

1. Deterministic report construction was incorrectly constrained by the model's eight-section schema. It now permits the bounded selected evidence set
2. Calendar-create verification checked only record existence. It now compares canonical requested fields, count and version; changed saved events fail verification
3. A final-name file could be reconciled before the original writer's durability barrier. Publication now uses private exclusive temporary bytes, file fsync, no-overwrite link, matching-temp unlink, directory fsync and independent readback. Recovery establishes its own fsync barrier before promotion
4. Model source coverage previously exceeded the actual excerpt sent. Whole-line reads now have a 1,800-byte model budget and are transmitted unchanged; deterministic full local parsing is separately labelled
5. A crash between child-draft creation and run linkage could orphan a live draft. Durable typed intent and operation key now precede dispatch; cancellation/restart recover the existing child receipt
6. Cancellation during the first artifact could previously dispatch the second. Current stored generation is checked before each dispatch
7. Scope initially dropped source-list pagination beyond 50 and omitted aggregate source-byte enforcement. Scope now admits all 100 retained candidates and creation caps selected bytes at 4 MiB
8. Structural completion could succeed with unread selected sources. Immutable outcome requirements and composition-time evidence now require selected acquisitions, complete declared source coverage and requested section titles; missing evidence yields partial. Semantic quality remains unassessed
9. Composer's own close path did not see its parent draft guard. Explicit Modal.dirty now protects goal/selection drafts
10. Frontend did not expose required explicit retry_model after unknown paid-call outcomes, and admitted empty/oversized model selections. Typed UI contracts now match the backend and distinguish paid retry from resume
11. Finished/expired proposal review links could close the run panel with no destination. The frontend gates pending/unexpired reviews; AssistantPanel reports a missing/handled/expired ID after an accepted current fetch
12. Browser supervisor could drain inherited pipes indefinitely after its leader exited. A separate post-exit drain deadline now returns unconfirmed cleanup; the test owns and cleans only its synthetic child
13. Browser approval originally checked only current visibility, allowing hide/show between checks. Durable privacy revision now fences approved dispatch and observations
14. A verified byte receipt could override unconfirmed process cleanup. Cleanup and browser-close evidence are distinct; uncertain cleanup keeps the job unknown and blocks further admission, while exact verified bytes may remain readable
15. Retained run-control receipts had no explicit cap. A per-run control-receipt limit now preserves cancellation while bounding other controls
16. Provider responses were fully buffered before raw-content limits. A 128-KiB streaming size cap, identity encoding, per-chunk monotonic deadline and phase timeout now bound ordinary body reading; malformed/deep JSON is normalized. It does not claim an OS-level hard-kill deadline
17. Old public observations could continue and publish after a replacement service marked them interrupted. Persisted active claims, checkpoint fences and state/token compare-and-swap now reject the old result
18. A privacy change after a normally closed source read could prevent recording confirmed cleanup. Cleanup evidence is now saved under the current claim before private-result authorization; content remains discarded on revocation without permanently disabling future work
19. The parent identified that legacy assistant proposal routes exposed run-origin task/calendar drafts to paired controllers. Owner/private route guards now classify linked and unlinked child drafts by durable canonical intent; unrelated legacy proposal semantics are preserved
20. Recovered operation receipts were accepted by key alone. A deliberately colliding unrelated draft could incorrectly satisfy a required requested mutation. Recovery, cancellation and origin classification now validate immutable typed arguments, stored operation request and current proposal payload; random per-reservation keys remain durable across retries. Mismatches block without adopting, cancelling or relabelling the unrelated draft
21. The browser's history cap also rejected cancellation. New work is bounded at 2,000 non-cancel receipts while one stop receipt per existing job remains available; different-key repeated stops do not grow event/receipt history

## Independent executions

No broad suite, real model call, public browser navigation, Chromium launch, account access or external mutation was performed by this reviewer in this batch.

- `review-focused-tests.log`: 15 passed / 63 deselected. Actual SQLite/files, real child-process exit/restart, temporary-file non-promotion, recovery fsync failure, revocation, provenance, orphan draft recovery, stored model-decision recovery, cancellation, missing coverage and calendar drift
- `review-focused-before.sha256`: seven backend modules and two test files were unchanged across that run
- `review-engine-final-tests.log`: 4 passed / 28 deselected. Composition-time evidence cannot be repaired retroactively, control receipt cap preserves cancel, model sees typed mutation schema, and real API selection-to-download path works
- `review-engine-final-before.sha256`: engine source and test hashes unchanged across that run
- `review-frontend-focused-tests.log`: 25 focused run/browser tests passed. These are contract/behavior helpers and streamed export checks, not rendered end-to-end acceptance
- `review-browser-focused-tests.log`: 4 passed / 19 deselected. Queued privacy revocation, effect restart fencing, independent cleanup evidence and actual trusted subprocess pipe-drain deadline
- `review-browser-before.sha256`: browser source/test hashes unchanged across that run
- `review-browser-probes.log`: independent synthetic supervisor probes show hide/show causes zero execution dispatches; exact export bytes with forced/unconfirmed process cleanup stay unknown with new admission blocked
- `review-browser-observation-restart.log`: reproduced original defect. Replacing BrowserService during observation marks its old row failed, but the old observation can still pass its checkpoint and overwrite the row as observed. `review-browser-observation-restart-fixed.log` shows the same independent probe now dispatches no post-restart read and returns BROWSER_RESTARTED; `review-browser-observation-fixed-test.log` has 1 passing regression. Probe scripts here create only synthetic local fixtures and perform no browser/network work
- `review-provider-bounds-tests.log`: 13 passed, with unchanged source/test hashes in `review-provider-before.sha256`
- `review-browser-privacy-cleanup.log`: original cleanup-order defect; `review-browser-privacy-cleanup-fixed.log` now shows the private result denied but no false cleanup admission block
- `review-browser-cancel-capacity.log`: original stop-at-cap defect; `review-browser-cancel-capacity-fixed.log` shows successful cancellation at capacity
- `review-browser-final-fault-tests.log`: 2 passed / 35 deselected, covering privacy-cleanup ordering and bounded cancellation at capacity
- `review-run-proposal-authorization-tests.log`: 3 passed / 32 deselected, covering actual controller HTTP denial, preserved unrelated legacy behavior, orphan-draft authority and hidden owner denial. `review-hidden-proposal-api.log` separately shows an actual hidden-owner filtered response, 403 confirmation and zero saved tasks
- `review-effect-key-collision.log`: original false required-outcome success reproduced. `review-effect-key-collision-fixed.log` injects a mismatched receipt at the actual newly reserved random key and proves typed conflict, no adoption, and an untouched/unclassified unrelated draft
- `review-final-receipt-and-auth-tests.log`: 5 passed / 33 deselected, including matching-intent recovery and mismatched-intent rejection
- All 14 critical source/test entries in `review-final-before.sha256` remained unchanged across the final receipt/auth and injected-collision checks. `review-final-source-manifest.json` freezes the wider final reviewed surface and its exact bytes

Focused pytest executions overlap where a fix was rechecked; the logs are not a new full-suite count. The reviewer did not perform broad aggregate testing. Synthetic probe files are local-only reproductions and do not themselves prove real browser exports.

## Explicit limitations

The browser adapter is disabled by default, fixed-catalog and public/synthetic-only. Routing filters and DNS preflight are defense in depth, not a hard private-network/metadata egress boundary. The larger design's hard-egress/general browsing acceptance is therefore unmet. No private selected source, generic URL or model browser-write tool is admitted by this implementation.

File hashes and structured source coverage prove stored bytes and declared ranges, not semantic truth. Deterministic compilation does not interpret arbitrary goals. Scripted model decisions prove protocol handling, not model quality. Unknown effects are retained and never automatically repeated or purged. Private source/run retention has no deletion UI in this slice and is explicitly disclosed.

Current hide mode blocks new authorized dispatch, but the run UI closes; metadata-only pause/cancel remain API capabilities rather than hidden-mode UI controls. A user can reveal owner context to use the normal run controls. Already dispatched effects are not rolled back.
