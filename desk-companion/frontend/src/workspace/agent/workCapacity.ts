export type CapacityDimension = {
  limit: number;
  used: number | null;
  remaining: number | null;
  state: "known" | "over_limit" | "unavailable";
};
export type WorkCapacity = {
  basis: "retained_reservations";
  observed_at: string;
  advisory: true;
  sources: {
    count: CapacityDimension;
    bytes: CapacityDimension;
    file_bytes: number;
  };
  artifacts: {
    count: CapacityDimension;
    bytes: CapacityDimension;
    file_bytes: number;
    per_run_count: number;
    per_run_bytes: number;
  };
  runs: { count: CapacityDimension };
  watches: { count: CapacityDimension };
};
const integer = (v: unknown): v is number =>
  typeof v === "number" && Number.isSafeInteger(v) && v >= 0;
const object = (v: unknown): v is Record<string, unknown> =>
  !!v && typeof v === "object" && !Array.isArray(v);
export function validCapacityDimension(v: unknown): v is CapacityDimension {
  if (!object(v) || !integer(v.limit) || v.limit === 0) return false;
  if (v.state === "unavailable") return v.used === null && v.remaining === null;
  if (v.state === "over_limit" && v.used === null) return v.remaining === null;
  if (!integer(v.used) || !integer(v.remaining)) return false;
  if (v.state === "known")
    return v.used <= v.limit && v.remaining === v.limit - v.used;
  return v.state === "over_limit" && v.used > v.limit && v.remaining === 0;
}
export function validWorkCapacity(v: unknown): v is WorkCapacity {
  if (
    !object(v) ||
    v.basis !== "retained_reservations" ||
    v.advisory !== true ||
    typeof v.observed_at !== "string" ||
    !/^\d{4}-\d\d-\d\dT.*(?:Z|\+00:00)$/.test(v.observed_at) ||
    !Number.isFinite(Date.parse(v.observed_at))
  )
    return false;
  for (const key of ["sources", "artifacts", "runs", "watches"]) {
    const item = v[key];
    if (!object(item) || !validCapacityDimension(item.count)) return false;
    if (key === "sources" || key === "artifacts") {
      if (
        !validCapacityDimension(item.bytes) ||
        !integer(item.file_bytes) ||
        !item.file_bytes
      )
        return false;
    }
    if (
      key === "artifacts" &&
      (!integer(item.per_run_count) ||
        !item.per_run_count ||
        !integer(item.per_run_bytes) ||
        !item.per_run_bytes)
    )
      return false;
  }
  return true;
}
