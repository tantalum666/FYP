# Experimental public-source browser workflow

Updated 2026-10-12. This is an additive FYP-owned executor, separate from existing note/API jobs and the general agent-run planner. Its fixed workflow is **one observed official Python documentation excerpt → immutable public/synthetic brief → owner approval → actual StackEdit UI → StackEdit Markdown download → independent byte readback**. Source/contract tests do not establish live application acceptance. The cloud browser launch was blocked by the environment's sandbox, and it was not retried or weakened for this implementation. An isolated Mac acceptance run is still required.

## Scope and admission

The feature is off by default. Only a signed-in owner with currently visible private context can observe, prepare or approve. It accepts catalog IDs `python_asyncio` and `python_pathlib`, not URLs, private files, calendar data, memories, screenshots or model-generated tool code. The title (120 characters maximum) and note (2,000) must be public/synthetic. There is no browser-write tool in the model's catalog and a general agent-run grant cannot authorize this effect.

`public_only: true` is an explicit JSON boolean acknowledgment. It is required on source observation, preview creation and final approval. Final approval binds the entire immutable intent: observed source digest, exact content, generated document name, StackEdit destination, adapter/catalog version, selected runtime environment and persistence behavior. Source text is escaped and quoted as untrusted data; instructions in the excerpt never become actions.

**Third-party destination:** `https://stackedit.io/app`. The approved brief is typed into this third-party web application and is therefore exposed to its scripts. There is no account, publishing, cloud synchronization or login. The editor workspace lives only in a fresh disposable browser context/profile; after normal closure the durable result is the real application-exported Markdown retained by FYP, not a document in the user's usual browser profile. Do not assume that third-party scripts cannot observe the text merely because synchronization is blocked.

The browser is sandboxed with Playwright's `chromium_sandbox=True`, has no granted permissions, blocks service workers and routed WebSockets, and has a fresh home/profile. The worker inherits no ambient proxy configuration or API/session credentials. This does **not** provide a proven network sandbox. Exact request routing and all-public DNS preflight are defense in depth; DNS rebinding, other browser channels and third-party script behavior remain outside a hard egress guarantee. This capability is explicitly experimental for public/synthetic information only. Private-data browser workflows require a separately enforced/proven boundary and explicit destination/data permission.

## Runtime prerequisites

Supported admission platforms are macOS and Linux with Python 3.12+. The optional dependency is pinned in `pyproject.toml` and `uv.lock`:

```sh
uv sync --locked --extra browser
```

This installs the declared Python extra from the locked package registry. It does not install a browser. An operator must separately provision a compatible Chromium executable from an authorized official installation. The application never downloads Chromium, chooses a private browser profile, attaches to an existing browser/debug port, installs LCU, requests Accessibility permission, or changes OS security settings.

After provisioning, launch the normal backend with both settings:

```sh
export DESK_BROWSER_ENABLED=1
export DESK_BROWSER_EXECUTABLE=/absolute/path/to/authorized/chromium
```

The absolute executable path is operator configuration, never model/input data. The environment digest identifies this configured path and adapter; it is not a binary-signature or OS attestation. Do not add `--no-sandbox`, disable security features or redirect the workflow to an unrelated application to obtain a passing result. A cloud sandbox failure is a real blocker. On macOS the executable may be inside an authorized application's bundle; supply the executable, not the bundle directory.

`GET /api/browser/capabilities` distinguishes configured/ready admission from `live_acceptance: "not_verified_here"`. Missing Python extra, missing executable, unsupported platform, default-off status and unresolved cleanup each have their own reason code. Ready does not prove the executable can launch or the live site matches the selectors.

## Owner HTTP contract

All routes use the existing owner cookie, request-origin rules and `X-Desk-Request: 1` for writes. Operation headers use `X-Operation-Id`; observation/prepare/approve/cancel store content-free fingerprints and stable references. Repeating an identical key returns the prior result, while changed intent conflicts. The reconcile header does not authorize an effect and does not cause replay.

