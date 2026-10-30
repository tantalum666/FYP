import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import {
  newWatchDraft,
  prepareWatch,
  watchActions,
  metadataOnly,
  followupTaskIds,
  scopePath,
} from "../src/workspace/responsibilities/types.ts";
import {
  newRunDraft,
  prepareRun,
  exactTaskHandoffReady,
  validWorkGoal,
} from "../src/workspace/agent/types.ts";
import type {
  WatchDetail,
  WatchScope,
  Responsibility,
} from "../src/workspace/responsibilities/types.ts";
import type { RunScope } from "../src/workspace/agent/types.ts";
const now = Date.parse("2026-10-13T10:00:00Z");
const scope: WatchScope = {
  tasks: [{ id: "one", title: "Synthetic task", version: 1, status: "todo" }],
  selected_task_ids: ["one"],
  fields: ["status", "due", "progress"],
  scope_revision: "a".repeat(64),
  server_time: new Date(now).toISOString(),
  limits: {},
  truncated: false,
};
const draft = {
  ...newWatchDraft(),
  title: "Synthetic watch",
  task_ids: ["one"],
  expires_at: "2026-10-14T10:00",
  retain_change_history: true,
};
const row = {
  id: "watch-one",
  version: 1,
  generation: 1,
  status: "active",
  title: "Secret title",
  task_ids: ["one"],
  fields: ["progress"],
  created_at: "2026-10-13T10:00:00Z",
  updated_at: "2026-10-13T10:00:00Z",
  baseline_at: "2026-10-13T10:00:00Z",
  expires_at: "2026-10-14T10:00:00Z",
  review_budget: 20,
  reviews_used: 0,
  daily_review_budget: 10,
  budget_day: "2026-10-13",
  daily_used: 0,
  blocked_code: null,
  pending_count: 0,
  hidden: false,
} as Responsibility;
test("watch admission binds exact fresh task/field scope and explicit retention", () => {
  const prepared = prepareWatch(draft, scope, now)!;
  assert.equal(prepared.kind, "selected_task_changes");
  assert.equal(prepared.expires_at, "2026-10-14T10:00:00.000Z");
  assert.equal(
    prepareWatch({ ...draft, retain_change_history: false }, scope, now),
    null,
  );
  for (const invalid of [[], ["other"], ["one", "one"]])
    assert.equal(
      prepareWatch({ ...draft, task_ids: invalid }, scope, now),
      null,
    );
  assert.equal(
    prepareWatch({ ...draft, fields: ["status"] }, scope, now),
    null,
  );
  assert.equal(
    prepareWatch(draft, { ...scope, scope_revision: null }, now),
    null,
  );
  assert.equal(prepareWatch(draft, { ...scope, tasks: [] }, now), null);
  assert.deepEqual(newWatchDraft().task_ids, []);
  assert.equal(newWatchDraft().retain_change_history, false);
  assert.equal(
    scopePath(["one", "two"], ["progress"]),
    "/responsibilities/scope?task_id=one&task_id=two&field=progress",
  );
});
test("watch expiry and budgets never imply indefinite or automatically renewed permission", () => {
  for (const changes of [
    { expires_at: "" },
    { expires_at: "2026-10-13T09:00" },
    { expires_at: "2027-10-14T10:00" },
    { review_budget: 0 },
    { review_budget: 101 },
    { review_budget: 1.5 },
    { daily_review_budget: 0 },
    { daily_review_budget: 21 },
  ])
    assert.equal(prepareWatch({ ...draft, ...changes }, scope, now), null);
  assert.deepEqual(watchActions("cancelled"), []);
  assert.deepEqual(watchActions("expired"), []);
  assert.deepEqual(watchActions("budget_exhausted"), []);
  assert.deepEqual(watchActions("future_state"), []);
  assert.deepEqual(watchActions("paused"), ["resume", "cancel"]);
  assert.deepEqual(watchActions("paused", true), ["cancel"]);
  assert.deepEqual(watchActions("blocked", true), ["pause", "cancel"]);
});
test("hidden projection erases unexpected titles, fields and IDs before storage", () => {
  const result = metadataOnly({ ...row, blocked_code: "Secret source text" });
  assert.equal(result.hidden, true);
  assert.equal(result.id, row.id);
  assert.equal(result.title, undefined);
  assert.equal(result.task_ids, undefined);
  assert.equal(result.fields, undefined);
  assert.equal(result.blocked_code, null);
  assert.doesNotMatch(JSON.stringify(result), /Secret|progress|task_ids/);
});
test("followup preserves every enrolled ID and never quietly shrinks unavailable scope", () => {
  const detail = {
    responsibility: { ...row, task_ids: ["one", "two"] },
    selected_tasks: [
      { id: "one", title: "A", available: true, version: 1 },
      { id: "two", title: "B", available: true, version: 1 },
    ],
    reviews: [],
    revision: 1,
  } as WatchDetail;
  assert.deepEqual(followupTaskIds(detail), ["one", "two"]);
  assert.equal(
    followupTaskIds({
      ...detail,
      selected_tasks: detail.selected_tasks.slice(0, 1),
    }),
    null,
  );
  assert.equal(
    followupTaskIds({
      ...detail,
      selected_tasks: detail.selected_tasks.map((task) => ({
        ...task,
        available: false,
      })),
    }),
    null,
  );
  assert.equal(
    validWorkGoal({
      id: "draft",
      text: "Compile evidence",
      exactTaskIds: ["one", "one"],
    }),
    false,
  );
});
test("Work handoff compiles current exact tasks, requires fresh review/retention and grants no provider/context", () => {
  const scope = {
    scope_revision: "a".repeat(64),
    modes: ["deterministic", "model"],
    destinations: [],
    sources: [],
    tasks: [
      { id: "one", title: "Current record", version: 2 },
      { id: "two", title: "Current other", version: 3 },
    ],
    events: [],
    limits: {},
    business_context_allowed: false,
  } as RunScope;
  const draft = {
    ...newRunDraft("Compile current task evidence"),
    task_ids: ["one", "two"],
  };
  assert.equal(exactTaskHandoffReady(["one", "two"], draft, scope), true);
  assert.equal(prepareRun(draft, scope), null);
  const input = prepareRun({ ...draft, retain: true }, scope)!;
  assert.equal(input.mode, "deterministic");
  assert.equal(input.share_sources_with_provider, false);
  assert.equal(input.personal_context, null);
  assert.equal(input.provider_destination_id, null);
  assert.deepEqual(input.task_ids, ["one", "two"]);
  assert.deepEqual(input.mutation_requests, []);
  assert.equal(
    exactTaskHandoffReady(["one", "two"], draft, {
      ...scope,
      tasks: scope.tasks.slice(0, 1),
    }),
    false,
  );
  assert.equal(
    exactTaskHandoffReady(
      ["one", "two"],
      { ...draft, task_ids: ["one"] },
      scope,
    ),
    false,
  );
  assert.equal(
    exactTaskHandoffReady(["one", "two"], { ...draft, mode: "model" }, scope),
    false,
  );
});
test("production seams preserve explicit actions and original retry IDs rather than mount acknowledgments", () => {
  const source = (name: string) =>
    readFileSync(new URL(`../src/workspace/${name}`, import.meta.url), "utf8");
  const panel = source("responsibilities/ResponsibilitiesPanel.tsx");
  assert.match(panel, /usePrivateMutation\(\)/);
  assert.match(panel, /expected_review_version: review.version/);
  assert.match(panel, /resume_policy: "baseline_now"/);
  assert.match(panel, /fence.accepts\(epoch\)/);
  assert.match(panel, /mutation.retry\(\)/);
  assert.match(panel, /desk:session/);
  assert.match(panel, /desk:personal-context/);
  assert.match(panel, /row.budget_day/);
  assert.doesNotMatch(panel, /Today \(UTC\)/);
  assert.doesNotMatch(panel, /localStorage|sessionStorage|\/agent-runs/);
  assert.match(
    source("agent/RunComposer.tsx"),
    /exactTaskHandoffReady\(exactTaskIds, draft, scope\)/,
  );
  assert.match(source("agent/RunPanel.tsx"), /reload\(true\).then/);
  assert.match(source("WorkTools.tsx"), /ResponsibilitiesPanel/);
});
