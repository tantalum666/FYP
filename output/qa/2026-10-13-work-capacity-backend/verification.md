# Retained capacity backend verification

Completed local backend slice 2026-10-13. Root released the prior task-watch source freeze before edits and retains shared Runtime/app wiring, publication and whole-suite freeze ownership. Same continuous-task 186-Markdown intake inherited; focused reading recorded in [focused-reading.json](focused-reading.json). No live model, provider, remote browser, Mac, credential setup, quota lift, deletion or reclamation performed.

## Implemented

- Dependency-free work limits reused by original source/artifact/file admission, run retention, search and saved-watch limit wrappers. Values and existing idempotency/admission/scope/error/reconciliation order preserved.
- New visible-owner global-only capacity read, strict typed aggregate, cap+1 scalar projection, UTF-8 metadata64KiB guard, malformed/ambiguous/oversized byte counts unavailable, retained rows still counted. No optional run usage; per-run limits only.
- Query-only observation transaction and fresh actual owner session/settings-version/personal-epoch fence. No file-body I/O, reconciliation, model/network, operation, revision or data writes. Unsupported schema gives safe unavailable error.
- Combined [feature contract](../../../desk-companion/docs/work-capacity.md) retains UI worker's lifecycle text and adds exact wire, constants, authority and accounting details.

## Actual checks

- [69 capacity checks](capacity-tests.txt) passed in21.90s: empty/full/count/byte/overflow/corrupt/hostile metadata, exact64KiB, bool/numeric strictness, malformed privacy, every retained state, authoritative SQL kind, fresh logout/expiry/hide-show/consent fences, consistent snapshot during writes, no-effect/query-only enforcement, stale concurrent source admission, same-key recovery at full source/artifact count/bytes, full run/watch same-key and cancellation, real FastAPI HTTP/no-store/origin and six paired transport/identity denials.
- [245 focused checks](inherited-focused.txt) passed in87.43s: nine capacity-admission cases plus inherited artifact, run, run-publication, search, responsibility and responsibility-worker suites. Nine overlap the69 capacity run; these are not314 unique tests.
- [Backend plus new-test Ruff](ruff.txt) passed.
- Independent reviewer additionally ran20 negative boundary checks together with the60 primary capacity cases:80 passed. See sibling work-capacity-audit/backend-combined.log. Reviewer found SQLite literal-NUL acceptance mismatch; added explicit pre-parse guard and metadata/privacy regressions, then independent recheck passed with no additional backend finding.
- Brief execution transport interruption occurred before an append/test command started. Exact file state was rechecked after recovery; interrupted checks were not counted. Initial HTTP404 tests preceded root route wiring; final69-case run above includes successful wired HTTP checks.

[Owned-file hashes](owned-files.sha256) identify the implementation/test/docs snapshot at handoff. Root-owned full freeze and CI/publication remain separate. Actual UI, Mac, model semantic quality and target hardware are not established by these checks.
