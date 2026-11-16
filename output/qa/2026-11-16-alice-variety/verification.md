# Group 2 · Contextual Alice motions and progress audit

16 November2026. Same motion PR123, based on main6153b41d. The owner still found the character rigid and wanted additional actions. No new model/animation asset, dependency, paid request or CI.

## Implementation

`motion-cues.ts` selects short contextual gestures with varied quiet intervals using the existing renderer clock. The action set is wave, smile/nod, curious tilt, compact open-hand explanation, glance, shoulder relaxation and pondering. A user greeting can interrupt automatic idle movement; rapid repeated greetings do not restart an arm mid-lift. Conversation-state changes preempt idle gestures. Input coalescing and pose sampling share the same eased envelope so a visually finished gesture immediately accepts the next click.

`alice-motion.ts` owns upper-body curves and shoulder/head/hand coordination. Listening/speaking no longer run continuous fixed nod/arm oscillations. The first broad explanation pose was reduced and brought forward after actual rig/render inspection; tests check both palms, torso clearance and fingertip extent. Feet/root and Alice size stay unchanged. VrmViewer keeps one render loop, separate elapsed gesture time and capped spring-physics time, with a short playback hold to avoid toggling poses between audio samples. Original state-only bridge and output-mouth ownership remain.

## Verification and caught failures

- Final main frontend387tests, compatible-runtime366tests, TypeScript and production builds pass. Existing bundle-size warning remains; no dependency was added.
- Actual Alice rig checks both wave/explanation hands, forward palm, compact fingertip extent, torso clearance and planted feet. Cue tests cover quiet periods, context preemption, rapid taps, visible-end click acceptance, missed-time behavior and finite/continuous clip endpoints.
- Real app checks through CUA at desktop1440×900 and phone393×852: all four click variants appeared. Final phone cycle wave/nod/curious/explain returned to idle, one canvas, document width393without horizontal overflow. Desktop snapshots/return states were observed; one bounded capture loop hit its final deadline, followed by a direct observed idle state. This retained harness result is not represented as a successful timing measurement.
- A phone sequence exposed a real quiet-tail bug: the pose had become visually idle but the old input deadline still rejected a new tap. Shared envelope fixed it; a regression and the complete final phone sequence passed. Initial connection check on unregistered5192was rejected; used existing trusted5190/8831instead of widening allowed origins.
- More navigation froze frame count985→985. Reduced-motion emulation removed the canvas/hello control; restoration yielded exactly one loaded canvas. All browser emulation is restored. No relevant app console errors. A transient weather-unavailable state later recovered from HKO without a source change.
- Clock sampling under6×CPU emulation:2.215wall seconds/2.19motion seconds/57frames; under20×:2.218wall seconds/2.21motion seconds/52frames. These are short Mac browser observations, not a Pi/low-frame-rate hardware benchmark.
- Actual native iPhone17Pro/iOS26.5Simulator built/installed/launched. Pi8891could not connect, so the UI was checked with a process-only Mac8831launch override; no Configure operation changed the persistent preference; direct plist readback showed it is absent (the prior Pi URL was a launch argument). Native recording and extracted frames show the model/idle glance. Final quiet-tail source was rebuilt and its normal connected native screen checked. Native tap/soft-keyboard, physical iPhone and real voice were not newly accepted.

## Runtime delivery

The same narrow motion overlay was built on the retained520ab563compatible frontend, avoiding unrelated main/Grok backend-dependent changes. Mac's running API/data stayed in place. The new frontend was staged, all68candidate files verified, old hashed assets retained, and an atomic symlink replacement served the new index. API PID28112did not change; A3/version9 and protected file hashes matched before/after. Previous frontend remains available as `dist-motion-20261113-v2`. Active index SHA256:6895c5cd85fc6383218b88df2b2e295d5b75771e064fd29743e23dd32f5bcfc3.

Pi's existing pinned relay check returned255/unreachable. This round did not deploy to or restart Pi, alter VPS/network policy or resume power diagnosis. Its last verified frontend activation remains13November; physical animation was unverified then and remains so. The rebuilt Simulator's current Mac launch is explicitly separate from Pi acceptance.

## Personal-agent audit and evidence

[Current capability map](../../../desk-companion/docs/personal-agent-status.md) records fresh GitHub/local connection checks and dated actual acceptance. Gmail is locally stored connected, Google Calendar configured/unconnected, Microsoft apps unconfigured/unconnected, and MCP configurations empty. No fresh token validity/mail-send/merchant trial is inferred. Main's reviewed additions and ordinary runtime delivery differ; real owner browser takeover, continuous inbox follow-up and transactions remain open.

Private evidence: `~/.config/desk-companion/alice-motions-20261116/` contains test/build logs, connection status, actual web/phone gesture screenshots, browser timing/loop receipts, native recordings and activation/rollback manifest. Test-only pose-search/review files are excluded from publication. The temporary model review server is stopped at closeout; normal Mac8831is the delivered entry. Native online checking uses the Mac launch override described above.

Updated product, avatar/home contracts, status/delivery/research indexes, decision/work logs and concise handoff/entry. Local links, staged scope and secrets/artifacts are checked before pushing to existing PR123. Source publication is separate from merge; no new merge is included. One next product step is the real same-browser owner-control/return flow on existing JobService.

Closeout: a deliberate interruption removed CUA before its completion-summary call and stopped the temporary Vite servers. Existing screenshots/recordings and observed outcomes were retained; no unavailable tool was called. Normal Mac8831was rechecked healthy. Persistent native-origin readback corrected the earlier saved-Pi-address assumption.

Publication: source0d53f4e2matched the remote head of [PR123](https://github.com/tantalum666/FYP/pull/123), still open/unmerged. [Receipt](publication.json). The subsequent commit records this result only.
