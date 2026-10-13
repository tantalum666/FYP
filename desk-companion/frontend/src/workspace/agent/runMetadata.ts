/** Deliberately separate from AgentRun: hidden views never retain private fields. */
export interface RunMetadata {
  id: string;
  state: string;
  version: number;
  created_at: string;
  updated_at: string;
}

const states = new Set([
  "queued",
  "planning",
  "running",
  "waiting_input",
  "waiting_review",
  "waiting_effect",
  "blocked",
  "paused",
  "verifying",
  "succeeded",
  "partial",
  "failed",
  "cancelled",
  "cancelling",
]);

export function runMetadata(value: unknown): RunMetadata | null {
  if (!value || typeof value !== "object") return null;
  const row = value as Record<string, unknown>;
  if (
    typeof row.id !== "string" ||
    !/^[a-zA-Z0-9_-]{1,128}$/.test(row.id) ||
    !Number.isSafeInteger(row.version) ||
    Number(row.version) < 1 ||
    typeof row.created_at !== "string" ||
    !Number.isFinite(Date.parse(row.created_at)) ||
    typeof row.updated_at !== "string" ||
    !Number.isFinite(Date.parse(row.updated_at))
  )
    return null;
  return {
    id: row.id,
    state:
      typeof row.state === "string" && states.has(row.state)
        ? row.state
        : "unknown",
    version: Number(row.version),
    created_at: new Date(row.created_at).toISOString(),
    updated_at: new Date(row.updated_at).toISOString(),
  };
}

export async function loadRunMetadata(
  read: (path: string) => Promise<unknown>,
) {
  const value = await read("/agent-runs");
  if (
    !value ||
    typeof value !== "object" ||
    !("runs" in value) ||
    !Array.isArray(value.runs)
  )
    throw new Error("RUN_METADATA_INVALID");
  // Project even an unexpectedly full server response before storing it in state.
  return value.runs
    .map(runMetadata)
    .filter((row): row is RunMetadata => row !== null);
}

export function metadataActions(state: string): ("pause" | "cancel")[] {
  if (["paused", "blocked"].includes(state)) return ["cancel"];
  if (
    [
      "queued",
      "planning",
      "running",
      "waiting_input",
      "waiting_review",
      "waiting_effect",
      "verifying",
    ].includes(state)
  )
    return ["pause", "cancel"];
  return [];
}

export function runAccess(
  owner: boolean,
  connected: boolean,
  surfaceVisible: boolean,
  privateVisible: boolean,
) {
  const available = owner && connected && surfaceVisible;
  return { available, privateVisible: available && privateVisible };
}
