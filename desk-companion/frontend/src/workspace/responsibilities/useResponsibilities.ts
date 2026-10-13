import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../../api";
import type { ResponseFence } from "../personal/responseFence";
import { recoverableRunReadError } from "../agent/useAgentRuns";
import { metadataOnly } from "./types";
import type { WatchList, WatchScope, WatchDetail } from "./types";
export function useResponsibilities(
  fence: ResponseFence,
  epoch: number,
  hidden: boolean,
  selected: string | null,
  selectionPath: string | null,
) {
  const key = JSON.stringify([hidden, selected, selectionPath]);
  const current = useRef(key);
  current.current = key;
  const sequence = useRef(0),
    active = useRef<number | null>(null);
  const [value, setValue] = useState<{
    epoch: number;
    key: string;
    list: WatchList;
    catalog: WatchScope | null;
    scope: WatchScope | null;
    detail: WatchDetail | null;
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
      const accepts = () =>
        fence.accepts(captured) &&
        current.current === key &&
        seq === sequence.current;
      let terminal: unknown = null;
      const read = <T>(path: string) =>
        request<T>(path).catch((reason) => {
          if (!recoverableRunReadError(reason) && accepts()) {
            terminal = reason;
            setValue(null);
            setError(reason);
          }
          throw reason;
        });
      try {
        const [list, catalog, scope, detail] = await Promise.all([
          read<WatchList>("/responsibilities"),
          hidden
            ? Promise.resolve(null)
            : read<WatchScope>("/responsibilities/scope"),
          !hidden && selectionPath
            ? read<WatchScope>(selectionPath)
            : Promise.resolve(null),
          !hidden && selected
            ? read<WatchDetail>(
                `/responsibilities/${encodeURIComponent(selected)}`,
              )
            : Promise.resolve(null),
        ]);
        if (!accepts()) return;
        if (
          !Array.isArray(list.responsibilities) ||
          (!hidden && (list.hidden || !Array.isArray(catalog?.tasks))) ||
          (selected &&
            !hidden &&
            (detail?.responsibility.id !== selected ||
              !Array.isArray(detail.reviews)))
        )
          throw { code: "RESPONSIBILITY_RESPONSE_INVALID" };
        setValue({
          epoch: captured,
          key,
          list: hidden
            ? {
                ...list,
                hidden: true,
                responsibilities: list.responsibilities.map(metadataOnly),
              }
            : list,
          catalog,
          scope,
          detail,
        });
        setError(null);
      } catch (reason) {
        if (!accepts()) return;
        if (terminal || !recoverableRunReadError(reason)) setValue(null);
        setError(terminal ?? reason);
      } finally {
        if (active.current === seq) active.current = null;
        if (seq === sequence.current) setLoading(false);
      }
    },
    [fence, key, hidden, selected, selectionPath],
  );
  useEffect(() => {
    setValue(null);
    setError(null);
    void reload(true);
    const tick = () => {
      if (!document.hidden) void reload();
    };
    const timer = window.setInterval(tick, 4000);
    document.addEventListener("visibilitychange", tick);
    return () => {
      sequence.current++;
      active.current = null;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [epoch, reload]);
  const visible =
    value && value.key === key && value.epoch === epoch && fence.accepts(epoch)
      ? value
      : null;
  return { value: visible, fresh: !!visible && !error, error, loading, reload };
}
