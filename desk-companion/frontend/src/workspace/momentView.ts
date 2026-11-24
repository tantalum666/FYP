export interface MomentSuggestion {
  id: string;
  reason_en: string;
  reason_zh: string;
}

export interface MomentSnapshot {
  suggestion: MomentSuggestion | null;
  dismissals: Array<{ id: string }>;
  paused: boolean;
  pause_reason_en: string;
  pause_reason_zh: string;
}

/** One Today suggestion, or a reset once something was dismissed. Hidden otherwise. */
export function momentView(moments: MomentSnapshot | null, owner: boolean) {
  if (!owner || !moments) return null;
  if (!moments.suggestion && !moments.paused && moments.dismissals.length === 0)
    return null;
  return {
    suggestion: moments.suggestion,
    paused: moments.paused
      ? { en: moments.pause_reason_en, zh: moments.pause_reason_zh }
      : null,
    canReset: moments.dismissals.length > 0,
  };
}
