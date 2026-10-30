import type { ResponseFence } from "../personal/responseFence.ts";
import type {
  ArtifactRecord,
  FileFormat,
  RunDetailResponse,
  RunMode,
  SourceRecord,
} from "./types.ts";

export type WorkSearchKind = "all" | "run" | "artifact" | "source";
export type MatchedField =
  "id" | "title" | "source_name" | "current_linked_goal";
export type MatchReason =
  | "browse"
  | "exact_id"
  | "exact_title"
  | "phrase"
  | "all_terms"
  | "linked_metadata";
export type OutputMembership = "current" | "earlier" | "unknown" | "unlinked";
interface SearchHit {
  id: string;
  title: string;
  timestamp: string | null;
  matched_fields: MatchedField[];
  match_reason: MatchReason;
}
interface FileHit extends SearchHit {
  format: FileFormat | null;
  byte_count: number | null;
  recorded_status: "verified" | "unknown";
}
export interface WorkRunHit extends SearchHit {
  kind: "run";
  state: string;
  version: number | null;
  mode: RunMode | null;
  plan_revision: number | null;
  source_names: string[];
}
export interface WorkArtifactHit extends FileHit {
  kind: "artifact";
  run_id: string | null;
  current_linked_goal: string | null;
  output_membership: OutputMembership;
  source_names: string[];
}
export interface WorkSourceHit extends FileHit {
  kind: "source";
  revision: number;
}
export type WorkSearchHit = WorkRunHit | WorkArtifactHit | WorkSourceHit;
export interface WorkSearchInput {
  query: string;
  kind: WorkSearchKind;
  limit: number;
  offset: number;
  snapshot?: string;
}
export interface WorkSearchResponse {
  items: WorkSearchHit[];
  total: number;
  snapshot: string;
  next_offset: number | null;
  search_scope: "local_metadata";
  ranking: "lexical_v1";
  file_status_basis: "last_recorded";
}
export type WorkSearchDetail =
  | { kind: "run"; value: RunDetailResponse }
  | { kind: "artifact"; value: ArtifactRecord }
  | { kind: "source"; value: SourceRecord };
export const searchKinds: WorkSearchKind[] = [
  "all",
  "run",
  "artifact",
  "source",
];
export const workSearchLimit = 20;
export function workSearchInput(
  query: string,
  kind: WorkSearchKind,
): WorkSearchInput | null {
  const trimmed = query.trim();
  // Count code points, matching the server's string-length boundary.
  if ([...trimmed].length > 200 || !searchKinds.includes(kind)) return null;
  return { query: trimmed, kind, limit: workSearchLimit, offset: 0 };
}
export function workHitKey(hit: Pick<WorkSearchHit, "id" | "kind">) {
  return `${hit.kind}:${hit.id}`;
}
export function workDetailPath(hit: Pick<WorkSearchHit, "id" | "kind">) {
  const prefix = {
    run: "/agent-runs/",
    artifact: "/artifacts/",
    source: "/sources/",
  }[hit.kind];
  return prefix + encodeURIComponent(hit.id);
}
const object = (value: unknown): value is Record<string, unknown> =>
  !!value && typeof value === "object" && !Array.isArray(value);
const integer = (value: unknown): value is number =>
  Number.isSafeInteger(value) && Number(value) >= 0;
const nullableInteger = (value: unknown) => value === null || integer(value);
const strings = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === "string");
const nullableString = (value: unknown) =>
  value === null || typeof value === "string";
const formats = ["text", "markdown", "csv", "json"];
const oneOf = (value: unknown, choices: string[]) =>
  typeof value === "string" && choices.includes(value);
