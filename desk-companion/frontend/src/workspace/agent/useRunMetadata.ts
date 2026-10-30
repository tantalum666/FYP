import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../../api";
import type { ResponseFence } from "../personal/responseFence";
import { loadRunMetadata } from "./runMetadata";
import type { RunMetadata } from "./runMetadata";

export function useRunMetadata(fence: ResponseFence, epoch: number) {
  const sequence = useRef(0),
    active = useRef<number | null>(null);
  const [value, setValue] = useState<{
    epoch: number;
    runs: RunMetadata[];
  } | null>(null);
  const [error, setError] = useState<unknown>(null),
    [loading, setLoading] = useState(false);
  const reload = useCallback(
    async (force = false) => {
      const captured = fence.capture();
      if (!fence.accepts(captured) || (!force && active.current !== null))
        return;
      const seq = ++sequence.current;
      active.current = seq;
      setLoading(true);
      try {
        const runs = await loadRunMetadata(request);
        if (!fence.accepts(captured) || sequence.current !== seq) return;
        setValue({ epoch: captured, runs });
        setError(null);
      } catch (e) {
        if (!fence.accepts(captured) || sequence.current !== seq) return;
        // Retain only content-free rows so uncertain control queues are not unmounted.
        // Their controls are disabled until a successful current refresh.
        setError(e);
      } finally {
        if (active.current === seq) active.current = null;
        if (sequence.current === seq) setLoading(false);
      }
    },
    [fence],
  );
  useEffect(() => {
    setValue(null);
    setError(null);
    void reload(true);
    const tick = () => {
      if (!document.hidden) void reload();
    };
    const timer = window.setInterval(tick, 4000);
    window.addEventListener("desk:agent-runs", tick);
    document.addEventListener("visibilitychange", tick);
    return () => {
      sequence.current++;
      active.current = null;
      clearInterval(timer);
      window.removeEventListener("desk:agent-runs", tick);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [epoch, reload]);
  const current = value?.epoch === epoch && fence.accepts(epoch) ? value : null;
  return {
    runs: current?.runs ?? null,
    fresh: !!current && !error,
    loading,
    error,
    reload,
  };
}
