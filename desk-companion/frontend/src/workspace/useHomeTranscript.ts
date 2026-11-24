import { useEffect, useRef, useState, type RefObject } from "react";
import { request } from "../api";
import type { ConversationTurn } from "./conversationTranscript";

type Snapshot = {
  enabled: boolean;
  generation: number;
  live_id: string | null;
  turns: ConversationTurn[];
};

/** Read local owner history on entry. No private transcript is stored by the browser. */
export function useHomeTranscript(
  enabled: boolean,
  generation: number | undefined,
  liveId: RefObject<string | undefined>,
) {
  const [saved, setSaved] = useState<ConversationTurn[]>([]);
  const [login, setLogin] = useState(0);
  const [failed, setFailed] = useState(false);
  const requestVersion = useRef(0);
  function clear() {
    requestVersion.current++;
    setSaved([]);
    setFailed(false);
  }
  useEffect(() => {
    const reset = () => {
      clear();
      setLogin((n) => n + 1);
    };
    window.addEventListener("desk:session", reset);
    return () => window.removeEventListener("desk:session", reset);
  }, []);
  useEffect(() => {
    clear();
    if (!enabled || generation === undefined) return;
    const token = requestVersion.current;
    void request<Snapshot>("/assistant/continuity")
      .then((snapshot) => {
        if (
          requestVersion.current !== token ||
          !snapshot.enabled ||
          snapshot.generation !== generation
        )
          return;
        setSaved(snapshot.turns);
        if (!liveId.current && snapshot.live_id)
          liveId.current = snapshot.live_id;
      })
      .catch(() => { if (requestVersion.current === token) setFailed(true); });
    return () => {
      requestVersion.current++;
    };
  }, [enabled, generation, login, liveId]);
  return { saved: enabled ? saved : [], clear, failed: enabled && failed, retry: () => setLogin(n => n + 1) };
}

export function withSavedTurns(
  saved: ConversationTurn[],
  current: ConversationTurn[],
) {
  const live = new Set(current.map((turn) => turn.id));
  return [...saved.filter((turn) => !live.has(turn.id)), ...current].slice(-40);
}
