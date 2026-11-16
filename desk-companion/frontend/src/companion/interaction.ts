/** Presentation only. No transcript, audio, permissions or business actions. */
export type CompanionState = "idle" | "listening" | "thinking" | "speaking";

export function companionState(value: string): CompanionState {
  if (value === "connecting") return "thinking";
  return value === "listening" || value === "thinking" || value === "speaking"
    ? value
    : "idle";
}

const sources = new Map<symbol, CompanionState>();
const listeners = new Set<(state: CompanionState | null) => void>();
const priority: CompanionState[] = ["speaking", "listening", "thinking"];

function current() {
  return (
    priority.find((state) => [...sources.values()].includes(state)) ?? null
  );
}

export function reportInteraction(
  source: symbol,
  state: CompanionState | null,
) {
  const before = current();
  if (state && state !== "idle") sources.set(source, state);
  else sources.delete(source);
  const after = current();
  if (before !== after) for (const receive of listeners) receive(after);
}

export function subscribeInteraction(
  receive: (state: CompanionState | null) => void,
) {
  listeners.add(receive);
  receive(current());
  return () => {
    listeners.delete(receive);
  };
}
