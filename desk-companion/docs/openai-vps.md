# Group 2 - Explicit OpenAI route through the owner VPS

7 November 2026. The owner requested Pi -> existing VPS -> OpenAI after the direct Pi request returned unsupported-region. This document describes the verified requested route; it does not claim direct Pi access, a provider-policy exception, successful audio conversation or paid inference. [QA](../../output/qa/2026-11-07-openai-vps/verification.md).

The existing encrypted transport provides pinned SSH to the owned VPS. A separate desk-openai-forward service maps Pi127.0.0.1:18443 to api.openai.com:443. The dedicated SSH key permits that exact outbound destination and retains its prior restricted reverse-management grant. The original management service is unchanged.

The small desk-openai-connect service listens on Pi127.0.0.1:17891, accepts only CONNECT api.openai.com:443, bounds headers/concurrency/lifetime and forwards opaque TLS bytes to18443. It stores no credentials or request bodies. HTTPX and websockets use DESK_OPENAI_PROXY_URL=http://127.0.0.1:17891 explicitly; their target remains the pinned HTTPS/WSS OpenAI endpoint with certificate verification enabled. Generic environment proxies are ignored. Other providers and public-browser page traffic remain separate.

The configuration helper accepts --proxy and validates a credential-free literal loopback URL. Changing transport invalidates pending browser/voice revision bindings. A supplied MockTransport remains offline even when a proxy is configured. The old region-unavailable flag is cleared only after successful live authentication on the selected route. Failure of this route does not trigger a direct retry or a provider switch.

Source: scripts/pi/openai_connect.py and setup_openai_tunnel.py; backend/desk/openai_transport.py owns provider selection. The two generated units use the original pinned relay key, NoNewPrivileges and read-only system/home protections. No general SOCKS listener or external listening port is added.

Recovery: keep the original service.env/unit/source backup. Restoring it returns to the prior direct-only unavailable state. Disabling only desk-openai-connect and desk-openai-forward does not disable the original SSH management relay. Restore the dedicated key's previous grant from its private VPS backup if removing the route entirely; preserve any later independently authorized changes.

Free acceptance: GET /v1/models through the explicit proxy and a Realtime WebSocket session.created followed by close. Do not send audio or response.create for this check. [Realtime per-response cost guidance](https://developers.openai.com/api/docs/guides/voice-latency-cost?api=realtime#per-response-costs). A model answer and human voice conversation are separate tests with separate usage reporting.
