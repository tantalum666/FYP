export type Substitution = "none" | "same_spec_cheaper";

/** Whole currency units, up to two decimals, as minor units. */
export function minorUnits(value: string, allowZero = false): number | null {
  const match = /^(\d{1,7})(?:\.(\d{1,2}))?$/.exec(value.trim());
  if (!match) return null;
  const total = Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0"));
  const lower = allowZero ? 0 : 1;
  if (!Number.isSafeInteger(total) || total < lower || total > 10_000_000) return null;
  return total;
}

export function formatMinor(minor: number, currency: string): string {
  const whole = Math.floor(Math.abs(minor) / 100);
  const fraction = String(Math.abs(minor) % 100).padStart(2, "0");
  return `${currency} ${whole}.${fraction}`;
}

/** Only keys the owner filled are sent. Omitted fields are not cleared. */
export function cardPatch(
  fields: Partial<{
    label: string;
    sku: string;
    quantity: number;
    unit: string;
    merchants: string[];
    budget_minor: number;
    currency: string;
    substitution: Substitution;
    address_scope: string;
  }>,
): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(fields)) {
    if (value !== undefined) body[key] = value;
  }
  return body;
}

export function merchantList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
}
