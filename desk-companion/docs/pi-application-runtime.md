# Group 2 · Pi application execution

6 November2026. Pi uses the same application jobs, receipts, permissions and Work
as the Mac reference environment. Only the operator-configured process transport
changes. [Current results](../../output/qa/2026-11-06-passwordless-device/verification.md).

## Local runtime

Install Debian's `podman`, `uidmap`, `fuse-overlayfs` and `catatonit`, then run the desktop as
the ordinary `desk` user. No root Docker group or rootful API is needed. The
verified ARM64 image is prepared from the existing Dockerfile and can be exported
with `docker save`, transferred through the authenticated management connection,
hash-checked and loaded using `podman load`. Docker/containerd may report an OCI manifest ID while Podman reports the image configuration ID; compare ARM64 architecture, configured user and all RootFS diff IDs with the verified source image, then use the inspected local Podman ID. Never copy a container with user
secrets or mount the whole project/home directory.

The current image's `desk` identity is501:1000; Pi's host identity is1000:1000.
`--userns=keep-id:uid=501,gid=1000` maps the owner into that non-root image account.
Inspect a rebuilt image before choosing these values. This follows the
[Podman user-namespace contract](https://docs.podman.io/en/latest/markdown/podman-run.1.html).

Prepare only `~/.local/share/desk-companion-apps`, with `support`, read-only
`inputs` and writable `workspace`. The existing preparation helper accepts this
exact owner-controlled path as well as a checkout's `.runtime`. A verified
`moby-default.json` cache can be transferred for offline preparation; its pinned
canonical hash is rechecked. The existing narrow Chromium namespace allowance
is retained. Chromium's sandbox remains enabled.

```sh
python3 scripts/application_desktop/prepare.py \
  --runtime "$HOME/.local/share/desk-companion-apps"
sh scripts/pi/start_applications.sh sha256:YOUR_INSPECTED_IMAGE_ID 501 1000
```

The launcher refuses root, unknown image tags, non-owner/symlink paths and an
existing container. It uses `--pull=never`, `--network none`,2CPU/256-process limits and a2GiB cap when the host exposes the memory controller and only the three prepared mounts. Existing containers must be inspected
and explicitly started/restarted; no automatic delete/recreate destroys their
application state. Initial keep-id storage mapping can take several minutes; use a bounded background installer and inspect completion instead of killing it at the normal per-job35-second limit. It does not install dependencies or change the API service.

## Connect the existing executor

Set only on the chosen Desk Companion service:

```ini
DESK_APP_ENGINE=podman
DESK_APP_CONTAINER=desk-applications
DESK_APPLICATION_ENABLED=1
DESK_APPLICATION_WORKSPACE=/home/desk/.local/share/desk-companion-apps/workspace
DESK_APPLICATION_INPUTS=/home/desk/.local/share/desk-companion-apps/inputs
XDG_RUNTIME_DIR=/run/user/1000
```

`ApplicationBridge` uses a fixed local `podman exec` command and JSON stdin.
Model data cannot select engine, container, flags, environment or shell command.
Changing engine invalidates previously admitted application scopes. The original
Docker scope encoding stays compatible with existing jobs.

The runtime browser reads explicitly selected local HTML, with scripts/forms and
external connections blocked. This milestone does not provide arbitrary websites,
logged-in shopping/email accounts, payment or unrestricted host-desktop clicks.
Those require separate connectors/browser capabilities and end-to-end validation.

Use the existing offline Work acceptance on Pi, including a changed quantity and
budget, a lost save acknowledgement, application restart, reconciliation and
independent file readback. Scripted planning is not evidence of live model quality.
Keep QA state separate from the owner's actual database and preserve failed runs.


The inspected Pi kernel currently exposes cpu/pids but no memory controller.
The launcher refuses this by default; this deployment explicitly uses
`DESK_APP_ALLOW_UNBOUNDED_MEMORY=1` after recording that limitation. It retains
CPU/process limits, non-root execution, Chromium sandbox and offline mounts.
There is no enforced container RAM cap on this host. No boot-argument change or
reboot was made to work around it. Future installation must not silently treat
an unsupported resource limit as active.


## Service lifecycle

The launcher uses Podman's init to forward termination signals and reap child
processes; inherited proxy variables are disabled. Install the supplied
`scripts/pi/desk-applications.service` in the owner's systemd user directory.
After the initial shell-started instance has no active jobs, stop that instance,
run `systemctl --user daemon-reload`, then enable/start `desk-applications`.
The API can Wants/After this optional unit while retaining NoNewPrivileges.
Restart the service when changing the application supervisor; saved artifacts
remain in the owner-mounted workspace. Ordinary job failure is not a reason to
recreate the container or erase its output directory.
