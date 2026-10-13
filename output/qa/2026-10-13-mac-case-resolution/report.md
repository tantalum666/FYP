# Mac narrow-card regression: blocked by source build

Exact source: `1e52e7106c03f5a1a365a9859dbec21cb0f921e6`; exact tree: `42079660aad46c72fedc1bace18f22be6bab55a3`. Repository `tantalum666/FYP`, branch context `codex/personal-agent-kernel-20261012`, Draft PR #5. The separate checkout is `task-2/fyp-narrow-1e52`. HEAD and tree match the parent’s checkpoint. The existing authenticated read-only GitHub connection supplied missing objects; 72 new blobs and 539 reconstructed trees were verified against Git object hashes. No network-download retry or forbidden route was used.

## Current finding

`npm run build` fails on this Mac with exit code 2 during `tsc --noEmit`; Vite does not run and no new `dist` exists. The component `src/workspace/agent/PublicCapture.tsx` and helper `src/workspace/agent/publicCapture.ts` have the same basename apart from case. On this filesystem, the candidate `PublicCapture.ts` resolves to the existing lowercase helper (confirmed same file). Extensionless `./PublicCapture` imports in RunPanel.tsx:9 and RunComposer.tsx:13 therefore resolve to the helper/type rather than the JSX component.

Reproduced diagnostics include TS1149/TS1261 casing conflicts, TS1484 type-only import requirements and TS2693 at RunPanel.tsx:165/:363 and RunComposer.tsx:650. The full local compiler output is `build-failure.log`; no broad unit suites were run. The saved reproduction is a second targeted build after the first identical failure, to retain complete output.

Both source files independently match the checkpoint: component Git blob `17b1268a0e8e09d1db906032d8cb8dbd6179097c`; helper Git blob `67630e12e97f8ebdd1407bf684ff78259b8a78ac`. The CSS matches Git blob `68a52afc7b630ae69182ac1cd3ead97562e81e41` and contains `.agent-run-choice { flex-shrink: 0; }` at line35. This proves the source change is present, but does not prove its mounted layout behavior. The parent reported successful exact CI runs; those do not establish a successful Mac build on this filesystem.

The parent owns the narrow source correction. Use distinct module basenames and update their imports, then provide the next verified SHA. No local production source edit, commit, push, merge or deployment was performed.

## Permission and acceptance state

The earlier default-sandbox bind probe for `127.0.0.1:5191` returned PermissionError errno1, Operation not permitted. Its original setup report and permission evidence are preserved separately. The parent subsequently authorized requesting one scoped per-action approval for the temporary loopback test service; that authorization is not an approval grant. No escalation was submitted in this continuation because the prerequisite exact-source build fails. No automatic approval rejection is claimed. After a corrected source builds, request that single scoped service approval and treat its result as authoritative; stop on denial, pending or unavailable approval.

No old database was opened, copied or migrated. No new schema-3 runtime was created or server started. No new browser interaction, screenshot, browser-console observation, computed flex-shrink, list/card geometry, scroll/final selection, unbroken/fallback title, busy-control or A1 result is claimed at this SHA. The full 390×844/desktop English/Chinese regression remains blocked. No Library upload occurred because there is no new regression screenshot.

## Preservation and reading

The ongoing round’s validated 186-file full-reading ledger was reused where valid. AGENTS.md and current handoff were read; relevant product/decision changes, public-capture schema/runtime opt-ins and the changed run-card contract were supplemented. Dependency installation was avoided: the new checkout references the existing node_modules, and package-lock bytes match the preserved source.

The prior `4e508411` report, manifest and screenshots remain preserved. Original frontend asset hashes remain exactly `63714cb1ece3475cb5e316e85c4a8aefefa913178d94c3a8d0e652d80d42dcdb` (JS) and `cdee47b225f3f8f380d3cb1223997fe99e90e51c2d25ce681f97c50c8dfebb45` (CSS). Existing acceptance5190 PID82674 and independent demo8843 PID79955 remain listening and untouched; 5191 and8832 have no listener. Original main checkout/runtime/8832 were not changed.

Pending CSV Save disposition remains unknown and was not retried. Unknown-effect fictional MCP evidence remains preserved without replay. No public MCP/browser/capture execution, model/provider call, hardware action, credential/access modification, sandbox weakening or model override occurred. Manual testing of the independent demo remains separately attributed to earlier checkpoints and does not establish general cross-app agent capability.
