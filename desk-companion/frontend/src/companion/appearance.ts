export const APPEARANCE_KEY = "desk.companion.complete-vrm.v2";
export const APPEARANCE_EVENT = "desk:complete-vrm-choice";
export const MODELS = {
  alice: {
    name: "AliceChan · 作者原版",
    nameEn: "AliceChan · Original",
    file: "/avatars/alice/alice-ready.vrm",
  },
  shino: {
    name: "Shino · 长发款",
    nameEn: "Shino · Long hair",
    file: "/avatars/open-models/shino-ready.vrm",
  },
  victoria: {
    name: "Victoria · 卷发款",
    nameEn: "Victoria · Wavy hair",
    file: "/avatars/open-models/victoria-ready.vrm",
  },
} as const;
export type Appearance = {
  model: keyof typeof MODELS;
  palette: "original" | "silver";
  headRatio: number;
};
const DEFAULT: Appearance = {
  model: "alice",
  palette: "original",
  headRatio: 1,
};
export function readAppearance(): Appearance {
  try {
    const raw: unknown = JSON.parse(
      localStorage.getItem(APPEARANCE_KEY) ?? "null",
    );
    if (!raw || typeof raw !== "object") return { ...DEFAULT };
    const value = raw as Partial<Appearance>;
    if (!value.model || !Object.hasOwn(MODELS, value.model))
      return { ...DEFAULT };
    return {
      model:
        value.model && Object.hasOwn(MODELS, value.model)
          ? value.model
          : "alice",
      palette: value.palette === "silver" ? "silver" : "original",
      headRatio:
        typeof value.headRatio === "number" && Number.isFinite(value.headRatio)
          ? Math.max(0.92, Math.min(1.08, value.headRatio))
          : 1,
    };
  } catch {
    return { ...DEFAULT };
  }
}
export function saveAppearance(value: Appearance): boolean {
  try {
    localStorage.setItem(APPEARANCE_KEY, JSON.stringify(value));
    window.dispatchEvent(new Event(APPEARANCE_EVENT));
    return true;
  } catch {
    return false;
  }
}
