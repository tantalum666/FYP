# Group 2 · Current handoff

25 November 2026, Hong Kong. Public `main` remains `fc3b8d2af57b4b581a9caefc18ccc3d5fe3be87d` (PR #157). [Product](product.md) · [decisions](decision-log.md) · [work history](work-log.md).

## This slice (#161)

The normal Mac Web and installed iPhone Simulator run application `83bcf577`. Desktop Tasks keeps its list beside the selection, mobile Tasks opens one detail at a time, and routine notices live in the dedicated Inbox. On the normal desk the original 17 updates remain accessible and the Tasks title is now 27.5 pixels from the top. [Workspace release and screenshots](output/qa/2026-11-25-workspace-redesign/verification.md). Home pages long speech into at most two visible lines. The normal account retains ordinary written exchanges and final completed voice transcripts. The standing worker checks Gmail without an open page, restores dated suggestions against the current grant and keeps first alerts pending through quiet hours. OpenAI-assisted research was authorized through 24 November; the dated allowance is now closed. Local explicit mail cues remain available. The 20:15 read returned ten previews; reopening the ordinary conversation showed three revalidated earlier suggestions with original Gmail links. Chrome has one active subscription. Older browser queue rows do not prove an on-screen alert; newer releases distinguish a successful push-service response. [Normal account and verification](output/qa/2026-11-25-proactive-mail/verification.md). The Mac must be awake and online. GPT-6.2 Sol handles text and research, with GPT-Live-1.1 and A3 v9 for speech. [Release and owner-scope evidence](output/qa/2026-11-24-continuity/verification.md).

## Four-way + live-owner cleanup closeout

UI port failures fixed on #158/`70accc16` and #159/`1f760a41`. Remaining `test_live_owner_page` `COMPUTER_CLEANUP_REQUIRED` was **not** Vite contention: old `_kill_chrome` kill-all fallback SIGKILLed the worker before cleanup; product blocker was correct; screen already returned `BROWSER_PAGE_LOST`. Chrome-only fix + regression on #158 tip **`0e9ea44a`**. Fresh local four-way tip **`0234fc1ebb`** (main→158→159→160→161): backend **3082 passed / 1 skipped / 0 failed**; frontend **442**; four Chrome UIs **4 passed** @1440+320. Prior trees `43b82c75` / `23d9f44a` preserved. No GitHub merge.

Per-PR heads: #158 `0e9ea44a` · #159 `1f760a41` · #160 `d8aad9fb` · #161 product `be5cfaf3` / notes tip after this commit · #162 `3079cddf` (FastClient active budget, from main).

## Running software (unchanged this slice)

Normal Mac Web and Simulator still run application `b759950c`. Defaults stay GPT-6.2 Sol / GPT-Live-1.1 / A3 v9.

## Not done

No GitHub merge, CI, deploy, Pi/hardware, live mailbox, paid model, or feature import across #158–#160 beyond the harness fixes above.

The standard storefront is the WooCommerce sandbox. Stripe’s original test-mode charges and refunds were read independently on isolated merchant copies. The separate Link recurring test authorization has an issuer-fixture compatibility issue. eBay’s developer registration review remains pending. [Marketplace evidence](output/qa/2026-11-20-overseas-shopping-sandboxes/verification.md) · [eBay follow-up](output/qa/2026-11-21-shopping-next-step/verification.md). The organisation's billing, keys, customer data and operator allowances are kept outside Git. Previous paid acceptance trials retain their original closed status.

## Hardware localisation

The standalone ArUco demo tracks ID 4 in pixels or uses the measured L-shaped markers 0, 1 and 2 for table-plane coordinates. The browser shows centimetres in L mode. The API and 37-column browser CSV store physical coordinates in millimetres. Camera calibration, obstacle accuracy and robot operation still require a physical trial. The hardware team’s next measurement is the two marker-centre distances with the camera fixed, followed by a comparison against ruler positions. [Hardware module and printable markers](research/2026-11-24-aruco-localisation/README.md) · [Synthetic tracking and packaging checks](output/qa/2026-11-24-aruco-progress/verification.md).

**Next step** — When the original Pi comes back on its pinned owner relay, apply its saved update from `92acac8e` to `83bcf577` and verify its existing store, accounts, A3 profile and kiosk build on the device.
