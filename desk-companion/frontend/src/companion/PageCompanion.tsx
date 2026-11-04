import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { KeyboardEvent, PointerEvent } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Ellipsis,
  Maximize2,
  Move,
  Pause,
  Play,
  RotateCcw,
  Sparkles,
  X,
} from "lucide-react";
import type { Translate } from "../types";
import { A1_ART } from "./art";
import { A1Canvas } from "./A1Canvas";
import { useWorkspace } from "../workspace/WorkspaceContext";
import {
  clamp,
  anchoredGeometry,
  avoidRegion,
  defaultPreference,
  edgeIntent,
  geometry,
  MODES,
  movedPreference,
  readPreference,
  scaleLimit,
} from "./placement";
import type {
  CompanionMode,
  CompanionAnchor,
  CompanionPreference,
  Geometry,
  Surface,
  Viewport,
} from "./placement";
import "./companion.css";
type Gesture = "none" | "nod" | "wave" | "step";

function FlatCharacter({ onError }: { onError: () => void }) {
  return (
    <svg
      viewBox={A1_ART.viewBox.join(" ")}
      width="100%"
      height="100%"
      aria-hidden="true"
    >
      <image
        href={A1_ART.idle}
        width={A1_ART.width}
        height={A1_ART.height}
        onError={onError}
      />
    </svg>
  );
}

const ASPECT = 0.6;
const viewport = (): Viewport => ({
  width: innerWidth,
  height: window.visualViewport?.height ?? innerHeight,
});
function load(key: string) {
  try {
    return readPreference(localStorage.getItem(key));
  } catch {
    return defaultPreference();
  }
}
type Drag = {
  pointer: number;
  startX: number;
  startY: number;
  offsetX: number;
  offsetY: number;
  moved: boolean;
  original: CompanionPreference;
  next: CompanionPreference;
  visual: Geometry;
  point: { x: number; y: number };
  frame: number;
};
type Resize = {
  pointer: number;
  startX: number;
  startY: number;
  original: CompanionPreference;
  height: number;
  scale: number;
  direction: number;
  fraction: number;
  moved: boolean;
  frame: number;
  point: { x: number; y: number };
};

