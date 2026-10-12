# LCU installation, provenance, and security assessment

Research date: 2026-10-12. All repository sources below are pinned to commit `146fe73fe08bf034756b91903269f6806eac2290`. This is source review, not a new installation, runtime test, penetration test, or legal opinion. No repository code was installed or executed, and no permissions or security settings were changed.

## Decision for the FYP agent

LCU is a credible **optional native-desktop execution backend**, with real application operation evidence. It is not a self-contained open-source computer-use runtime, a hosted cloud desktop, or a ready-made bounded-action security layer.

For the FastAPI/Python agent with durable approved jobs, use it only behind a separately owned execution broker and an already provisioned disposable desktop environment. Do not expose its generic JavaScript tool directly to the planner or mistake tool approval for per-application confinement. Do not fix an unavailable sandbox by disabling AppArmor, enabling privileged containers, changing host security settings, or selecting LCU's unsandboxed mode.

A demo HTTP app would not establish this capability. Acceptance needs actual cross-application actions on independently observable native applications, with a file/content oracle, cancellation cleanup, and negative boundary tests.

## 1. What is open source and what must already exist

- The repository's glue, adapters and setup code have an MIT license, copyright Amont Labs. The license does not relicense OpenAI's desktop app, original runtime, instructions, native helper, or proprietary components
- Current release archives are described as thin archives: LCU plus separately licensed setup dependencies, with no OpenAI application payload or copied original instructions
- The official ChatGPT desktop application must already be installed on the machine where LCU runs. LCU discovers and reuses that application; it does not download, install or authenticate it
- No ChatGPT/Codex sign-in is required by LCU's local computer-use runtime. This is not a free model service: a chosen model/harness remains a separate dependency. The ordinary documented harness setup expects an already installed/authenticated harness; a custom scripted MCP client can perform local fixtures without an account-backed model
- LCU runs on the Node supplied inside the app's CUA runtime. Current instructions say Python is not an installation prerequisite
- There is no basis in the MIT license alone to conclude that bundling or redistributing the proprietary runtime into the FYP product, or deploying it arbitrarily, is licensed. Keep the dependency separate and review its own applicable terms before distribution

