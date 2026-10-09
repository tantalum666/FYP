# Full-body 3D avatar verification

9 October 2026 · Group 2 · M2 Mac development environment. Flow: Assistant / independent avatar / device scene → licensed full-body VRM → state previews and measured playback mouth motion → stop, mirror, replace, recover.

## Scope and source

- User requested a Razer AVA-like full-body anime companion, and selected a female character. The pixiv development sample is replaceable; no final character art or optical assembly is claimed.
- Initial main: `ccfac48ce8c68e6f9c8796911bbe5f35728d7807`. Work branch: `codex/full-body-3d-avatar`.
- [Full initial reading](reading-record.json): 127 project-owned Markdown files, 11,994 lines, 47 chunks; completed at 22:53:28+08:00. Chunk 18 was re-emitted alone after truncation. Compaction resumed this same record. Generated QA, runtime, dependencies and builds are excluded, not historical research.
- Official model commit `ff42fae4fcee1fcbca2cd262c7f5f8cbddeaf5ab`, SHA256 `12c2b97e95e700783a6a550dc0eee2d7880aeedccef9ae67bc4c5a2f0f2631a2` verified against the fixed upstream URL. 10,776,032 bytes; 36,470 triangles / 13 primitives / 18 textures. Licence text, copyright and embedded permissions retained.

## Automated checks

| Check | Result | Evidence |
|---|---|---|
| Frontend regression and new presentation tests | 22 passed | [Log](frontend-tests.txt) |
| Backend voice / tool dispatch / completion edge regression | 26 passed; existing Starlette/httpx deprecation warning | [Log](backend-voice-tests.txt) |
| TypeScript and Vite production build | Passed | [Log](build.txt) |
| npm audit | 0 reported vulnerabilities after source-map-js update | [JSON](npm-audit.json) |
| Original files and main calendar | 107 hashes unchanged; seven event rows identical to the prior private backup | [Preservation](preservation.json) |

The 26 targeted backend checks are not a rerun of the previous 149-test suite. No backend business or database schema changed. The 3D renderer is a separate lazy chunk (~1.10 MB minified / ~288 kB gzip), with a separate 10.78 MB model; Vite reports its size warning. It is not loaded merely to view an ordinary calendar. Three.js emits an upstream Clock deprecation warning through R3F. These warnings are recorded, not suppressed.

## Actual browser checks

Browser plugin skill absent; available CUA in-app browser was used for all UI operations and scoped developer checks. No external Playwright or native shell UI automation was used. Page title `Desk Companion` and expected local routes were confirmed; meaningful DOM, canvas and no framework overlay observed.

- Main preview: `http://127.0.0.1:5190/?surface=avatar`. Normal original owner session; no main preferences or events changed.
- Isolated fictional workspace: `http://localhost:5191/` → API8833, private `.runtime/avatar-qa-20261009/`. Separate hostname avoided replacing the main cookie. Existing test credentials were read into the browser tool without output and cleared after sign-in.
- **Full-body / state:** model reports ready; head and feet fit; idle, listening, speaking and posture-attention controls are available. Local previews are labelled and call no provider or tool.
- **Actual synthetic output / mouth:** browser analyser levels observed `0.27 → 0.66 → 0.35`; rendered mouth weights `0.14 → 0.51 → 0.40`. After output ended, state became idle and both values returned `0.00`. [Close view](mouth-check.png). This is synthesized vowel playback, not model speech quality.
- **Pause / mirror:** paused renderer reports paused and mouth zero. Only the viewport has `matrix(-1,0,0,1,0,0)`; header transform remains none. Restore / Live cancels the local preview.
- **Reduced motion:** browser emulation observed `animation=reduced`; override cleared. Real background-tab visibility transitions were not proved by IAB, which reported both bound surfaces visible. Visibility / intersection handling is implemented but is not claimed as an observed OS background test.
- **English desktop:** 1280×800 actual DOM dimensions; [listening](desktop-listening.png) / [speaking](desktop-speaking.png).
- **Simplified Chinese phone size:** 390×844, document scroll width 390; full body and controls accessible; [image](mobile-zh.png). Browser viewport check does not prove iPhone native performance.
- **Independent device scene:** saved Companion & next event in isolated workspace; 1024×600 actual DOM, time / character / next schedule / posture / touch management visible; [image](device-1024x600.png).
- **Model replacement:** invalid `.vrm` rejected while current sample remains ready; selecting the legitimate local sample produced ready with its model name; no upload endpoint. Restore returned to bundled source. Local files use their own licence, not a misleading pixiv link.
- **Clean output:** black computed background, no visible header / state labels, mirrored viewport; [image](clean-mirrored.png). Keyboard-return link retained.
- **Failure / recovery:** scoped test invoked `WEBGL_lose_context` on this page's own canvas; localized error / Retry / calendar return appeared. Retry recreated the renderer and reached ready. [Failure](webgl-error.png). No persistent GPU / browser setting was changed.
- **Console:** normal application flow had no relevant error; upstream Clock warnings remain. Injected context loss is a test condition, not a production failure.

