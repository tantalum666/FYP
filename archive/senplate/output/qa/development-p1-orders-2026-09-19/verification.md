# Senplate M1.1 verification — 19 September 2026

Status: **LOCAL_PROTOTYPE_VERIFIED**. This report covers the menu / QR / cart / order / reservation / fulfillment batch, on top of P0. It does not certify real sensors, food recognition, nutrition, commercial savings, an external deployment or a school submission.

## Scope and authority

The user requested the next batch. The existing handoff routed it to M1.1. Default English and optional Simplified Chinese, the selected V7 plain bowl, one station and Group 2 remain. No agents were delegated. All 80 existing project Markdown files, 7,017 lines, were fully read before implementation; [reading record](reading-record.json) records 51 batches, ranges and completion. Compaction used focused recovery rather than repeating that read.

Before modification, the owned PostgreSQL demo was backed up to `.runtime/backups/p0-before-p1-20260919.dump` and source to `.runtime/backups/p0-code-before-p1-20260919.tar.gz`. Both are local private backups. Additive schema migration retained P0 runs and records. The backend test fixture only resets the guarded `senplate_test` database.

## Backend and build evidence

- `uv run pytest -q`: **33 passed**, 18.37 seconds, including 15 P0 and 18 new order cases. Two dependency deprecation warnings remain (Starlette/httpx and the AnyIO BlockingPortal alias).
- After tightening pickup codes to six ASCII digits, `uv run pytest -q tests/test_orders.py -k pickup`: **1 passed, 17 deselected**. This is a targeted rerun of an existing test, not a 34th test.
- `uv run ruff check services/api tests scripts/dev.py tools/simulator/client.py`: passed.
- Web `npm run build`: TypeScript and Vite production build passed; final generated JS approximately 280.22 kB, CSS 18.28 kB.
- iPhone Simulator build/run and eight individually staged XCTest cases passed. These tests share a live service and require the inputs below; do not run all eight concurrently as isolated tests.
- Generic `iphoneos` unsigned build passed, including the non-Simulator AVFoundation implementation. [Build log](ios-device-compile.log). Nonblocking warnings: no App Intents metadata dependency and the existing portrait/full-screen orientation configuration. This build is not a physical-device installation or camera test.

Backend cases cover concurrent measured and manual reservation, all-or-nothing acceptance, price snapshots and quote versions, stale admin stock edits, cancellation versus portioning races, unpublished / self-service / stale items, owner privacy, role revocation, idempotency, one active measured serving window, event ordering and non-reuse, multiple scoops, manager variance review, open-order session guards, malformed payloads, and pickup code throttling.

## Real local cross-client flow

The live demo run was `1807c798-872f-469f-b88c-db49050f5455`, starting at 2,000 g. Web changed service from buffet to staff portioning. The iPhone customer created a cart of 3 × 100 g chicken and 1 salad, at HK$90. Cart contents survived app termination. Web changed salad from HK$18 to HK$19. The iPhone kept the original draft and required **Use latest menu & prices** before submitting at HK$91.

The resulting order was `ca71ce95-9485-4ab0-8417-543f131ed061` / #001. Kitchen acceptance was exercised with a held HTTP 200 response: the request committed, but the response was held until the client timed out. A later explicit `Fetch.failRequest` could not address the already-aborted interception. The resulting uncertain-operation UI was observed; **Check and retry** recovered the original operation, with one order and one acceptance history entry. The interception patterns were cleared. This proves the Web timeout/recovery path; it does not prove native iPhone network fault injection.

| Observed checkpoint | Physical S | Reserved R | Available to promise | Manual salad stock / reserved |
|---|---:|---:|---:|---:|
| Acceptance recovered once | 2,000 g | 300 g | 1,700 g | 12 / 1 |
| 100 g + 200 g removed, before verification | 1,700 g | 300 g | 1,400 g | 12 / 1 |
| Both events linked, ready | 1,700 g | 0 g | 1,700 g | 11 / 0 |
| Correct customer code collected | 1,700 g | 0 g | 1,700 g | 11 / 0 |

An incorrect collection code left the order ready. The correct code displayed on the customer's iPhone completed it. [Machine-readable checkpoints](cross-client-checkpoints.json), [timeout UI](web-reply-timeout.txt), [event selection](web-reconcile.png), [customer ready screen](06-order-ready.png), [collected screen](11-collected-zh.png).

A second local API-created fixture order #002, one 100 g chicken portion, was accepted and portioned in the **work iPhone app**. A new simulated 100 g decrease was selected there and confirmed. It remains ready for collection, leaving 1,600 g and no measured reservation. Switching the manager to personal mode showed no customer orders, proving the observed navigation/cache separation as well as the API ownership tests. The ready order remains available for review; no data was silently deleted to reset the demo.

## Native UI sequence and evidence

All runs used Xcode 26.6, iOS 26.5. Pro is 402 × 874 points; SE3 is 375 × 667 points. The minimum deployment target is 17.0, which was not executed.

