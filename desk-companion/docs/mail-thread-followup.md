# Group 2 · Selected mail-thread follow-up

18 November 2026. A selected Gmail/Outlook conversation can be linked to one existing or new task, checked for incoming updates, and replied to through the existing reviewed sender. This is a bounded source subscription. It is not whole-inbox ingestion or an autonomous agent scheduler. [Official capability audit](../../research/2026-11-17-official-capability-audit.md), [verification](../../output/qa/2026-11-17-mail-thread-followup/verification.md).

## 25 November 2026 · One reminder, then a draft the owner chooses

The poll above still watches a thread the owner chose to follow. When a new incoming message id appears, Alice keeps one reminder on that same task. Chat shows the summary and source. Inbox offers the task. The task card is the same reminder. Quiet hours leave it unpublished until quiet hours end. A restart or the same message does not add a second reminder.

**Read the message** rereads that message from its source. The text is shown and is not written into saved memory, task evidence, or the stored read receipt. A failed read says it failed and does not become a confirmed new reply.

**Draft a reply** appears only after the owner asks for it. **Save draft** stores the text the owner reviewed, bound to the message, revision, and summary on screen. It does not send. **Check again** rereads and, if an earlier send is unknown, says so without sending again. **Not now** clears this reminder only.

A local sample in Work & tools is labeled “Not a live mailbox.” Following one sample thread does not attach a reply from the other sample thread. Connected Gmail or Outlook still use the same reminder when a synthetic or real selected thread reports a new message. This slice did not accept a live mailbox, did not call a model, and did not change GPT-6.2 Sol, GPT-Live 1.1, or A3 v9. [Verification](../../output/qa/2026-11-25-followed-reply/verification.md).

## Owner journey

1. Ask Alice to find a particular email using the connected-account read tools.
2. Ask to follow that email. A fresh owner request uses the existing Normal/Less often proactive preference and starts the newly prepared read-only subscription without a second approval card, including in Ask mode. It follows the open task while the service is online, approximately every fifteen minutes. Manual preview/forms and legacy requests retain their explicit seven-day checkbox; changing a preference does not authorize an old pending draft.
3. New incoming message IDs add evidence to that same task and one coalesced notification. Open **Tasks → Followed emails → Open task** to see the latest five message headers. **Mark reviewed** acknowledges only the observed revision; a newer arrival is not cleared by a stale screen.
4. **Ask Alice about this update** opens the same task discussion. Alice can read current follow-up state and prepare a reply to a specific message. The owner reviews recipient, exact subject and body before **Send reply**.
5. **Stop following** prevents subsequent source reads and notifications and excludes that thread from ambient research; the existing task/history remain. Closing a task ends following. Legacy manual scopes also end after seven days; automatic scopes renew an internal lease while the task remains open. Reopening a closed task does not reauthorize an ended subscription. A later explicit new follow request can start it again.

The standing proactive setting permits bounded contextual research from connected previews; selected-thread tracking still requires a fresh request identifying the thread. Full access does not authorize sending. Browser session expiry does not cancel an already started read-only subscription. Hide private, Proactivity Off or pausing the linked task suspends reads and delivery; the service resumes only while the original account version and grant remain valid. Quiet hours defer notifications without silently discarding observations. Service/device downtime is not covered by a cloud monitor; closed-phone push delivery is not claimed.

## Responsibilities

- mail_threads.py: fixed Google/Graph metadata endpoints, account/token reuse, bounded parsing and checkpoints around requests. It never follows mail links or provider pagination URLs.
- mail_followups.py: selected-source grant, durable claim/expiry, message-ID baseline, task evidence and one pending notice. The existing Runtime worker schedule invokes mail_sources / poll_source_once. No model, AgentLoop, independent queue or cron parser is added.
- email_replies.py: fresh message/recipient/subject binding for a draft and again before sending. Existing OutboundMail/AssistantService decisions own the send reservation, acceptance and unknown-write behavior.
- MailFollowupReview and MailFollowupsPanel: shared proposal review and owner web/phone task details (ambient display keeps private mail details hidden), existing task refresh and component-lifetime private-write recovery. No independent frontend polling loop or mailbox data in browser storage.
- Future scheduled reasoning/goal work should use official Agents Automations/Sessions. Live already delegates through official Responses and exposes the same business functions. The older primary text AgentLoop is an explicit remaining migration gap, not a new architecture extended by this feature.

