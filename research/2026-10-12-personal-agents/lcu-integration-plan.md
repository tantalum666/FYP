# LCU and a real FYP cross-application executor

Research date: **2026-10-12 UTC**. Public LCU source pinned to **`146fe73fe08bf034756b91903269f6806eac2290`**. Research and design only: no LCU installation, execution, desktop attachment, credential setup, browser launch retry, paid call or security-setting change was performed.

## Recommendation

1. Implement an additive **FYP-owned typed browser worker** using the Playwright Python library for the first genuine existing-application workflow. The FYP service, rather than a developer’s browser tool, must own execution, approval, artifacts and verification.
2. Keep **LCU as an optional later native-desktop backend**, conditional on an explicitly provisioned isolated desktop, verified runtime provenance, active confinement and correct approval/lifecycle integration. It provides broad native computer control, not the narrow policy boundary FYP needs by itself.
3. Develop source, schema, persistence and policy tests in the current cloud. **Actual browser execution is presently blocked:** the parent verified a sandbox socket `Operation not permitted` failure in both ordinary and permitted escalated launches. Do not retry with weaker flags or infer usability from an installed Chromium binary. Use the existing authorized Mac QA task for real acceptance once the FYP adapter exists and prerequisites are checked. A job-owned browser/context is not an isolated Mac or desktop; the test must record actual sandbox and network-boundary readiness.

Detailed supporting reports: [LCU security/provenance](lcu-security-provenance.md), [browser/desktop options](bounded-browser-options.md), [Grok product gaps](grok-capability-gap.md).

## 1. What LCU actually provides

