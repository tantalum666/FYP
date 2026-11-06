# Group 2 - Pi OpenAI through the owned VPS

7 November 2026, Asia/Hong_Kong. Latest owner instruction prioritizes connecting Pi through their existing VPS and getting OpenAI interfaces working. JD/Taobao account and transaction work remains queued; no account/login/payment completion is claimed. The user explicitly authorizes this fixed VPS route, superseding the previous direct-only runtime choice. Paid experiment budgets remain closed.

## Read scope and design

Current AGENTS/entry/handoff, product current requirements and recent decisions; focused Markdown inventory, current browser contract/research index, relay setup/client code, text/voice/computer provider transport paths, protected credential loader and configuration helper. Exact current official OpenAI computer-use, account takeover, supported-region and Realtime per-response cost documentation fetched; Realtime connections alone have no listed connection charge. A referenced VPS chat was read but current live SSH inventory is authoritative.

Existing VPS: pinned SSH identity, AlmaLinux9.7/x86_64,2CPUs/1GB memory. Existing encrypted Pi transport and management reverse relay retained. The dedicated Pi authorized key previously allowed only loopback discard port9 as its outbound target; its exact permitopen grant now allows api.openai.com:443. Original key, forced false command, restrict and reverse management port preserved. No sshd restart or global proxy/firewall/OS DNS change.

Two separate Pi services provide a pinned SSH forward and a loopback-only HTTP CONNECT bridge. The bridge accepts only api.openai.com:443; keys are not copied to VPS, TLS is not terminated by the bridge, client SNI/certificate verification and API hostname remain OpenAI. The application has one explicit OpenAI-only proxy setting; Qwen/Gemini and browser web traffic do not inherit it. An unavailable proxy does not silently retry direct. Injected test transports remain offline.

## Validation so far

VPS DNS/TLS verified and unauthenticated API401. First Pi attempt was administratively prohibited by the old per-key grant, not a model failure. After the narrow grant and service install, Pi GET/v1/models returned200with96models and both configured model IDs. Realtime initially hit a Host header formatting difference (default443omitted); acceptance was corrected for exactly the bare OpenAI hostname or hostname:443, with unchanged CONNECT target. Real WSS then returned session.created for gpt-realtime-2.1 and closed normally; no audio, response.create or inference.

101focused checks,26voice/proxy checks and357cross-provider/text/voice/job regressions passed. The final Host-header correction adds a real loopback byte-forwarding case;14bridge/route checks and Ruff passed. No CI. Stopped/checkpointed21-file Pi runtime/config backup was copied to Mac; archive and every file hash verified. Current app activation/readback follows this source commit.
