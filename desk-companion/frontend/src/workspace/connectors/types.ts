export type ConnectorState =
  | "review"
  | "queued"
  | "preflight"
  | "dispatching"
  | "observed_result"
  | "unknown_effect"
  | "failed"
  | "rejected"
  | "cancelled"
  | "expired"
  | "unrecognized";

/** Content-free projection, including when the server unexpectedly returns detail. */
export interface ConnectorMetadata {
  id: string;
  state: ConnectorState;
  version: number;
  created_at: string;
  updated_at: string;
  expires_at: string;
  dispatched: boolean;
  cancel_requested: boolean;
}
export interface ConnectorDestination {
  tool_id: string;
  connector_id: string;
  tool_name: string;
  endpoint: string;
  server_name: string;
  server_version: string;
  destination_scope: string;
  effect: "read" | "write";
  arguments: Record<string, unknown>;
  data_policy: "public_or_synthetic";
  descriptor_sha256: string;
  grant_sha256: string;
  notice: string;
  provider_destination: {
    id: string;
    kind: "text";
    provider: string;
    endpoint: string;
  } | null;
}
export interface ConnectorResult {
  text: string[];
  structured_content: Record<string, unknown> | null;
  is_error: boolean;
  untrusted: true;
  verified: false;
  sha256: string;
  snapshot_sha256: string;
}
export interface ConnectorIntent extends ConnectorMetadata {
  intent?: ConnectorDestination;
  intent_hash?: string;
  result?: ConnectorResult | null;
  code?: string | null;
}
export interface ConnectorTool {
  tool_id: string;
  connector_id: string;
  tool_name: string;
  effect: "read" | "write";
  endpoint: string;
  descriptor_sha256: string;
  grant_sha256: string;
  destination_scope: string;
  data_policy: "public_or_synthetic";
  review_required: true;
  live_acceptance: string;
}
export interface ConnectorCapabilities {
  tools: ConnectorTool[];
  scope_revision: string;
}

const states = new Set<string>([
  "review",
  "queued",
  "preflight",
  "dispatching",
  "observed_result",
  "unknown_effect",
  "failed",
  "rejected",
  "cancelled",
  "expired",
]);
export const connectorId = (value: unknown): value is string =>
  typeof value === "string" && /^[a-f0-9]{32}$/.test(value);
export const connectorHash = (value: unknown): value is string =>
  typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
const record = (value: unknown): value is Record<string, unknown> =>
  !!value && typeof value === "object" && !Array.isArray(value);
const dated = (value: unknown): value is string =>
  typeof value === "string" && Number.isFinite(Date.parse(value));

