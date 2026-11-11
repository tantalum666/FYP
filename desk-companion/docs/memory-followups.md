# Owner-approved memory follow-ups

## Reviewed integration — 11 November 2026

Owner routes honor private-hide. Morning facts are resolved from current active memories on each owner inbox read; persisted, browser and push notifications only say to open Memory. Forgotten/expired wording is not replayed by follow-up/check-in operation receipts. One existing rules clock is retained; no real mailbox monitoring is implied. The controls are expandable on Memory. [Review evidence](../../output/qa/2026-11-11-grok-review/verification.md). Runtime rollout is separate.

10 November 2026. Group 2. This is an offline slice. It does not call a model, read a mailbox, or write a calendar event or task.

Alice can raise one saved memory at a local time the owner approves. Quiet hours and “proactive reminders off” hold that same follow-up. They do not create a second one. Forgetting or expiring the memory cancels it and does not repeat the wording.

## What the owner does

1. On Memory, choose one active fact and a future minute, then prepare a follow-up. Preparation does not write a row.
2. Approve it. That is the only step that arms the follow-up. A paired display cannot prepare, approve, change, or close one.
3. The rules tick raises it once the approved instant has arrived, quiet hours are over, and proactive reminders are not off. The bell says to open Memory. It does not include the fact. The memory page shows the current wording and why it fired.
4. The owner can mark it handled, dismiss it, or, after it has been raised, ask for another reminder in one hour. Handled and dismissed do not fire again.

A memory can have one open follow-up. At most 50 can be open. One tick publishes at most three. The rest wait one minute, still as the same follow-up.

## Time, versions, and retries

The time is a local minute plus an IANA timezone. The workspace timezone is used when the request omits it. An explicit empty time does not clear a saved time. A missing or doubled civil time is rejected. A time that has already arrived is rejected.

Changing the follow-up sends `expected_version`. Fields the request does not include stay as stored. A raised, handled, dismissed, or cancelled follow-up is not moved to a new time; snooze is the way to ask again after a raise.

The same operation id and the same body return the original follow-up and do not insert another row. A different body with that id conflicts and leaves the row unchanged. A rejected confirm, including a stale memory version, does not store a success. The same operation id can then be used for a later valid approve.

If the notice delivery fails after the follow-up is marked raised, that delivery is not success. The next tick sends it once. Quiet hours and proactive reminders off still delay that retry. A restart does not create a second notice.

An owner session lasts eight hours of workspace time. The follow-up stays in the store, so a later sign-in still sees it.

## What this does not do

It does not read email, continue a Work run, or take over a browser. Those are separate open changes. It does not put the fact on the always-on display. A model has no tool that arms this follow-up.

## Morning check-in

10 November 2026. The same rules tick can also raise one morning check-in. There is no second scheduler. The owner approves one future local minute. Preparation does not write a row. Until that approval, nothing is scheduled.

At that minute the check-in gathers every still-open follow-up that is due by then into one notice. The notice cites each fact that is still active, using the current wording. The always-on display only says to open Memory. It does not speak the facts. Each cited fact is marked raised with that notice, so it does not also raise on its own. A follow-up that is already raised, or that is due later than the check-in, stays out of the notice.

Quiet hours and “proactive reminders off” hold that same check-in. They do not create another one, and they do not let a covered follow-up raise early. Forgetting or expiring a fact drops it. Its wording is not cited, including when a notice has to be sent again because delivery did not succeed. If every cited fact is gone before delivery, no notice is sent.

Approval, a time change, and dismiss each use an operation id. The same id and the same body return the original check-in. A rejected confirm does not store a success. A time change that omits a field leaves the stored value. An explicit empty time does not clear it. Dismiss before the notice is sent releases the covered follow-ups; they can then raise on their own, still without putting the fact on the bell. One check-in can be open. A paired display cannot prepare, approve, change, or dismiss it.

A model has no tool that arms this check-in. The wording of the notice is fixed. There is no model call.
