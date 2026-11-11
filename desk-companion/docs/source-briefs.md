# Offline source comparison

## Reviewed integration — 11 November 2026

Compare saved notes is expandable below the existing memory list. New writes recheck current owner/private visibility in the same transaction. Sources remain bounded owner-entered data and exact quotes, not fetched material or instructions. Original PR dependency/merge notes below are historical; the integrated source includes these features. [Review evidence](../../output/qa/2026-11-11-grok-review/verification.md). Runtime rollout is separate.

11 November 2026. Grok Bot, for Codex. This is the handoff for this slice. It does not edit `handoff.md`, `work-log.md`, `decision-log.md`, `AGENTS.md`, `START_HERE_NEXT_CHAT.md`, `product.md`, or the research index.

## What this is

The owner compares notes they already have. Each point quotes one of those notes, or it is marked “Not in these sources.” A note that could not be read stays a gap. Saving stores that exact set on this desk. Nothing is fetched, bought, booked, mailed, or marked complete, and no model is called.

This is the research gap still outside the open pull requests. The [research index](../../research/personal-agent-research-index.md) already has offline mail, shopping, and calendar journeys on main, and open PRs cover Work re-show and continue (#95, #96, #99), the folder-job clock (#98), browser takeover (#101), memory follow-ups and the morning check-in (#102, #103), trip quotes and re-approval (#104, #105), saved and scheduled skills (#108, #109), and the staple purchase card (#110). Codex #97 owns Alice, attachments, Gmail/Outlook drafts, and voice. Dot’s gap table calls a cited comparison, with a failed source left as a gap, a high-priority missing loop. Grok’s gap table asks for the same shape: a source that cannot be read stays a visible limitation. Public URL capture remains a separate, off-by-default GET. This slice does not start one.

## Behavior

- Only a visible owner session can open, revise, add, or save. The service checks the session and private context. A paired display is rejected.
- An omitted note or locator is not stored. JSON null does not clear a field and does not count as omitted. A blank note is rejected.
- An unavailable source requires a gap and cannot take a body. An available source requires a body and cannot take a gap. A point cannot quote an unavailable source. A quote must be an exact substring of that source. An unknown point cannot carry a source or a quote.
- Two points can disagree. Both stay. A page that says to approve itself stays text; the comparison stays a draft until this owner saves it.
- The same operation id and body returns the same row. A different body conflicts. A failed check does not consume the id.
- Interrupting before commit rolls the write back. The same id can then commit once. A second save of an already saved comparison is refused.
- An approval names the digest of the question, note, sources, and points. A later point makes the previous digest stale. There is nothing to save until there is a point or a gap.
- At most 8 comparisons, 4 sources, and 6 points. `Runtime.tick` is unchanged. `mailbox_bundle`, `shopping_bundle`, and `offline_calendar_bundle` are unchanged. No comparison bundle was added. No file is written, so there is no filename to collide on macOS.

## Where it sits

- `runtime.py`: `self.source_briefs` immediately after `self.sources`. No tick call. After #102–#105 and #110, tick quiet-release stays mailbox, shopping, trip quotes, offline calendar, then memory follow-ups, and the purchase-card release stays last.
- `app.py`: `source_brief_routes` immediately after `sources_routes`.
- `MemoryPanel.tsx`: the panel directly under the page heading, above the memory composer. #102 inserts `MemoryFollowUps` lower, after the fact list.

The page is Saved memories on the desk and on the phone More list. The result line is “Saved on this desk.” A missing source adds that the comparison is not complete.

## Codex

Keep the service’s own session and `require_visible` checks. Keep null distinct from omitted on open, revise, source, and claim. Do not approve from a model, a routine, or text inside a source. Do not add these rows to a backup bundle. Do not describe a saved comparison as a live lookup.
