# Group 2 · Connected Google and Microsoft apps

Updated 17 November 2026. The owner chose an app catalog with browser sign-in/consent and rejected application-password entry. The built-in catalog uses official OAuth and provider APIs. It is not an unrestricted plugin installer, and does not inherit Codex's account tokens. Existing public/synthetic MCP connectors retain their separate contract. The new [selected-thread follow-up and reply](mail-thread-followup.md) uses those same grants and business services; its live grant/real-provider acceptance remains separate.

## Available operations

| Connection | Implemented operations | Actual account status this round |
|---|---|---|
| Gmail | Bounded previews; selected-thread metadata follow-up; reviewed new email or same-thread reply | 8November FYP self-send/readback;16November Mac/Pi consent and actual profile reads passed. New follow-up/reply has local synthetic-provider evidence only |
| Google Calendar | Read primary-calendar events; existing preview and explicit local import | 16November Mac/Pi consent and bounded primary-calendar reads passed |
| Microsoft 365 | Outlook previews, selected-thread metadata and reviewed sending/reply; calendar events; OneDrive directory; To Do; OneNote | Software/protocol tests; personal-account setup remains blocked at human verification. No live FYP Graph grant claimed |
| Microsoft Teams | Work/school chat list and bounded messages | Organization authorization deferred |
| SharePoint | Followed sites and document-library lists | Organization authorization deferred |

Word, Excel and PowerPoint are represented by OneDrive file metadata. This release does not read or edit arbitrary document contents through Graph. Existing local Calc/Writer/browser jobs remain separate. Connecting an account does not start unattended mailbox monitoring, accept invitations, send chat messages or place orders.

## Responsibilities and authority

`app_specs.py` holds bundled provider identities, exact callback routes, scopes and capabilities. `app_oauth.py` owns PKCE S256, one-use state, an owner-session-bound ten-minute result, encrypted verifier/tokens, refresh, cancellation and account versions. The existing Calendar adapter reuses it via `google_oauth.py`; there is no second credential implementation. A callback chooses only a registered URI matching the request origin and redeems the same URI. Unregistered origins fail rather than redirecting to a different desk. Cancellation, replacement, session expiry and late callbacks cannot restore a grant.

`AppConnectionsPanel` opens an official Google/Microsoft window from a click gesture. It polls only FYP's owner-bound flow status while authorization is pending. It does not trust popup closure as success, because cross-origin window isolation can change that signal. Parent clock/translation renders do not tear down the popup. No password, token or client secret goes through the frontend. Permissions are described in Access details; ordinary home UI contains no connector diagnostics.

`connected_app_data.py` and `microsoft_apps.py` own fixed Google/Graph destinations and bounded GET operations. URLs are not model arguments. Returned emails, events and chat messages are untrusted evidence, never instructions or authority. Account and privacy revisions are checked around reads. No remote pagination URL is followed. Gmail returns at most ten metadata previews; other reads return at most twenty items and a 48 KB result. Large mailbox latency and live Microsoft behavior remain unverified.

`outbound_mail.py` reuses AssistantService proposals and owner decisions. Mail functions share the canonical catalog used by text and Live; no separate mail agent or OAuth store is added. Sending and background-follow-up confirmation are not model tools and are not silently covered by Full access. With multiple senders the assistant asks which account; `me` resolves to the selected authorized account. Drafts bind the sender account/version. Recipient and single-line subject validation prevent header injection. Proper replies additionally bind the original message, exact subject, recipient and provider thread; source changes and unknown writes are not replayed.

The durable `outgoing_mail_attempts` record reserves a possible send before network dispatch. Known connection/rejection failures remain distinct from unknown writes. Repeated confirmation recovers an accepted receipt; uncertain writes are not resent, cancelled as if unsent, or reset after restart. Gmail's message ID and Graph's HTTP202/request ID mean provider acceptance, not delivery. Gmail may rewrite the submitted MIME Message-ID; independently read back the provider message ID, recipient and content. This round's self-email was found in both SENT and INBOX with exact Test content, one attempt. No third-party recipient was contacted.

## Operator setup and lifecycle

Private config uses `DESK_GOOGLE_CLIENT_FILE` / `DESK_MICROSOFT_CLIENT_FILE`, a mode600 owner file containing a web client ID, optional Microsoft/public-client secret, and exact registered redirect URIs. Google requires its server client secret. Environment variables remain compatible. Credentials, encrypted runtime stores, original voice metadata and backups stay outside Git.

The approved FYP-only Google project is External/Testing with the owner as its sole test user. Gmail API and Calendar API are enabled. Current local callbacks are loopback ports5190,8831and8891 with `/api/apps/gmail/callback` and `/api/google/callback`. Public mobile/native callbacks need a separate supported origin setup; the local desktop URL is not a phone-reachable service. Native account tokens belong to each host's encrypted runtime, and are not copied into portable personal exports.

Testing-mode Google refresh grants can expire and require Reconnect. Google disconnect revokes its token; because both Google connections use the same client, provider grant revocation can affect the other Google connection. Microsoft disconnect removes local tokens without claiming a global Microsoft sign-out. Work/school tenant policy and administrator approval still apply. The VTC tenant previously denied developer access. On16November the owner requested authorization again, but personal-account device login stopped at CAPTCHA difficulty. Do not bypass/repeatedly trigger it or reuse the expired device code. Mac and Pi have separate encrypted account stores. The owner completed both Pi grants later on16November; Pi provider reads passed independently, without copying Mac tokens. [Current QA](../../output/qa/2026-11-16-agent-runtime/verification.md).

## Sources and evidence

[Google web-server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server), [Gmail send](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send), [Google Gmail MCP preview](https://developers.google.com/workspace/gmail/api/guides/configure-mcp-server), [Microsoft authorization code flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow), [Graph sendMail](https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0), [Teams chat messages](https://learn.microsoft.com/en-us/graph/api/chat-list-messages?view=graph-rest-1.0), [SharePoint followed sites](https://learn.microsoft.com/en-us/graph/api/sites-list-followed?view=graph-rest-1.0), [Work IQ MCP](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/work-iq/mcp/overview).

Google's MCP preview and organizational Work IQ still require their own developer/account configuration. They do not make another product's grant transferable or prove all account types and operations work. This implementation deliberately shares the app-authorization UX while using the provider API needed for each implemented operation. [Current QA](../../output/qa/2026-11-08-caption-mail-voice/verification.md).
