import assert from "node:assert/strict";
import test from "node:test";
import {
  currentVoiceRuns,
  emptyVoiceInputs,
  reduceVoiceInputs,
  validVoiceDraft,
  validVoiceGoal,
  voiceGoalOrigin,
} from "../src/workspace/voiceWork/types.ts";
import type {
  VoiceInput,
  VoiceDraft,
} from "../src/workspace/voiceWork/types.ts";
import {
  newRunDraft,
  prepareRun,
  validWorkGoal,
} from "../src/workspace/agent/types.ts";
import type { RunScope } from "../src/workspace/agent/types.ts";
const now = Date.parse("2026-10-13T06:00:00Z");
const event = (changes: Partial<VoiceInput> = {}): VoiceInput => ({
  type: "voice_input",
  role: "user",
  operation: "replace",
  voice_session_ref: "session",
  input_segment_id: "input1",
  revision: 1,
  sequence: 1,
  text: "Synthetic report goal",
  boundary: "unfinalized",
  eligible: true,
  reason: null,
  provider: "gemini",
  model: "protocol-fake",
  destination_id: "destination",
  observed_at: new Date(now).toISOString(),
  ...changes,
});
const frozen = (input = event()): VoiceDraft => ({
  voice_origin_ref: "reference",
  text: input.text,
  revision: input.revision,
  boundary: input.boundary,
  provider: input.provider,
  model: input.model,
  destination_id: input.destination_id,
  observed_at: input.observed_at,
  owner_reviewed_at: new Date(now).toISOString(),
  expires_at: new Date(now + 300000).toISOString(),
  snapshot_kind: "owner_snapshot",
});
test("protocol-fake normalized inputs stay separate and never infer Gemini finality", () => {
  let state = reduceVoiceInputs(emptyVoiceInputs(), event());
  const snapshot = state.inputs[0];
  state = reduceVoiceInputs(
    state,
    event({ sequence: 2, revision: 2, text: "Synthetic report goal expanded" }),
  );
  assert.equal(state.inputs[0].boundary, "unfinalized");
  assert.equal(snapshot.text, "Synthetic report goal");
  state = reduceVoiceInputs(
    state,
    event({
      sequence: 3,
      input_segment_id: "input2",
      text: "Separate input",
      boundary: "provider_final",
    }),
  );
  assert.equal(state.inputs.length, 2);
  assert.equal(state.inputs[0].text, "Synthetic report goal expanded");
  assert.equal(state.inputs[1].text, "Separate input");
  assert.equal(validVoiceDraft(frozen(), snapshot, now), true);
});
test("assistant, tools, raw deltas, completion and stale or foreign events never become inputs", () => {
  const state = reduceVoiceInputs(emptyVoiceInputs(), event());
  for (const changes of [
    { type: "transcript" },
    { type: "turn_complete" },
    { type: "tool", text: "start work" },
    { role: "assistant" },
    { role: "unknown" },
    { operation: "append" },
    { boundary: "owner_approved" },
    { sequence: 0 },
    { sequence: 1, revision: 2 },
    { sequence: 2, revision: 1 },
    { sequence: 2, voice_session_ref: "foreign" },
    { sequence: 2, revision: 2, model: "" },
  ])
    assert.strictEqual(
      reduceVoiceInputs(state, { ...event(), ...changes }),
      state,
    );
});
test("blank and oversize input fail clearly without creating a truncated goal", () => {
  const state = reduceVoiceInputs(emptyVoiceInputs(), event());
  const oversize = reduceVoiceInputs(
    state,
    event({ sequence: 2, revision: 2, text: "A".repeat(4001) }),
  );
  assert.equal(oversize.inputs[0].eligible, false);
  assert.equal(oversize.inputs[0].text, "");
  assert.equal(oversize.overflow, true);
  const blank = reduceVoiceInputs(emptyVoiceInputs(), event({ text: " " }));
  assert.equal(blank.inputs[0].eligible, false);
  const invalid = reduceVoiceInputs(
    state,
    event({
      sequence: 2,
      revision: 2,
      eligible: false,
      text: "",
      reason: "VOICE_INPUT_INVALID",
    }),
  );
  assert.equal(invalid.inputs[0].text, "");
  assert.equal(validVoiceGoal("😀".repeat(4001)), false);
});
test("input storage is bounded by eight records and 32KiB UTF-8, never concatenated", () => {
  let state = emptyVoiceInputs();
  for (let sequence = 1; sequence <= 12; sequence++)
    state = reduceVoiceInputs(
      state,
      event({ sequence, input_segment_id: `item${sequence}` }),
    );
  assert.equal(state.inputs.length, 8);
  assert.equal(state.overflow, true);
  state = emptyVoiceInputs();
  for (let sequence = 1; sequence <= 8; sequence++)
    state = reduceVoiceInputs(
      state,
      event({
        sequence,
        input_segment_id: `item${sequence}`,
        text: "字".repeat(4000),
      }),
    );
  assert.ok(
    state.inputs.reduce((n, item) => n + Buffer.byteLength(item.text), 0) <=
      32768,
  );
  assert.equal(state.overflow, true);
});
test("freeze receipt must match the exact selected snapshot and have a live expiry", () => {
  for (const changes of [
    { text: "different" },
    { revision: 2 },
    { boundary: "provider_final" },
    { model: "other" },
    { destination_id: "other" },
    { expires_at: new Date(now).toISOString() },
    { snapshot_kind: "provider_final" },
    { voice_origin_ref: "" },
  ])
    assert.equal(
      validVoiceDraft({ ...frozen(), ...changes }, event(), now),
      false,
    );
  assert.equal(
    "text" in voiceGoalOrigin(frozen()),
    false,
    "handoff metadata cannot retain duplicate raw transcript",
  );
});
test("voice origin adds no evidence, retention, sharing or provider permission", () => {
  const scope: RunScope = {
    scope_revision: "s".repeat(64),
    modes: ["deterministic", "model"],
    sources: [
      {
        id: "csv",
        name: "synthetic.csv",
        format: "csv",
        sha256: "h".repeat(64),
        byte_count: 10,
        revision: 1,
        status: "verified",
      },
    ],
    tasks: [],
    events: [],
    limits: {},
    business_context_allowed: false,
    destinations: [],
  };
  const draft = {
    ...newRunDraft("Reviewed edited goal"),
    voice_origin_ref: "reference",
  };
  assert.equal(prepareRun(draft, scope), null);
  assert.equal(prepareRun({ ...draft, retain: true }, scope), null);
  const admitted = prepareRun(
    { ...draft, retain: true, source_ids: ["csv"] },
    scope,
  )!;
  assert.equal(admitted.goal, "Reviewed edited goal");
  assert.equal(admitted.voice_origin_ref, "reference");
  assert.equal(admitted.mode, "deterministic");
  assert.equal(admitted.share_sources_with_provider, false);
  assert.equal(admitted.personal_context, null);
  assert.equal(admitted.allow_mutation_proposals, false);
  assert.equal(
    "voice_origin_ref" in
      prepareRun(
        { ...newRunDraft("Typed goal"), retain: true, source_ids: ["csv"] },
        scope,
      )!,
    false,
  );
});