LCU is third-party MIT-licensed transport/setup glue that reuses the **locally installed official ChatGPT application’s proprietary CUA runtime**. It is not an official public OpenAI desktop API, hosted VM, independent open-source CUA engine or free model service. No sign-in is required for its local runtime, but the chosen planning model/harness is separate. Its current thin distribution does not grant a right to redistribute the required proprietary application/runtime. Review those terms separately before product distribution. [Repository](https://github.com/amontlabs/lcu/tree/146fe73fe08bf034756b91903269f6806eac2290), [license](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/LICENSE), [installation](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/INSTALLATION.md)

The selected app supplies screenshots, accessibility, browser behavior, input, JavaScript execution and original instructions. LCU’s adapters integrate this runtime with Codex, Claude Code, Pi, Oh My Pi and Hermes. This supports **host/model interchange at the transport layer**; it does not make every model equally capable of vision, planning or reliable tool use. A text path pointing at saved audio is not proof of audio delivery to a model. [Adapters](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/ADAPTERS.md#same-case-result-forwarding)

### Platform fit

| Platform | Required environment | FYP consequence |
|---|---|---|
| Linux arm64/x64 | Ubuntu 24.04-compatible glibc, active X11 and D-Bus, installed supported ChatGPT app | A headless FastAPI host is insufficient. ARM64 support is not evidence of acceptable Raspberry Pi performance |
| Apple Silicon macOS | Signed official app and existing approved Accessibility/screen-recording permissions | Possible later isolated acceptance target; FYP’s executable needs its own actual permission state |
| Windows 11 x64 | Candidate/historical path | Not a current supported delivery target in the reviewed installation guidance |
| Intel Mac, native Wayland, musl | Unsupported in current LCU guidance | Do not promise these by confusing product-client platform support with LCU runtime support |

“Pi” in LCU’s harness list is the coding-agent framework, not a Raspberry Pi deployment claim. LCU does not create a desktop. Its session helper discovers exactly one XFCE desktop belonging to the calling UID, or requires explicit direct-session configuration. It refuses a different account. [Session source](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/lcu/session.mjs)

## 2. Actual public lifecycle and schema contract

This is the verified host contract, not an invented typed screenshot/click API:

| Stage | Public code/docs establish | FYP obligation |
|---|---|---|
| Discover runtime | Resolve installed app/runtime and required desktop/session | Record exact app, runtime, LCU and platform identity; fail closed on drift or missing prerequisites |
| Connect | `createCuaClient` starts a fixed argv through MCP stdio; initialization then `listTools` | No caller-supplied executable, args, environment or working directory |
| Discover tools | Forward the installed runtime’s original **`js` and `js_reset`** descriptors | Schemas are runtime-discovered, not a stable vendored collection of desktop RPC schemas |
| Instructions | Original initialization instructions and first-call guide are authoritative for direct model use | Do not omit required policy/instructions or recreate private prompts from assumptions |
| Observe | Documented first call can be `cua.getState()`; runtime exposes state/screenshot/application and browser guidance | Capture real inventory and observation time; select targets from actual identity, not guessed titles/IDs |
| Act | Generic `js` reaches original runtime APIs; results retain `content` and `isError` | Keep generic code behind trusted mediation; expose typed operations to FYP’s planner instead |
| Elicit | Original native-app/browser approval request is delivered to the host | Render the actual requested scope and return actual human answer; absent handler cancels |
| Identity | Real `sessionId` and `turnId` required; call/thread/model metadata can be included | Persist run/step identity; do not fabricate host identities, permissions or provider provenance |
| End | `turnEnded` accepts `Stop`, `Interrupt`, `SubagentStop`, then close | Keep cleanup separate from business success; block later actions if cleanup remains unresolved |
| Reset | Client interrupts tracked turns before resetting runtime; next call gets fresh upstream identity | A reset is not a harmless read and is not durable recovery of a lost business task |

Primary code: [shared client](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/adapters/client.mjs#L538-L765), [instruction delivery](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/INSTRUCTIONS.md), [host contract audit](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/verification/harness-contract-audit-2026-09-25.md).

An illustrative host-only call shape from the public client contract is:

```js
await client.connect();
const descriptors = client.publicTools();  // actual installed js/js_reset schemas
const result = await client.call(
  'js', { code: 'await cua.getState()' },
  { sessionId: actualRunId, turnId: actualStepTurnId, signal }
);
await client.turnEnded({ sessionId: actualRunId, turnId: actualStepTurnId, event: 'Stop' });
await client.close();
```

This snippet is a source-based contract illustration, **not executed code or a proposed model-facing FYP tool**. Exact nested computer methods and arguments must be taken from the installed runtime’s actual guide and validated after authorized setup. A repository test fixture’s simplified schema must not be presented as the production schema.

Additional lifecycle details matter:

- Connection/tool discovery permits 120 seconds. Normal tool timeout is at least 120 seconds; an explicit JS timeout extends the bound by 30 seconds. Pending human approval pauses the tool deadline, with an independently abortable long approval wait
- FYP must still impose its own bounded approval expiry and job budget; otherwise runtime waiting can outlive the intended task window
- A turn-ended handler may time out while cleanup continues. The client exposes `LCU_TURN_CLEANUP_TIMEOUT`; subsequent actions must not start merely because the chat turn ended
- macOS `controlStatus`/`controlStop` use a private per-client socket and exact session/turn/app identity. They are not supported uniformly on Linux. A stop acknowledgment is not proof no key was delivered immediately beforehand
- Browser selection needs real browser/profile/tab inventory and fresh tab state. Convenience selection guidance is not an enforceable permission boundary
- LCU session/cross-turn continuity is not a persisted queue, checkpoint graph, idempotency journal or recovery oracle. FYP must own those

Sources: [timeout and approval handling](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/adapters/client.mjs#L14-L94), [turn cleanup/control](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/adapters/client.mjs#L695-L765), [request context record](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/verification/request-context-2026-09-27.md).

## 3. Security and provenance admission gates

Generic LCU tool approval is **too broad** for a strict no-shell FYP workflow. Linux has no native per-app approval; desktop control can reach terminals even if no shell tool is listed. Current Linux confinement separates a sandboxed JavaScript kernel from an unsandboxed trusted Sky worker. The kernel remains confined only where the sandbox is available; unavailable bubblewrap can leave both processes direct/unsandboxed. A read-only root does not establish secret-read isolation, and kernel network isolation does not constrain a browser controlled through Sky. [Sandbox contract](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/ADAPTERS.md#linux-sandbox-state)

Do not treat `lcu doctor` exit 0 as proof of active confinement. Its sandbox report does not itself fail readiness. `LCU_REQUIRE_SANDBOX=1` is a repository-test gate, not a verified production launch switch. Tested-version entries are informational: upstream explicitly permits unknown pairs and does not hash the installed Linux tree against those package digests. [Doctor](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/lcu/doctor.mjs#L184-L230), [tested versions](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/tested-versions.json)

The current October 12 macOS verification reports real Calculator/Finder/TextEdit work and cleanup, but one TextEdit setup flow used shell-assisted opening. Do not label that entire flow shell-free. Historical broad parity summaries are older than the current implementation. Consult dated per-platform tests, not one blanket badge. [Current macOS record](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/verification/macos-chatgpt-26.1007-2026-10-12.md)

Conditional future admission requires all of: explicit supported isolated environment; reviewed official app provenance and exact versions; active confinement independently checked; no personal profile/secrets/host-home mounts; trusted broker with fixed actions and target checks; approval UI outside the controlled desktop; bounded cleanup; denied-terminal and denied-target tests. Runtime schema drift, unavailable sandbox, unresolved cleanup or new permission prompts must disable the adapter, not downgrade security. Installation from this third-party repository remains a distinct authorization prerequisite; this study grants none.

## 4. Fit with the existing FYP source

The current `ComputerExecutor` interface is `execute(job, checkpoint)` followed by `verify(job)`. `JobService` owns exact-intent approval, task-version fencing, one run lock, restart-to-unknown, conservative write handling and read-only reconciliation. These are useful invariants to retain.

It is not yet a long-running agent worker: execution is synchronous, current approvals give a fixed 60-second execution deadline, receipt validation is specialized to notes and demo records, and cancellation cannot forcibly terminate a blocked process. There is no persisted plan/step graph, GUI lease, screenshot artifact lifecycle or authenticated remote executor protocol. Simply adding `browser` to the four-action enum and calling a large script would hide these gaps.

Recommended additive design, coordinated with the durable-run design owner:

1. **AgentRun** owns the goal, current plan version, budgets, active stage, user attention and verified partial outputs. It references existing task IDs without marking their business completion automatically
2. **Typed steps** carry code-owned capability/adapter versions, exact source/application/environment identity, approved content digest, observation precondition, expiry and effect classification
3. **Trusted execution broker** validates the persisted grant immediately before effects, issues a single-use dispatch/lease token, and gives the planner no shell/JS/permission APIs
4. **Dedicated worker process** owns a fresh browser/context or an admitted desktop session; supervision has bounded close/kill for only owned processes. The API and physical-stop paths remain responsive
5. **Effect journal** separates prepared, dispatching, observed, verified and unknown. Crash after dispatch requires reconciliation. Read-only work can be repeated within budget; ambiguous writes cannot
6. **Artifact/verifier service** independently reads application-produced output, records digest/size/type/source links and maps it to the approved step. A generic executor success string is insufficient
7. **Owner review and progress UI** show scope and evidence; hidden/stale/offline private context suppresses sensitive content and approval while retaining stop/reconcile metadata

These are proposed application contracts, not claims about LCU or Grok Bot architecture. Keep existing notes/demo actions and their regression seam unchanged; do not silently relax their expiry or receipt requirements.

## 5. Practical first workflow and typed vocabulary

Use a reviewed catalog entry for one public source and an existing document editor such as **StackEdit**. The catalog owns exact origins, expected paths, permissible asset endpoints and adapter version; the model cannot supply arbitrary URLs or selectors. Initial public/synthetic content avoids transmitting private information.

Proposed operations are `observe_source`, `prepare_source_brief`, `create_editor_document`, `export_document` and `verify_export`. These are **new FYP names**, not upstream APIs. The planner may select an allowed source or compose an approved bounded draft; it cannot inject code. UI interactions are reviewed adapter code using semantic locators, current state checks and fixed operations.

The real acceptance flow:

1. Within the user-authorized read scope, FYP opens the approved source, verifies final identity and records observed heading/title/source evidence
2. FYP prepares the exact brief from those observations and presents its full preview/digest, destination app, output format and environment for owner approval. A later bounded-transformation grant would be a separate explicit contract; it is not silently substituted for today's exact-content approval
3. In a distinct clean destination context, FYP operates the actual editor UI, creates the named document, inserts that approved text and invokes the application's export
4. Export lands in a preallocated application-owned artifact slot; an independent parser verifies required fields, Unicode, source link, bytes and hash
5. UI shows the verified result and evidence, while a separate test confirms target state and owned-process cleanup. Only the independently retained export is durable: the nonpersistent editor context and its local workspace disappear on close

No direct generation of the final file, fake app routes, injected editor state or self-authored CRUD page may replace the application action. Exact current UI selectors, no-login behavior and asset/service-worker requirements are **unverified prerequisites**, not completed acceptance. If the live app cannot meet the boundary, stop and report; a pinned unmodified upstream local app is a separate provisioning option, not a silent substitution.

Use fresh nonpersistent contexts, `chromium_sandbox=True`, no inherited profiles/credentials, no security-bypass flags, and default-deny reviewed requests. Block unexpected navigation, popups, frames, service workers, WebSockets and imports. Downloads are denied except for one explicitly approved artifact export in the dedicated destination context; cancel unexpected downloads and independently validate count, type, path, size and hash. Browser request routing is defense in depth, **not a complete network sandbox**, especially across redirects and browser-process traffic. A strict egress guarantee needs an already approved external boundary; do not change OS/network policy to manufacture it. See [browser comparison](bounded-browser-options.md) for primary Playwright sources and limitations.

## 6. Verification and stopping criteria

### Cloud source/contract work

Cover exact-target normalization, operation/schema versions, stale plan/approval, hidden context, hostile source-as-data, replaced observations, duplicate dispatch, restart and lost receipt, budgets, cancellation races, download/path collisions, verifier mismatch and unavailable backend. Fake transports prove policy/state behavior only.

### Authorized real application acceptance

Run the FYP adapter itself, record exact commit/adapter/browser versions, source and destination identity, real action trace, export and independent digest. Require approval-before-effect and one output. Inject one read-only transient failure, one target denial, one cancel-before-write and one acknowledgment-loss-after-export at the FYP adapter/transport boundary; never alter the third-party app to simulate success or duplicate the export blindly. Bind the real download event and artifact to this run, rejecting stale files and any final Markdown generated directly by the adapter. Show the same source-to-output dependency and cleanup in actual screenshots/logs without unrestricted HAR or sensitive state. If no hard external egress boundary exists, a routing-only test must be labeled limited public/synthetic-data acceptance, not a strict confinement pass.

### Breadth after the first path

Test legitimate variations and a bounded replan rather than only one recorded sequence. Add a second existing application/workflow after the first is stable. Measure outcome verification and correct blocking separately from model planning quality. A model-free deterministic pass is a necessary executor proof, not a claim of novel-task autonomy.

### Current verified limit

The first checkpoint’s actual HTTP/SQLite record proof remains valid but limited. LCU has not been installed or run here. Real browser work in this cloud is blocked. Mac acceptance has not yet validated this proposed new adapter. No paid model, user account login or hardware behavior was tested. The stopping condition for this research is a reviewed implementation/acceptance contract with named prerequisites; the stopping condition for implementation is a real FYP-owned application result, not this document.

## 7. Coverage ledger

Core public review covered README; full ADAPTERS, INSTRUCTIONS and host-contract audit; complete session launcher and tested-version record; shared client initialization/timeout and connect/call/cleanup/control sections; relevant request-context verification. The security review separately covered installation, license/provenance, runtime/platform/doctor/sandbox implementation and dated live-test records, with its exact scope listed in [that report](lcu-security-provenance.md). The proprietary original runtime and every repository file were not audited.

FYP follow-up reread current architecture and computer-job contract, implementation plan/checkpoint report, registry, notes executor and job execution/recovery path. Prior project-wide Markdown reading gate and source/QA evidence remain in the repository’s October 12 records. A supplemental line/hash ledger accompanies this research; it does not claim unread ranges or truncated output as EOF.
