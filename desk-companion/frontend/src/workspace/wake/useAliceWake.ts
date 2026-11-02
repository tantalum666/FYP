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
}: {
  available: boolean;
  paused: boolean;
  engaged: boolean;
  onWake: () => Promise<void>;
}) {
  const [enabled, setEnabled] = useState(false);
  const [state, setState] = useState<
    "off" | "starting" | "waiting" | "active" | "error"
  >("off");
  const current = useRef<WakeAudio | null>(null);
  const callback = useRef(onWake);
  callback.current = onWake;
  const pause = useCallback(() => {
    current.current?.stop();
    current.current = null;
  }, []);
  const disable = useCallback(() => {
    pause();
    setEnabled(false);
    setState("off");
  }, [pause]);
  const failed = useCallback(() => {
    pause();
    setEnabled(false);
    setState("error");
  }, [pause]);
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
  }, [enabled, available, paused, engaged, pause, failed]);
  return {
    enabled,
    state,
    pause,
    disable,
    failed,
    enable: () => {
      setState("starting");
      setEnabled(true);
    },
  };
}
