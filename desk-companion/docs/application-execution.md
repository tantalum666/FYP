# Group 2 · Bounded application execution

30 October 2026. Chromium source review, LibreOffice Calc edits/recalculation, Writer editing and PDF export now run in an isolated Linux desktop. The [scripted acceptance](../../output/qa/2026-10-30-application-execution/verification.md) includes changed constraints, a saved-but-unacknowledged workbook, process/application restart and revoked authority. It is execution-layer evidence. Autonomous voice planning, production OpenAI integration and unseen variants remain separate gates.

## Responsibility and supported operations

| Module | Owns |
|---|---|
| `application_models.py` | Separate typed `ApplicationJobInput`; bounded cells, formulas, document blocks, PDF/text operations and stored-intent validation |
| `application_runtime.py` | Fixed Docker transport, bounded time/bytes, explicit read-only source directory, hashes and path checks |
| `application_executor.py` | Dependency versions, private staging, independent reopen, atomic publication, immutable download versions and reconciliation |
| `application_bridge.py` | Real UNO/CDP app calls in the owned desktop; no caller code, executable, arbitrary path or URL |
| `application_desktop.py` | Dedicated app profiles and source server inside the isolated environment |
| Existing `JobService` / `PermissionService` / `TaskService` | One queue, approval/version/deadline/cancellation, current authority, operation receipts and task state |
| `ApplicationPreview` / `JobActionCard` / `TaskJobs` | Exact cell/content review, shared action controls, downloads and durable stage projection; no new polling loop |

The original six `JobInput` note/verification actions are unchanged. `application` is a separate action with one of four typed steps:

- `workbook`: create XLSX or update a referenced verified workbook using explicit cell values/formulas. At most six sheets, 500 edits, columns A–X and rows 1–150. Only the documented arithmetic/aggregate/conditional formula whitelist is accepted; no external links, DDE or web functions.
- `document`: create or replace/append to a referenced ODT with title, heading, paragraph, table and page-break blocks. No macros or caller-selected templates.
- `pdf`: export a referenced verified Writer document, optionally replacing a referenced prior PDF. A changed document or output version invalidates the pending operation.
- `text`: exact UTF-8 `.txt`/`.md` output. This is ordinary local file writing and is never labeled a GUI operation.

Sources are explicitly connected `.md`, `.csv`, `.txt` and `.html` files, bounded by count/size. HTML is served locally and read in the dedicated Chromium instance with scripts, connections, forms and external assets blocked by CSP. The model receives source IDs, content, hashes and an untrusted-data flag. Reference text does not grant authority. No repository, controller answers, host home, credentials or Docker socket is mounted into the desktop.

The owner-only tools are `application_sources`, `application_source_read`, `application_job_draft`, `application_task_state` and `application_artifact_read`. Drafting is not approval. Existing Ask first / Full access handling authorizes eligible new requests; the model cannot change that policy. A current task ID/version and stable stage name are required. `source_job_id` and `depends_on` bind verified artifacts, while `sources` binds the input versions.

## Save, check and resume

An application works on `staging/<job-id>/`. It opens an owned copy, saves through the actual app, closes its in-memory document, then reopens the saved bytes. Cell types/formulas/values, untouched cells and ordered document content must match. Every requested sheet is created before formulas are parsed. XLSX sheet-name canonicalization is normalized while absolute cell anchors and quoted strings remain significant.

The final checkpoint rechecks task/permission versions, source hashes, dependent file hashes and cancellation before atomic publication. `history/<job-id>/<filename>` preserves the verified version; `artifacts/<task-id>/<filename>` is the active filename. Partial staging files are not promoted. Cancellation before publication leaves an existing final version intact. A success receipt binds the task, operation marker, executor/scope, app identity, bytes and SHA-256.

PDF verification uses independent Poppler metadata and text extraction. Ordered raw text avoids interleaving wrapped table cells; the complete normalized content and exact operation subject must agree. Visual layout still requires a separate rendered-page check. A text/file hash alone does not establish app execution.

