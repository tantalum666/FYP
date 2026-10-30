import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../../api";
import type {
  ContextSettings,
  Conversation,
  ConversationDetail,
  PersonalMemory,
} from "./types";

export function usePersonalContext(visible: boolean, selected: string | null) {
  const [settings, setSettings] = useState<ContextSettings | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [memories, setMemories] = useState<PersonalMemory[]>([]);
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const generation = useRef(0);
  const current = useRef({ visible, selected });
  current.current = { visible, selected };
  const reading = useRef<number | null>(null);
  const reload = useCallback(
    async (force = false) => {
      if (force) generation.current += 1;
      const token = generation.current;
      if (
        !visible ||
        !current.current.visible ||
        current.current.selected !== selected ||
        reading.current === token
      )
        return;
      reading.current = token;
      setLoading(true);
      try {
        const [nextSettings, threads, facts, conversation] = await Promise.all([
          request<ContextSettings>("/assistant/context-settings"),
          request<{ conversations: Conversation[] }>(
            "/assistant/conversations",
          ),
          request<{ memories: PersonalMemory[] }>("/assistant/memories"),
          selected
            ? request<ConversationDetail>(
                `/assistant/conversations/${encodeURIComponent(selected)}`,
              )
            : Promise.resolve(null),
        ]);
        if (
          generation.current !== token ||
          !current.current.visible ||
          current.current.selected !== selected
        )
          return;
        setSettings(nextSettings);
        setConversations(threads.conversations);
        setMemories(facts.memories);
        setDetail(conversation);
        setError(null);
      } catch (e) {
        if (
          generation.current !== token ||
          !current.current.visible ||
          current.current.selected !== selected
        )
          return;
        // A failed read must never leave yesterday's private text visible.
        setSettings(null);
        setConversations([]);
        setMemories([]);
        setDetail(null);
        setError(e);
      } finally {
        if (reading.current === token) reading.current = null;
        if (generation.current === token) setLoading(false);
      }
    },
    [visible, selected],
  );
  useEffect(() => {
    generation.current += 1;
    setSettings(null);
    setConversations([]);
    setMemories([]);
    setDetail(null);
    setError(null);
    if (visible) void reload();
    const timer = setInterval(() => {
      if (!document.hidden) void reload();
    }, 4000);
    const resume = () => {
      if (!document.hidden) void reload();
    };
    window.addEventListener("desk:personal-context", resume);
    document.addEventListener("visibilitychange", resume);
    return () => {
      generation.current += 1;
      clearInterval(timer);
      window.removeEventListener("desk:personal-context", resume);
      document.removeEventListener("visibilitychange", resume);
    };
  }, [reload, visible]);
  return { settings, conversations, memories, detail, error, loading, reload };
}
export type PersonalContext = ReturnType<typeof usePersonalContext>;
