import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../../api";
import { apiOrigin } from "../../native";
import { handoverTicket } from "../voice-ticket";
import { WakeAudio } from "./WakeAudio";

export function useAliceWake({
  available,
  paused,
  engaged,
  onWake,
  ownerKey,
  occupied = false,
}: {
  available: boolean;
  paused: boolean;
  engaged: boolean;
  onWake: () => Promise<void>;
  ownerKey?: string;
  occupied?: boolean;
}) {
  const [enabled, setEnabled] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<
    "off" | "starting" | "waiting" | "active" | "error"
  >("off");
  const current = useRef<WakeAudio | null>(null);
  const restored = useRef<string | undefined>(undefined);
  const preference = ownerKey
    ? `desk.alice-wake.v1:${apiOrigin()}:${ownerKey}`
    : undefined;
  const savePreference = useCallback(
    (value: boolean) => {
      if (!preference) return;
      try {
        localStorage.setItem(preference, value ? "on" : "off");
      } catch {
        /* optional device preference */
      }
    },
    [preference],
  );
  const callback = useRef(onWake);
  callback.current = onWake;
  const pause = useCallback(() => {
    current.current?.stop();
    current.current = null;
  }, []);
  const rearm = useCallback(() => {
    pause();
    setAttempt((value) => value + 1);
  }, [pause]);
  const disable = useCallback(() => {
    pause();
    setEnabled(false);
    setState("off");
    savePreference(false);
  }, [pause, savePreference]);
  const failed = useCallback(() => {
    pause();
    setEnabled(false);
    setState("error");
    savePreference(false);
  }, [pause, savePreference]);
  useEffect(() => {
    if (
      !available ||
      occupied ||
      !preference ||
      restored.current === preference
    )
      return;
    let live = true;
    try {
      if (localStorage.getItem(preference) !== "on") {
        restored.current = preference;
        return;
      }
    } catch {
      return;
    }
    // Restore only a deliberate preference with an already granted browser mic
    // permission. Never prompt for capture merely because a page was opened.
    void navigator.permissions
      ?.query({ name: "microphone" as PermissionName })
      .then((status) => {
        if (live) {
          restored.current = preference;
          if (status.state === "granted") setEnabled(true);
        }
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [available, occupied, preference]);
  useEffect(() => {
    if (!enabled || !available || paused || engaged) {
      pause();
      if (enabled) setState(engaged ? "active" : "off");
      return;
    }
    let live = true;
    const engine = new WakeAudio((event) => {
      if (!live || current.current !== engine) return;
      if (event.type === "ready") setState("waiting");
      else if (event.type === "wake") {
        current.current = null;
        setState("active");
        void callback.current().catch(failed);
      } else failed();
    });
    current.current = engine;
    setState("starting");
    const url = new URL("/api/wake/ws", apiOrigin());
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    void engine.start(
      () =>
        handoverTicket(
          async () =>
            (
              await request<{ ticket: string }>("/wake/tickets", {
                method: "POST",
                body: "{}",
              })
            ).ticket,
          () => live && current.current === engine,
        ),
      url.href,
    );
    return () => {
      live = false;
      engine.stop();
      if (current.current === engine) current.current = null;
    };
  }, [enabled, available, paused, engaged, pause, failed, attempt]);
  return {
    enabled,
    state,
    pause,
    rearm,
    disable,
    failed,
    enable: () => {
      savePreference(true);
      setState("starting");
      setEnabled(true);
    },
  };
}
