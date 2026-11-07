# Group 2 · General browser work and OpenAI

6 November2026. The owner requested fixing/merging all pending PRs, broader
shopping/booking/computer use, and OpenAI defaults. They subsequently selected
**general browser capability first, without choosing particular merchants**.
This supersedes the former Qwen-default runtime choice and avoids treating a
fixed office demonstration as general personal-agent acceptance.

## Refreshed primary evidence

OpenAI's current [computer-use guide](https://developers.openai.com/api/docs/guides/tools-computer-use)
supports structured `computer_call.actions` and screenshot replies through the
Responses API. Its [model page](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
lists image input, structured output and computer use for GPT6.1Sol. The SDK
helpers are optional: this project preserves its existing HTTPX adapter boundary
and implements the documented native exchange separately from business tools.
The browser driver supplies observations/actions; it is not a model-generated
shell or JavaScript executor.

Grok Bot describes a persistent computer with retained browser sessions and
structured connectors, with user takeover for sensitive steps.
[Computer and apps](https://docs.x.ai/grok-bot/computer-and-apps).
Its credential and payment facilities are separate services; a model API does
not supply Vault or completed-order evidence.
[Vault](https://docs.x.ai/grok-bot/vault).
For FYP, this motivates resumable browser state and explicit outcome records,
without claiming a third-party account or payment integration exists.

Muse's published architecture separates the runtime, credentials, connectors,
browser mediation and independent action/network authorization.
[Architecture](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse).
FYP retains its independent PermissionService and executor checks. Its current
browser request filtering is not equivalent to Muse's host-level enforcement,
credential surrogation or complete transaction system.

Your dot retains assigned work between conversations, can wait for missing input,
and distinguishes a finished run from an achieved user outcome.
[Tasks and memory](https://learn.chatgpt.com/docs/dots/tasks-and-memory).
FYP therefore links execution to existing jobs/tasks, keeps observed page state,
and labels browser preparation as reviewable evidence rather than a purchase,
reservation or issued ticket.

These are vendor descriptions read on the date above, not measured competitor
reliability or access to proprietary code. Earlier research remains indexed in
[the research entry](personal-agent-research-index.md).

## Implemented direction

The new public-browser executor is registered on the existing JobService queue.
The owner selects a goal, entry page, optional additional sites and screenshot
sharing. Ask first/Full access remains separate from that data-sharing choice.
New grants do not approve older pending work. Native model actions are bounded
to the supplied1280×800screen; clipboard/system shortcuts and arbitrary code are
rejected. Browser creation uses a fresh profile, normal sandbox and no provider
key in the worker environment.

Browser state can continue only through an explicit new job that binds the
previous verified state, task and site scope. Lost provider responses are not
automatically resent. Stopping can preserve a normally closed observed page for
a new reviewed continuation; unconfirmed cleanup blocks further admission.
Restored portable job records cannot replay browser inputs.

The current scope is public-page research and preparation. HTTP writes, extra
navigation sites, sensitive fields and final order/booking controls stop for the
owner. This is deliberately not an authenticated merchant/payment integration.
POST-based search or cart services may therefore require handoff too. Specific
merchant adapters and independent order/ticket verification remain later work.

## Evidence and access

Actual Chromium tests cover a retained shopping cart with price/quantity/coupon
changes, a flight form with people/baggage/date/fees and next-day arrival, explicit
stop/continue, and live public-catalogue navigation. Planning is scripted through
mock Responses; browser input/screenshots are real. No order or booking was made.
[Current QA](../output/qa/2026-11-06-openai-agent-merge/verification.md).

Mac's existing FYP key returned200from the free model-list endpoint and included
the selected text/Realtime models. Pi returned403with
`unsupported_country_region_territory`. The [official error guide](https://developers.openai.com/api/docs/guides/error-codes#api-errors)
identifies this as a regional access refusal; the [supported-region page](https://developers.openai.com/api/docs/supported-countries)
governs availability. Configuration is not successful inference. No model
generation was requested and no region refusal was routed around.

For public browser traffic only, the inspected Mac uses an existing local proxy
with fake-IP DNS. The new optional browser setting explicitly selects that local
proxy and validates public DNS via bounded HTTPS DNS. It changes no OS/VPS
settings and is not applied to OpenAI provider requests.
[Playwright proxy support](https://playwright.dev/python/docs/network#http-proxy),
[Google HTTPS DNS format](https://developers.google.com/speed/public-dns/docs/doh/json).
This remains routing/preflight protection, not a proven OS egress sandbox.
