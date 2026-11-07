# Group 2 - Pi OpenAI through the owned VPS

7 November 2026, Asia/Hong_Kong. Latest owner instruction prioritizes connecting Pi through their existing VPS and getting OpenAI interfaces working. JD/Taobao account and transaction work remains queued; no account/login/payment completion is claimed. The user explicitly authorizes this fixed VPS route, superseding the previous direct-only runtime choice. Paid experiment budgets remain closed.

## Read scope and design

Current AGENTS/entry/handoff, product current requirements and recent decisions; focused Markdown inventory, current browser contract/research index, relay setup/client code, text/voice/computer provider transport paths, protected credential loader and configuration helper. Exact current official OpenAI computer-use, account takeover, supported-region and Realtime per-response cost documentation fetched; Realtime connections alone have no listed connection charge. A referenced VPS chat was read but current live SSH inventory is authoritative.

Existing VPS: pinned SSH identity, AlmaLinux9.7/x86_64,2CPUs/1GB memory. Existing encrypted Pi transport and management reverse relay retained. The dedicated Pi authorized key previously allowed only loopback discard port9 as its outbound target; its exact permitopen grant now allows api.openai.com:443. Original key, forced false command, restrict and reverse management port preserved. No sshd restart or global proxy/firewall/OS DNS change.

Two separate Pi services provide a pinned SSH forward and a loopback-only HTTP CONNECT bridge. The bridge accepts only api.openai.com:443; keys are not copied to VPS, TLS is not terminated by the bridge, client SNI/certificate verification and API hostname remain OpenAI. The application has one explicit OpenAI-only proxy setting; Qwen/Gemini and browser web traffic do not inherit it. An unavailable proxy does not silently retry direct. Injected test transports remain offline.

## Validation so far

VPS DNS/TLS verified and unauthenticated API401. First Pi attempt was administratively prohibited by the old per-key grant, not a model failure. After the narrow grant and service install, Pi GET/v1/models returned200with96models and both configured model IDs. Realtime initially hit a Host header formatting difference (default443omitted); acceptance was corrected for exactly the bare OpenAI hostname or hostname:443, with unchanged CONNECT target. Real WSS then returned session.created for gpt-realtime-2.1 and closed normally; no audio, response.create or inference.

101focused checks,26voice/proxy checks and357cross-provider/text/voice/job regressions passed. The final Host-header correction adds a real loopback byte-forwarding case;14bridge/route checks and Ruff passed. No CI. Stopped/checkpointed21-file Pi runtime/config backup was copied to Mac; archive and every file hash verified. Current app activation/readback follows this source commit.


## Normal runtime activated

Source9625f137is activated at /opt/desk-companion-releases/20261107-openai-vps. All284runtime source/assets hashes verified; frozen dependencies are shared from the retained previous release. No schema migration. The stopped21-file backup was copied off-device and every archived file rehashed. The configure helper selected the explicit loopback route and cleared the obsolete direct-path region flag after authenticated200and Realtime session.created.

Normal runtime readback reports text, realtime voice and computer use configured, empty configuration_error, background generation off and original local owner keys preserved. Alice/wake/application executors retain their previous state. Real Realtime handshake used no input audio or response.create and closed normally. A model-generated answer, spoken response or end-to-end wake conversation was not claimed. No paid inference and no CI.

Merchant/account planning is recorded separately in ../2026-11-07-browser-accounts; the owner selected JD/Taobao, then explicitly moved Pi/VPS/OpenAI connectivity first. No merchant credential, order, payment, booking or ticket was created.


Actual rendered Pi check: Alice visible, Desk connected, Start conversation enabled, Say Alice to wake unchecked, OpenAI Realtime/microphone off; old region notice absent, console warnings/errors empty. The Mac viewer listener had ended and was restarted with the existing pinned launcher. This does not affect the Pi's own boot-enabled VPS route. No media control was activated. Updated product/decisions/README/provider and browser contracts, research index, entry/handoff/work-log; final link/scope/publish readback follows.

Final readback: both new units enabled/active and original management relay active; both listeners bind only127.0.0.1. Actual requests for another domain or OpenAI port80were rejected403. Changed Markdown links resolve; diff whitespace and complete changed-file secret/scope checks pass. No private key, backup, database, raw screenshot or workflow is staged.
