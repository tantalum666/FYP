# Group 2 · Listening in Alice’s conversation

On the expanded desktop home, the active voice controls used 222 CSS pixels of height. The corrected row uses 48 pixels. At the reported 1267 × 720 viewport the transcript gains 247 pixels, and the finished Kiwi research card replaces its queued status. A new caption follows the conversation when the owner is at the bottom and keeps older messages in place when the owner scrolls back. [Desktop before](before-desktop.jpg) · [Desktop after](after-desktop.jpg).

| Viewport | Entire area below the transcript, before → after | Scrollable transcript, before → after | Final result |
| --- | ---: | ---: | --- |
| Desktop, 1267 × 720 | 305 → 58 px | 201 → 448 px | The completed quote, purchase request and reply remain readable while listening. |
| Phone, 390 × 844 | 292 → 102 px | 250 → 440 px | The purchase request and reply are fully visible. Four 44 × 44 px controls share the voice row. |
| Phone landscape, 844 × 390 | 292 → 50 px | 22 → 204 px | Both messages fit and the stop and microphone controls remain on screen. |

The entire area includes the voice row, permission and wake controls, and applicable spacing. Values are CSS pixels rounded to the nearest integer. The desktop and wide landscape layouts place preferences alongside the call. The portrait layout keeps them in a second row. [Phone](after-phone.jpg) · [Phone landscape](after-landscape.jpg) · [Measured geometry and interaction receipts](measurements.json).

## Actual interactions

The browser opened the ordinary Home UI on loopback. Desktop used the default route. Phone used its existing `?surface=phone` entry. The desktop test enabled **Say Alice**, observed the waiting state, and used a controlled wake event to open the voice session. The phone tests tapped **Start conversation**. A real Chromium microphone stream, audio worklet, voice ticket and WebSocket handshake produced the listening state. The microphone was synthetic. The loopback server supplied the flight quote and caption events without connecting to a provider.

While listening, the test approved the ordinary research card, observed **Using the browser**, delivered a completed quote from the same job, then received the spoken purchase request and Alice’s reply. The original UI still displayed “Research started” twice after completion. One copy came from the decision notice and the other from a saved conversation turn. The corrected UI showed zero copies and retained the current job card. A later caption arrived while the reader was at the top of the transcript. The reading position held, and the conversation could still be scrolled to its latest message.

The test opened and closed the permission popover and camera panel, sent **Stop speaking**, muted the microphone and typed into the focused composer. On the image-capable phone fixture it also opened the image/screen sharing controls and closed them without sending anything. Every voice action had a 44 × 44 pixel hit area on the final build. The permission popover fit inside all three panels. Each tested page had the correct title, meaningful content, a connected desk, zero uncaught page errors, no framework overlay and a clean browser console.

## Version and checks

The baseline was `412721b2`. Its frontend source matched the installed release’s `08200201` frontend source. The layout change is `d6ffb509`, and the tested follow-up is `3e3630d4`. The call now uses one horizontal status-and-actions row, the chat allocates the remaining height to the transcript, and the voice-to-text control focuses the editor. The research turn points to its existing job instead of storing a permanent startup message. [Interface contract](../../../desk-companion/docs/ui-copy.md).

A first revised desktop run exposed a layout update that could leave the reply 60 px below the viewport. The final transcript observes its viewport and its contents, including late job-card and font sizing. An upward scroll pauses following. Returning to the bottom enables it again. The final source passed six independent runs, including four desktop sessions, one portrait and one landscape session. All six finished at the latest reply and kept an earlier reading position when a later caption arrived.

TypeScript type checking, the Vite production build, 56 focused frontend tests and `git diff --check` passed. The focused suites cover proposal decisions, conversational transcripts, voice lifecycle, audio, visual sharing, voice-work rendering and browser workflow. Google Chrome 157.0.8103.80 ran through the installed Playwright package. The Browser plugin skill was unavailable in this session. The original screenshot was inspected as layout evidence and kept outside the repository. Its 2534 × 1438 image corresponds to approximately 1267 × 719 CSS pixels at 2× scale.

Read the repository agent instructions, current product and handoff, recent calendar-aware and commerce decisions, the interface-copy contract, and the active conversation, audio, wake and job-card implementation. The branch contains the focused interface contract, code, regression coverage and this QA record. The integration owner handles shared handoff and release state. This acceptance used a synthetic microphone and local provider fixtures. A live paid voice session, physical phone and deployment were outside this run.
