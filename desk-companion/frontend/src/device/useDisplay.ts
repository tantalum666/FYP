import { useCallback, useEffect, useRef, useState } from "react";
import { DateTime } from "luxon";
import { pendingWrite } from "../api";
import { IDLE_MS, mayReturnToDisplay } from "./model";

export function useDisplayClock() {
  const [now, setNow] = useState(() => DateTime.now());
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const tick = () => {
      setNow(DateTime.now());
      clearTimeout(timer);
      timer = setTimeout(tick, 60_000 - (Date.now() % 60_000) + 30);
    };
    const visible = () => {
      if (!document.hidden) tick();
    };
    tick();
    document.addEventListener("visibilitychange", visible);
    return () => {
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", visible);
    };
  }, []);
  return now;
}

export function useIdleDisplay(blocked: boolean, onIdle: () => void) {
  const callback = useRef(onIdle);
  callback.current = onIdle;
  useEffect(() => {
    let lastActivity = Date.now();
    let timer: ReturnType<typeof setTimeout>;
    const check = () => {
      if (
        mayReturnToDisplay(blocked, !!pendingWrite(), Date.now() - lastActivity)
      )
        callback.current();
      timer = setTimeout(check, IDLE_MS);
    };
    const activity = () => {
      lastActivity = Date.now();
      clearTimeout(timer);
      timer = setTimeout(check, IDLE_MS);
    };
    if (!blocked) activity();
    document.addEventListener("pointerdown", activity, { passive: true });
    document.addEventListener("keydown", activity);
    document.addEventListener("wheel", activity, { passive: true });
    return () => {
      clearTimeout(timer);
      document.removeEventListener("pointerdown", activity);
      document.removeEventListener("keydown", activity);
      document.removeEventListener("wheel", activity);
    };
  }, [blocked]);
}

export function useScreenAwake() {
  const [enabled, setEnabled] = useState(false);
  const [state, setState] = useState<
    "off" | "active" | "released" | "unavailable"
  >("off");
  const sentinel = useRef<WakeLockSentinel | null>(null);
  const toggle = useCallback(() => setEnabled((v) => !v), []);
  useEffect(() => {
    let alive = true;
    let requesting = false;
    const acquire = async () => {
      if (!enabled || document.hidden || requesting || sentinel.current) return;
      if (!("wakeLock" in navigator)) {
        setState("unavailable");
        return;
      }
      requesting = true;
      try {
        const lock = await navigator.wakeLock.request("screen");
        if (!alive) {
          await lock.release();
          return;
        }
        sentinel.current = lock;
        setState("active");
        lock.addEventListener("release", () => {
          if (sentinel.current === lock) sentinel.current = null;
          if (alive) setState("released");
        });
      } catch {
        if (alive) setState("unavailable");
      } finally {
        requesting = false;
      }
    };
    const visible = () => {
      if (!document.hidden) void acquire();
    };
    if (enabled) void acquire();
    else setState("off");
    document.addEventListener("visibilitychange", visible);
    return () => {
      alive = false;
      document.removeEventListener("visibilitychange", visible);
      const lock = sentinel.current;
      sentinel.current = null;
      if (lock) void lock.release().catch(() => {});
    };
  }, [enabled]);
  return { enabled, state, toggle };
}
