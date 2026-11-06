# Group 2 - Pi OpenAI route and account-work continuation

7 November 2026. Active checkout: `/Users/tantalum/.codex/worktrees/account-handoff-20261107/FYP`, branch `codex/openai-vps-20261107`. Source9625f137is deployed on Pi. This follows the PR94browser milestone; prior PRs73/87/88/89-92were merged viaPR93. Latest owner priority: first connect Pi through the owned VPS and make OpenAI interfaces work. They selected JD or Taobao for the later account/takeover work. Only red-LED investigation is deferred; no CI and paid experiment budgets remain closed.

## Current verified state

Pi uses `/opt/desk-companion-releases/20261107-openai-vps` with original schema3data, identity keys, Alice/wake assets and office executors preserved. Text, Realtime and native computer clients now use the explicit OpenAI-only loopback CONNECT route; generic proxy variables/other providers/browser-page traffic are untouched. The former direct-route region flag was removed only after the selected VPS route succeeded.

Actual Pi GET /v1/models: HTTP200,96models, configured GPT6.1Sol and Realtime2.1present. Actual Realtime WSS: session.created for gpt-realtime-2.1, normal close, no audio or response.create. No generated model answer or spoken output was tested. Normal service readback has text/voice/computer configured, empty configuration error, background generation off. [Pi interface](http://127.0.0.1:8891/?surface=device) visibly shows Alice, enabled conversation button, unchecked Say Alice to wake and OpenAI Realtime/microphone off. No media permission was enabled by this check.

The existing encrypted SSH transport remains. Dedicated VPS key permitopen now names only api.openai.com:443, with forced false command and reverse-management grant retained. Two new Pi units, desk-openai-forward and desk-openai-connect, start at boot and retry failures. TLS stays between Pi and OpenAI; no API key was copied to VPS. The original management relay is unchanged. Other locations and a physical reboot were not retested.

[Transport contract](desk-companion/docs/openai-vps.md), [QA](output/qa/2026-11-07-openai-vps/verification.md), [receipt](output/qa/2026-11-07-openai-vps/runtime-receipt.json).357provider/voice/text/job checks passed, followed by14final bridge tests and Ruff. The final bridge fix accepts the standard omission of443in WebSocket Host headers while keeping the CONNECT destination fixed. Frontend source was unchanged.

## Recovery and operating paths

Private material: `~/.config/desk-companion/openai-vps-20261107`. Latest21-file stopped/checkpointed backup is20261107-before-openai-vps.tar.gz; copied to Mac and every archived file rehashed. Retain the previous release because its frozen environment is reused by the new release. activate_pi_vps.py can restore the preceding unit/autostart/environment if activation fails. VPS original key restriction is backed up privately at/root/desk-openai-vps-20261107/authorized_keys.before. Do not use the historical zero-byte Pi backup.

Pinned remote helper remains `~/.config/desk-companion/pi5-dorm-ethernet-20261104/pi_remote.py`; it still depends on the network-recovery checkout. The Mac8891/5901viewer launcher was restarted for actual UI QA; Pi's new OpenAI path does not depend on Mac being online. The Mac app remains the prior direct OpenAI configuration, not a new native build.

## Remaining work and one next step

The generic public browser in PR94passed real Mac/Pi browser execution with scripted planning. Private merchant accounts, interactive takeover, actual payment, booking/ticket receipt verification and autonomous voice-to-browser are not implemented yet. The Nov7 account-work record contains findings only; no JD login or transaction occurred.

Next: implement the real JD account/browser takeover path on the existing job/permission system, keeping owner input and sensitive screens out of model observation during takeover, then verify a real owner-completed login and deliberate return of control. Any paid-model test needs a fresh explicit budget; a concrete purchase/flight still needs item/itinerary/amount and transaction authority.