A lost completion or interrupted process becomes `unknown`, never an automatic write retry. Reconciliation reopens the published artifact and recovers the original job receipt. If the app is unavailable, the job stays unknown and can be checked again after reconnecting. The same file hash and modification time establish that recovery did not rewrite it. JSON backup restores active jobs to review and strips authority; it does not bundle the actual office artifacts.

Task stages and latest verified file references are derived from existing jobs. File completion does not complete the parent task. An old verified download remains an immutable prior version; attempting to recheck it against a newer active filename correctly reports a mismatch. Re-read current task state before preparing a dependent change.

## Local ARM64 macOS setup

Prerequisites are installed Colima/Docker, the project's existing Python environment and Node dependencies. This recipe creates a dedicated profile and retains Chromium's sandbox. It changes neither the user's active Docker context nor installed Mac applications. The tested Colima VM uses two CPUs, 3 GiB RAM and 20 GiB disks. Package downloads/image construction need network access; the running desktop uses an internal Docker network.

From `desk-companion/`:

```sh
.venv/bin/python scripts/application_desktop/prepare.py --copy-fictional-inputs
app_root="$PWD/.runtime/app-desktop"
colima start fyp-apps --activate=false --ssh-config=false --ssh-agent=false \
  --cpus 2 --memory 3 --disk 20 --root-disk 20 --vm-type vz \
  --runtime docker --mount "$app_root:w"
docker --context colima-fyp-apps build --build-arg DESK_UID="$(id -u)" \
  -t fyp/application-desktop:20261030 scripts/application_desktop
docker --context colima-fyp-apps network create --internal desk-apps-internal
docker --context colima-fyp-apps run -d --name desk-applications \
  --label fyp.executor=applications --network desk-apps-internal --shm-size 256m \
  --security-opt "seccomp=$app_root/chromium-seccomp.json" \
  --mount "type=bind,src=$app_root/support,dst=/opt/desk,readonly" \
  --mount "type=bind,src=$app_root/inputs,dst=/inputs,readonly" \
  --mount "type=bind,src=$app_root/workspace,dst=/workspace" \
  fyp/application-desktop:20261030
```

