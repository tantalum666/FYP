import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../../api";
import type { ResponseFence } from "../personal/responseFence";
import type { AgentRun, RunDetailResponse, RunScope } from "./types";
export function useAgentRuns(
  fence: ResponseFence,
  selected: string | null,
  epoch: number,
) {
  const current = useRef(selected);
  current.current = selected;
  const sequence = useRef(0),
    active = useRef<{
      epoch: number;
      selected: string | null;
      sequence: number;
    } | null>(null);
  const [value, setValue] = useState<{
    epoch: number;
    selected: string | null;
    runs: AgentRun[];
    scope: RunScope;
    detail: RunDetailResponse | null;
  } | null>(null);
  const [error, setError] = useState<unknown>(null),
    [loading, setLoading] = useState(false);
  const reload = useCallback(
    async (force = false) => {
      const captured = fence.capture(),
        id = current.current;
      if (!fence.accepts(captured)) return;
      if (
        !force &&
        active.current?.epoch === captured &&
        active.current.selected === id
      )
        return;
      const seq = ++sequence.current;
      active.current = { epoch: captured, selected: id, sequence: seq };
      setLoading(true);
      try {
        const [list, scope, detail] = await Promise.all([
          request<{ runs: AgentRun[] }>("/agent-runs"),
          request<RunScope>("/agent-runs/scope"),
          id
            ? request<RunDetailResponse>(
                `/agent-runs/${encodeURIComponent(id)}`,
              )
            : Promise.resolve(null),
        ]);
        if (
          !fence.accepts(captured) ||
          current.current !== id ||
          sequence.current !== seq
        )
          return;
        setValue({
          epoch: captured,
          selected: id,
          runs: list.runs.filter((run) => !run.private_hidden),
          scope,
          detail,
        });
        setError(null);
      } catch (e) {
        if (
          !fence.accepts(captured) ||
          current.current !== id ||
          sequence.current !== seq
        )
          return;
        setValue(null);
        setError(e);
      } finally {
        if (active.current?.sequence === seq) active.current = null;
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
  }, [epoch, selected, reload]);
  const visibleValue =
    value &&
    value.epoch === epoch &&
    fence.accepts(value.epoch) &&
    value.selected === selected
      ? value
      : null;
  return { value: visibleValue, error, loading, reload };
}
