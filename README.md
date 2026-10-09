# FYP · Group 2

**Team repository:** [tantalum666/FYP](https://github.com/tantalum666/FYP) · private · default branch `main`. The repository name is temporarily **FYP**; the current product development name remains **Desk Companion**. Start with the [collaboration and setup guide](CONTRIBUTING.md) to join, clone, run the software and contribute through branches / pull requests.

This repository preserves the complete project work: current and retired code, school deliverables and originals, planning, research, hardware procurement studies, design / brand assets, source delivery packages and QA evidence. User-supplied originals are indexed in [inputs](inputs/README.md). Local credentials, private runtime databases, installed dependencies and build caches are excluded and remain on each developer's machine. Third-party materials retain their own licences and provenance.

**9 October 2026 current direction:** Desk Companion is a personal AI agent with a physical desktop terminal; bounded, real computer/software operation is a core requirement alongside one identity, durable tasks, natural voice and the existing calendar. The fixed-camera posture feedback/reassessment loop remains mandatory. Existing software has local evidence within the [S1–S10 scope](planning/2026-10-02/software-completion-plan.md); a durable, owner-approved local-notes executor and nonblocking voice dispatch are implemented, cloud-tested and locally reviewed. General desktop/LCU control and RIG-Arm/cleaner integration remain unfinished. Read the [Chinese discussion and next-step plan](planning/2026-10-06/personal-agent-discussion-and-next-steps.md) for confirmed requirements, architecture, LCU evaluation, safety boundaries, team work packages and acceptance scenarios. The retired Senplate project remains preserved below.

Read the [active product contract](product.md), [handoff](handoff.md), [software README](desk-companion/README.md) and [operator guide](desk-companion/docs/operator-guide.md). The separate always-on Linux layout follows the [device specification](planning/2026-09-30/device-display-spec.md), while phone and desktop management retain their own layouts. English is the default, with Simplified Chinese available.

**Full-body 3D companion (9 October):** the user requested an anime-style female desktop character. A replaceable licensed pixiv VRM now supplies skinned-body state motion, blinking, playback-driven mouth opening, local previews and clean black / mirrored output. Read the [avatar contract](desk-companion/docs/avatar.md) and [task QA](output/qa/2026-10-09-3d-avatar/verification.md). Character art is a development sample; Pi, remote audio and optical performance remain unmeasured.

**Character art research (10 October):** [the Chinese study](research/2026-10-10-avatar-art/popular-character-study.md) separates recent popularity results from official visual references. The user has retained the silver / soft-tech and dark / urban directions for further design. The [wardrobe study](research/2026-10-10-avatar-art/wardrobe-study.md) and [clothing reference board](research/2026-10-10-avatar-art/wardrobe-reference-board.html) add hosiery, fitted tailoring and mild sensual styling for an adult original character. Four written outfit briefs are ready; no final outfit, concept image or replacement VRM is selected. The licensed sample and application code are unchanged.

**Dot integration verification (9 October):** [local Dot integration QA](output/qa/2026-10-09-dot-integration/verification.md) records 149 backend tests, 15 frontend tests, Ruff, TypeScript, production build and actual desktop / narrow phone / independent display checks. The integration fixes rejected duplicate tool replies incorrectly releasing disconnect cleanup. The [6 October architecture audit](planning/2026-10-06/software-architecture-audit.md) and [cloud QA](output/qa/software-completion-2026-10-06/verification.md) retain their dated results; real voice providers and hardware remain unverified.

**Existing task implementation:** the [Your dot–inspired extension](desk-companion/docs/task-tracking.md) now saves tasks and evidence-backed progress, schedules durable check-ins, prepares confirmable assistant drafts, and exposes them on phone, desktop and the independent desk display. The [UI / UX review and fixes](output/qa/task-enhancement-ux-2026-10-03/verification.md) cover dates, unsaved edits, conflicts, offline state, review clarity and narrow screens. Qwen / Gemini text adapters are optional and disabled by default; no inbox or whole-computer monitoring is enabled.

The current software uses React / TypeScript / Vite, FastAPI and SQLite in `desk-companion/`. Calendar, paired access, posture processing, voice adapters, named output control, file exchange, read-only sharing, backup, Google read-only calendar integration code, Linux installation scripts and an iPhone project are implemented. [Local verification](output/qa/software-completion-2026-10-02/verification.md) records the exact checks and their limits; protocol and replay results do not establish real-device or paid-service performance.

Calendar requirements are preserved in [Part 1](planning/2026-09-29/calendar-part1-functional-scope.md) and its [original teammate list](planning/2026-09-29/calendar-part1-teammate-source.md). The [September development plan](planning/2026-09-29/software-development-plan.md) is historical; use S1–S10 and the current product contract for actual completion. Voice selection remains open; the [6 October update](planning/2026-10-06/personal-agent-discussion-and-next-steps.md) distinguishes current model APIs from complete-agent products. Earlier dated comparisons include [quality / tools research](research/2026-09-29-voice-ai/naturalness-and-tools-review.md), [price research](research/2026-09-29-voice-ai/price-and-value-ranking.md) and a [tentative DGX-1 / V100 route](research/2026-09-28-local-voice/server-deployment-comparison.md). No natural-voice benchmark or school-server deployment is claimed.

School documents are the [English proposal DOCX](<output/submission/2026-09-28/AY26_ProjectProposal_Group 2.docx>) / [PDF](<output/submission/2026-09-28/AY26_ProjectProposal_Group 2.pdf>), [Chinese v3](planning/2026-09-28/desk-companion-proposal-zh-v3.md), and [team log DOCX](<output/submission/2026-09-28/member-breakdown-v2/AY26_Logsheet_Group 2_YuanYuchen_250342840.docx>) / [PDF](<output/submission/2026-09-28/member-breakdown-v2/AY26_Logsheet_Group 2_YuanYuchen_250342840.pdf>). The log lists all three members, with individual attribution retained as a member-review draft. This software work does not update, sign or submit those files.

**5 October hardware research:** [RIG-Arm secondary development](research/2026-10-05-rig-arm/secondary-development-review.md) checks the assembled SKU, official MCP workflows and two fixed firmware commits. The arm is a candidate with replaceable AI paths; its small display and moving snapshot camera do not replace the fixed posture camera or independent calendar touchscreen. A RIG driver, compatible firmware and actual stop / completion behaviour remain to be integrated. No purchase, firmware execution or hardware performance is claimed; upstream code and restricted mechanical model files are not vendored into this repository.

## HISTORICAL: Senplate local prototype and instructions

The material below remains for preservation and can still describe the old local software. Do not use its hardware BOM, brand, or proposal as the current project specification.

**21 September 2026 — supervisor feedback under review:** Marco questioned the need for Gemini 2 and the accuracy of mixed-dish nutrition. The new engineering recommendation is to test RGB plus calibrated weight first, with RGB-D optional, and to ground nutrition estimates in verified batch recipes and cooked yield. [Technical review](planning/2026-09-21/marco-camera-and-nutrition-review.md). This is not yet an approved change of the project's main focus; the existing proposal files below are preserved and have not been revised for this feedback.


A local food monitoring, replenishment, ordering and meal-recording prototype with a native iPhone app, a kitchen workbench, a station display, and a shared API.

**Status — 19 September 2026:** the replenishment loop, M1.1 menu / ordering, and M1.2 personal meals / anonymous school samples run locally. Interfaces default to **English** and switch to **Simplified Chinese**, with a preference saved on each device. The current inputs are explicitly simulated; no physical sensor or trained vision model is connected.

Read [AGENTS.md](AGENTS.md), [product.md](product.md), and [handoff.md](handoff.md) before continuing work. The full reading procedure in AGENTS.md applies to a new work session.

## HISTORICAL School food project proposal

**21 September 2026:** the English, 10-page AY26 proposal is ready for group / supervisor review in both [editable DOCX](<output/docx/AY26_ProjectProposal_Group 2.docx>) and [PDF](<output/pdf/AY26_ProjectProposal_Group 2.pdf>). It covers all seven guideline requirements, the single station with three sequential modes, architecture and algorithms, a measurable evaluation plan, a six-month team schedule, and the 40 / 30 / 30 responsibility split. [Authoring record and scope](planning/2026-09-21/proposal-spec.md).

The team's submission target is **Monday, 28 September 2026**. The supplied Moodle screenshot gives **Tuesday, 29 September 2026, 23:59** as the platform deadline and requests both formats. The longer technical schedule is a proposed team plan, to be aligned with the course timetable. Signatures and review comments remain blank; nothing has been uploaded or formally approved. Both earlier project suggestions remain unchanged. Software status below was last verified on 19 September; this document-only task did not restart services or continue M1.3.

## Run locally

Tested on macOS / Apple Silicon with Python 3.12, PostgreSQL 16, Node 22 and Xcode 26.6. PostgreSQL binaries must be on PATH. Start from this repository directory.

```sh
uv sync --python 3.12
uv run python scripts/dev.py setup
uv run python scripts/dev.py api
```

`setup` creates only the project-owned PostgreSQL cluster in `.runtime/postgres` on `127.0.0.1:55437`. The API listens on `http://127.0.0.1:8799`. Keep that terminal running.

In a second terminal:

```sh
cd apps/operations-web
npm ci
npm run dev
```

Open [the kitchen workbench](http://127.0.0.1:5177). Accounts and generated passwords are in the private, Git-ignored `.runtime/credentials.json` file. Usernames: `manager`, `kitchen`, `viewer`, `personal`; the last two demonstrate read-only access and personal-only access. Passwords and device keys are not embedded in either client.

For iPhone, open [Senplate.xcodeproj](apps/ios/Senplate.xcodeproj), select the Senplate scheme and an iPhone simulator, then Run. The app connects to the Mac loopback API in Simulator. The project uses local simulator signing; physical iPhone signing/network access has not been configured. The deployment target is iOS 17.0, but only iOS 26.5 simulators have been tested. To regenerate the Xcode project after configuration changes:

```sh
cd apps/ios
xcodegen generate
```

In the app, use **Profile → Language** in personal mode, or **Account → Language** in work mode. In the web workbench, use the language selector in the sidebar. Changing language does not change permissions or create another workspace.

## Reproduce the replenishment demo

With the API running, use a third terminal at the repository root:

```sh
uv run python tools/simulator/client.py new
uv run python tools/simulator/client.py consume 300
uv run python tools/simulator/client.py consume 500
```

A new run starts at 1,500 g; the two steps take it to 700 g. The interface offers a 1,000 g **rule-based** suggestion. Accept it, open the task, choose **Start preparation → Mark ready → Begin refill**. The measured amount stays at 700 g through these actions.

```sh
uv run python tools/simulator/client.py add 1000
```

Select the new +1,000 g measurement and confirm it. The batch becomes Completed and the remaining amount stays at **1,700 g**. Confirmation links the measurement; it does not add the planned amount a second time.

Use `remove`, `unstable`, `occlude`, `disconnect`, `restore`, `closing`, `rebind`, `pause`, or `resume` in place of the simulator action to inspect alternative states. `advance --seconds 6` advances the demo clock without a new measurement. `replay` starts a separately tagged replay run. New runs preserve old database records and move the workspace to the new demonstration; they do not delete earlier runs.

Stop the API/Web with Ctrl+C in their terminals. To stop only Senplate's owned database:

```sh
uv run python scripts/dev.py stop-db
```

## Reproduce the menu and ordering demo

Resolve any open orders or measurement checks before creating a new run. Existing records are retained.

```sh
uv run python tools/simulator/client.py new --service staff_portioned --initial 2000
```

1. On the Web, open **Menu & service** to see the genuine menu QR / code and edit prices, publication, allergens or manual kitchen stock as `manager`.
2. In the iPhone app, sign in as `personal`, choose **Dining**, and enter the displayed code. Physical-camera capture still needs real-iPhone verification; Simulator offers manual entry. The deep link uses `senplate://menu/<code>` and grants no work permissions.
3. Add three 100 g chicken portions and submit. The request does not reserve stock yet. In **Orders** on the Web or **Tasks → Orders** in work mode, accept it: 300 g is now reserved.
4. Begin portioning. Run `uv run python tools/simulator/client.py consume 300`, select that weight decrease, then **Confirm portioning**. The measured weight is 1,700 g; releasing the reservation does not deduct another 300 g.
5. Read the six-digit collection code in the customer's ready order and enter it on the kitchen screen. Collection changes the order status, not the weight or payment status.

Buffet mode makes the measured dish browse-only; manual counter items can still be ordered. Popularity counts only collected portions in the current service. The photos in [assets/menu](assets/menu/manifest.json) are generated illustrations, not sensor evidence. The seeded measured portion is fixed at 100 g in this batch.

The staged order XCTest cases require the live steps between them: phase 1 prepares a 3-chicken / 1-salad cart at HK$90; change salad to HK$19 on the Web before phase 2; accept / portion / verify before phase 3; collect before phase 4. Phase 5 uses a second 100 g order and manager credentials; add its measurement before phase 6. Phase 7 is the independent SE3 UI check; phase 8 expects an already invoked system menu link. See the QA report for exact evidence. Do not run all staged cases in parallel against a shared demo.

## Personal meals and anonymous samples (M1.2)

Open [the station console](http://127.0.0.1:5177/device). Use the private setup key in `.runtime/station-console.json`, created by `setup`. A staff login cannot replace this station identity. Resolve open orders, replenishment tasks and an active meal before switching the same station to another mode; never cancel someone else's order just to reset a demo.

1. Choose **Your meal**. In **Demo input controls**, send a stable 0 g reading; then **Confirm empty plate**. These controls simulate data and do not read a scale.
2. On iPhone, **Dining → Record a meal**, scan / enter the short-lived meal code. Match the four-digit number and applicant on the station, then confirm that person. A menu code does not pair a meal.
3. On either paired phone or station, choose **Cooked white rice → Begin this item**, then send a simulated total of 200 g and **Record this portion**. Repeat with chicken at total 300 g and broccoli at total 450 g. The recorded portions are 200 / 100 / 150 g.
4. **Finish plating**, send total 350 g, then complete with that remaining weight. Provided reference nutrition remains 477.5 kcal / 39.97 g protein. The system does not infer item-level intake from the 100 g decrease.
5. For school, choose **School sample** instead. No phone or child account is required. Use the same sequential recording; the workbench **School samples** lists anonymous records, source/date filters and manager CSV.
6. If a plate is removed or contents change, complete with a reason and unknown remaining weight. Unknown food references keep nutrients blank. A demonstration portion plan is labelled unreviewed; it is not a school nutrition standard.

Fixed references and their CC0 provenance: [source audit](research/2026-09-19-nutrition/reference-audit.md). References are selected by a person, not identified by a trained camera model.

### Isolated UI QA without changing current orders

This batch preserves the original demo orders and uses another **test database**, not a second physical station. Create it once without resetting existing data:

```sh
uv run python scripts/meals_qa_environment.py
SENPLATE_CONFIG=.runtime/meals-qa-config.json uv run uvicorn senplate_api.app:create_app --factory --app-dir services/api --host 127.0.0.1 --port 8800
```

In a separate terminal, run `npm run dev -- --mode meals-qa` in `apps/operations-web`. Use **http://localhost:5178** (QA), while the original demo uses **http://127.0.0.1:5177**. The different host names prevent browser cookies from colliding. QA credentials and console key are in `.runtime/meals-qa-credentials.json` and `.runtime/meals-qa-config.json`.

Only a Debug Simulator launch with `SENPLATE_QA_ENV=meals` connects the iPhone to API 8800, using a separate Keychain service. Normal launches keep API 8799. No arbitrary server URL or release-build switch was added.

`MealsUITests` is staged: phase 1 requires a fresh pairing code and QA credentials; confirm on the Web before phase 2; send a 200 g rice reading before phase 3. Phase 3 supplies further simulated observations through the QA API while operating the native UI. Phase 4 reads completed QA meals in English / Chinese / large type and can run on SE3. Phase 5 is a read-only review of the original demo containing order #003, with original demo credentials. Do not run all phases together or in parallel. Test-runner environment names are documented in the test source; no passwords belong in code or QA reports.

## Source and verification

| Area | Entry |
|---|---|
| Native iPhone | [SwiftUI source](apps/ios/Senplate/Sources/SenplateApp.swift) |
| Kitchen and station display | [React app](apps/operations-web/src/App.tsx) |
| API / permissions | [FastAPI routes](services/api/senplate_api/app.py) |
| Replenishment rules | [Domain state machine](services/api/senplate_api/domain.py) |
| Simulated input | [CLI](tools/simulator/client.py) |
| Backend tests | [15 P0 scenarios](tests/test_api.py) + [18 ordering scenarios](tests/test_orders.py) + [22 meal scenarios](tests/test_meals.py) |
| iPhone UI tests | [P0 scenarios](apps/ios/SenplateUITests/SenplateUITests.swift) + [8 staged order scenarios](apps/ios/SenplateUITests/OrderingUITests.swift) + [staged meal scenarios](apps/ios/SenplateUITests/MealsUITests.swift) |
| Scope, coverage and limitations | [P0 record](planning/2026-09-18/development-p0.md) / [M1.1 contract](planning/2026-09-19/menu-orders-contract.md) / [M1.2 contract](planning/2026-09-19/meals-samples-contract.md) |
| Visual QA and comparisons | [P0 QA](output/qa/development-p0-2026-09-18/verification.md) / [M1.1 QA](output/qa/development-p1-orders-2026-09-19/verification.md) / [M1.2 QA](output/qa/development-m1-2-meals-2026-09-19/verification.md) |

```sh
uv run pytest -q
uv run ruff check services/api scripts/dev.py scripts/meals_qa_environment.py tools/simulator/client.py tests
cd apps/operations-web
npm run build
```

The backend suite only clears `senplate_test` after checking the local cluster marker, host, port and database name. It does not reset the demonstration database. The iPhone UI tests are staged integration tests against the running API: prepare a fresh 700 g run for `testEnglishChinesePersistenceAndKitchenFlow`; it leaves a task awaiting measurement. Add and confirm 1,000 g before running `testVerifiedBatchAndLargeText`. Run them individually, with generated credentials passed through `TEST_RUNNER_SENPLATE_TEST_USERNAME` and `TEST_RUNNER_SENPLATE_TEST_PASSWORD`; they are not a fixture-free full-suite command. Exact successful runs are recorded in the QA report.

## HISTORICAL Food prototype boundaries

The first software slice includes authenticated roles, one monitored station, valid/unknown/stale states, suggestions, task ownership, measured refill reconciliation, records, source filters, a manager CSV export, and the personal / work identity boundary. The screen assets use the chosen V7 plain bowl and the licensed Manrope / Noto Sans SC fonts. Font license files are bundled with the clients.

M1.1 adds real menu QR generation, strict menu-link parsing, an iPhone cart with explicit repricing, private orders / pickup codes, kitchen fulfillment and reservations, and manager editing of the current three seeded menu items. M1.2 adds station-confirmed pairing, sequential portions, immutable reference snapshots, owner-only meal records, anonymous school samples and scoped CSV. Full food catalogue creation, recipe editing, approved school-plan configuration, disposition tracking and wider operational reports remain M1.3 work. Camera inference, calibration, Pi operation and measurements belong to M2. This prototype does not establish food recognition accuracy, nutritional accuracy or real waste reduction. External deployment, APNs, TestFlight, App Store distribution and coursework submission have not happened.

The original [VI package](output/brand/Senplate_VI_Kit_v1.zip), [brand specification](brand.md), [trademark research](research/2026-09-18-senplate-trademark/trademark-review.md) and both project suggestions remain available below. The selected logo is retained; no new trademark clearance is implied by development.

## 建议书版本

大陆参赛延伸见[全国与省级赛事](research/2026-09-16-competitions/mainland-national-provincial.md)：区分明确港澳学籍入口、VTC获奖先例、需确认的高职／赛区和需要额外训练的省级技能赛，不要求注册公司，不把区域奖混作全国奖。

参赛参考见[无需公司落地的候选](research/2026-09-16-competitions/no-company-options.md)。用户暂不打算在任何地方注册公司；按三位非香港永久居民、高级文凭与FYP身份核对学生赛奖金、资格和日期，深创赛／广州创业落地奖移出当前主选，[首轮研究](research/2026-09-16-competitions/competition-shortlist.md)保留比较。名单不是报名，不代表应用、硬件或参赛已经全部完成；品牌最新决定为Senplate，当前视觉工作另由用户授权。

| 版本 | 主题与状态 | 文件 |
|---|---|---|
| V2 保留供修订 | Food and Nutrition Monitoring；四页已检查，盘位及识别文字待同步本轮澄清 | [DOCX](<output/docx/AY26_ProjectSuggestion_Group 2_v2_MultiScenario.docx>) / [PDF](<output/pdf/AY26_ProjectSuggestion_Group 2_v2_MultiScenario.pdf>) |
| V1 保留 | Food Replenishment and Waste Reduction；原文件不变，四页 | [DOCX](<output/docx/AY26_ProjectSuggestion_Group 2.docx>) / [PDF](<output/pdf/AY26_ProjectSuggestion_Group 2.pdf>) |

## 设计与研究

- [当前参赛计划：现在至2027年7月底，资格、奖金、报名与作品要求](research/2026-09-16-competitions/plan-to-july-2027.md)
- [世界职业院校技能大赛：学校报名路线、当届截止与Marco询问草稿](research/2026-09-16-competitions/world-vocational-registration.md)
- [当前选定Logo与品牌规范](brand.md)
- [历史餐食计量Logo R5](planning/2026-09-17/senplate-logo-measured-plate-r5.md)
- [已完成选稿的GPT网页版设计简报](Senplate_Logo_ImageGen_Brief.md)
- [Profile／层序R4视觉参考](planning/2026-09-17/senplate-logo-profile-r4.md)
- [旧Interval图形近似初筛与官方证据](research/2026-09-17-logo-similarity/similarity-review.md)
- [Interval原创矢量Logo草稿与初步认可](planning/2026-09-17/senplate-vector-logo-studies.md)
- [Logo真实标记审美校准与已选参照](planning/2026-09-16/logo-reference-calibration.md)
- [已撤下的Logo方向重整R3](planning/2026-09-16/senplate-logo-reset-r3.md)
- [已否决的Logo修订R2](planning/2026-09-16/senplate-logo-refinement-r2.md)
- [Senplate旧VI方向与已选工作基准](planning/2026-09-16/senplate-logo-vi-directions.md)
- [Senplate商标与域名初筛](research/2026-09-16-senplate-name-check/senplate-trademark-and-domains.md)
- [历史命名候选、读法与取舍](planning/2026-09-16/naming-shortlist.md)
- [旧品牌候选、Logo与App概念图](planning/2026-09-16/brand-visual-directions.md)
- [详细页面、导航、权限与异常](planning/2026-09-16/app-pages-and-permissions.md)
- [状态、数据、19项首批接口与JSON示例](planning/2026-09-16/software-workflows-and-api.md)
- [开发工作包与分阶段验收场景](planning/2026-09-16/software-mvp-and-acceptance.md)
- [iPhone双角色、工作台Web、共享后台与开发顺序](planning/2026-09-16/software-scope-and-architecture.md)
- [Metafoodx App公开界面与功能研究](research/2026-09-16-metafoodx-app/app-review.md)
- [V2 多场景范围、营养依据与分工](planning/2026-09-14/multi-scenario-suggestion-v2.md)
- [单设备、单盘位与食物识别可靠性](planning/2026-09-14/single-station-recognition-reliability.md)
- [AI 训练、RGB-D 融合与树莓派算力验证](planning/2026-09-14/ai-training-and-pi-deployment.md)
- [持续监测与计算硬件](planning/2026-09-14/continuous-monitoring-architecture.md)
- [Gemini／RealSense、统一供电及共享成本](planning/2026-09-15/camera-power-and-scaling.md)
- [单台demo电源具体选型与接线](planning/2026-09-15/power-supply-detail.md)
- [亚博供货、屏幕与定制合作](planning/2026-09-15/yahboom-sourcing-and-customization.md)
- [当前整机硬件制作询价V3.1附图版](planning/2026-09-15/hardware-fabrication-enquiry-v3-1-images.md)
- [V1 详细范围与分工历史记录](planning/2026-09-14/scope-and-roles-for-review.md)
- [Metafoodx 硬件与 Pomona 案例](research/2026-09-14-metafoodx-hardware/hardware-and-technical-review.md)
- [硬件图片／视频核对记录](research/2026-09-14-metafoodx-hardware/evidence-review-log.md)
- [直接竞品与电子菜单研究](research/2026-09-14-suggestion-deep-review/deep-review.md)
- [早期视频记录](research/2026-09-14-suggestion-deep-review/video-review-log.md)
- [Metafoodx／Controliza 对照](research/2026-09-10-metafoodx-controliza/competitive-review.md)
- [早期证据表](research/2026-09-10-metafoodx-controliza/evidence-register.md)
- [未发送的演示与询价问题](research/2026-09-10-metafoodx-controliza/demo-questions.md)

研究资料保留原有日期与证据边界；旧共享扫描站方案、默认扩展至 2–3 个节点及其整套预算均不作为当前交付要求或报价。当前桌面设备范围只以product.md及其路由的新提案为准；此处食品项目多场景说明、单盘位研究、旧Proposal和V1/V2 Suggestion均为历史，不可用于新题目提交。
