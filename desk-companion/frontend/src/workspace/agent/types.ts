export type RunMode = "deterministic" | "model";
export type RunAction =
  "pause" | "resume" | "cancel" | "steer" | "answer" | "retry_model";
export type FileFormat = "text" | "markdown" | "csv" | "json";
export interface SourceRecord {
  id: string;
  name: string;
  format: FileFormat;
  sha256: string;
  byte_count: number;
  revision: number;
  status: "verified" | "unknown" | "failed";
  created_at?: string;
}
export interface RunDestination {
  id: string;
  kind: string;
  provider: string;
  endpoint: string;
}
export interface RunScope {
  scope_revision: string;
  modes: RunMode[];
  destinations: RunDestination[];
  sources: SourceRecord[];
  tasks: { id: string; title: string; version: number }[];
  events: {
    id: string;
    title: string;
    version: number;
    start_local?: string;
    end_local?: string;
    timezone?: string;
  }[];
  limits: Record<string, number>;
  business_context_allowed: boolean;
}
export interface AgentRun {
  id: string;
  goal?: string;
  mode: RunMode;
  state: string;
  state_reason: string | null;
  version: number;
  plan_revision: number;
  created_at: string;
  updated_at: string;
  source_ids: string[];
  task_ids: string[];
  event_ids: string[];
  artifact_ids: string[];
  proposal_ids: string[];
  model_calls: number;
  evidence_count: number;
  private_hidden?: boolean;
  question?: string | null;
  plan?: string[];
  current_artifact_ids?: string[];
  unmet_requirements?: {
    code: string;
    evidence_id?: string;
    covered_through_line?: number;
    total_lines?: number;
    section?: string;
  }[];
  outcome_requirements?: {
    formats: string[];
    selected_source_coverage: string;
    required_sections: string[];
  };
  evidence?: {
    id: string;
    label: string;
    kind: string;
    at: string;
    sha256: string;
    coverage: {
      start_line?: number;
      end_line?: number;
      total_lines?: number;
      truncated?: boolean;
    };
    local_parser_coverage?: { start_line: number; end_line: number } | null;
  }[];
}
export interface ArtifactRecord {
  id: string;
  run_id: string;
  step_id: string;
  display_name: string;
  format: FileFormat;
  mime: string;
  byte_count: number;
  sha256: string;
  created_at: string;
  version: number;
  provenance: {
    source_id: string;
    source_revision: number;
    start_line: number;
    end_line: number;
    sha256: string;
  }[];
  authorship: "deterministic" | "model" | "owner";
  status: "verified" | "unknown" | "failed";
  verification: "byte_readback" | "unverified";
  quality: "not_semantically_checked";
}
export interface RunDetailResponse {
  run: AgentRun;
  steps: {
    id: string;
    kind: string;
    label: string;
    state: string;
    result?: Record<string, unknown> | null;
    error?: string | null;
  }[];
  events: { sequence: number; kind: string; at: string; details?: unknown }[];
  artifacts: ArtifactRecord[];
  proposals: {
    id: string;
    kind: string;
    state?: string;
    expires_at?: string;
  }[];
}
export interface RunCreateInput {
  goal: string;
  mode: RunMode;
  source_ids: string[];
  task_ids: string[];
  event_ids: string[];
  retain: true;
  scope_revision: string;
  provider_destination_id: string | null;
  share_sources_with_provider: boolean;
  mutation_requests: [];
  allow_mutation_proposals: boolean;
  required_sections: string[];
}
export interface RunDraft {
  goal: string;
  mode: RunMode;
  source_ids: string[];
  task_ids: string[];
  event_ids: string[];
  retain: boolean;
  destination: string;
  share: boolean;
  allow_mutation_proposals: boolean;
  required_sections: string;
}
export function newRunDraft(): RunDraft {
  return {
    goal: "",
    mode: "deterministic",
    source_ids: [],
    task_ids: [],
    event_ids: [],
    retain: false,
    destination: "",
    share: false,
    allow_mutation_proposals: false,
    required_sections: "",
  };
}
export function runActions(
  state: string,
  reason: string | null = null,
  planRevision = 1,
): RunAction[] {
  const steer: RunAction[] = planRevision < 2 ? ["steer"] : [];
  if (["cancelled", "cancelling"].includes(state)) return [];
  if (["succeeded", "partial", "failed"].includes(state)) return steer;
  if (state === "waiting_input") return ["answer", ...steer, "cancel"];
  if (["paused", "blocked"].includes(state))
    return [
      reason === "RUN_PROVIDER_OUTCOME_UNKNOWN" ? "retry_model" : "resume",
      ...steer,
      "cancel",
    ];
  if (
    [
      "queued",
      "planning",
      "running",
      "waiting_review",
      "waiting_effect",
      "verifying",
    ].includes(state)
  )
    return ["pause", ...steer, "cancel"];
  return []; // Unknown future states never gain mutation authority in this client.
}
export function prepareRun(
  draft: RunDraft,
  scope: RunScope,
): RunCreateInput | null {
  const goal = draft.goal.trim();
  const sections = draft.required_sections
    .split("\n")
    .map((x) => x.trim())
    .filter(Boolean);
  const selectionCount =
    draft.source_ids.length + draft.task_ids.length + draft.event_ids.length;
  const validSelection = (
    ids: string[],
    choices: { id: string }[],
    max: number,
  ) =>
    ids.length <= max &&
    new Set(ids).size === ids.length &&
    ids.every((id) => choices.some((x) => x.id === id));
  if (
    !goal ||
    goal.length > 4000 ||
    !draft.retain ||
    scope.scope_revision.length !== 64 ||
    !scope.modes.includes(draft.mode)
  )
    return null;
  if (
    !selectionCount ||
    (draft.mode === "model" && selectionCount > 10) ||
    sections.length > 8 ||
    sections.some((x) => x.length > 160)
  )
    return null;
  if (
    !validSelection(
      draft.source_ids,
      scope.sources.filter((x) => x.status === "verified"),
      12,
    ) ||
    !validSelection(draft.task_ids, scope.tasks, 10) ||
    !validSelection(draft.event_ids, scope.events, 10)
  )
    return null;
  if (selectedBytes(draft.source_ids, scope.sources) > 4 * 1024 * 1024)
    return null;
  if (
    draft.mode === "model" &&
    (!draft.share ||
      !scope.destinations.some(
        (x) => x.id === draft.destination && x.kind === "text",
      ))
  )
    return null;
  if (
    draft.mode === "model" &&
    (draft.task_ids.length || draft.event_ids.length) &&
    !scope.business_context_allowed
  )
    return null;
  return {
    goal,
    mode: draft.mode,
    source_ids: [...draft.source_ids],
    task_ids: [...draft.task_ids],
    event_ids: [...draft.event_ids],
    retain: true,
    scope_revision: scope.scope_revision,
    provider_destination_id: draft.mode === "model" ? draft.destination : null,
    share_sources_with_provider: draft.mode === "model" && draft.share,
    mutation_requests: [],
    allow_mutation_proposals:
      draft.mode === "model" && draft.allow_mutation_proposals,
    required_sections: sections,
  };
}
export function sourceFormat(name: string): FileFormat | null {
  const extension = name.toLowerCase().split(".").at(-1);
  const formats: Record<string, FileFormat> = {
    txt: "text",
    md: "markdown",
    markdown: "markdown",
    csv: "csv",
    json: "json",
  };
  return formats[extension ?? ""] ?? null;
}
export function selectedBytes(ids: string[], sources: SourceRecord[]) {
  return sources
    .filter((x) => ids.includes(x.id))
    .reduce((n, x) => n + x.byte_count, 0);
}
export function byteVerified(artifact: ArtifactRecord) {
  return (
    artifact.status === "verified" && artifact.verification === "byte_readback"
  );
}
export function canReviewProposal(
  proposal: { state?: string; expires_at?: string },
  now = Date.now(),
) {
  return (
    proposal.state === "pending" &&
    !!proposal.expires_at &&
    Number.isFinite(Date.parse(proposal.expires_at)) &&
    Date.parse(proposal.expires_at) > now
  );
}