Sources: [README](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/README.md), [MIT license](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/LICENSE), [provenance](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/PROVENANCE.md), [installation prerequisites](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/INSTALLATION.md#prerequisites)

## 2. Platform and provenance gates

| Platform | Current delivery requirement | Important limit |
| --- | --- | --- |
| Linux ARM64 / x86-64 | Ubuntu 24.04-compatible glibc, existing X11 desktop, D-Bus session, installed official ChatGPT app | No native per-app approval. Native Wayland and musl unsupported |
| Apple Silicon macOS | Signed official ChatGPT app plus user-approved Accessibility and screen-recording permissions | Intel Macs unsupported; grants cannot be established by a successful metadata-only doctor check |
| Windows 11 x64 | Candidate implementation and historical isolated tests exist | Deferred from current delivery, not a supported substitute |

LCU does not create a VM or desktop. Linux session discovery defaults to exactly one existing XFCE session owned by the account. Other X11 environments use direct session mode with the actual DISPLAY, D-Bus address and Xauthority. GTK4 input relies on XTEST and screenshot infrastructure; the translation path also uses local X-Resource/PID-namespace information. A generic headless web server/container is not sufficient.

Linux validates architecture, runtime manifest, expected files/host layout, executable bits, and ownership/writability across the executable runtime and relevant plugin trees. Owners must be root or the trusted account; untrusted group/ACL writes and symlinks escaping the app are rejected. The checks use local account membership and Linux ACL attributes and have documented visibility limits. Crucially, these are structural and filesystem-trust checks, **not authentication of the app bytes**. Linux does not hash/inventory the installed app tree or check it against an allowlisted runtime digest.

macOS validates official bundle/team identity, signatures, arm64 architecture, runtime manifest and recognized host layout. Deep signature verification occurs during install/setup/status/doctor/update and on a changed app generation; subsequent launches reuse the recorded seal and signer checks. The documentation notes that changes which do not change its observed version/build/seal are not deeply rechecked at every launch.

Release checksum sidecars verify correspondence to downloaded archive bytes. This review did not establish an independent reproducible-build or release-signing guarantee.

Sources: [Linux install and app checks](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/INSTALLATION.md#linux), [platform implementation](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/lcu/platforms.mjs#L492-L524), [desktop/session readiness](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/INSTALLATION.md#desktop-and-browser)

## 3. Versions: observed compatibility is not an admission policy

There is no universal minimum ChatGPT app version that establishes compatibility. The date-stamped app version and 0.0.x runtime versions are not semantic compatibility promises. `tested-versions.json` records exact app/runtime/platform/architecture pairs, and `lcu status --json` reports tested, untested or unknown. **Untested and unknown pairs only warn; LCU continues.**

At this commit, the record includes:
- Linux arm64/x64: ChatGPT 26.915.31945 / CUA 0.0.16 and 26.928.31416 / CUA 0.0.27
- macOS arm64: ChatGPT 26.917.62051 / CUA 0.0.16, 26.928.20755 / CUA 0.0.27, and 26.1007.30912 / CUA 0.0.29
- The Oct 5 sandbox record additionally tested Linux x86-64 app 26.930.41038 / CUA 0.0.27 and 26.915.31945 / CUA 0.0.16; do not conflate that evidence with a universal matrix entry

The newest pinned macOS record is Oct 12, using LCU 0.11.2. It reports real Calculator/Finder/TextEdit operations, independent output verification, and reset/turn-end event-tap cleanup. One Finder opening action failed and shell-assisted opening was used before TextEdit editing; therefore that particular flow is not wholly shell-free. The separate Codex run used five LCU calls for Calculator/Finder observation with no shell UI calls, then independently checked the resulting values.

`PARITY-STATUS.md` is dated Sept 27 and `VERIFICATION.md` explicitly labels most results historical v0.2.1. Do not use their historical bundled-payload/install claims as current instructions. `PROVENANCE.md` also retains an older paragraph saying Linux copies the complete app; current installation text and `resolveInstalledLinuxApp` clearly say in-place reuse. Prefer the current implementation and dated specific verification records.

Updates can replace a live app's files underneath a running LCU process. The guide says stop sessions before updating ChatGPT and restart afterward to avoid mixing generations. A reproducible FYP test must pin and record **both** LCU and app/runtime identities.

Sources: [tested pairs](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/tested-versions.json), [version policy](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/INSTALLATION.md#tested-app-versions), [Oct 12 macOS record](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/verification/macos-chatgpt-26.1007-2026-10-12.md), [historical verification](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/VERIFICATION.md)

## 4. Approval layers are different controls

### Harness tool approval

The harness chooses whether the agent may invoke LCU's generic `js` / `js_reset` tools. The optional auto mode preapproves exactly those two tools, not future tools or all server tools. It changes harness configuration; it is not a sandbox.

The adapter table says Claude Code and Codex normally prompt, Pi has no permission system, Hermes has no applicable pre-tool gate registered by LCU, and Oh My Pi defaults to a nonprompting mode. The FYP must implement its own durable action approvals rather than inherit assumptions about an external harness.

### Native application approval

macOS and the candidate Windows runtime ask for native-app approval. Linux does not. The explicit Linux evidence covers listing, focusing and typing into any window without any elicitation. The Oct 5 sandbox test even types into xterm.

Consequently, Linux tool approval grants a much broader action surface than “this approved app/action.” The macOS host-app guard which prevents approving the agent's own terminal/editor host is not a Linux protection. Its implementation depends on native-app elicitation, and the documentation explicitly excludes Linux.

The macOS scope experiment establishes once/session/always response forwarding to the original runtime. A second app still prompts. The “always” check crossed a fresh bridge/session; that particular record did not prove persistence after helper restart or revocation. LCU's later app-management command adds authenticated convenience controls, but its approval list is still an ordinary account-owned file and the guide explicitly calls this a guard rather than a sandbox.

### Chrome site approval

External Chrome control is opt-in and needs the official browser extension plus native-host registration. It preserves provider-origin approvals. The exact-origin shortcut is documented only for Pi/OMP and accepts actual requests for previously approved origins; it cannot lift an existing denial.

This is not evidence that arbitrary native-desktop manipulation of a browser is origin-confined. A Linux native worker can control the browser application UI without the per-app gate. Treat extension site decisions and native desktop boundaries separately.

### Persistence/lifecycle

The cross-turn setting is a lifecycle convenience, not a security boundary. It is stored in an account-editable file. Turn cleanup, cancellation and reset must remain part of FYP execution lifecycle; durable queue status alone does not stop native UI effects.

Sources: [approval boundary and host guard](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/ADAPTERS.md#approval-boundary), [native scope record](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/verification/native-app-approval-scopes-2026-09-25.md), [app controls](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/INSTALLATION.md#manage-approved-apps), [Chrome setup](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/INSTALLATION.md#desktop-and-browser)

## 5. Linux sandbox: useful kernel confinement, broad desktop authority

### History matters

- 0.8.1: where bubblewrap worked, both JavaScript kernel and Sky worker were sandboxed. Seccomp blocked their X11 socket connection, breaking computer use
- 0.8.2–0.9.2: LCU sent a disabled profile to make Sky work; this also left model-authored JavaScript unsandboxed
- From 0.9.3: the kernel remains under the original Codex sandbox, while an identified trusted Sky worker runs outside it
- If bubblewrap/user-namespace availability probing fails, the original runtime still runs both processes directly. Current LCU does not globally fail closed on an unavailable sandbox
- Host-supplied disabled metadata or explicit off mode can also produce an unsandboxed kernel

The current shim recognizes exact launch forms, selected runtime Node and parent `node_repl`, expected private temporary worker files, and the selected trusted service packages. Unknown sandbox invocations are refused. Lookalike workers fall back into the sandbox. This is meaningful fail-closed launch classification, **not** a guarantee that every environment has an active sandbox.

### What the live tests prove

On the tested x86-64 host and runtime pairs:
- Kernel writes to HOME/workspace/tmp/approval file failed
- Direct TCP, X11 and D-Bus connections failed
- Synchronous process spawn failed
- Asynchronous child spawn succeeded, but the child inherited confinement
- Kernel seccomp was active; trusted worker seccomp was not
- Desktop listing, screenshots, xterm input, GTK4 flows and several restart/input checks worked

These checks establish the recorded confinement properties, not complete resistance to sandbox escapes or arbitrary runtime compromise.

A read-only root filesystem is not a confidentiality boundary: do not infer it hides readable user files, app state or secrets. This is an architectural inference from the recorded read-only profile, not a measured secret-read exploit. Likewise, network isolation of the kernel does not imply network isolation of browsers/apps controlled by the trusted worker.

### Preflight traps

`lcu doctor` prints a sandbox-status line but does not fail readiness solely because the sandbox is unavailable. In code, that reporting function returns no failure status; Linux exit 0/2 subsequently depends on window/screenshot readiness. Thus a successful doctor exit is insufficient.

`LCU_REQUIRE_SANDBOX=1` is used by repository test gates to assert sandbox availability. It must not be advertised as a production launcher guarantee: the reviewed launcher/doctor code has no such fail-closed switch. Add an independent application admission test.

The app's AppArmor profile is tied to its original Electron executable and is not a sandbox for LCU's direct Node/REPL path. The guide explicitly says keep Chrome's sandbox and system AppArmor protections in place.

Sources: [sandbox contract](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/ADAPTERS.md#linux-sandbox-state), [shim source](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/lcu/sandbox_shim.mjs), [runtime setup](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/lcu/runtime.mjs#L222-L270), [doctor status and readiness code](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/lcu/doctor.mjs#L184-L230), [Oct 5 live sandbox record](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/verification/linux-kernel-sandbox-2026-10-05.md), [test-only requirement](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/tests/adapter_paths.py#L266-L267), [0.9.3 security release](https://github.com/amontlabs/lcu/blob/146fe73fe08bf034756b91903269f6806eac2290/docs/releases/0.9.3.md)

## 6. Recommended FYP admission and acceptance checklist

These are proposed controls, not capabilities already proved in FYP:

1. Admit only an explicitly provisioned supported desktop VM/account with no personal files, credentials, browser profile, production integrations or host-home mounts
2. Record immutable LCU release/commit and observed official app/runtime versions. Fail closed on unreviewed runtime drift for the prototype even though upstream permits it
3. Verify real kernel confinement in the launched session, not merely doctor exit 0. Refuse no-sandbox/off/disabled/unknown states. If the existing environment cannot support it, report a blocker without weakening security settings
4. Keep generic JavaScript/MCP details inside a trusted adapter. Let the planner request bounded typed operations; map only reviewed operations to backend calls. Reject terminal, shell, launcher, arbitrary-code, permission/settings and authentication targets by policy
5. Validate approved job, current target identity and allowed operation immediately before dispatch. Window titles or IDs alone are not strong app identity; handle replaced windows, focus, modal dialogs, stale observations and changed plans explicitly
6. Recognize the limit: an action allowlist is application mediation, not an OS boundary. Broad UI interaction can still trigger capabilities inside an app. A strict no-shell claim requires negative tests and an appropriately constrained environment, not merely hiding a shell tool
7. Keep the planner/backend control channel and approval UI outside the controlled desktop. Persist approval scope separately; never let the model supply approval responses or mutable sandbox metadata
8. Bound execution time, steps and artifact bytes. Serialize focus-changing operations, cancel/close turns on stop, and verify no residual helper/input activity after reset/disconnect
9. Start with at least two real low-risk applications on the isolated desktop. Save a known artifact through UI, read it with an independent test oracle, and show that a second non-target window remains unchanged. Include deny-target, target-change, missing-sandbox and cancellation tests
10. If Chrome is used, prove a real extension connection, actual approved-origin action and denied-origin behavior. Extension discovery/configuration alone is not proof
11. Report unsupported/unverified applications honestly. GTK4/Qt calls have historically returned success with no effect, so tool success is not task success. Observe the resulting state
12. Do not enable audio, auto approvals, cross-turn behavior, desktop grants or browser permissions merely to make a demo pass; each is a separate authorized choice

## Coverage and evidence limits

Fully retrieved and reviewed for the assigned questions: README, LICENSE, INSTALLATION, PROVENANCE, VERIFICATION, PARITY-STATUS; the required Oct 5 kernel sandbox, Oct 2 sandbox/GTK4 and Sept 25 native-approval records; sandbox_shim, runtime, platforms, doctor; and relevant approval/security sections of ADAPTERS. Also inspected tested-versions, the Oct 12 macOS record, 0.9.3/0.11.2 release notes and adapter sandbox test gates.

The authoritative runtime is locally supplied and not in this public repository. Public source review therefore cannot audit its entire implementation. Upstream records are maintainer-reported tests, not independently rerun here. The reviewed Oct 5 host tests skipped Chrome and real installed harnesses, and their evidence is bounded to named versions/platforms. No claim is made that LCU is available in the current FYP execution environment or that integration has been authorized/performed.

