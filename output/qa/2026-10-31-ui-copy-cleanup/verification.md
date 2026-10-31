# Group 2 · UI copy cleanup verification

31 October–1 November 2026, Asia/Shanghai. Owner feedback: too much text on every page. This round changes shared frontend presentation on branch `codex/ui-copy-cleanup-20261031`, based on PR74 `89f215e`. It does not change backend services, stored user content, provider grants or real account data.

## Observed problems and changes

| Observed in actual before screens | Implemented response |
|---|---|
| Work results buried under IDs, counters, storage and repeated qualifications | Goal/state/actions/files first; plan, technical detail, history and storage are explicit disclosures |
| Empty new-work form leads with limits and optional configuration | Goal/mode/selected content first; optional report headings and advanced scope in More options |
| Settings/task/memory/style repeat their headings or implementation caveats | Short labels and relevant current state; no repeated introductory paragraphs |
| Import/share shows several full manuals before choosing an action | Calendar file import first; Google, backup, import rules and sharing expand individually |
| Phone repeats all Work goals above the selected goal | Detail replaces the list at narrow widths; All work uses existing guarded selection |

Critical information stays at the action: exact review, provider destination and sharing, retention with no current delete control, model charge/retry consequences, Full-access explicit save, share audience/expiry, cancellation and unknown-result recovery. Folded form fields remain mounted. Alice and existing phone navigation remain.

## Before/after rendering evidence

Screenshots were captured and inspected from the same local QA application. Default English desktop viewport1280×800; Chinese phone393×852. Visible text counts use `innerText` of the named active dialog or main region, including its scrollable content but excluding collapsed details and modal background. They are character counts, not word counts or usability scores. Early unscoped modal counts were corrected.

| Surface | Before | After | Scope |
|---|---:|---:|---|
| Tasks |229|155|Same synthetic task |
| New work |1368|290|Same empty foreground form, default local mode |
| Settings |1177|722|Same settings |
| Memory |353|238|Same stored content |
| Style |231|137|Editor content unchanged |
| Import/share |1184|200|Secondary actions now folded |
| Task detail |711|423|Same synthetic task |

Work detail before2710; intermediate after528. Final screenshot565 includes an additional local-test Work in the navigation, so do not treat final whole-dialog counts as an identical-data comparison. Selected phone detail260 Chinese characters, document width393. The Chinese AI form has explicit provider and sharing controls, with no horizontal overflow; it was discarded without model execution. [Raw scoped metrics](visible-copy.json).

Selected unchanged image bytes:
- [New work before](03-before-new-work.png), [new work after](25-final-new-work.png).
- [Final desktop Work](24-final-desktop-work.png), [Chinese phone Work](21-phone-work.png).

All source screenshots remain locally in ignored `desk-companion/.runtime/ui-copy-audit`. Accepted final screenshots were captured after a separate DOM check; an immediate HMR screenshot was visually stale and was not used as final evidence.

## Interaction and state verification

- Keyboard Enter expands/collapses More options. A typed optional heading survives collapsing/reopening. Closing a dirty form offers Continue editing/Discard; Continue retains input.
- Local Work Review stays disabled without explicit retention. Selected one synthetic task and retention, reviewed exact goal, started via UI and observed completion with2 artifacts, mode `deterministic`, model_calls0. [Readback](workflow-check.json).
- Selected Full-access **draft**, inspected scope, then Cancel. Persisted Ask/version1 remained unchanged. No authorization was expanded for this demonstration.
- Edited a temporary persona draft, collapsed/reopened, observed unchanged input, then restored the original text without saving.
- Opened sharing with keyboard and checked the audience/seven-day expiry before any creation. No share/OAuth/import operation was executed.
- Chinese phone Alice remains visible. Plan/Tasks navigation, selected Work→All work→list and new-work discard operate correctly. No393px page overflow. Temporary viewport was reset and original English language restored.
- Current render logs contain only the earlier development-time Vite JSX reload error; it was repaired. No later runtime error was observed on the exercised final paths. This is not an exhaustive console history claim.

## Local checks and limits

`npm test`:303/303 pass. [Summary](frontend-tests.txt); full TAP remains in ignored runtime. `npm run build`:TypeScript and Vite pass; [build log](build.txt) retains the existing >500kB chunk warning. Initial stale-copy and formatting-sensitive assertions were updated while retaining approval/draft/identity/inert-content checks. A temporary missing JSX brace was fixed before acceptance. Final source review also replaced an unconditional “files checked” claim and kept charge consequences visible on AI review.

No backend change or new dependency. Prior PR74's1,701 backend result belongs to that round and was not rerun here. No native package rebuild or real touch/software keyboard, assistive-technology matrix, voice/model autonomy, real external account or every advanced integration panel was tested. No paid requests, CI, Pi continuation or transaction. Existing API8861/Vite5191 use isolated synthetic QA data, with offline fixture providers; the only new Work here was deterministic.

## Documentation and publication

Updated AGENTS, product, decision log, current entry/handoff, work log, software maintenance, dated UI/permission guidance and the new [copy contract](../../../desk-companion/docs/ui-copy.md). Local link, scope, formatting, secret-pattern and diff checks are recorded at publication. Selected screenshots contain only synthetic QA data; runtime stores, credentials, full browser inventory and private artifacts are excluded.

Publication pending. New UI PR is stacked on the still-unmerged PR74, not an implicit main merge or device deployment. Next software step remains ordinary Alice/Omni long-task admission/recovery through existing Work, respecting the new concise-interface contract.