| Route | Input / behavior |
|---|---|
| `GET /api/browser/capabilities` | Fixed sources, StackEdit destination, limits and admission reason |
| `POST /api/browser/observations` | `{source_id, public_only:true}`; real bounded browser read, at most 60 seconds before supervision cleanup |
| `POST /api/browser/jobs` | `{observation_id, title, note, public_only:true}`; creates immutable review, no destination activity |
| `GET /api/browser/jobs?limit=50&cursor=…` | Bounded ID-keyset history, limit 1–100, `next_cursor`; IDs are not a chronological cursor |
| `GET /api/browser/jobs/{id}` | Current metadata, history and, when visible, full exact request/hash |
| `POST /api/browser/jobs/{id}/approve` | `{expected_version, intent_hash, public_only:true}`; queues the exact reviewed effect |
| `POST /api/browser/jobs/{id}/cancel` | Records cancellation; does not claim to undo an already completed export |
| `POST /api/browser/jobs/{id}/reconcile` | Reads existing receipt/export only; never opens StackEdit or repeats typing/export |
| `GET /api/browser/jobs/{id}/export` | Same-owner, visible-context download after independent fixed-slot readback; available even if new-work runtime is disabled |

Observation includes ID, catalog ID/URL, observed page title, heading, one paragraph excerpt, observed UTC time, SHA-256 and version. This is not a claim to have read the entire source document. Review expires after five minutes; an approved execution has a 180-second total deadline. UTF-8 exports are limited to 65,536 bytes. Only fixed `export.md`/`receipt.json` slots are read; links, hard links, special files, unsafe directories, oversized content and mismatched bytes are rejected.

The intent's `destination` is a string; the capability destination is `{id,url}`. A visible job includes `request`, `intent_hash`, lifecycle metadata, `result` and `history`. Hidden list/detail/cancel/reconcile results omit the request and any receipt fields that identify content, title, source excerpts or document name. Hidden observe/prepare/approve/export are rejected. Session revocation and durable personal-context revision changes invalidate authorization, including a hide→show transition between worker polls.

The current experimental store reserves at most 2,000 work-operation fingerprints and then refuses new work with `BROWSER_HISTORY_LIMIT`. Cancellation remains available at capacity, with at most one additional cancel receipt per existing job; different-key repeat cancellations are no-ops and do not grow history. There is no silent pruning, automatic deletion, archive feature or unlimited-history claim. Read-only history/export remains available. This capacity and cleanup recovery are explicit remaining lifecycle limitations.

## Lifecycle, recovery and cleanup

A job moves through `review → queued → running → verifying → succeeded`, or ends as `failed`, `cancelled`, `expired` or `unknown`. Running cancellation may briefly show `cancelling`. Before each fixed action, the worker requests a parent checkpoint; the parent checks the original session, privacy revision, claim token, content hash and deadline, then durably marks dispatch before allowing the action. Only one browser operation runs at a time in one service instance.

A restart fences the old worker claim. An interrupted source read becomes failed; an interrupted destination operation becomes unknown. Neither is silently rerun. Persisted effect evidence can be reconciled against the original execution ID without granting old worker authority. A stale worker cannot overwrite replacement-service recovery state.

The receipt separates three statements:

- `verified` plus `sha256`/`byte_count`: independent readback matches the exact approved bytes and bound application-export receipt
- `browser_close_confirmed`: the worker's normal context/browser close calls returned
- Job `cleanup_confirmed` and result `process_cleanup_confirmed`: supervisor observed its worker/protocol termination without a forced stop or unconfirmed retained pipes

The supervisor does not audit every possible OS descendant. A forced stop, lost cleanup acknowledgment or retained child pipe leaves cleanup unconfirmed. A valid export **does not clear this uncertainty**. Such a job stays `unknown` with `BROWSER_CLEANUP_UNCONFIRMED`, while verified bytes may still be downloaded. Later new-work admission is blocked.