export function connectorMetadata(value: unknown): ConnectorMetadata | null {
  if (
    !record(value) ||
    !connectorId(value.id) ||
    !Number.isSafeInteger(value.version) ||
    Number(value.version) < 1 ||
    !dated(value.created_at) ||
    !dated(value.updated_at) ||
    !dated(value.expires_at) ||
    typeof value.dispatched !== "boolean" ||
    typeof value.cancel_requested !== "boolean"
  )
    return null;
  return {
    id: value.id,
    state:
      typeof value.state === "string" && states.has(value.state)
        ? (value.state as ConnectorState)
        : "unrecognized",
    version: Number(value.version),
    created_at: new Date(value.created_at).toISOString(),
    updated_at: new Date(value.updated_at).toISOString(),
    expires_at: new Date(value.expires_at).toISOString(),
    dispatched: value.dispatched,
    cancel_requested: value.cancel_requested,
  };
}
export function connectorAccess(
  owner: boolean,
  connected: boolean,
  surfaceVisible: boolean,
  privateVisible: boolean,
) {
  const available = owner && connected && surfaceVisible;
  return { available, privateVisible: available && privateVisible };
}
export function connectorCancellable(intent: ConnectorMetadata) {
  return (
    ["review", "queued", "preflight", "dispatching"].includes(intent.state) &&
    !intent.cancel_requested
  );
}
export function connectorReviewable(
  intent: ConnectorIntent,
  catalog: ConnectorCapabilities | null,
  fresh: boolean,
  now: number,
) {
  const detail = intent.intent;
  if (
    !fresh ||
    !catalog ||
    !detail ||
    intent.state !== "review" ||
    intent.cancel_requested ||
    intent.dispatched ||
    !connectorHash(intent.intent_hash) ||
    !connectorHash(catalog.scope_revision) ||
    !connectorHash(detail.descriptor_sha256) ||
    !connectorHash(detail.grant_sha256) ||
    !Number.isSafeInteger(intent.version) ||
    intent.version < 1 ||
    Date.parse(intent.expires_at) <= now ||
    !Number.isFinite(Date.parse(intent.expires_at)) ||
    !record(detail.arguments) ||
    !["read", "write"].includes(detail.effect) ||
    detail.data_policy !== "public_or_synthetic" ||
    !(
      detail.provider_destination === null ||
      (record(detail.provider_destination) &&
        detail.provider_destination.kind === "text" &&
        [
          detail.provider_destination.id,
          detail.provider_destination.provider,
          detail.provider_destination.endpoint,
        ].every((s) => typeof s === "string" && !!s.trim()))
    ) ||
    ![
      detail.server_name,
      detail.server_version,
      detail.destination_scope,
      detail.notice,
    ].every((s) => typeof s === "string" && !!s.trim())
  )
    return false;
  return catalog.tools.some(
    (tool) =>
      !!tool &&
      tool.tool_id === detail.tool_id &&
      tool.connector_id === detail.connector_id &&
      tool.tool_name === detail.tool_name &&
      tool.endpoint === detail.endpoint &&
      tool.effect === detail.effect &&
      tool.descriptor_sha256 === detail.descriptor_sha256 &&
      tool.grant_sha256 === detail.grant_sha256 &&
      tool.destination_scope === detail.destination_scope &&
      tool.data_policy === "public_or_synthetic" &&
      tool.review_required === true,
  );
}
/** Includes the displayed content, so even an inconsistent same-hash response clears the checkbox. */
export function connectorReviewKey(intent: ConnectorIntent) {
  return JSON.stringify([
    intent.id,
    intent.version,
    intent.intent_hash,
    intent.intent,
  ]);
}
export function connectorSelection(
  current: string | null,
  next: string | null,
  dirty: boolean,
  busy: boolean,
) {
  if (current === next || busy) return "stay";
  return dirty ? "confirm" : "switch";
}

export async function loadConnectorMetadata(
  read: (path: string) => Promise<unknown>,
) {
  const result = await read("/connectors/intents?metadata_only=true");
  if (!record(result) || !Array.isArray(result.intents))
    throw new Error("CONNECTOR_RESPONSE_INVALID");
  return result.intents
    .map(connectorMetadata)
    .filter((row): row is ConnectorMetadata => row !== null);
}
export async function loadConnectorPrivate(
  read: (path: string) => Promise<unknown>,
  selected: string | null,
  visible: boolean,
) {
  // This branch is intentionally above every private read, including capabilities.
  if (!visible) return { capabilities: null, detail: null };
  const [capabilities, detail] = await Promise.all([
    read("/connectors/capabilities"),
    connectorId(selected)
      ? read(`/connectors/intents/${selected}`)
      : Promise.resolve(null),
  ]);
  if (
    !record(capabilities) ||
    !Array.isArray(capabilities.tools) ||
    !connectorHash(capabilities.scope_revision)
  )
    throw new Error("CONNECTOR_RESPONSE_INVALID");
  if (
    detail !== null &&
    (!record(detail) ||
      !record(detail.intent) ||
      !connectorMetadata(detail.intent) ||
      detail.intent.id !== selected)
  )
    throw new Error("CONNECTOR_RESPONSE_INVALID");
  return {
    capabilities: capabilities as unknown as ConnectorCapabilities,
    detail: detail ? (detail as { intent: ConnectorIntent }).intent : null,
  };
}

/** Hidden linked calls can be older than the bounded recent list. */
export async function loadConnectorSelectedMetadata(
  read: (path: string) => Promise<unknown>,
  selected: string | null,
) {
  if (!connectorId(selected)) return null;
  const value = await read(
    `/connectors/intents/${selected}?metadata_only=true`,
  );
  if (!record(value)) throw new Error("CONNECTOR_RESPONSE_INVALID");
  const metadata = connectorMetadata(value.intent);
  if (!metadata || metadata.id !== selected)
    throw new Error("CONNECTOR_RESPONSE_INVALID");
  return metadata;
}