Reuse a matching owned profile/network/container on later runs; inspect it before changing it. Do not replace an unrelated profile of the same name. The only VM mount must be `app_root`; do not add the whole repository or home directory. The helper refuses to overwrite a different input dataset. It fetches the [Moby default seccomp profile](https://github.com/moby/profiles/blob/4b8214fc4971e06172938a1f1554ccff6647ee80/seccomp/default.json) at a pinned revision and verifies its canonical JSON SHA-256. Only `clone`, `unshare` and `setns` are additionally allowed for Chromium's namespace sandbox inside this VM. No privileged flag, added capability or `--no-sandbox` is used. Upstream profile/cache stays in ignored runtime storage.

The initial tested VM had a broken `/etc/resolv.conf` link to missing files under `/run/systemd/resolve`. Diagnose with `colima ssh fyp-apps -- readlink /etc/resolv.conf`. Only when that exact missing-target condition exists, recreate the target resolver files inside this dedicated VM with the operator's DNS resolvers; do not change host DNS. Runtime files may need restoring after a VM reboot. This workaround is an environment issue, not an application dependency or a reason to disable isolation.

Internal-network port publishing did not expose noVNC on this host. Use a loopback-only SSH forward through this profile's existing SSH config:

```sh
app_ip="$(docker --context colima-fyp-apps inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' desk-applications)"
ssh -F "$HOME/.colima/_lima/colima-fyp-apps/ssh.config" -N \
  -o ExitOnForwardFailure=yes -L "127.0.0.1:5530:$app_ip:6080" lima-colima-fyp-apps
```

Review `http://127.0.0.1:5530/vnc.html?autoconnect=true&resize=scale&view_only=true`. This is an operator preview of the isolated desktop; it is not a public remote-control service. `start.sh` clears only this container's stale display lock before restarting Xvfb. A clean container restart and fresh app-instance ID were verified. Source-code changes to the bridge can be copied by the prepare helper; supervisor changes require restarting the owned container; image/start-script changes require rebuilding and recreating it while preserving the host workspace.

Set these variables only for the selected FYP process. Keep its core runtime outside the app mount:

```sh
export DESK_APP_DOCKER_CONTEXT=colima-fyp-apps DESK_APP_CONTAINER=desk-applications
export DESK_APPLICATION_ENABLED=1
export DESK_APPLICATION_WORKSPACE="$app_root/workspace"
export DESK_APPLICATION_INPUTS="$app_root/inputs"
export DESK_RUNTIME_DIR="$PWD/.runtime/application-main-01"
export DESK_TEXT_PROVIDER=none DESK_VOICE_PROVIDER=none
export DESK_TEXT_BACKGROUND=0 DESK_MEMORY_EXTRACT=0 DESK_WEB_PUSH=0
```

To stop, stop only `desk-applications` or `colima stop fyp-apps`. Cancel the exact SSH forward with `ssh -O cancel -L ...` using the same profile config; do not kill Colima's shared control master. Preserve runtime artifacts/core database when work is to be resumed.

## Reproduce the controlled acceptance

Use a fresh core runtime and report directory for a new case. The input copy is fictional. The runner does not import the reference solver or controller answer files and sends no email. Its scripted decisions and direct calendar service calls are explicitly test infrastructure, not an autonomous agent.

```sh
.venv/bin/python scripts/application_acceptance.py --run-real-apps --phase initial \
  --runtime .runtime/application-main-01 --report ../output/qa/your-case
.venv/bin/python scripts/application_acceptance.py --run-real-apps --phase revise \
  --runtime .runtime/application-main-01 --report ../output/qa/your-case
# Expected exit 73: revised workbook published, completion not acknowledged.
docker --context colima-fyp-apps restart --timeout 3 desk-applications
.venv/bin/python scripts/application_acceptance.py --run-real-apps --phase recover \
  --runtime .runtime/application-main-01 --report ../output/qa/your-case
```

Wait for the owned desktop/UNO bridge to become ready before recovery. An unavailable read remains recoverable; it must not cause another write. A deliberately repaired failed preparation can use a new `--attempt` identity. Previously successful identical steps are read back and reused; unknown work must be reconciled. Keep failed attempt logs.

The main path checks Aster HKD 809.60 initially; no feasible 40-copy colour proposal under HKD 1,000; Delta HKD 669.24 after the scripted black-and-white clarification, including 10 extra minimum-order copies. It checks nine unique tasks/seven open/14.5 hours, five total calendar events, and the same second rehearsal ID revised to Thursday. A queued write after revocation is rejected. All API-model budgets remain closed in this run.

## 31 October: persistent Work integration

[Application Work](application-work.md) now admits selected tasks/inputs and coordinates the existing queue through the registered tool bridge. Independent results return to later decisions; existing job approvals and full-permission versions remain separate from the model. Current and superseded immutable files are verified separately. Supported formula syntax is normalized before UNO execution, retaining the original approved request. The new [acceptance](../../output/qa/2026-10-31-personal-agent-cross-app/verification.md) adds a four-job real-app run with offline decisions, changed constraints and lost-save recovery, plus web/phone review/cancel/download.

## Remaining gates

The ordinary HTTP assistant still stops after one effect-producing tool. The separate admitted Work flow now supplies bounded model coordination over the real executor; its live-model quality has not been tested in this milestone. The normal App has not switched to OpenAI. Run offline provider/tool-loop integration and held-out source/layout/cancellation variants before a newly scoped paid voice comparison. Real microphone quality, voice-driven planning, general GUI browsing/clicking, native iOS touch/keyboard and Pi/Wayland acceptance remain open. No CI, physical output, purchase, message or school submission is part of this milestone.
