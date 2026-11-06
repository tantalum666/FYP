/** Transient, server-observed input only. Never derive work from display strings. */
export type VoiceBoundary = "provider_final" | "unfinalized";
export interface VoiceProvenance {
  boundary: VoiceBoundary;
  provider: string;
  model: string;
  destination_id: string;
  observed_at: string;
}
export interface VoiceInput extends VoiceProvenance {
  type: "voice_input";
  voice_session_ref: string;
  input_segment_id: string;
  revision: number;
  sequence: number;
  role: "user";
  operation: "replace";
  text: string;
  eligible: boolean;
  reason: string | null;
}
export interface VoiceDraft extends VoiceProvenance {
  voice_origin_ref: string;
  text: string;
  revision: number;
  owner_reviewed_at: string;
  expires_at: string;
  snapshot_kind: "owner_snapshot";
}
export interface VoiceOrigin extends VoiceProvenance {
  channel: "voice";
  owner_reviewed_at: string;
  edited: boolean;
}
export type VoiceGoalOrigin = Omit<VoiceDraft, "text">;
export interface VoiceInputs {
  session: string | null;
  sequence: number;
  inputs: VoiceInput[];
  overflow: boolean;
}
export const emptyVoiceInputs = (): VoiceInputs => ({
  session: null,
  sequence: 0,
  inputs: [],
  overflow: false,
});
const boundedString = (value: unknown, limit = 512): value is string =>
  typeof value === "string" && !!value && value.length <= limit;
export function validVoiceGoal(text: string) {
  return (
    !!text.trim() &&
    Array.from(text).length <= 4000 &&
    new TextEncoder().encode(text).length <= 32768
  );
}
/** Complete replacement events only; stale, malformed and foreign-session events fail closed. */
export function reduceVoiceInputs(
  state: VoiceInputs,
  raw: unknown,
): VoiceInputs {
  if (!raw || typeof raw !== "object") return state;
  const input = raw as VoiceInput;
  if (
    input.type !== "voice_input" ||
    input.role !== "user" ||
    input.operation !== "replace" ||
    !boundedString(input.voice_session_ref) ||
    !boundedString(input.input_segment_id) ||
    !Number.isSafeInteger(input.revision) ||
    input.revision < 1 ||
    !Number.isSafeInteger(input.sequence) ||
    input.sequence <= state.sequence ||
    (state.session !== null && state.session !== input.voice_session_ref) ||
    !["provider_final", "unfinalized"].includes(input.boundary) ||
    !boundedString(input.provider) ||
    !boundedString(input.model) ||
    !boundedString(input.destination_id) ||
    !Number.isFinite(Date.parse(input.observed_at)) ||
    typeof input.text !== "string" ||
    typeof input.eligible !== "boolean"
  )
    return state;
  const old = state.inputs.find(
    (x) => x.input_segment_id === input.input_segment_id,
  );
  if (
    old &&
    (input.revision <= old.revision ||
      (old.boundary === "provider_final" &&
        input.boundary !== "provider_final"))
  )
    return state;
  const oversized =
    Array.from(input.text).length > 4000 ||
    new TextEncoder().encode(input.text).length > 32768;
  const next: VoiceInput = {
    ...input,
    text: oversized || !input.eligible ? "" : input.text,
    eligible: !oversized && input.eligible && !!input.text.trim(),
    reason: oversized ? "VOICE_INPUT_TOO_LARGE" : input.reason,
  };
  let inputs = state.inputs.filter(
    (x) => x.input_segment_id !== input.input_segment_id,
  );
  inputs.push(next);
  const countOverflow = inputs.length > 8;
  inputs = inputs.slice(-8);
  while (
    inputs.reduce((n, x) => n + new TextEncoder().encode(x.text).length, 0) >
    32768
  )
    inputs.shift();
  return {
    session: input.voice_session_ref,
    sequence: input.sequence,
    inputs,
    overflow:
      state.overflow ||
      oversized ||
      countOverflow ||
      inputs.length < Math.min(state.inputs.length + (old ? 0 : 1), 8),
  };
}
export function validVoiceDraft(
  raw: unknown,
  selected: VoiceInput,
  now = Date.now(),
): raw is VoiceDraft {
  if (!raw || typeof raw !== "object") return false;
  const draft = raw as VoiceDraft;
  return (
    boundedString(draft.voice_origin_ref) &&
    draft.snapshot_kind === "owner_snapshot" &&
    draft.revision === selected.revision &&
    draft.text === selected.text &&
    validVoiceGoal(draft.text) &&
    draft.boundary === selected.boundary &&
    draft.provider === selected.provider &&
    draft.model === selected.model &&
    draft.destination_id === selected.destination_id &&
    draft.observed_at === selected.observed_at &&
    Number.isFinite(Date.parse(draft.owner_reviewed_at)) &&
    Date.parse(draft.expires_at) > now
  );
}
export function voiceGoalOrigin(draft: VoiceDraft): VoiceGoalOrigin {
  const { text: _text, ...origin } = draft;
  return origin;
}
export interface CurrentWorkRun {
  id: string;
  goal?: string;
  state: string;
  plan_revision: number;
  task_ids: string[];
}
const RUN_ID = /^[a-f0-9]{32}$/;
/** Current means the same steer rule as ConversationWork: not cancelled, and still on its first goal. */
export function currentVoiceRuns(
  runs: unknown,
  taskId?: string,
): CurrentWorkRun[] {
  if (!Array.isArray(runs)) return [];
  const current: CurrentWorkRun[] = [];
  for (const item of runs) {
    if (!item || typeof item !== "object") continue;
    const run = item as CurrentWorkRun & { private_hidden?: boolean };
    if (run.private_hidden) continue;
    if (typeof run.id !== "string" || !RUN_ID.test(run.id)) continue;
    if (run.state === "cancelled") continue;
    if (typeof run.plan_revision !== "number" || run.plan_revision >= 2)
      continue;
    const tasks = Array.isArray(run.task_ids)
      ? run.task_ids.filter((id) => typeof id === "string")
      : [];
    if (taskId && !tasks.includes(taskId)) continue;
    current.push({
      id: run.id,
      goal: typeof run.goal === "string" ? run.goal : undefined,
      state: typeof run.state === "string" ? run.state : "",
      plan_revision: run.plan_revision,
      task_ids: tasks,
    });
  }
  return current;
}