IAB high-level viewport control applied to a different selected surface, and ordinary screenshot capture did not reliably match emulated dimensions. Responsive proof therefore used tab-scoped CDP metrics, read back actual DOM bounds, and saved unedited CDP screenshots with matching clips. The initial wrong-size device capture was replaced. Two attempted crop frames captured a different region and were discarded. A Fetch fault-injection attempt returned a stale unrelated Document event; Invalid InterceptionId was not counted as a test result. Patterns were cleared with `Fetch.enable({patterns:[]})` and the page reloaded; the successful failure test used actual local WebGL loss instead.

## Review and corrections

- Removed the SVG placeholder and added bounded bone / expression motion without moving calendar, task or authorization logic into the render loop.
- A Canvas fallback React effect originally fired even with working WebGL and caused a false unavailable state. It was removed; loss listeners now have scoped cleanup, and actual loss / retry passed.
- Pausing could leave a partially open mouth after one demand frame; inactive presentation now closes it immediately.
- Same-window playback delivery remains available without BroadcastChannel. Silence, stale / invalid samples and interruption reset are covered.
- Local-model attribution no longer points to the bundled pixiv licence. Restore cancels pending local previews; file / async result generations protect replacements and unmount.
- First patch combined delete/add of one path and was rejected atomically. Two harness fixture writes used the wrong working directory and created no file; paths were corrected before successful tests. These are not counted as completed checks.

## Preservation and delivery

School originals / proposal / log sheet, Group 2 identity and retired Senplate content remain unchanged. No raw personal media, provider calls, microphone permission, hardware action, server login, purchase, invitation, external message or school submission occurred.

The first directory-wide secret scan also inspected intentionally ignored private runtime files and reported 22 local credential occurrences. Its redacted report was moved into the ignored private research directory, not included in Git. The deliverable is checked using staged-file scanning and a comparison against local private values; final results are recorded in validation.json / gitleaks-staged.json.

Updated: product, root/software READMEs, architecture, operator guide, device display specification, third-party notice/licences, new avatar contract, decision log, handoff and work log. Internal links, group terminology, asset provenance and deliverable existence are checked in validation.json. Staged Gitleaks scan found 0 items; 15 locally private values were compared with 47 initially staged files without matches. QA8833 / 5191 stopped, main8831 / 5190 retained; browser overrides and interception cleared. GitHub branch / PR outcome is appended after actual push and readback.

## Remaining limits

Final character art, detailed visemes, real cloud voice / interruption / AEC, same-origin bridge with real provider output, cross-device / Python audio bridge, Pi thermal / GPU / parallel-workload performance, native iPhone rendering, optical/fan real-time input and actual posture/hardware accuracy remain unverified. The 30 Hz schedule is a target, not a measured hardware result. The avatar cannot approve tools or replace the mandatory fixed-camera posture reassessment loop.

Shutdown readback initially ran before Uvicorn finished its graceful exit; the first assertion failed and was not used as proof. A later completed-process / port readback confirmed QA closed. Vendor build-log trailing whitespace was normalized without changing diagnostic content.

## GitHub readback

Software commit `c866d32a8c108509df4604234d2355bab92cdccc` was pushed to the private repository branch `codex/full-body-3d-avatar`. [PR #4](https://github.com/tantalum666/FYP/pull/4) was created and attached to the chat. Its returned head matched that commit; base `main` remained `ccfac48ce8c68e6f9c8796911bbe5f35728d7807`. No merge was performed. A following documentation-only closeout records service cleanup and PR delivery; tested application code remains unchanged.
