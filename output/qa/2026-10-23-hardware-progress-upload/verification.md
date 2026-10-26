# Hardware progress upload — pre-push verification

Date: 2026-10-23. Group 2, Xu Ziqian hardware progress. Target: private repository `tantalum666/FYP`. Base commit: `a663d83d28ce9209849cedc332bf7ed107a5a13d`.

## Authority and scope

The user asked to upload current hardware progress and explicitly prohibited deployment, leaving unified deployment to teammates. The user confirmed the repository URL and explicitly allowed reading only task-relevant documents instead of this round's full-repository read. [Reading scope](reading-record.json) does not claim completion of the 132-file inventory.

Upload scope: a [dated hardware handoff](../../../research/2026-10-23-mini-robot-hardware/README.md), the unchanged latest 9-page illustrated catalog, 13 sanitized source records, 22 completeness rows, verification/integration plans and an integrity manifest. README, product, handoff, decision log and work log receive dated documentation updates only. Existing software evidence, roles, historical research and school originals remain intact.

No admissions/coursework files, local runtime data, credentials, private teardown videos, third-party firmware source or restricted mechanical models are included. Old V3 wiring and superseded battery/GPIO diagrams are described as historical rather than uploaded as approved assembly instructions.

## Completed local checks

- Latest PDF copied byte-for-byte; `cmp` passed. SHA-256: `4b225e9baa76c0b130891ba5f90557a0f5425ccf6185b9ff5f16f4a985d45182`; bytes: 9,576,703; Git blob SHA-1: `b7a7153af106a427454c6f38e0a830654957057f`.
- Earlier authoring task rendered and visually checked all 9 pages, with 13 images / 30 links. This upload does not modify/regenerate the PDF, so that visual QA is retained rather than claimed as a new render.
- Source JSON has 13 unique IDs and no `local_image` absolute paths; completeness JSON has 22 rows. Walking-reference subtotal recomputed as US$76.89, not a full budget or live HKD conversion.
- Package-relative Markdown links resolve. New repository links are checked against the remote base tree plus this upload's planned files; no application or deployment paths are edited.
- New package text scanned for local user/temp paths and common private-key/token prefixes: no matches. This is a scoped check, not a claim of a full-repository security audit or a Gitleaks run.
- The current base tree contains no `.github/` workflows or Vercel/Netlify deployment config. The upload uses a separate `codex/` documentation branch and PR, not `main`; no deployment API, workflow dispatch, service startup, firmware operation or merge is requested. External repository webhooks were not independently audited.

## Evidence limits and next step

This upload is a procurement-pre-review handoff, **not** a build-approved BOM. Stock motor breakout/harness, fan, battery, Qi/charger/power-path capacity and protection, cliff-sensor supply/real-desk behavior, mechanics/docking and the HK$2,000 whole-system total remain unresolved. No purchases, real wiring, runtime, cleaning, navigation or charging success is asserted.

No application source changed, so software tests/builds and hardware tests were not run for this documentation upload. Next hardware action: close the finished motor-adapter chain and single-battery/Qi/fan power design before purchases; next software action remains the existing software team's handoff.

This file records **pre-upload** checks. Remote branch/tree and PR read-back must be verified after publication; actual results and links belong in the PR description and local upload receipt, not preclaimed here. The PR is left unmerged for teammates.
