/** Request bodies for a source comparison. Omitted fields are left out of the JSON. */

export interface BriefSource {
  id: string;
  label: string;
  locator: string | null;
  available: boolean;
  gap: string | null;
  body: string | null;
  position: number;
}

export interface BriefClaim {
  id: string;
  kind: "cited" | "unknown";
  text: string;
  source_id: string | null;
  quote: string | null;
  position: number;
}

export interface BriefGap {
  id: string;
  label: string;
  gap: string;
  locator: string | null;
}

export interface SourceBrief {
  id: string;
  question: string;
  note: string | null;
  status: "draft" | "saved";
  sources: BriefSource[];
  claims: BriefClaim[];
  gaps: BriefGap[];
  digest: string;
  live_lookup: false;
  model_call: false;
  created_at: string;
  saved_at: string | null;
}

export function openBody(input: { question: string; note?: string }) {
  const body: { question: string; note?: string } = { question: input.question };
  if (input.note !== undefined) body.note = input.note;
  return body;
}

export function sourceBody(input: {
  label: string;
  available: boolean;
  locator?: string;
  body?: string;
  gap?: string;
}) {
  const payload: {
    label: string;
    available: boolean;
    locator?: string;
    body?: string;
    gap?: string;
  } = { label: input.label, available: input.available };
  if (input.locator !== undefined) payload.locator = input.locator;
  if (input.available) {
    if (input.body !== undefined) payload.body = input.body;
  } else if (input.gap !== undefined) payload.gap = input.gap;
  return payload;
}

export function claimBody(input: {
  kind: "cited" | "unknown";
  text: string;
  sourceId?: string;
  quote?: string;
}) {
  if (input.kind === "unknown") return { kind: "unknown" as const, text: input.text };
  return {
    kind: "cited" as const,
    text: input.text,
    source_id: input.sourceId ?? "",
    quote: input.quote ?? "",
  };
}

export function citableSources(brief: SourceBrief) {
  return brief.sources.filter((source) => source.available);
}

export function canSave(brief: SourceBrief) {
  return brief.status === "draft" && (brief.claims.length > 0 || brief.gaps.length > 0);
}

export function savedLine(brief: SourceBrief, language: "en" | "zh") {
  if (brief.gaps.length > 0) {
    return language === "en"
      ? "Saved on this desk. A source is still missing, so this is not a complete comparison."
      : "已保存在这台桌面。仍有一份资料缺失，所以这还不是完整对照。";
  }
  return language === "en"
    ? "Saved on this desk. Nothing was looked up live."
    : "已保存在这台桌面。没有进行实时查找。";
}
