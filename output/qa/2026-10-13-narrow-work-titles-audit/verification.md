# Independent retained Work title audit

Date: 13 October 2026. Verdict: no blocking source/test finding in the narrow patch. Rendered acceptance remains pending the separate Mac retest.

## Scope and evidence

The reported real-Mac failure was invisible retained Work goal titles at 390×844 on source 4e508411. That is the parent-provided observation, not a rendering reproduced in this audit. This shared workspace has no Git metadata; final review is pinned to file SHA-256 values in `scope-hashes.json`, not a claimed commit. Same-task 186-document intake is inherited; supplementary actual reads are recorded in `reading-ledger.json`.

The entire production CSS difference from the owner's saved original is one comment and `flex-shrink: 0` on `.agent-run-choice`. New regression file is `desk-companion/frontend/tests/work-card-layout.test.ts`. RunPanel and general styles were reviewed for interaction; this reviewer made no production, shared-document or Git changes.

## Findings

- The list is a column flex container with 18rem max-height and vertical auto overflow. Its children are grid buttons, and the clipped two-line title is an inner row. Preventing child flex shrink is an appropriately scoped way to preserve natural card height and let the existing list scroll. Actual collapse causality remains an inference until measured in the browser.
- Desktop keeps the same behavior with the existing 32rem list cap at min-width 850px. Narrow screens keep the existing 42px button minimum. The fix does not impose a fixed height, so multiline status/mode metadata remains able to increase a card's height. A tall list remains bounded; a single unusually tall card can be scrolled.
- The patch does not change horizontal sizing. Existing global border-box, card width 100%, min-width 0 on layout children, minmax(0, 1fr) narrow grid and overflow-wrap:anywhere on titles and metadata mitigate long-word overflow. No additional .agent-run-choice rule or overriding flex-shrink rule was found. Source inspection cannot establish actual scrollWidth/clientWidth, scrollbar geometry or all browser layout interactions.
- Native button/type semantics, full goal text in the DOM, localized nav label, one aria-current selected card, global focus-visible styling and guard.busy disabled behavior remain unchanged. The same selected-card click remains a no-op; another card forwards its exact ID. Parent go() still checks the response fence, busy state and dirty-draft routing. The focused SSR tests validate markup and callback wiring, not actual keyboard focus, accessibility-tree output or mounted busy-state races.
- The new tests are honestly labeled source/SSR regressions. They read actual production JSX and cover 100 English/Chinese long-title cards, fallback titles, status, selection, busy disabling and exact navigation target. The CSS assertion checks the intended invariant rather than measuring rendered title visibility. It can catch removing this fix but is not a browser layout regression test.

## Checks

- Independently executed focused tests against the final production CSS: 4/4 pass, `patched-focused-tests.log`.
- Independently replayed the new test source against the saved prepatch CSS while retaining current production JSX: 3 pass / 1 fail, only the expected flex-shrink invariant. Exit 1, `before-replay.log`. The isolated replay harness changes source-file URLs only; it does not modify production. Its temporary dependency symlink was removed afterward.
- Reviewed owner's logs: frontend suite 242/242 pass, typecheck passes, production build passes with existing large-chunk warning. These are owner-executed results, not a duplicate independent full-suite run.
- No browser install, sandbox modification, user database operation, real-model call, deployment or Git action occurred in this audit.

## Required rendered confirmation

Use the separate authorized Mac task with exact patched source/bundle identity. Check 390×844 and desktop with enough retained cards to overflow; visible distinct titles/status, long English and Chinese wrapping, empty-goal fallback, first and final card reachability, selected state, native keyboard focus and no document/list horizontal overflow. Check busy controls in the mounted UI. Record screenshots and computed card/title geometry. Until that evidence arrives, describe this as source/test validation of a likely fix, not a verified visual repair.

## Final pinned files

- agent.css: `b0354005de5866438c8d1007af3a0adb57a1a5615104c121316dd22422034656`
- work-card-layout.test.ts: `84cc3ac855dc47c180bf7df001c1cc8beacb68682e8e3dacf938cf4d84d88407`
- RunPanel.tsx (unchanged reviewed context): `cdc349fbb26b7313763c44fe092af55c5d4129b3771bb89c90c6b19237bf1409`
- Original CSS: `8e95a6e4e8063bfd56a7e04d85b1f05d0be10493d2e7b0b33fd4d9c9c65cfb71`
