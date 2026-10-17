import { useEffect, useRef, useState } from "react";
import type { A1Renderer, ActionName } from "./renderer";
export function A1Canvas({
  active = true,
  action = "Idle",
  nonce = 0,
  state = "idle",
  review = false,
  angle,
  onError,
}: {
  active?: boolean;
  action?: ActionName;
  nonce?: number;
  state?: string;
  review?: boolean;
  angle?: number;
  onError?: () => void;
}) {
  const host = useRef<HTMLDivElement>(null),
    engine = useRef<A1Renderer | null>(null);
  const current = useRef({ active, action, nonce, state, review });
  current.current = { active, action, nonce, state, review };
  const latestError = useRef(onError);
  latestError.current = onError;
  const [status, setStatus] = useState("loading");
  useEffect(() => {
    let alive = true;
    let instance: A1Renderer | null = null;
    void import("./renderer")
      .then(({ A1Renderer }) => {
        if (!alive || !host.current) return;
        try {
          instance = new A1Renderer(
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
  }, []);
  useEffect(() => {
    engine.current?.update({ active, action, nonce, state, review });
  }, [active, action, nonce, state, review]);
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