| Stage | Actual check | Result / evidence |
|---|---|---|
| 01 | Personal login, code entry, 3 chicken + salad cart, app restart | passed; [cart](02-cart-en.png), [restored](03-cart-restored.png) |
| 02 | Web price change, explicit reprice, submit, authoritative state | passed; [price review](04-cart-price-changed.png), [submitted](05-order-submitted.png) |
| 03 | Ready code, English→Chinese, restart, largest accessibility text | passed; [ready](06-order-ready.png), [Chinese](07-menu-zh.png), [large text](09-large-text-menu.png) / [lower](10-large-text-lower.png) |
| 04 | Collected state hides code; scan fallback and return; restore English | passed; [collected](11-collected-zh.png), [fallback](12-scanner-fallback.png) |
| 05 | Work login, order queue, accept / start portioning | passed; [waiting for weight](13-work-awaiting-weight.png) |
| 06 | Link 100 g event, ready, no employee-visible pickup code, personal isolation | passed; [work ready](14-work-ready.png), [isolation](15-personal-context-isolation.png) |
| 07 | SE3 menu and detail actions in English and Chinese | passed; [menu](16-small-menu-en.png), [detail](17-small-dish-en.png), [Chinese](18-small-menu-zh.png) |
| 08 | `simctl openurl` system confirmation → installed app → correct menu / Dining tab | passed; [menu link](19-menu-link-opened.png) |

Result bundles are retained under the local XcodeBuildMCP FYP workspace. Exported evidence and manifests are in `ios-phase1` through `ios-phase6`, `ios-small` and `ios-deeplink` here. Stage 01 initially failed because the automation used a generic Increment label instead of the stable `dish.quantity-Increment` identifier; fixed and rerun. Stage 04 initially left Simulator camera scanning on an empty capture view; Simulator now explicitly uses the manual-entry fallback, and the case passed. The real iPhone branch still requests camera permission and captures QR metadata; it awaits a physical test.

The Xcode UI-snapshot tool still returned a Simulator translation error; XCTest and screenshots provided the interaction evidence. A CUA coordinate attempt on the system link prompt reported windowNotFound; no unrelated simulator was manipulated. A targeted XCTest accepted the observed system prompt and verified the destination. The Rillora simulator and data were not changed.

## QR, assets and Web UI

[The actual rendered Web QR](web-menu-en.png) was decoded using Apple Vision, producing exactly `senplate://menu/SP-E5B968D0FE`. The same executable also checks four valid and nine invalid inputs against the production Swift parser: [source](qr-check/main.swift). It rejects HTTP links, foreign hosts, credentials, ports, query strings, fragments, multiple path components and non-ASCII lookalikes. This is QR generation / decoding / routing evidence, not a live camera scan.

Web was inspected at 1,440 × 1,000 and 390 × 844 CSS pixels, including manager editing, order actions, QR, English and Simplified Chinese. Narrow-screen navigation labels were shortened visually while retaining full accessibility names. Final narrow layout had `scrollWidth = innerWidth = 390`; navigation targets were approximately 65 × 64.5 pixels. [Narrow orders](web-orders-narrow-zh.png). The browser's first viewport screenshots had an incorrect backing-scale crop; setting the temporary test device scale to 2 produced correct captures. The viewport / scale override was reset afterward.

Three ImageGen dish illustrations were created and inspected, then copied to the Web and iOS bundles. The [manifest](../../../assets/menu/manifest.json) records original files, dimensions and hashes; [chicken prompt](../../../assets/menu/chicken-prompt.txt), [salad prompt](../../../assets/menu/salad-prompt.txt), [soup prompt](../../../assets/menu/soup-prompt.txt) record actual generation requests. No sensor or portion accuracy claim derives from these images. New personal UI text uses a darker muted colour for readability; the original VI source assets were not edited.

Camera implementation checked the Apple primary API constraint that requested metadata types must be supported: [AVCaptureMetadataOutput metadataObjectTypes](https://developer.apple.com/documentation/avfoundation/avcapturemetadataoutput/metadataobjecttypes). Configuration checks `.qr` support before assignment and starts / stops capture on a private queue.

## Remaining scope

M1.1 edits the current three demo items; it does not yet create arbitrary food / recipe / nutrition catalogues, upload dish photos, edit the fixed measured 100 g portion or copy menus between services. Customer and work queues are current/recent views, not full historical reporting. Local generated demo credentials and loopback URLs remain; no production registration, TLS deployment, payments, push notifications or distribution was added.

Personal meal pairing / portions / reference nutrition and school anonymous samples are the next M1.2 batch. Real calibration, camera recognition and Pi runtime remain M2. Physical iPhone / real camera, minimum OS 17, VoiceOver, native network-loss injection and long-duration stress are outstanding. The tested failures do not imply these unperformed checks passed.

Documentation, protected source hashes, local links and identity details are recorded in [closeout-validation.json](closeout-validation.json). Current authority is [product](../../../../../product.md), [handoff](../../../../../handoff.md), and [menu / order contract](../../../planning/2026-09-19/menu-orders-contract.md).