export function PageCompanion({
  t,
  surface = "web",
  blocked = false,
  homeId,
  avoidId,
  onOpenAssistant,
}: {
  t: Translate;
  surface?: Surface;
  blocked?: boolean;
  homeId?: string;
  avoidId?: string;
  onOpenAssistant: () => void;
}) {
  const key = `desk.a1.page-companion.v1.${surface}`;
  const layoutKey = `desk.companion.layout.v1.${surface}`;
  const [preferHome, setPreferHome] = useState(() => {
    try {
      return localStorage.getItem(layoutKey) !== "floating";
    } catch {
      return true;
    }
  });
  const [anchor, setAnchor] = useState<CompanionAnchor | null>(null);
  useLayoutEffect(() => {
    const node = homeId ? document.getElementById(homeId) : null;
    if (!node || surface !== "web") return;
    const update = () => {
      const rect = node.getBoundingClientRect();
      const next =
        rect.width && rect.height
          ? { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
          : null;
      setAnchor((previous) =>
        JSON.stringify(previous) === JSON.stringify(next) ? previous : next,
      );
    };
    const observer = new ResizeObserver(update);
    observer.observe(node);
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, { passive: true });
    update();
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update);
    };
  }, [homeId, surface]);
  const [avoid, setAvoid] = useState<CompanionAnchor | null>(null);
  useLayoutEffect(() => {
    const node = avoidId ? document.getElementById(avoidId) : null;
    if (!node) {
      setAvoid(null);
      return;
    }
    const update = () => {
      const rect = node.getBoundingClientRect();
      const next =
        rect.width && rect.height
          ? { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
          : null;
      setAvoid((old) =>
        JSON.stringify(old) === JSON.stringify(next) ? old : next,
      );
    };
    const observer = new ResizeObserver(update);
    observer.observe(node);
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, { passive: true });
    update();
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update);
    };
  }, [avoidId]);
  const { data } = useWorkspace();
  const [modalOpen, setModalOpen] = useState(false);
  const obscured = blocked || modalOpen;
  useEffect(() => {
    const update = () =>
      setModalOpen(
        !!document.querySelector(
          'dialog[open][data-companion-blocking="true"]',
        ),
      );
    window.addEventListener("desk:modal-state", update);
    update();
    return () => window.removeEventListener("desk:modal-state", update);
  }, []);
  const [use3D, setUse3D] = useState(() => {
    try {
      return localStorage.getItem(`desk.a1.3d.v2.${surface}`) !== "false";
    } catch {
      return true;
    }
  });
  const [action3D, setAction3D] = useState<
    "Idle" | "Wave" | "Turn" | "Walk" | "Stretch"
  >("Idle");
  const [preference, setPreference] = useState(() => load(key));
  const pref = useRef(preference);
  const [view, setView] = useState(viewport);
  const [menu, setMenu] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [previewMode, setPreviewMode] = useState<CompanionMode | null>(null);
  const [responding, setResponding] = useState(false);
  const [gesture, setGesture] = useState<Gesture>("none");
  const [pulse, setPulse] = useState(0);
  const [resizing, setResizing] = useState(false);
  const [greeting, setGreeting] = useState(false);
  const [reduced, setReduced] = useState(
    () => matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [visible, setVisible] = useState(() => !document.hidden);
  const [assetError, setAssetError] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const art = useRef<HTMLDivElement>(null);
  const hit = useRef<HTMLButtonElement>(null);
  const controls = useRef<HTMLDivElement>(null);
  const drag = useRef<Drag | null>(null);
  const resize = useRef<Resize | null>(null);
  const resizeHandle = useRef<HTMLButtonElement>(null);
  const scaleSaveTimer = useRef(0);
  const skipResizeClick = useRef(false);
  const clickTimer = useRef(0),
    responseTimer = useRef(0);
  const skipClick = useRef(false);
  const currentMode =
    previewMode === "hidden" ? "head" : (previewMode ?? preference.mode);
  const homeGeometry =
    preferHome && surface === "web"
      ? anchoredGeometry(preference.mode, anchor, view, ASPECT)
      : null;
  const atHome = !!homeGeometry;
  const resting =
    homeGeometry ??
    avoidRegion(geometry(preference, view, surface, ASPECT), avoid);
  const moving = preference.motion && !reduced && visible && !obscured;
  const limit = scaleLimit(view, surface, ASPECT);
  const effectiveScale = Math.min(preference.scale, limit);

  function store(next: CompanionPreference) {
    try {
      localStorage.setItem(key, JSON.stringify(next));
    } catch {
      /* The current session still works. */
    }
  }
  function persist(next: CompanionPreference) {
    pref.current = next;
    setPreference(next);
    store(next);
  }
  function changeScale(value: number, saveLater = true) {
    const scale = clamp(
      Math.round(value * 100) / 100,
      0.5,
      scaleLimit(view, surface, ASPECT),
    );
    const next = { ...pref.current, scale };
    pref.current = next;
    setPreference(next);
    if (saveLater) {
      clearTimeout(scaleSaveTimer.current);
      scaleSaveTimer.current = window.setTimeout(
        () => store(pref.current),
        180,
      );
    }
  }
  function flushScale() {
    clearTimeout(scaleSaveTimer.current);
    store(pref.current);
  }
  function paint(g: Geometry) {
    if (!atHome) g = avoidRegion(g, avoid);
    const node = root.current;
    if (!node) return;
    const values = {
      "--a1-x": g.x,
      "--a1-y": g.y,
      "--a1-width": g.width,
      "--a1-height": g.height,
      "--a1-visible": g.visibleHeight,
      "--a1-handle-x": g.handleX,
      "--a1-handle-y": g.handleY,
      "--a1-options-x": clamp(
        g.x + (g.x + g.width / 2 > view.width / 2 ? -34 : g.width + 5),
        8,
        view.width - 40,
      ),
      "--a1-options-y": clamp(g.y + 8, 8, view.height - g.bottomInset - 36),
      "--a1-resize-x": clamp(
        g.x + (g.x + g.width / 2 > view.width / 2 ? -13 : g.width - 10),
        8,
        view.width - 32,
      ),
      "--a1-resize-y": clamp(g.y - 16, 8, view.height - g.bottomInset - 30),
      "--a1-popup-x": clamp(g.x + g.width / 2 - 104, 8, view.width - 216),
      "--a1-bubble-y": clamp(g.y - 60, 8, view.height - g.bottomInset - 62),
      "--a1-menu-y": clamp(
        g.y - (controls.current?.offsetHeight ?? 280) - 10,
        8,
        view.height - (controls.current?.offsetHeight ?? 280) - 12,
      ),
    };
    for (const [name, value] of Object.entries(values))
      node.style.setProperty(name, `${value}px`);
  }
  useLayoutEffect(() => {
    paint(drag.current?.visual ?? resting);
  }, [preference, view, previewMode, menu, anchor, preferHome, avoid]);
  useEffect(() => {
    const change = () => {
      cancelDrag();
      cancelResize();
      setView(viewport());
    };
    const visibility = () => {
      if (document.hidden) {
        cancelDrag();
        cancelResize();
      }
      setVisible(!document.hidden);
    };
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const motion = () => setReduced(media.matches);
    window.addEventListener("resize", change);
    window.visualViewport?.addEventListener("resize", change);
    document.addEventListener("visibilitychange", visibility);
    media.addEventListener("change", motion);
    const save = () => store(resize.current?.original ?? pref.current);
    window.addEventListener("pagehide", save);
    return () => {
      window.removeEventListener("resize", change);
      window.visualViewport?.removeEventListener("resize", change);
      document.removeEventListener("visibilitychange", visibility);
      media.removeEventListener("change", motion);
      if (drag.current) cancelAnimationFrame(drag.current.frame);
      if (resize.current) cancelAnimationFrame(resize.current.frame);
      window.removeEventListener("pagehide", save);
      save();
      clearTimeout(scaleSaveTimer.current);
      clearTimeout(clickTimer.current);
      clearTimeout(responseTimer.current);
    };
  }, []);
  useEffect(() => {
    if (obscured) {
      cancelDrag();
      cancelResize();
      setMenu(false);
      setGreeting(false);
    }
  }, [obscured]);
  useEffect(() => {
    const sync = (e: StorageEvent) => {
      if (e.key === layoutKey) {
        cancelDrag();
        cancelResize();
        setPreferHome(e.newValue !== "floating");
      }
      if (e.key === key && !drag.current && !resize.current) {
        const next = readPreference(e.newValue);
        pref.current = next;
        setPreference(next);
      }
    };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, [key, layoutKey]);
  useEffect(() => {
    if (!menu) return;
    const close = (e: globalThis.PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) setMenu(false);
    };
    document.addEventListener("pointerdown", close);
    controls.current?.querySelector<HTMLButtonElement>("button")?.focus();
    return () => document.removeEventListener("pointerdown", close);
  }, [menu]);
  useEffect(() => {
    if (!moving || currentMode === "hidden") {
      art.current?.style.setProperty("--a1-lean", "0deg");
      art.current?.style.setProperty("--a1-follow", "0px");
      return;
    }
    let frame = 0,
      x = 0,
      y = 0;
    const follow = (e: globalThis.PointerEvent) => {
      if (e.pointerType !== "mouse" || drag.current || resize.current) return;
      x = e.clientX;
      y = e.clientY;
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        const box = art.current?.getBoundingClientRect();
        if (!box || !art.current) return;
        const amount = clamp(
          (x - box.left - box.width / 2) / Math.max(180, view.width * 0.3),
          -1,
          1,
        );
        art.current.style.setProperty("--a1-lean", `${amount * 0.28}deg`);
        art.current.style.setProperty("--a1-follow", `${amount * 0.55}px`);
      });
    };
    window.addEventListener("pointermove", follow, { passive: true });
    return () => {
      window.removeEventListener("pointermove", follow);
      cancelAnimationFrame(frame);
    };
  }, [moving, currentMode, view]);
  useEffect(() => {
    const node = hit.current;
    if (!node || obscured || atHome) return;
    let frame = 0,
      delta = 0;
    const wheel = (event: WheelEvent) => {
      if (drag.current || resize.current) return;
      event.preventDefault();
      delta +=
        event.deltaY *
        (event.deltaMode === 1 ? 14 : event.deltaMode === 2 ? view.height : 1);
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        changeScale(
          Math.min(pref.current.scale, scaleLimit(view, surface, ASPECT)) *
            Math.exp(-delta * 0.002),
        );
        delta = 0;
      });
    };
    node.addEventListener("wheel", wheel, { passive: false });
    return () => {
      node.removeEventListener("wheel", wheel);
      cancelAnimationFrame(frame);
    };
  }, [currentMode, view, obscured, surface, atHome]);

  function cancelResize() {
    const active = resize.current;
    if (!active) return;
    cancelAnimationFrame(active.frame);
    resize.current = null;
    if (resizeHandle.current?.hasPointerCapture(active.pointer))
      resizeHandle.current.releasePointerCapture(active.pointer);
    pref.current = active.original;
    setPreference(active.original);
    setResizing(false);
    skipResizeClick.current = active.moved;
  }
  function startResize(e: PointerEvent<HTMLButtonElement>) {
    if (e.button !== 0 || obscured || atHome) return;
    e.preventDefault();
    cancelDrag();
    flushScale();
    setMenu(false);
    const g = geometry(pref.current, view, surface, ASPECT);
    resize.current = {
      pointer: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      original: pref.current,
      height: g.height,
      scale: Math.min(pref.current.scale, limit),
      direction: g.x + g.width / 2 > view.width / 2 ? -1 : 1,
      fraction: g.visibleHeight / g.height,
      moved: false,
      frame: 0,
      point: { x: e.clientX, y: e.clientY },
    };
    skipResizeClick.current = false;
    e.currentTarget.setPointerCapture(e.pointerId);
  }
  function updateResize() {
    const active = resize.current;
    if (!active) return;
    active.frame = 0;
    const dx = active.point.x - active.startX,
      dy = active.point.y - active.startY;
    if (!active.moved && Math.hypot(dx, dy) < 3) return;
    active.moved = true;
    setResizing(true);
    const dh =
      (dx * active.direction * ASPECT - dy * active.fraction) /
      (ASPECT * ASPECT + active.fraction * active.fraction);
    changeScale(active.scale + dh / (active.height / active.scale), false);
  }
  function moveResize(e: PointerEvent<HTMLButtonElement>) {
    if (!resize.current || resize.current.pointer !== e.pointerId) return;
    resize.current.point = { x: e.clientX, y: e.clientY };
    if (!resize.current.frame)
      resize.current.frame = requestAnimationFrame(updateResize);
  }
  function endResize(e: PointerEvent<HTMLButtonElement>) {
    const active = resize.current;
    if (!active || active.pointer !== e.pointerId) return;
    active.point = { x: e.clientX, y: e.clientY };
    cancelAnimationFrame(active.frame);
    updateResize();
    resize.current = null;
    if (e.currentTarget.hasPointerCapture(e.pointerId))
      e.currentTarget.releasePointerCapture(e.pointerId);
    setResizing(false);
    skipResizeClick.current = active.moved;
    flushScale();
  }

  function cancelDrag() {
    const active = drag.current;
    if (!active) return;
    cancelAnimationFrame(active.frame);
    drag.current = null;
    if (hit.current?.hasPointerCapture(active.pointer))
      hit.current.releasePointerCapture(active.pointer);
    setDragging(false);
    setPreviewMode(null);
    paint(geometry(pref.current, viewport(), surface, ASPECT));
    skipClick.current = active.moved;
  }
  function start(e: PointerEvent<HTMLButtonElement>) {
    if (e.button !== 0 || obscured || atHome) return;
    const g = geometry(pref.current, view, surface, ASPECT);
    drag.current = {
      pointer: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      offsetX: e.clientX - g.x,
      offsetY: e.clientY - g.y,
      moved: false,
      original: pref.current,
      next: pref.current,
      visual: g,
      point: { x: e.clientX, y: e.clientY },
      frame: 0,
    };
    e.currentTarget.setPointerCapture(e.pointerId);
    skipClick.current = false;
  }
  function updateDrag() {
    const active = drag.current;
    if (!active) return;
    active.frame = 0;
    const { x, y } = active.point;
    if (!active.moved && Math.hypot(x - active.startX, y - active.startY) < 6)
      return;
    if (!active.moved) {
      clearTimeout(responseTimer.current);
      setResponding(false);
      setGesture("none");
    }
    active.moved = true;
    const intent = edgeIntent(x, y, view, surface);
    active.next = movedPreference(
      active.original,
      x - active.offsetX,
      y - active.offsetY,
      intent,
      view,
      surface,
      ASPECT,
    );
    // Keep a faint head mounted until release, so pointer capture survives a hide preview.
    active.visual = geometry(
      { ...active.next, mode: intent.mode === "hidden" ? "head" : intent.mode },
      view,
      surface,
      ASPECT,
    );
    paint(active.visual);
    setDragging(true);
    setMenu(false);
    setGreeting(false);
    setPreviewMode((old) => (old === intent.mode ? old : intent.mode));
  }
  function move(e: PointerEvent<HTMLButtonElement>) {
    if (!drag.current || drag.current.pointer !== e.pointerId) return;
    drag.current.point = { x: e.clientX, y: e.clientY };
    if (!drag.current.frame)
      drag.current.frame = requestAnimationFrame(updateDrag);
  }
  function end(e: PointerEvent<HTMLButtonElement>) {
    const active = drag.current;
    if (!active || active.pointer !== e.pointerId) return;
    active.point = { x: e.clientX, y: e.clientY };
    cancelAnimationFrame(active.frame);
    updateDrag();
    if (e.currentTarget.hasPointerCapture(e.pointerId))
      e.currentTarget.releasePointerCapture(e.pointerId);
    drag.current = null;
    setDragging(false);
    setPreviewMode(null);
    skipClick.current = active.moved;
    if (active.moved) persist(active.next);
  }
  function greet(kind: Gesture = "wave") {
    clearTimeout(responseTimer.current);
    setResponding(true);
    setGesture(use3D ? "nod" : kind);
    setAction3D("Wave");
    setPulse((value) => value + 1);
    setGreeting(true);
    responseTimer.current = window.setTimeout(() => {
      setResponding(false);
      setGesture("none");
      setAction3D("Idle");
      setGreeting(false);
    }, 3400);
  }
  function chooseMode(mode: CompanionMode) {
    clearTimeout(clickTimer.current);
    skipClick.current = false;
    persist({
      ...pref.current,
      mode,
      dock:
        mode === "full"
          ? "free"
          : pref.current.dock === "free"
            ? "bottom"
            : pref.current.dock,
    });
    setMenu(false);
    setGreeting(false);
  }
  function openAssistant() {
    clearTimeout(clickTimer.current);
    setMenu(false);
    setGreeting(false);
    onOpenAssistant();
  }
  function keyboard(e: KeyboardEvent<HTMLButtonElement>) {
    if (e.key === "Escape") {
      e.preventDefault();
      cancelDrag();
      cancelResize();
      setMenu(false);
      return;
    }
    if (e.key === "Enter" && e.shiftKey) {
      e.preventDefault();
      openAssistant();
      return;
    }
    const delta = e.shiftKey ? 36 : 14;
    const offsets: Record<string, [number, number]> = {
      ArrowLeft: [-delta, 0],
      ArrowRight: [delta, 0],
      ArrowUp: [0, -delta],
      ArrowDown: [0, delta],
    };
    if (offsets[e.key]) {
      e.preventDefault();
      if (atHome) return;
      const [dx, dy] = offsets[e.key];
      const g = geometry(pref.current, view, surface, ASPECT);
      persist(
        movedPreference(
          pref.current,
          g.x + dx,
          g.y + dy,
          { mode: pref.current.mode, dock: "free" },
          view,
          surface,
          ASPECT,
        ),
      );
    }
  }
  const modeLabel = (mode: CompanionMode) =>
    ({
      full: t("Full body", "全身"),
      half: t("Half body", "半身"),
      head: t("Head only", "露头"),
      hidden: t("Hidden", "隐藏"),
    })[mode];

  return (
    <div
      ref={root}
      className={`a1-companion ${dragging ? "is-dragging" : ""} ${resizing ? "is-resizing" : ""} ${moving ? "has-motion" : ""} ${responding ? "is-responding" : ""} ${previewMode === "hidden" ? "will-hide" : ""}`}
      data-testid="page-companion"
      data-mode={currentMode}
      data-saved-mode={preference.mode}
      data-dock={preference.dock}
      data-surface={surface}
      data-placement={atHome ? "sidebar" : "floating"}
      data-layout={preferHome ? "sidebar" : "floating"}
      data-motion={moving ? "active" : "paused"}
      data-expression={use3D && !assetError ? "blink-enabled" : "open-eyes"}
      data-renderer={use3D && !assetError ? "skinned-3d" : "whole-image-2d"}
      data-action={gesture}
      data-scale={effectiveScale.toFixed(2)}
      hidden={obscured}
    >
      {preference.mode === "hidden" && !dragging ? (
        <button
          type="button"
          className="a1-restore"
          aria-label={t("Show companion", "唤回伙伴")}
          onClick={() => {
            chooseMode("full");
            greet();
          }}
          title={t("Bring companion back", "唤回伙伴")}
          onContextMenu={(e) => {
            e.preventDefault();
            setMenu(true);
          }}
        >
          {preference.dock === "right" ? (
            <ChevronLeft size={16} />
          ) : preference.dock === "left" ? (
            <ChevronRight size={16} />
          ) : (
            <Sparkles size={16} />
          )}
          <span>{t("Companion", "伙伴")}</span>
        </button>
      ) : (
        <>
          <div className="a1-crop">
            <div ref={art} className="a1-art" aria-hidden="true">
              {use3D && !assetError ? (
                <A1Canvas
                  active={
                    moving && !dragging && !resizing && currentMode !== "hidden"
                  }
                  action={currentMode === "head" ? "Idle" : action3D}
                  nonce={pulse}
                  state={data?.voice.state ?? "idle"}
                  onError={() => setAssetError(true)}
                />
              ) : assetError && !use3D ? (
                <div className="a1-art-fallback">
                  <Sparkles />
                  <span>{t("Companion", "伙伴")}</span>
                </div>
              ) : (
                <div className="a1-image-motion">
                  <div
                    key={pulse}
                    className={`a1-whole-response action-${gesture}`}
                  >
                    <FlatCharacter onError={() => setAssetError(true)} />
                  </div>
                </div>
              )}
            </div>
            <button
              ref={hit}
              type="button"
              className="a1-hit"
              aria-label={
                atHome
                  ? t(
                      "Companion. Double-click to open assistant.",
                      "桌面伙伴。双击打开助理。",
                    )
                  : t(
                      "Page companion. Drag to move; double-click to open assistant.",
                      "桌面伙伴。拖动换位置，双击打开助理。",
                    )
              }
              aria-describedby="a1-interaction-help"
              onPointerDown={start}
              onPointerMove={move}
              onPointerUp={end}
              onPointerCancel={cancelDrag}
              onLostPointerCapture={() => {
                if (drag.current) cancelDrag();
              }}
              onClick={(e) => {
                if (skipClick.current) {
                  skipClick.current = false;
                  return;
                }
                if (e.detail > 1) return;
                clearTimeout(clickTimer.current);
                const g = resting;
                const fraction =
                  e.detail === 0 ? 0.4 : (e.clientY - g.y) / g.height;
                const kind: Gesture =
                  fraction < 0.22 ? "nod" : fraction > 0.73 ? "step" : "wave";
                clickTimer.current = window.setTimeout(() => greet(kind), 240);
              }}
              onDoubleClick={openAssistant}
              onKeyDown={keyboard}
              onContextMenu={(e) => {
                e.preventDefault();
                setMenu(true);
              }}
            />
          </div>
          <button
            ref={resizeHandle}
            type="button"
            className="a1-resize"
            hidden={atHome}
            aria-label={t("Resize companion", "缩放伙伴")}
            title={t(
              "Drag to resize · scroll on the companion",
              "拖动缩放 · 在人物上滚轮缩放",
            )}
            onPointerDown={startResize}
            onPointerMove={moveResize}
            onPointerUp={endResize}
            onPointerCancel={cancelResize}
            onLostPointerCapture={() => {
              if (resize.current) cancelResize();
            }}
            onClick={() => {
              if (skipResizeClick.current) {
                skipResizeClick.current = false;
                return;
              }
              setMenu(true);
            }}
            onKeyDown={(e) => {
              if (
                ["ArrowUp", "ArrowRight", "ArrowDown", "ArrowLeft"].includes(
                  e.key,
                )
              ) {
                e.preventDefault();
                changeScale(
                  effectiveScale +
                    (["ArrowUp", "ArrowRight"].includes(e.key) ? 0.03 : -0.03),
                );
              } else if (e.key === "Escape") {
                e.preventDefault();
                cancelResize();
              }
            }}
          >
            <Maximize2 size={12} />
          </button>
          <button
            type="button"
            className="a1-options"
            aria-label={t("Companion controls", "伙伴控制")}
            aria-expanded={menu}
            onClick={() => setMenu((old) => !old)}
          >
            <Ellipsis size={17} />
          </button>
          {(dragging || greeting) && (
            <div className="a1-bubble" role="status">
              {dragging ? (
                <>
                  <Move size={13} />
                  {t("Release: ", "松手：")}
                  {modeLabel(previewMode ?? "full")}
                </>
              ) : (
                t("I'm here. Need a hand?", "我在。需要帮忙吗？")
              )}
            </div>
          )}
          {!atHome && !dragging && !greeting && !menu && (
            <div className="a1-hint">
              {t(
                "Drag to an edge · scroll to resize",
                "拖到边缘收起 · 滚轮缩放",
              )}
            </div>
          )}
        </>
      )}
      <span className="a1-sr-only" id="a1-interaction-help">
        {atHome
          ? t(
              "Click for a response; double-click or Shift+Enter opens the assistant. Use Companion controls to float and move the character.",
              "点击人物会回应；双击或Shift+Enter打开助理。可在伙伴控制中改为自由悬浮。",
            )
          : t(
              "Arrow keys move the companion. Scroll or drag the corner to resize continuously. Click head, body or feet for a response. Right-click for controls. Shift+Enter opens the assistant.",
              "方向键移动；滚轮或拖动角点连续缩放；点击头、身体或脚会回应；右键打开控制，Shift+Enter打开助理。",
            )}
      </span>
      {menu && (
        <div
          ref={controls}
          className="a1-controls"
          role="group"
          aria-label={t("Page companion controls", "桌面伙伴控制")}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              e.preventDefault();
              e.stopPropagation();
              setMenu(false);
              hit.current?.focus();
            }
          }}
        >
          <header>
            <span>
              <i />
              <small>{t("Your companion", "桌面伙伴")}</small>
            </span>
            <button
              type="button"
              aria-label={t("Close Companion controls", "关闭伙伴控制")}
              onClick={() => {
                setMenu(false);
                hit.current?.focus();
              }}
            >
              <X size={15} />
            </button>
          </header>
          <p>{t("Make a little room.", "留一点空间，也随时在。")}</p>
          {homeId && anchor && (
            <button
              type="button"
              className="a1-menu-action"
              onClick={() => {
                const next = !preferHome;
                setPreferHome(next);
                try {
                  localStorage.setItem(
                    layoutKey,
                    next ? "sidebar" : "floating",
                  );
                } catch {}
                setMenu(false);
              }}
            >
              <Move size={14} />
              {preferHome
                ? t("Float over workspace", "改为自由悬浮")
                : t("Return to sidebar", "回到侧栏")}
            </button>
          )}
          <button
            className="a1-menu-action"
            type="button"
            onClick={() => {
              const next = !use3D;
              setUse3D(next);
              setAssetError(false);
              try {
                localStorage.setItem(`desk.a1.3d.v2.${surface}`, String(next));
              } catch {}
            }}
          >
            {use3D
              ? t("Use intact 2D", "使用完整 2D")
              : t("Try the 3D model", "试用 3D 模型")}
          </button>
          {use3D && (
            <>
              <button
                className="a1-menu-action"
                type="button"
                disabled={!moving}
                onClick={() => greet("nod")}
              >
                {t("Brief response", "简短回应")}
              </button>
              <a
                className="a1-menu-action"
                href="?surface=avatar"
                target="_blank"
                rel="noreferrer"
              >
                {t("Explore all angles", "查看各个角度")}
              </a>
            </>
          )}
          <a
            className="a1-menu-action"
            href="?surface=models"
            target="_blank"
            rel="noreferrer"
          >
            {t("Character & credits", "角色与作者署名")}
          </a>
          {assetError && (
            <p role="status">
              {t(
                "3D could not load. Showing the intact illustration.",
                "3D 未能加载，已显示完整原画。",
              )}
            </p>
          )}

          <div className="a1-mode-options">
            {MODES.map((mode) => (
              <button
                key={mode}
                type="button"
                aria-pressed={preference.mode === mode}
                onClick={() => chooseMode(mode)}
              >
                {modeLabel(mode)}
              </button>
            ))}
          </div>
          {!atHome && (
            <div className="a1-scale-control">
              <label>
                {t("Scale", "大小")}
                <output>{Math.round(effectiveScale * 100)}%</output>
                <input
                  type="range"
                  min="50"
                  max={Math.floor(limit * 100)}
                  step="1"
                  value={Math.round(effectiveScale * 100)}
                  aria-label={t("Character scale", "角色缩放")}
                  onChange={(e) => changeScale(Number(e.target.value) / 100)}
                  onPointerUp={flushScale}
                  onKeyUp={flushScale}
                  onBlur={flushScale}
                />
              </label>
            </div>
          )}
          <button
            type="button"
            className="a1-menu-action"
            onClick={() =>
              persist({ ...pref.current, motion: !pref.current.motion })
            }
          >
            {preference.motion ? <Pause size={14} /> : <Play size={14} />}{" "}
            {preference.motion
              ? t("Pause movement", "暂停动态")
              : t("Resume movement", "恢复动态")}
          </button>
          <button
            type="button"
            className="a1-menu-action"
            onClick={() => {
              if (homeId) {
                setPreferHome(true);
                try {
                  localStorage.setItem(layoutKey, "sidebar");
                } catch {}
              }
              persist({
                ...pref.current,
                mode: "full",
                dock: "free",
                x: 1,
                y: 1,
              });
              setMenu(false);
            }}
          >
            <RotateCcw size={14} />
            {t("Reset position", "重置位置")}
          </button>
          <button
            type="button"
            className="a1-assistant-action"
            onClick={openAssistant}
          >
            <Sparkles size={14} />
            {t("Open assistant", "打开助理")}
          </button>
        </div>
      )}
    </div>
  );
}
