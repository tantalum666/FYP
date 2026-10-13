import type { VoiceGoalOrigin, VoiceOrigin } from "../voiceWork/types";
import { browserReady } from "../browser/types.ts";
import type { BrowserCapabilities, BrowserJob } from "../browser/types.ts";
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
export interface RunConnectorTool {
  tool_id: string;
  connector_id: string;
  tool_name: string;
  effect: "read" | "write";
  input_schema: Record<string, unknown>;
  descriptor_sha256: string;
  grant_sha256: string;
  destination_scope: string;
  endpoint: string;
  data_policy: "public_or_synthetic";
  review_required: true;
  live_acceptance: "not_verified_here";
}
export interface RunContextCatalog {
  memories: {
    id: string;
    version: number;
    category: string;
    summary: string;
  }[];
  conversations: {
    id: string;
    version: number;
    title: string;
    eligible_message_count: number;
  }[];
  memory_allowed: boolean;
  history_allowed: boolean;
  limits: { memories: number; messages: number };
  revision: string;
}
export interface RunPersonalSelection {
  memory_ids: string[];
  conversation_id: string | null;
  retain_derived_context: boolean;
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
  browser?: BrowserCapabilities;
  connectors?: { tools: RunConnectorTool[]; scope_revision: string };
  personal_context?: RunContextCatalog;
}
export interface AgentRun {
  voice_origin?: VoiceOrigin | null;
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
  model_call_budget?: number;
  tool_call_budget?: number;
  tool_calls?: number;
  browser_job_ids?: string[];
  tool_results?: {
    tool: string;
    arguments: Record<string, unknown>;
    operation_key: string;
    reference_id: string;
    state: "observed" | "pending" | "verified" | "unknown" | "rejected";
    result: Record<string, unknown>;
  }[];
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
  browser_jobs?: BrowserJob[];
  proposals: {
    id: string;
    kind: string;
    state?: string;
    expires_at?: string;
  }[];
}
export interface RunCreateInput {
  voice_origin_ref?: string;
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
  browser_source_ids: string[];
  browser_public_only: boolean;
  model_call_budget: number;
  tool_call_budget: number;
  connector_tool_ids: string[];
  share_connector_results_with_provider: boolean;
  personal_context: RunPersonalSelection | null;
}
export interface RunDraft {
  voice_origin_ref?: string;
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
  browser_source_ids: string[];
  browser_public_only: boolean;
  model_call_budget: number;
  tool_call_budget: number;
  connector_tool_ids: string[];
  share_connector_results_with_provider: boolean;
  personal_context: RunPersonalSelection;
}
export interface WorkGoalRequest {
  voiceOrigin?: VoiceGoalOrigin;
  id: string;
  text: string;
}
export function validWorkGoal(request: WorkGoalRequest | null | undefined) {
  return (
    !!request?.id &&
    !!request.text.trim() &&
    Array.from(request.text).length <= 4000 &&
    (!request.voiceOrigin ||
      (!!request.voiceOrigin.voice_origin_ref &&
        Date.parse(request.voiceOrigin.expires_at) > Date.now()))
  );
}
export function newRunDraft(initialGoal = ""): RunDraft {
  return {
    goal: initialGoal,
    mode: "deterministic",
    source_ids: [],
    task_ids: [],
    event_ids: [],
    retain: false,
    destination: "",
    share: false,
    allow_mutation_proposals: false,
    required_sections: "",
    browser_source_ids: [],
    browser_public_only: false,
    model_call_budget: 8,
    tool_call_budget: 8,
    connector_tool_ids: [],
    share_connector_results_with_provider: false,
    personal_context: {
      memory_ids: [],
      conversation_id: null,
      retain_derived_context: false,
    },
  };
}
export function runActions(
  state: string,
  reason: string | null = null,
  planRevision = 1,
): RunAction[] {
  const steer: RunAction[] = planRevision < 2 ? ["steer"] : [];
  if (["cancelled", "cancelling"].includes(state)) return [];
  if (
    reason &&
    [
      "RUN_PERSONAL_CONTEXT_CHANGED",
      "RUN_PERSONAL_CONTEXT_BINDING_CHANGED",
      "RUN_PERSONAL_CONTEXT_BINDING_INVALID",
      "RUN_PERSONAL_CONTEXT_UNAVAILABLE",
      "RUN_PERSONAL_CONTEXT_NOT_APPROVED",
      "RUN_PERSONAL_CONTEXT_LIMIT",
      "RUN_CONNECTOR_SCOPE_CHANGED",
    ].includes(reason)
  )
    return ["succeeded", "partial", "failed"].includes(state) ? [] : ["cancel"];
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
    draft.source_ids.length +
    draft.task_ids.length +
    draft.event_ids.length +
    draft.browser_source_ids.length;
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
    Array.from(goal).length > 4000 ||
    !draft.retain ||
    scope.scope_revision.length !== 64 ||
    !scope.modes.includes(draft.mode)
  )
    return null;
  if (
    !Number.isInteger(draft.model_call_budget) ||
    draft.model_call_budget < 1 ||
    draft.model_call_budget > budgetLimit(scope, "model") ||
    !Number.isInteger(draft.tool_call_budget) ||
    draft.tool_call_budget < 1 ||
    draft.tool_call_budget > budgetLimit(scope, "tool")
  )
    return null;
  if (
    draft.browser_source_ids.length &&
    (draft.mode !== "model" ||
      !draft.browser_public_only ||
      !browserReady(scope.browser ?? null, true) ||
      !validSelection(
        draft.browser_source_ids,
        scope.browser?.sources ?? [],
        2,
      ))
  )
    return null;
  const contextSelected =
    draft.personal_context.memory_ids.length > 0 ||
    !!draft.personal_context.conversation_id;
  if (
    draft.connector_tool_ids.length &&
    (draft.mode !== "model" ||
      !draft.share_connector_results_with_provider ||
      !validSelection(
        draft.connector_tool_ids,
        scope.connectors?.tools
          .filter(
            (tool) =>
              tool.review_required === true &&
              tool.data_policy === "public_or_synthetic",
          )
          .map((tool) => ({ id: tool.tool_id })) ?? [],
        8,
      ) ||
      draft.source_ids.length > 0 ||
      draft.task_ids.length > 0 ||
      draft.event_ids.length > 0 ||
      contextSelected)
  )
    return null;
  if (
    contextSelected &&
    (draft.mode !== "model" ||
      !draft.personal_context.retain_derived_context ||
      (draft.personal_context.memory_ids.length > 0 &&
        !scope.personal_context?.memory_allowed) ||
      !validSelection(
        draft.personal_context.memory_ids,
        scope.personal_context?.memories ?? [],
        8,
      ) ||
      (draft.personal_context.conversation_id &&
        (!scope.personal_context?.history_allowed ||
          !scope.personal_context.conversations.some(
            (item) =>
              item.id === draft.personal_context.conversation_id &&
              item.eligible_message_count > 0,
          ))))
  )
    return null;
  if (
    (!selectionCount && !draft.connector_tool_ids.length) ||
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
    ...(draft.voice_origin_ref
      ? { voice_origin_ref: draft.voice_origin_ref }
      : {}),
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
    browser_source_ids:
      draft.mode === "model" ? [...draft.browser_source_ids] : [],
    browser_public_only:
      draft.mode === "model" &&
      draft.browser_source_ids.length > 0 &&
      draft.browser_public_only,
    model_call_budget: draft.model_call_budget,
    tool_call_budget: draft.tool_call_budget,
    connector_tool_ids:
      draft.mode === "model" ? [...draft.connector_tool_ids] : [],
    share_connector_results_with_provider:
      draft.mode === "model" &&
      draft.connector_tool_ids.length > 0 &&
      draft.share_connector_results_with_provider,
    personal_context: contextSelected
      ? {
          ...draft.personal_context,
          memory_ids: [...draft.personal_context.memory_ids],
        }
      : null,
  };
}
export function budgetLimit(scope: RunScope, kind: "model" | "tool") {
  const ceiling = kind === "model" ? 24 : 16;
  const configured = scope.limits[`${kind}_call_budget_max`];
  return Number.isInteger(configured) && configured > 0
    ? Math.min(configured, ceiling)
    : ceiling;
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
