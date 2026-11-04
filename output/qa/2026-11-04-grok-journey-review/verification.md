# Grok offline journey review and integration

4 November 2026. Owner request: review Grok's new GitHub work, repair issues and merge when verified. Local source is frozen at `63e538b420f5cb0e3fb4cad3622f4dbe4cb800ca`; final full-run passed1738 backend/305 frontend; publication is recorded separately below. No GitHub Actions, live providers, accounts, payment, Pi or real-data migration.

## Scope

Five independent PRs on main `dac527b`: #78 acceptance harness, #79 mailbox, #80 shopping, #82 calendar, and #81 merge guide. [Frozen heads](frozen-prs.json). All five heads are retained as merge ancestors. Original dirty academic/Pi worktrees and the current preview are preserved.

The source conflicts were shared router composition, proposal filtering/decision dispatch, three portable backup bundles, and rules-tick delivery. Each journey retains its own result types and dataset. The guide's earlier claim that calendar has no portable bundle was stale; current #82 includes it.

## Findings and repairs

| Finding | Repair and evidence |
|---|---|
| Shopping notices disappeared during quiet hours and equal event IDs from different connections suppressed each other | Persist holds through the existing Notifier/rules tick and scope notice IDs to connection+event; combined JSON backup retains holds. Two focused regressions failed before repair. |
| A later mailbox batch could overwrite a newer thread deadline with an older message | Compare applied history within the same thread and report skipped IDs. The delayed-message regression failed before repair. |
| Mailbox backup accepted a mismatched message-to-task target and an impossible cursor | Cross-check thread/task links and completed cursor history before preview accepts the bundle. The tampered-backup regression failed before repair. |
| Sync held the same lock needed by revoke and did not recheck login between effects | Revoke commits independently; mailbox/calendar recheck state and login before the next admitted item; shopping rechecks login. Four HTTP stop/logout variants prove later items are not committed. |
| Portable shopping restore retained a dangling Work ID; create-then-pause admitted a briefly runnable job | Explicit owner sync reattaches one paused run to the existing restored task. Internal `start_paused` admission is atomic and does not extend the HTTP model schema or restore execution/session authority. |
| An interrupted later calendar batch produced a valid partial state that its own backup validator rejected | Preserve the last completed cursor while allowing newer committed revisions from an interrupted batch. Restore-and-continue regression failed before repair. |
| Calendar fingerprint omitted the operation, conflict pairs never expired, and native-calendar conflicts broke backup | Include effective upsert/cancel in identity; retain active overlaps so a resolved conflict can reappear; validate linked local events and drop stale external dedup markers from export. Three regressions failed before repair. Repeated cancellation advances bookkeeping without another cancellation notice. |
| Restored calendar operation responses were only size-checked and could falsely claim email/RSVP effects | Validate the full receipt shape, connection and item identities, progress fields, and mandatory sent=false/accepted=false before replay. Three tampering cases failed before repair. |
| New proposal kinds fell through to the calendar/device UI, and confirmation claimed a calendar write | Shared JourneyAdvice renders the actual task, proposed change, expandable source/reply details and exact save effect. Shared decision copy says the review was saved to the task. Five frontend regressions plus real web/phone interaction/readback. |
| Mailbox's ingestion, HTTP and 600+ lines of backup logic shared one large module | Move portable serialization/validation/restore to MailboxBackup; existing service entrypoints and the one SQLite/core remain. |

These are offline fixtures and controlled application tests. They do not connect an inbox/store/calendar account, send messages, pay, accept invitations, or establish model autonomy. No new AI quality score is claimed.

## Verification

Final run summaries are in [validation summary](validation-summary.json). Final frozen source passed1738 backend tests and305 frontend tests, lint, typecheck and build. The earlier1734 run and later targeted runs remain historical; they are not added together. The final source and test hashes are unchanged by documentation closeout.

A separate local rehearsal merged current PR77 head `0d73f1c` with this integration. Application sources merged without conflicts. Initial compatibility:123 focused backend checks plus319 frontend tests and type/build; the final calendar receipt patch passed29 focused checks after replay. This rehearsal does not merge PRs73–77 or change the owner's running preview. [Compatibility](compatibility.json).

Actual local preview used an isolated fictional store, API8870 and Vite5190, with scheduler, providers, computer execution and public capture off. An initial5192 origin was correctly rejected; using an already permitted loopback origin fixed QA setup without relaxing origin policy. Native CUA IAB is the browser path; no standalone Playwright or user-tab resizing. Web shows all three proposal kinds, expands source details, confirms shopping/calendar/mail notes and cancels the old mail draft while preserving unsent text. Independent HTTP task details contain the saved source notes. A393×852 phone view has scrollWidth393, displays/expands the mail card, cancels it and preserves its draft. The inspected final browser has no error/warning logs. Native iOS keyboard and hardware were not exercised. The owned tab, temporary metrics and both preview processes were cleaned up; the user preview was untouched.

Initial rehearsal notes are not product failures: an unpublished conflict-resolution helper overmatched text and was discarded/rebuilt from the frozen base; no remote/user code changed. The first combined validator placed calendar validation before its event-ID set; fixed before acceptance. The first pytest console-script run omitted the scripts namespace; final checks use `python -m pytest`. An overlong quiet-hour test expired its8-hour login and was corrected to a3-hour interval; an initial stop-test route typo was corrected. Failures remain local evidence and are not mislabeled as Grok defects or passes.

## Delivery boundary

[Secret scan](gitleaks.json) reports no findings; source scope excludes credentials, runtime data, school files, restricted art and workflows. Local source and compatibility results do not deploy code into the current OpenAI preview. The next software integration must retain PR74–77's primary chat/Alice baseline. Final GitHub PR/head/merge receipts are in `publication.json` after actual readback.

Published build logs normalize only trailing terminal whitespace; outcomes and warnings are retained.