function validHit(hit: unknown): hit is WorkSearchHit {
  if (
    !object(hit) ||
    typeof hit.id !== "string" ||
    !hit.id ||
    typeof hit.title !== "string" ||
    !nullableString(hit.timestamp) ||
    !strings(hit.matched_fields) ||
    !hit.matched_fields.every((field) =>
      ["id", "title", "source_name", "current_linked_goal"].includes(field),
    ) ||
    !oneOf(hit.match_reason, [
      "browse",
      "exact_id",
      "exact_title",
      "phrase",
      "all_terms",
      "linked_metadata",
    ])
  )
    return false;
  if (hit.kind === "run")
    return (
      typeof hit.state === "string" &&
      nullableInteger(hit.version) &&
      nullableInteger(hit.plan_revision) &&
      (hit.mode === null || oneOf(hit.mode, ["model", "deterministic"])) &&
      strings(hit.source_names)
    );
  if (
    !oneOf(hit.kind, ["artifact", "source"]) ||
    !(hit.format === null || oneOf(hit.format, formats)) ||
    !nullableInteger(hit.byte_count) ||
    !oneOf(hit.recorded_status, ["verified", "unknown"])
  )
    return false;
  if (hit.kind === "source") return hit.revision === 1;
  return (
    nullableString(hit.run_id) &&
    nullableString(hit.current_linked_goal) &&
    oneOf(hit.output_membership, [
      "current",
      "earlier",
      "unknown",
      "unlinked",
    ]) &&
    strings(hit.source_names)
  );
}
/** Reject malformed pages rather than rendering a partial or misleading result set. */
export function validWorkSearchResponse(
  value: unknown,
  input: WorkSearchInput,
): value is WorkSearchResponse {
  if (
    !object(value) ||
    value.search_scope !== "local_metadata" ||
    value.ranking !== "lexical_v1" ||
    value.file_status_basis !== "last_recorded" ||
    typeof value.snapshot !== "string" ||
    !/^[a-f0-9]{64}$/.test(value.snapshot) ||
    (input.snapshot && input.snapshot !== value.snapshot) ||
    !integer(value.total) ||
    value.total > 600 ||
    !Array.isArray(value.items) ||
    value.items.length > input.limit ||
    !value.items.every(validHit)
  )
    return false;
  if (
    value.items.some((hit) => input.kind !== "all" && hit.kind !== input.kind)
  )
    return false;
  const end = input.offset + value.items.length;
  return (
    new Set(value.items.map(workHitKey)).size === value.items.length &&
    end <= value.total &&
    (value.next_offset === null
      ? end === value.total
      : integer(value.next_offset) &&
        value.next_offset === end &&
        end < value.total &&
        value.items.length === input.limit)
  );
}
/** A compact hit is never a full record. Validate the exact detail response separately. */
export function workSearchDetail(
  hit: WorkSearchHit,
  body: unknown,
): WorkSearchDetail | null {
  if (!object(body)) return null;
  if (hit.kind === "run") {
    if (
      !object(body.run) ||
      body.run.id !== hit.id ||
      body.run.private_hidden ||
      !integer(body.run.version) ||
      !Array.isArray(body.steps) ||
      !Array.isArray(body.events) ||
      !Array.isArray(body.artifacts) ||
      !Array.isArray(body.proposals)
    )
      return null;
    return { kind: "run", value: body as unknown as RunDetailResponse };
  }
  if (
    body.id !== hit.id ||
    !oneOf(body.format, formats) ||
    !integer(body.byte_count) ||
    typeof body.sha256 !== "string" ||
    !/^[a-f0-9]{64}$/.test(body.sha256) ||
    !oneOf(body.status, ["verified", "unknown", "failed"])
  )
    return null;
  if (hit.kind === "source") {
    if (typeof body.name !== "string" || body.revision !== 1) return null;
    return { kind: "source", value: body as unknown as SourceRecord };
  }
  if (
    typeof body.display_name !== "string" ||
    !Array.isArray(body.provenance) ||
    !body.provenance.every(
      (ref) =>
        object(ref) &&
        typeof ref.source_id === "string" &&
        integer(ref.source_revision) &&
        integer(ref.start_line) &&
        integer(ref.end_line) &&
        typeof ref.sha256 === "string",
    ) ||
    !oneOf(body.authorship, ["deterministic", "model", "owner"]) ||
    !oneOf(body.verification, ["byte_readback", "unverified"])
  )
    return null;
  return { kind: "artifact", value: body as unknown as ArtifactRecord };
}
/** Separate sequence and privacy tokens fence both search and exact detail requests. */
export class WorkSearchFence {
  private sequence = 0;
  invalidate() {
    this.sequence++;
  }
  begin(fence: ResponseFence) {
    return { sequence: ++this.sequence, epoch: fence.capture() };
  }
  accepts(ticket: { sequence: number; epoch: number }, fence: ResponseFence) {
    return ticket.sequence === this.sequence && fence.accepts(ticket.epoch);
  }
}
