import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../../api";
import { ResponseFence } from "../personal/responseFence";
import type { BrowserCapabilities, BrowserJob } from "./types";

export function useBrowserData(
  active: boolean,
  identity: string,
  available: boolean,
  privateVisible: boolean,
  selected: string | null,
  cursor: string | null,
) {
  const fence = useRef(new ResponseFence());
  fence.current.update(
    `${identity}:${privateVisible}:${selected ?? "list"}:${cursor ?? "first"}`,
    active && available,
  );
  const epoch = fence.current.version;
  const [snapshot, setSnapshot] = useState<{
    epoch: number;
    at: number;
    capabilities: BrowserCapabilities;
    jobs: BrowserJob[];
    detail: BrowserJob | null;
    nextCursor: string | null;
  } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [now, setNow] = useState(Date.now());
  const reading = useRef<number | null>(null);
  const sequence = useRef(0);
  const reload = useCallback(async () => {
    const token = fence.current.capture();
    if (!fence.current.accepts(token) || reading.current === token) return;
    reading.current = token;
    const serial = ++sequence.current;
    setLoading(true);
    try {
      const [capabilities, listing, detail] = await Promise.all([
        request<BrowserCapabilities>("/browser/capabilities"),
        request<{ jobs: BrowserJob[]; next_cursor: string | null }>(
          `/browser/jobs${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`,
        ),
        selected
          ? request<{ job: BrowserJob }>(
              `/browser/jobs/${encodeURIComponent(selected)}`,
            )
          : Promise.resolve(null),
      ]);
      if (!fence.current.accepts(token) || serial !== sequence.current) return;
      setSnapshot({
        epoch: token,
        at: Date.now(),
        capabilities,
        jobs: listing.jobs,
        detail: detail?.job ?? null,
        nextCursor: listing.next_cursor,
      });
      setError(null);
    } catch (e) {
      if (!fence.current.accepts(token) || serial !== sequence.current) return;
      setSnapshot(null);
      setError(e);
    } finally {
      if (reading.current === token) reading.current = null;
      if (fence.current.accepts(token) && serial === sequence.current)
        setLoading(false);
    }
  }, [selected, cursor, epoch]);
  useEffect(() => {
    setSnapshot(null);
    setError(null);
    if (active && available) void reload();
    const timer = window.setInterval(() => {
      setNow(Date.now());
      if (!document.hidden && active && available) void reload();
    }, 2000);
    const refresh = () => {
      if (!document.hidden && active && available) void reload();
    };
    window.addEventListener("desk:browser-jobs", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      ++sequence.current;
      window.clearInterval(timer);
      window.removeEventListener("desk:browser-jobs", refresh);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [active, available, reload]);
  const current =
    snapshot && fence.current.accepts(snapshot.epoch) ? snapshot : null;
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
