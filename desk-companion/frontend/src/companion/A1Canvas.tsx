import { useEffect, useRef, useState } from "react";
import type { ActionName } from "./renderer";
import type { NativeA1Renderer } from "./vrm-viewer";
import { APPEARANCE_KEY, APPEARANCE_EVENT } from "./appearance";
export function A1Canvas({
  active = true,
  action = "Idle",
  nonce = 0,
  state = "idle",
  review = false,
  framing = "full",
  angle,
  onError,
}: {
  active?: boolean;
  action?: ActionName;
  nonce?: number;
  state?: string;
  review?: boolean;
  framing?: "full" | "face";
  angle?: number;
  onError?: () => void;
}) {
  const host = useRef<HTMLDivElement>(null),
    engine = useRef<NativeA1Renderer | null>(null);
  const current = useRef({ active, action, nonce, state, review, framing });
  current.current = { active, action, nonce, state, review, framing };
  const latestError = useRef(onError);
  latestError.current = onError;
  const [status, setStatus] = useState("loading");
  const [appearanceVersion, setAppearanceVersion] = useState(0);
  useEffect(() => {
    const reload = () => setAppearanceVersion((value) => value + 1);
    const storage = (event: StorageEvent) => {
      if (event.key === APPEARANCE_KEY) reload();
    };
    window.addEventListener(APPEARANCE_EVENT, reload);
    window.addEventListener("storage", storage);
    return () => {
      window.removeEventListener(APPEARANCE_EVENT, reload);
      window.removeEventListener("storage", storage);
    };
  }, []);
  useEffect(() => {
    let alive = true;
    let instance: NativeA1Renderer | null = null;
    setStatus("loading");
    void import("./vrm-viewer")
      .then(({ NativeA1Renderer: Renderer }) => {
        if (!alive || !host.current) return;
        try {
          instance = new Renderer(
            host.current,
            () => {
              if (alive) setStatus("ready");
            },
            () => {
              if (alive) {
                setStatus("error");
                latestError.current?.();
              }
            },
          );
          engine.current = instance;
          instance.update(current.current);
        } catch {
          setStatus("error");
          latestError.current?.();
        }
      })
      .catch(() => {
        if (alive) {
          setStatus("error");
          latestError.current?.();
        }
      });
    return () => {
      alive = false;
      engine.current = null;
      instance?.dispose();
    };
  }, [appearanceVersion]);
  useEffect(() => {
    engine.current?.update({ active, action, nonce, state, review, framing });
  }, [active, action, nonce, state, review, framing]);
  useEffect(() => {
    if (angle !== undefined) engine.current?.view(angle);
  }, [angle, status]);
  return (
    <div
      className="a1-canvas"
      ref={host}
      data-status={status}
      aria-hidden="true"
      style={{ width: "100%", height: "100%" }}
    />
  );
}