test("Unicode voice goals and Work admission agree; expired origins never become typed work", () => {
  const goal = {
    id: "handoff",
    text: "😀".repeat(2001),
    voiceOrigin: {
      ...voiceGoalOrigin(frozen()),
      expires_at: new Date(Date.now() + 60000).toISOString(),
    },
  };
  assert.equal(validVoiceGoal(goal.text), true);
  assert.equal(validWorkGoal(goal), true);
  assert.equal(
    validWorkGoal({
      ...goal,
      voiceOrigin: {
        ...goal.voiceOrigin,
        expires_at: new Date(Date.now() - 1).toISOString(),
      },
    }),
    false,
  );
});

test("current work for a voice review is the one steerable run, or an explicit choice", () => {
  const id = (char: string) => char.repeat(32);
  const run = (char: string, extra: Record<string, unknown> = {}) => ({
    id: id(char),
    goal: `Goal ${char}`,
    state: "queued",
    plan_revision: 1,
    task_ids: ["task-a"],
    ...extra,
  });
  const open = run("a");
  assert.deepEqual(
    currentVoiceRuns([open, run("b", { task_ids: ["task-b"] })], "task-a").map(
      (item) => item.id,
    ),
    [id("a")],
  );
  assert.deepEqual(
    currentVoiceRuns([
      open,
      run("b"),
      run("c", { state: "cancelled" }),
      run("d", { plan_revision: 2 }),
      run("e", { private_hidden: true }),
      { id: "short", state: "queued", plan_revision: 1, task_ids: ["task-a"] },
    ]).map((item) => item.id),
    [id("a"), id("b")],
  );
  assert.deepEqual(currentVoiceRuns([open], undefined).map((item) => item.id), [
    id("a"),
  ]);
  assert.deepEqual(currentVoiceRuns(null), []);
  assert.deepEqual(currentVoiceRuns([run("a", { task_ids: ["other"] })], "task-a"), []);
});
