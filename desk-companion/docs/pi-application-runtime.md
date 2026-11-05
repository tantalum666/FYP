# Group 2 · Pi application execution

6 November2026. Pi uses the same application jobs, receipts, permissions and Work
as the Mac reference environment. Only the operator-configured process transport
changes. [Current results](../../output/qa/2026-11-06-passwordless-device/verification.md).

## Local runtime

Install Debian's `podman`, `uidmap` and `fuse-overlayfs`, then run the desktop as
the ordinary `desk` user. No root Docker group or rootful API is needed. The
verified ARM64 image is prepared from the existing Dockerfile and can be exported
with `docker save`, transferred through the authenticated management connection,
hash-checked and loaded using `podman load`. Never copy a container with user
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
existing container. It uses `--pull=never`, `--network none`,2CPU/2GiB/256-process
limits and only the three prepared mounts. Existing containers must be inspected
and explicitly started/restarted; no automatic delete/recreate destroys their
application state. It does not install dependencies or change the API service.

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
