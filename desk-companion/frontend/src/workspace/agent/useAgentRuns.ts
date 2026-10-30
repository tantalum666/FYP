import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../../api";
import type { ResponseFence } from "../personal/responseFence";
import type { AgentRun, RunDetailResponse, RunScope } from "./types";

/** Only transient transport/server failures may retain an already visible draft. */
export function recoverableRunReadError(error: unknown) {
  if (!error || typeof error !== "object") return false;
  const { code, status } = error as { code?: unknown; status?: unknown };
  if (
    typeof code === "string" &&
    /AUTH|SESSION|OWNER|PRIVATE|PRIVACY|CONTEXT_HIDDEN/.test(code)
  )
    return false;
  return (
    (code === "CONNECTION_LOST" && status === 0) ||
    [408, 429, 500, 502, 503, 504].includes(Number(status))
  );
}
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
      let terminalError: unknown = null;
      const currentResponse = () =>
        fence.accepts(captured) &&
        current.current === id &&
        sequence.current === seq;
      const read = <T>(path: string) =>
        request<T>(path).catch((error) => {
          // A parallel transient failure must not hide a later access denial.
          if (!recoverableRunReadError(error) && currentResponse()) {
            terminalError = error;
            setValue(null);
            setError(error);
          }
          throw error;
        });
      try {
        const [list, scope, detail] = await Promise.all([
          read<{ runs: AgentRun[] }>("/agent-runs"),
          read<RunScope>("/agent-runs/scope"),
          id
            ? read<RunDetailResponse>(`/agent-runs/${encodeURIComponent(id)}`)
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
        // Keep same-view editors and unknown-receipt queues mounted during a
        // transient poll failure. No action may use this snapshot until refreshed.
        // Access/privacy failures and malformed responses still clear immediately.
        if (!recoverableRunReadError(e) || terminalError) setValue(null);
        setError(terminalError ?? e);
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
  return {
    value: visibleValue,
    fresh: !!visibleValue && !error,
    error,
    loading,
    reload,
  };
}
