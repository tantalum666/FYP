# Group 2 · Memory continuity and native phone checkpoint

28 October 2026, Asia/Hong_Kong. Branch `codex/native-memory-reliability-20261028`, based on main `9bfe2eedf0ea05b9f7d143a18388d84e36e19de0`. The owner asked to continue AI/software with maintainable code and local validation. This checkpoint does not claim that the whole product is ready.

## Behavior changed

- Model memory search previously filtered only the 40 recent prompt facts. An older valid fact could not be queried, corrected or forgotten through these tools. `MemoryService.active_facts()` now supplies one filtered model-safe projection of all active facts (store cap200); default prompt/no-query output remains40 and ranked query output remains8. No attribution notes or previous wording enter that projection.
- Correction/deletion drafts and exact-text local forgetting can address older active facts. Owner checks, explicit confirmation and confirmation-time version checks remain. Retired/deleted/expired facts are excluded.
- Conversation revision covers the entire active projection, so deleting or expiring a fact outside the recent40 clears old HTTP/realtime replay and recall focus on the next context check. The initial prompt still contains at most40 facts. No new transcript store or automatic model reconnect was introduced.
- Shared `MemoryFactList` owns rendering and a local English/Chinese search over already-loaded active facts. `MemoryPanel` retains fetching, writes, versions and draft protection. No new API, package or phone navigation destination was added. Search and competing row edits are locked during correction; messages are near the list and previous wording renders on its own line.

## Local automated evidence

| Check | Result | Evidence |
|---|---|---|
| Reproduce against original source | 8 failed /1 passed | [before](memory-before.txt): older English/Chinese query, replace/delete draft, exact forget and delete/expiry replay invalidation |
| Focused memory/retrieval/HTTP/Omni regression |43 passed | [after](memory-after.txt) |
| Full backend |459 passed,1 existing Starlette deprecation warning | [log](backend-tests.txt) |
| Frontend suite |89 passed | [log](frontend-tests.txt) |
| Gitleaks staged scan / changed-document links |No leaks / no broken local links |[audit](publication-audit.json) |
| Ruff backend/tests |Passed | Command `.venv/bin/ruff check backend tests` |
| TypeScript and production Vite |Passed; existing large-chunk advisory remains | [build](frontend-build.txt) |
| Capacitor sync and native feature wiring |Passed | [sync](capacitor-sync.txt) |
| Pinned Capacitor8.5.2/Cordova archives |Official archives verified by existing SHA256 checks | [preparation](native-preparation.txt) |
| Native Simulator build/install/launch |Succeeded, exact UDID and build paths recorded | [build result](native-build.json) |

All model behavior tests use local rules, offline fixtures or scripted protocols. No CI, hosted-model call, actual mic/camera/screen sharing or hardware operation was run. Neither credentials nor runtime databases are publication artifacts.

## Actual browser and API verification

Flow: existing Saved memories → search older fact → correct → attempted navigation guard → keep editing → save → independent API/current recall readback. CUA in-app browser APIs were used; the separate Browser skill was not listed, and no external Playwright process was needed.

Environment: current Vite source `http://127.0.0.1:5191`, API8832, fictional isolated `.runtime/native-memory-20261028`. Both providers `none`; extraction/background/push/computer/Linux executors off. Old user runtimes are preserved. [Fixtures](fixtures.json) contain only42 fictional facts.

- At1365×900: `LAB  locker` found the older English fact, Chinese `柜子` found the older Chinese fact, no-match displayed0/42 plus recovery text, and Clear restored the list. Correcting Orion→Lyra kept the fact ID and produced version2; previous wording was visibly separated. Leaving during correction opened the guard and Keep editing retained the text.
- At393×852 and320×740: phone More→Saved memories retained compact navigation. Search matched current facts with no horizontal page overflow. Back to Alice during a Chinese correction offered Continue/Discard; Continue restored the exact draft; Cancel left the persisted Chinese fact unchanged. Other correction buttons and search were disabled during one edit.
- Phone browser Plan→New→Save→Back created `Demo software review`, showed the saved day item and returned to Alice. This is browser evidence, not native keyboard evidence.
- API readback independently confirmed42 facts, English version2, unchanged Chinese version1 and a local recall of Lyra without Orion. [Readback](api-readback.json).
- Page titles/URLs matched Desk Companion, no blank/framework error surface, and inspected web/phone console warning/error lists were empty. Screenshots: [desktop](web-memory.jpg), [phone393](phone-memory.jpg), [phone320](phone-memory-320.jpg).

## Native outcome and open gate

The final built source was installed and launched on iPhone17Pro/iOS26.5, UDID `F57B6381-6448-434C-AE61-A2663F3458A7`, bundle `dev.group2.deskcompanion`, Debug Simulator build with `CODE_SIGNING_ALLOWED=NO`. A launch-only defaults argument selects loopback API8832; the saved real-phone configuration and TLS policy were not changed. The live mirror displayed Alice and the fictional event saved from the browser, demonstrating native bridge reads. [Native frame](native-phone.jpg).

**Native Plan→New→Save→Back, soft keyboard and keyboard interruption are still unverified.** Mirror input logged taps but no app transition; the native CUA view was a transformed/offscreen Device Hub thumbnail and coordinate input returned `windowNotFoundAtPosition`. Its AX controls could change window chrome but did not expose usable WebView input. Accessibility overlay later exposed app labels, but did not resolve taps. This is an input/automation limitation, not proof of an app interaction defect or pass. No fake keyboard injection or browser result is labelled native.

The earlier8831 installation/runtime and historical450/89 integration evidence remain historical. Current local services: API exec85864, Vite exec5997, mirror exec56630. Recheck listeners before reuse; these IDs are session-local, not deployment evidence. The mirror is pinned to this Simulator with a scoped cleanup trap.

## Closeout and next work

Updated product/entry/handoff, memory/Omni/maintenance contracts, phone implementation note, decision/work log and [delivery gates](../../../desk-companion/docs/delivery-readiness.md). The next software slice is one actual task → approved bounded job → independently verified result → phone continuation, including restart/lost-acknowledgement handling. Native input, human voice comparison, real delivery, posture and Pi/Luwu retain their separate gates.

Alice screenshot content uses the project's existing AliceChan asset, edisonlee55/yuna0x0, CC BY-SA4.0; [source/licence](../../../desk-companion/frontend/public/avatars/alice/LICENSE.md). No art asset was changed. Publication receipt records branch/PR state separately from main merge and deployment.

Publication: draft[PR64](https://github.com/tantalum666/FYP/pull/64), code commit`1c6c589607eb3c61e7ef0b03531d2deb50705488`, open/unmerged. The GitHub response confirmed the source head and main base;[receipt](publication.json). Final remote head is checked again after this documentation closeout.