**Recovery procedure:** use read-only reconcile once evidence is available and download an independently verified export if present. Repeating reconcile with unchanged evidence does not increment the job version or rerun the application. If the receipt is missing or mismatched, retain unknown; do not create a second write to guess at completion. If cleanup is unconfirmed, restarting the backend is not proof of cleanup and does not clear the block. This batch intentionally has no automatic override. An operator must inspect/retire the dedicated isolated browser environment, preserve the evidence, and establish a clean environment before a new reviewed workflow. Do not delete an unknown row, kill an arbitrary reused PID or use a security bypass as recovery. A safely attested rearm mechanism remains future work.

Normal confirmed cleanup is recorded even when a privacy/session change prevents publishing an observation result. Observation data is discarded in that case; a permission change alone does not manufacture a cleanup failure. Closing the UI or aborting a request wait is not a server-side cancellation.

## Workspace interface

The owner-only Browser workflow button opens a bilingual modal. It shows the fixed catalog, bounded observed excerpt/time/hash, title/note limits and public/synthetic acknowledgment. Approval shows the immutable content, destination, runtime environment and digest. Readiness is labeled experimental and separately from real application acceptance.

Cancel and read-only verification/download use independent queues; an uncertain approval response need not prevent inspection of an existing export. Downloads are streamed up to 65,536 bytes and their size/SHA-256 are checked before opening. Privacy/session/selection changes reject late download results. Drafts/retry bodies are memory-only; hidden, offline or stale state masks review content and disables approval. Closing the modal does not cancel the server job. Source observation waits up to 75 seconds in the UI to accommodate the worker's 60-second bound and cleanup.

## Real acceptance, without substitution

The [acceptance runner](../scripts/check_browser_workflow.py) invokes FYP's actual BrowserService and separate supervised worker, not the development assistant's browser tools. Use a **new** evidence directory and an already authorized executable:

```sh
uv run --locked --extra browser python scripts/check_browser_workflow.py \
  --chromium /absolute/path/to/authorized/chromium \
  --output /tmp/fyp-browser-acceptance-unique \
  --approve-public-fixture
```

The approval flag is limited to the script's fixed fictional note and one actual observed public Python excerpt at the displayed StackEdit destination. Without it, the script performs the source read and prints/persists the exact review but makes no destination write. A second invocation uses a new workspace; it is not an automatic retry of an uncertain effect.

Acceptance requires all of: no destination effect before approval; actual source DOM observation; real StackEdit UI creation; one actual application download; exact exported bytes/hash; independent artifact-store readback; normal browser and supervisor cleanup; and repeated preparation returning the same effect without a second execution. The output records implementation hashes, actual Playwright/browser versions, state/history and exported-byte evidence. It copies the actual independently read download; it never writes the expected preview as a replacement export. Keep the generated `runtime/` directory out of commits and preserve unknown evidence for operator inspection.

Selectors are derived from the public [StackEdit source at 6dce2a5](https://github.com/benweet/stackedit/tree/6dce2a5e36b755a0c244522b48a06c91a2df0f59), including its editor, explorer, navigation, menus and FileSaver export implementation. That provenance does not prove compatibility with today's deployed app. Selector drift, network denial, download mismatch, CAPTCHA, sign-in or unexpected permissions must stop the fixed workflow; no fallback arbitrary JavaScript/URL/shell tool is exposed. If a live run fails, report the exact boundary and stage rather than claiming a mock or direct-written file as application acceptance.

The focused [tests](../tests/test_browser_jobs.py) deliberately use a clearly labeled fake browser for protocol/state-machine faults and trusted local subprocess fixtures for supervision. They cover approval/idempotency, stale review, privacy/session fences, cancellation, restart fencing, receipt loss, unknown cleanup, hidden HTTP routes, forbidden targets and safe-file boundaries. They are source/contract evidence only. LCU, general cross-application autonomy, authenticated applications, private-data browser tasks and physical devices remain outside this adapter's demonstrated scope.
