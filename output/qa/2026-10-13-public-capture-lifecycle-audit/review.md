# Independent public capture lifecycle audit

13 October 2026. This audit uses synthetic temporary SQLite stores and immutable files, injected transport results and controlled failures. No external URL/provider request, actual user database migration, application edit or Git operation was performed. Shared source fixes belong to the implementation worker; final aggregate and publication belong to the coordinator.

## Findings and corrections

1. Exact source lookup originally selected the complete SQL row before enforcing its metadata bound. An instrumented SQLite row factory proved a corrupt 2,000,000-byte value reached Python. The owner moved all source fields behind SQL CASE bounds; independent retest passed. Receipt lookup received the same bounded projection fix. A final sweep also reproduced 2-MiB materialization from corrupt INTEGER-affinity settings-version/personal-epoch columns, and the owner added SQL type/range projection guards there; both independent final tests pass.
2. Exact source metadata used Python equality, allowing integer `policy_version=1` to become boolean `true` while retaining the original canonical request hash. The owner now recomputes the actual stored request's canonical hash as well as the expected hash. Independent rejection test passed.
3. Cancellation after final linking, or hide→show at that point, still allowed the shared writer to mark the source verified automatically. The owner carried the existing checkpoint through final readback and status commit. Independent tests now preserve unknown retained bytes until an explicit currently authorized local reconcile, while the capture remains cancelled/unknown.
4. A corrupt review row changed only to `state=verified` returned a verified lifecycle with no acquisition, source or approval receipt. The owner added verified-state requirements. Independent final rejection test passed.
5. Operation-key input permitted values which its own bounded receipt projection rejected only after commit (100 non-ASCII characters or embedded NUL). That could persist an unreadable review despite returning an error. The owner now accepts only 1–100 printable non-whitespace ASCII operation-key characters before any write; both invalid cases leave zero capture/receipt rows. Independent final tests passed.

## Independent coverage

The standalone fixture covers scalar SQL materialization, canonical metadata identity, exact 200-capture/600-receipt boundaries, original-key recovery/no-op duplicates at full history, collision ordering before unrelated target access, hidden stop with corrupt private JSON, restart inspection, real session response fences, privacy/session/wall-clock changes across dispatch and publication, cleanup failure and retained capacity, temporary-only/double-hardlink/single-final-link readback without repair, dispatch-possible versus actual GET count, explicit ordinary Work selection and independent artifact filesystem hashes, exact source byte capacity, and same-source operation reuse at full count with unrelated corrupted accounting.

The transport is deliberately injected here: recorded fixture GET invocations are not live public HTTP evidence. The implementation worker independently owns its real local-loopback HTTP workflow; the transport auditor owns strict framing and cleanup integration. Work creates no model calls and captured text remains untrusted, with no provider-sharing grant. Browser mount/download, live TLS/DNS and real model quality are not claimed.

## Verification status

Final frozen run: **56 passed** (40 independent audit scenarios plus 16 existing app/runtime wiring cases), with one existing FastAPI/Starlette TestClient deprecation warning. Eleven source/test hashes were unchanged before and after the run. See `frozen-tests.txt`, `freeze-before.json` and `freeze-after.json`. No unresolved lifecycle blocker remains within this audit scope. The 16 runtime cases and any overlapping implementation tests must not be added again to the coordinator's full-suite count. Early runs and discovered failures are retained for traceability. A byte-boundary fixture initially assumed 27 bytes instead of the independently confirmed 28-byte extraction; the fixture expectation was corrected, with no application change required for that test error.

Verified at 2026-10-13 09:49 UTC. Core SHA-256 values:

- `public_captures.py`: `aa6ca78a58c34b19774761d96de8e96ce827531dd3de8c7db5b2982c4f3720bf`
- `file_store.py`: `ae5d1b98fbd038468396c341097036867781f2ff567f768d5b77d843398b2618`
- `sources.py`: `0630e524e46899f9f9038f2d56d66090415cfa425e00e5978748f54ebdbc1c01`
- `work_capacity.py`: `5a085a9dcf90ac7b546ab27d70f3cc84bb478595fc1e15a748c4f8e028dae333`

The reviewer changed only this QA directory. Current product/operator contract updates and Git delivery remain coordinator/implementation-owner responsibilities. Actual user stores, network settings, protected assets and original previews were not touched.
