export type SurfaceFailure =
  | "offline"
  | "error"
  | "session-expired"
  | "signed-out";

function httpStatus(error: unknown): number | null {
  if (typeof error !== "object" || error === null) return null;
  if (!("status" in error) || !("code" in error)) return null;
  const status = error.status;
  return typeof status === "number" ? status : null;
}

/** Classify a failed owner or device request. A 401 only means expiry after a session existed. */
export function classifyFailure(
  error: unknown,
  hadSession: boolean,
): SurfaceFailure {
  const status = httpStatus(error);
  if (status === null) return "offline";
  if (status === 401) return hadSession ? "session-expired" : "signed-out";
  if (status >= 400) return "error";
  return "offline";
}
