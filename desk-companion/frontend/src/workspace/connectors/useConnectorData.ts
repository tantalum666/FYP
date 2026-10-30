import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../../api";
import type { ResponseFence } from "../personal/responseFence";
import {
  loadConnectorMetadata,
  loadConnectorPrivate,
  loadConnectorSelectedMetadata,
} from "./types";
import type {
  ConnectorCapabilities,
  ConnectorIntent,
  ConnectorMetadata,
} from "./types";

export function useConnectorData(
  fence: ResponseFence,
  epoch: number,
  privateVisible: boolean,
  selected: string | null,
) {
  const sequence = useRef(0),
    active = useRef<number | null>(null);
  const alive = useRef(true);
  const [snapshot, setSnapshot] = useState<{
    epoch: number;
    selected: string | null;
    at: number;
    rows: ConnectorMetadata[];
    selectedMetadata: ConnectorMetadata | null;
    capabilities: ConnectorCapabilities | null;
    detail: ConnectorIntent | null;
  } | null>(null);
  const [error, setError] = useState<unknown>(null),
    [loading, setLoading] = useState(false);
  const [now, setNow] = useState(Date.now());
  const reload = useCallback(
    async (force = false) => {
      const captured = fence.capture();
      if (
        !alive.current ||
        !fence.accepts(captured) ||
        (!force && active.current !== null)
      )
        return;
      const serial = ++sequence.current;
      active.current = serial;
      setLoading(true);
      try {
        const [rows, details, selectedMetadata] = await Promise.all([
          loadConnectorMetadata(request),
          loadConnectorPrivate(request, selected, privateVisible),
          privateVisible
            ? Promise.resolve(null)
            : loadConnectorSelectedMetadata(request, selected),
        ]);
        if (
          !alive.current ||
          !fence.accepts(captured) ||
          serial !== sequence.current
        )
          return;
        setSnapshot({
          epoch: captured,
          selected,
          at: Date.now(),
          rows,
          selectedMetadata,
          ...details,
        });
        setError(null);
      } catch (e) {
        if (
          !alive.current ||
          !fence.accepts(captured) ||
          serial !== sequence.current
        )
          return;
        // The workspace owns mutation queues; a failed refresh must not recreate them.
        setSnapshot(null);
        setError(e);
      } finally {
        if (active.current === serial) active.current = null;
        if (
          alive.current &&
          fence.accepts(captured) &&
          serial === sequence.current
        )
          setLoading(false);
      }
    },
    [fence, epoch, privateVisible, selected],
  );
  useEffect(() => {
    alive.current = true;
    setSnapshot(null);
    setError(null);
    void reload(true);
    const tick = () => {
      setNow(Date.now());
      if (!document.hidden) void reload();
    };
    const timer = window.setInterval(tick, 2000);
    window.addEventListener("desk:connector-intents", tick);
    document.addEventListener("visibilitychange", tick);
    return () => {
      alive.current = false;
      ++sequence.current;
      active.current = null;
      window.clearInterval(timer);
      window.removeEventListener("desk:connector-intents", tick);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [reload]);
  const current =
    snapshot &&
    snapshot.epoch === epoch &&
    snapshot.selected === selected &&
    fence.accepts(snapshot.epoch)
      ? snapshot
      : null;
  const fresh = !!current && !error && now - current.at < 6000;
  return {
    snapshot: fresh ? current : null,
    fresh,
    error,
    loading,
    reload,
    now,
  };
}
