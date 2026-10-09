# Group 2 avatar art research verification

Task started 9 October 2026 before midnight in Hong Kong; research and closeout continued on 10 October. This is an art-reference research deliverable. No application, model, school-document or hardware implementation is included in this round.

## Reading and current scope

[reading-record.json](reading-record.json) records the full body of 128 project-owned Markdown files, 12,096 lines and 48 chunks. Chunks 2 / 3 initially exceeded the combined output budget and were each re-emitted and read separately. All other chunks were delivered individually after that correction. Reading completed at 00:50:21+08:00 on 10 October, with all initial source hashes unchanged. Compaction retained this ledger; recovery re-read the entry files, current decisions and avatar contract, then continued the unread chunks.

The user requested current popular anime-character research before art optimization. The previous handoff's Pi performance next step is retained as an independent acceptance gate, while this round's next art deliverable is an original A / B full-body and facial-expression concept comparison. No art direction has been approved or original character image generated.

## Source verification

- Anime Corner: organizer's 5 October Summer 2026 community results and demographics; multi-select, 15,117 participants. No global / China-representative claim or derived voter counts.
- Anime Trending: organizer's 21 March 2026 results recognize 2025 characters. The top three are recorded with exact votes; the periods and communities are not merged.
- Official images: Emilia, Frieren, Maomao and Marin actually viewed using CUA; public asset URLs observed from the official pages. Miyabi uses the actual official image in a HoYoverse technical lead's PlayStation Blog article.
- Official YouTube videos: Furina and Firefly channel identity and sampled frames inspected. Saved frames at approximately 1:37 and 2:52 are used. Additional Firefly far / legs frames are retained as unused evidence, not called portraits. Background playback is not counted as continuous complete viewing. No full video download or lyric reproduction.
- Razer: January / February Kira references are dated. The current product page was visibly read and lists AVA / SUMI / NIKO personality names, with development caveats. Its hero only shows the logo / cylinder and is accurately labelled. The unavailable linked February image was not retried or claimed inspected.
- Frieren's official poll page lacks final results in the accessed body. No precise final rank is used. Personal game recaps and video views are not treated as global popularity awards.

The curated [source register](../../../research/2026-10-10-avatar-art/source-register.json) contains 8 visual / product references and 5 additional primary sources. Art interpretations and original direction suggestions are explicitly separated from reported popularity facts. Official external images require connectivity; they are not new reusable application assets.

## Reference-board browser check

The static [reference board](../../../research/2026-10-10-avatar-art/reference-board.html) was loaded through a temporary loopback-only preview server at port 5192. It serves only this research directory and this QA directory; a request outside those scopes is denied. No private runtime directory is exposed.

At the browser's default 1280 × 720 viewport, all 8 images loaded with nonzero dimensions and document width did not exceed the viewport. A full-page screenshot was visually inspected. The light / dark button changed its pressed state and background, and the dark screenshot was also inspected. Whole image proportions are preserved; the Furina controls remain part of the original screenshot. A separate narrow viewport was not tested, and no viewport override was set.

- [Light board](reference-board-light.png)
- [Dark board](reference-board-dark.png)
- [Firefly sampled face](firefly-official-portrait-frame.png)
- [Furina sampled pose](furina-official-frame.png)
- [Miyabi official illustration](miyabi-official-blog.png)
- [Current AVA device hero](ava-official-hero.png)

The main avatar preview at 5190 is preserved. This research board does not change owner preferences, events or tool permissions. Browser theme is restored to light for delivery. No CAPTCHA, account, invitation, API subscription or supplier contact was involved.

## Preservation and documentation

[validation.json](validation.json) records local links, 107 school / identity / retired-code protected hashes, unchanged application paths, the pinned pixiv-model SHA, JSON / frame checks and preview route boundaries. Product, root README, avatar contract, decision log, handoff and work log are synchronized. The model remains `12c2b97e95e700783a6a550dc0eee2d7880aeedccef9ae67bc4c5a2f0f2631a2`.

There is no React / backend / native application or dependency change, so no application suite was rerun. The 22 frontend / 26 targeted backend checks belong to the previous avatar task, and the 149 backend / 15 frontend baseline belongs to the previous Dot integration. No new DOCX / PDF or school edits require rendering. Original seven events were not operated on during this task.

A combined documentation patch initially failed because a partial README line did not match; Git diff confirmed it made no changes. A subsequent exact patch succeeded. The first local-link check correctly found this not-yet-written QA report; after the report was created it was rerun. GitHub CLI PR metadata was denied by the existing token; the already-authorized connector supplied the open PR state without changing permissions.

## Git delivery

Existing branch: `codex/full-body-3d-avatar`; existing open [PR #4](https://github.com/tantalum666/FYP/pull/4). Initial feature head `6ac85d53d824bebcc742071b5dddcb05bb331d6a`; initial main `ccfac48ce8c68e6f9c8796911bbe5f35728d7807`. The staged Gitleaks scan completed with zero findings (approximately 140 KB of staged text scanned). The 564 local Markdown links, protected hashes and unchanged application / model checks passed. Research commit / remote readback are recorded during closeout. No automatic merge into main or public deployment is performed.

Actual delivery: research commit `876d89e5f3b97c8c9a25eac240244340a995ecdc` was pushed successfully. `git ls-remote` and connector PR metadata independently read back that head; main remains `ccfac48ce8c68e6f9c8796911bbe5f35728d7807`. PR #4 remains open and its description now includes the research scope. A final closeout commit only synchronizes these records and handoff status, then follows the same push/readback path.
