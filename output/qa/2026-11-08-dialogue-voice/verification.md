# Group 2 · Latest-turn captions, conversation and Alice voice

8 November 2026. This record separates source tests, offline real-browser replay, provider resource creation, the failed paid audition and activation. No GitHub CI was used.

## Scope and reading

Owner requested only the newest spoken exchange on home, separate multi-round conversation history, removal of Voice input/Work conversion cards, readable dark styling and an Alice-matching voice. The preferred voice is light/young/cute with natural Mandarin, English and Cantonese. The original design uses an adult feminine voice and does not imitate a performer or existing character.

Focused reading: active AGENTS.md, START_HERE_NEXT_CHAT.md, handoff.md and product.md; decision-log.md current 7–8 November sections; complete alice-home.md, desktop-conversation.md and voice-work.md; current protocol/responsibility/cost sections of openai-alice-wake.md; conversation-work.md goal/snapshot/review/recovery sections; software-maintenance.md ownership/lifecycle sections. Read all modified implementation files and their relevant regression fixtures. Frontend debugging and React review skills were applied. Prior historical research was not mechanically reread.

Official OpenAI Docs checked transcript deltas, voice options, prompt-created custom voices and graceful usage close. Live start_ms/end_ms describe a session timeline, without a provider completed-turn event. Sources: [Live transcript deltas](https://developers.openai.com/api/docs/guides/live-conversations#transcript-deltas), [custom voices](https://developers.openai.com/api/docs/guides/custom-voices), [usage and graceful close](https://developers.openai.com/api/docs/guides/live-conversations#usage-and-graceful-close).

## Repairs and boundaries

Playback completion previously flushed display text and sometimes referenced a retired/null audio turn. Display now uses bounded timeline groups separately from audio acknowledgement. Stable speaker messages update the existing conversation RAM buffer and client list; late fragments update older messages without replacing the current response. The compact home shows the latest assistant reply and clears it for a pending new question. This is a presentation heuristic, not provider-final transcription or authority. Assistant text reaches replay only after grounding checks.

Conversation no longer mounts optional Voice input or Work conversion cards. Required approvals for requested actions remain. Dark text/bubbles/menu have readable contrast, expanded history scrolls above the nonshrinking input, and the empty compact caption no longer reserves calendar space. The 320-pixel placeholder no longer wraps into a clipped second line. Existing Work snapshot/admission APIs remain, with their review and authority requirements; the old review screen is not advertised as current navigation.

Owner-only versioned voice settings use the existing operation service. They select a Live voice and delivery style for the next session, refuse mid-call changes, and never make generation requests when saved. Cached sample playback is conditional on a real local file. Two additive private SQLite tables retain preferences/registered profiles; full private runtime backup includes them, portable personal-history export deliberately does not. No new key, frontend credential, model loop or package dependency was introduced.

## Local and rendered verification

Final backend: 2064 passed in 328.51 seconds, with two existing warnings. Frontend: 348 passed, zero failures. Typecheck, Vite build, scoped Ruff and git diff --check passed. Vite retains its existing large-chunk advisory. Commands: `.venv/bin/python -m pytest -q`, scoped `.venv/bin/ruff check`, `npm test`, `npm run build`. No CI was triggered.

Actual Chrome through CUA, in a separate 127.0.0.1:8832 QA tab, ran production capture/protocol/display code with synthetic silent capture and an offline provider. The provider waits 6.5 seconds before ready, then sends two exchanges, performs an actual local calendar_query and delivers the first answer's last fragment after the second answer. Home retained only the second answer. Conversation showed four distinct messages and zero Voice input cards. The dark user/text contrast is greater than 8:1 and assistant/text contrast greater than 12:1 in the measured fixture.

Desktop 1312-pixel width, phone393×852 and small phone320×568 were inspected. On the small phone, history ended at390px and the composer began at400px; no horizontal overflow. The history remains independently scrollable. More → Assistant style → choose Gleam → edit delivery → Save → reload preserved both fields. Those changes affected only the offline fixture. No blank page or framework error overlay; observed console warnings came from an existing MetaMask extension, not app source. Owner tabs were not resized. Private screenshots are under `~/.config/desk-companion/dialogue-voice-20261108/screens/`.

## Original voice and actual failed trial

One free prompt-created original voice succeeded. Attempt1 returned400for a short optional script_hint; attempt2 returned500with a longer hint. Readback found no saved voice from that failure. The documented minimal request without the optional hint returned200 and saved one voice resource. No audio session occurred during creation. Voice IDs/prompts/keys stay private and outside Git.

A separate USD0.25-capped real browser trial reserved USD0.249. Complete27-tool preflight counted5226input tokens; the custom voice reached session.started. It then produced no assistant speech or backend response receipt. The browser aborted silent warmup at the old five-second pre-ready buffer limit; subsequent client loss also interrupted final receipt collection. The record ended after10.2local seconds with zero input-audio seconds and no finalized provider duration. Ledger closed with USD0.249 retained as an unknown reservation, not confirmed actual cost.

Repairs keep only half a second of silent preroll until the independent ten-second connection deadline, retain the five-second bound for captured speech, handle the newer client-disconnected exception and drain final speech/backend receipts with one receiver. Offline delayed-start, disconnect-drain and grounded-history regressions pass. The successful old full-catalog wake trial remains separate historical evidence; it does not prove this new voice's naturalness. An optional additional USD0.10preview request is pending; no additional paid generation was made.

## Activation and outstanding work

Mac was idle-checked, stopped and checkpointed before a fresh11-file private backup, archive SHA49376acbeb0e46bd1e59bcef140ecdbe22bc6d865eca5bb6c61e7d67e341efe3. New API started healthy with GPT Live still configured. The original Alice · Clear & Warm profile and requested trilingual delivery were saved for the next conversation; no sample is available yet.

Pi backup was stopped/checkpointed, SQLite quick_checkpassed, active work zero,22members checked both on device and after retrieval. Archive SHA94e767e0e67323dd01be3fecc48e276791827b1b050e275194b846052d5a49db. Source00387d6activated on Pi after293file hashes. Both app/application services are active, served frontend matches the build exactly, and original owner keys/environment are unchanged. Free provider metadata readback confirmed that Pi can access the created voice; the same profile/delivery was saved there without speech generation. [Activation receipt](activation-summary.json). Existing credentials, environment, VPS path and deferred power investigation remain separate.

Remaining: actual trilingual audition of the created voice and real human/acoustic/physical Pi acceptance are not passed. No original audio or user speech was published. Current core UI has offline end-to-end evidence; paid provider acceptance of the new cold-start path remains open. Next step is one capped voice-only sample after fresh approval, then cache that actual sample for repeat playback without generation.

## Final closeout

Normal Web5190, phone5190 and Pi8891preview show Desk connected; Pi reload fetched the new asset names and displayed Alice. Normal Web Assistant style visibly selects Alice · Clear & Warm. Temporary offline browser tabs and server8832are closed; phone viewport override was cleared. The real pages contain no synthetic capture. Current owner pages were returned to Alice home with no cloud call in progress. These are configuration/rendering observations, not a new acoustic test.

Updated AGENTS, START, handoff, product, decision-log, work-log and the focused Alice-home, voice, desktop-conversation, maintenance, voice-work and conversation-work contracts. Source/credentials/private voice ID/workflow diff checks and referenced local-file checks passed. An initial broad key-pattern scan matched the substring in a pre-existing desk-companion path; the corrected boundary-aware added-line scan passed. No new workflow/dependency or private backup/audio entered Git.
