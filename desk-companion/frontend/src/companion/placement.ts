export type CompanionMode = "full" | "half" | "head" | "hidden";
export type CompanionDock = "free" | "left" | "right" | "bottom";
export type CompanionSize = "small" | "medium" | "large";
export type Surface = "web" | "device";
export interface CompanionPreference {
  version: 1;
  mode: CompanionMode;
  dock: CompanionDock;
  x: number;
  y: number;
  size: CompanionSize;
  scale: number;
  motion: boolean;
}
export interface Viewport {
  width: number;
  height: number;
}
export interface Geometry {
  x: number;
  y: number;
  width: number;
  height: number;
  visibleHeight: number;
  handleX: number;
  handleY: number;
  bottomInset: number;
}
export interface CompanionAnchor {
  x: number;
  y: number;
  width: number;
  height: number;
}
export const MODES: CompanionMode[] = ["full", "half", "head", "hidden"];
const DOCKS: CompanionDock[] = ["free", "left", "right", "bottom"];
const SIZES: CompanionSize[] = ["small", "medium", "large"];
const FRACTION = { full: 1, half: 0.54, head: 0.21, hidden: 0 };

export function anchoredGeometry(
  mode: CompanionMode,
  anchor: CompanionAnchor | null,
  view: Viewport,
  aspect: number,
): Geometry | null {
  if (
    !anchor ||
    !Object.values(anchor).every(Number.isFinite) ||
    !Number.isFinite(aspect) ||
    aspect <= 0
  )
    return null;
  const height = Math.min(
    240,
    anchor.height - 44,
    (anchor.width - 44) / aspect,
  );
  if (height < 60 || anchor.x < 0 || anchor.y < 0) return null;
  const width = height * aspect;
  const visibleHeight = height * FRACTION[mode];
  return {
    x: anchor.x + (anchor.width - width) / 2,
    y: anchor.y + 4 + Math.max(0, (anchor.height - 44 - visibleHeight) / 2),
    width,
    height,
    visibleHeight,
    handleX: anchor.x + (anchor.width - 40) / 2,
    handleY: anchor.y + anchor.height - 78,
    bottomInset: Math.max(0, view.height - anchor.y - anchor.height),
  };
}
export const clamp = (n: number, low: number, high: number) =>
  Math.max(low, Math.min(Math.max(low, high), n));

export function defaultPreference(): CompanionPreference {
  return {
    version: 1,
    mode: "full",
    dock: "free",
    x: 1,
    y: 1,
    size: "medium",
    scale: 1,
    motion: true,
  };
}
export function readPreference(raw: string | null): CompanionPreference {
  try {
    const p = JSON.parse(raw ?? "null");
    if (!p || p.version !== 1) return defaultPreference();
    return {
      version: 1,
      mode: MODES.includes(p.mode) ? p.mode : "full",
      dock: DOCKS.includes(p.dock) ? p.dock : "free",
      x: typeof p.x === "number" && Number.isFinite(p.x) ? clamp(p.x, 0, 1) : 1,
      y: typeof p.y === "number" && Number.isFinite(p.y) ? clamp(p.y, 0, 1) : 1,
      size: SIZES.includes(p.size) ? p.size : "medium",
      scale:
        typeof p.scale === "number" && Number.isFinite(p.scale)
          ? clamp(p.scale, 0.5, 2)
          : { small: 0.8, medium: 1, large: 1.2 }[
              SIZES.includes(p.size) ? (p.size as CompanionSize) : "medium"
            ],
      motion: p.motion !== false,
    };
  } catch {
    return defaultPreference();
  }
}
export function bottomInset(v: Viewport, surface: Surface) {
  return surface === "device" ? 76 : v.width < 700 ? 80 : 22;
}
export function scaleLimit(v: Viewport, surface: Surface, aspect: number) {
  const base = surface === "device" ? 276 : v.width < 700 ? 236 : 340;
  return clamp(
    Math.min(
      2,
      (v.height - bottomInset(v, surface) - 32) / base,
      (v.width - 48) / aspect / base,
    ),
    0.5,
    2,
  );
}
export function geometry(
  p: CompanionPreference,
  v: Viewport,
  surface: Surface,
  aspect: number,
): Geometry {
  const inset = Math.min(
    bottomInset(v, surface),
    Math.max(12, v.height * 0.25),
  );
  const base = surface === "device" ? 276 : v.width < 700 ? 236 : 340;
  const factor = p.scale;
  const height = Math.min(
    base * factor,
    Math.max(80, v.height - inset - 32),
    Math.max(80, (v.width - 48) / aspect),
  );
  const width = height * aspect;
  const visibleHeight = height * FRACTION[p.mode];
  let x = 12 + p.x * Math.max(0, v.width - width - 24);
  let y = 12 + p.y * Math.max(0, v.height - inset - visibleHeight - 24);
  if (p.dock === "left") x = -width * 0.14;
  if (p.dock === "right") x = v.width - width * 0.86;
  if (p.dock === "bottom") y = v.height - inset - visibleHeight;
  const handleX =
    p.dock === "left"
      ? 4
      : p.dock === "right"
        ? v.width - 40
        : clamp(x + width / 2 - 18, 8, v.width - 44);
  const handleY =
    p.dock === "bottom" || p.dock === "free"
      ? v.height - inset - 38
      : clamp(
          12 + p.y * Math.max(0, v.height - inset - 60),
          8,
          v.height - inset - 44,
        );
  return {
    x,
    y,
    width,
    height,
    visibleHeight,
    handleX,
    handleY,
    bottomInset: inset,
  };
}
export function edgeIntent(
  x: number,
  y: number,
  v: Viewport,
  surface: Surface,
): { dock: CompanionDock; mode: CompanionMode } {
  const edges = [
    { dock: "left" as const, distance: x },
    { dock: "right" as const, distance: v.width - x },
    {
      dock: "bottom" as const,
      distance: v.height - bottomInset(v, surface) - y,
    },
  ].sort((a, b) => a.distance - b.distance);
  const edge = edges[0];
  if (edge.distance > 72) return { dock: "free", mode: "full" };
  return {
    dock: edge.dock,
    mode:
      edge.distance <= 12 ? "hidden" : edge.distance <= 36 ? "head" : "half",
  };
}
export function movedPreference(
  p: CompanionPreference,
  left: number,
  top: number,
  intent: { dock: CompanionDock; mode: CompanionMode },
  v: Viewport,
  surface: Surface,
  aspect: number,
): CompanionPreference {
  const next = { ...p, ...intent };
  const g = geometry(next, v, surface, aspect);
  return {
    ...next,
    x: clamp((left - 12) / Math.max(1, v.width - g.width - 24), 0, 1),
    y: clamp(
      (top - 12) / Math.max(1, v.height - g.bottomInset - g.visibleHeight - 24),
      0,
      1,
    ),
  };
}