The original offline mailbox fixture and reply-owed flows remain independent compatibility evidence. Their parser-produced task updates and portable fixture cursor do not supply authority for live messages.

## Data, bounds and lifecycle

Only a specifically selected thread is followed. Gmail requests metadata headers; Graph selects IDs, subject, sender, timestamps and draft status. Bodies, attachments and mail-linked websites are not fetched in the background. A current thread can contain at most 50 messages, the response at most 192 KB, and a subscription can remember at most 256 observed IDs. An oversized/incomplete thread stops with an actionable error instead of pretending the omitted messages were checked.

At most 20 active/blocked subscriptions and 500 retained subscription records are accepted. Each source is bound to provider, account version and thread ID; identical active scopes reuse the same task/subscription. A reply arriving between preview and confirmation is still observed against the original preview baseline. Existing task version, status, due date and progress are never changed from email headers. A new task starts Waiting without a separate scheduled task check-in.

A database claim plus account/privacy/task/expiry checks fences late reads, concurrent service instances and restarts. Source IDs deduplicate label-only changes and repeated responses. Outgoing mail does not create an incoming-update notice. Gmail uses SENT/draft/trash/spam metadata; Graph's owner-address classification is not sender authenticity or delivery proof.

Headers are untrusted display data. They cannot change permissions, request a tool, select destinations, send messages, or mark tasks complete. Notifications contain generic text; details require owner context. A stopped source retains prior observations. Portable business backups preserve task/evidence, but omit live subscription grants and tokens; importing a task cannot silently reenable account polling. Private full-database recovery is distinct from a portable task export.

Account disconnect/replacement, missing scopes or an unavailable source block further reads. Restoring connectivity does not silently rebind an old source to a new account version. Stop the blocked subscription and review a new selected-thread grant. Transient failures preserve the baseline and retry at the normal interval. An unknown send is never reset by creating another reply draft for the same target.

## Proper reply contract

Gmail uses the existing message's exact decoded Subject, threadId and RFC Message-ID in both In-Reply-To and References. Incoming Reply-To is respected; replying to one's own sent message uses its original sole To recipient. Multiple/ambiguous recipients, missing identity or oversized identity fields require clarification rather than guessing or truncating. Graph uses the official message reply endpoint and immutable IDs, not a new standalone sendMail request.

The owner-visible draft binds account version, recipient and source fingerprint. A source change before confirmation rejects the send before reserving an attempt. A lost HTTP acknowledgement can recover the same durable receipt without resending. A provider timeout after dispatch remains unknown and blocks a second draft for the same reply target. The generic sender retains its existing behavior.

Gmail response threadId matching establishes provider-reported thread binding; Graph HTTP 202 means accepted, with thread binding/delivery unconfirmed. Neither is proof that a recipient received/read the message. Current acceptance includes real-model follow/stop choices over synthetic provider data; no real email was sent in this integration. Historical native self-send acceptance remains separately dated.

## Function/API surface

Shared functions: mail_followup_draft, mail_followup_status, mail_followup_stop, email_reply_draft. They are owner-only. The model has no confirm function. Retained-chat compatibility exposes draft/status/stop within its existing narrower catalog; normal text and Live support reply drafting.

Owner routes: POST /api/mail-followups/preview, GET /api/mail-followups, POST /api/mail-followups/{id}/acknowledge or /stop, and POST /api/email/reply-drafts. Manual confirmation uses the existing proposal decision route with an explicit boolean follow_mail_thread. Fresh conversational follow-up can instead use PermissionService's captured read-only proactivity grant. The cached receipt refreshes actual active/paused/stopped state without executing a new subscription. Stop remains possible while private context is hidden. Unknown frontend mutations keep their original operation ID only in the current component; after closing, query state before repeating an action.

## Primary sources

[Gmail thread reads](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.threads/get), [Gmail reply/thread requirements](https://developers.google.com/workspace/gmail/api/guides/threads), [Graph message reads](https://learn.microsoft.com/en-us/graph/api/user-list-messages?view=graph-rest-1.0), [Graph immutable IDs](https://learn.microsoft.com/en-us/graph/outlook-immutable-id), [Graph reply](https://learn.microsoft.com/en-us/graph/api/message-reply?view=graph-rest-1.0).
