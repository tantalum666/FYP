import { useEffect, useRef, useState } from "react";
import { request } from "../../api";
import { ResponseFence } from "../personal/responseFence";
import {
  RetentionWriteQueue,
  retentionBody,
  retentionDenial,
  validMaintenanceList,
  validMaintenanceDetail,
  validRetentionPreview,
} from "./retention";
import type {
  MaintenanceList,
  RetentionAction,
  RetentionPreview,
  WatchMutationResult,
} from "./retention";
import type { Responsibility, WatchDetail } from "./types";

/** Mounted only in visible-owner maintenance. All effects are reads; writes require explicit callbacks. */
export function useWatchRetention(
  parent: ResponseFence,
  epoch: number,
  fresh: boolean,
  snapshot: number | undefined,
  onChanged: (result: WatchMutationResult) => void,
  onDenied: (error: unknown) => void,
) {
  const local = useRef(new ResponseFence()).current;
  local.update(`${epoch}:${fresh}:${snapshot}`, fresh && parent.accepts(epoch));
  const token = local.version;
  const alive = useRef(true);
  const serial = useRef(0);
  const dataToken = useRef(token);
  const previewToken = useRef<number | null>(null);
  const previewDeadline = useRef(0);
  const [list, setList] = useState<MaintenanceList | null>(null);
  const [detail, setDetail] = useState<WatchDetail | null>(null);
  const [preview, setPreview] = useState<RetentionPreview | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<WatchMutationResult | null>(null);
  const [queue] = useState(
    () => new RetentionWriteQueue(request, () => crypto.randomUUID()),
  );
  const current = useRef({ token, fresh, preview, detail });
  current.current = {
    token,
    fresh,
    preview: previewToken.current === token ? preview : null,
    detail: dataToken.current === token ? detail : null,
  };
  const accepts = () =>
    alive.current &&
    parent.accepts(epoch) &&
    local.accepts(token) &&
    current.current.fresh;
  function invalidatePreview() {
    serial.current++;
    current.current.preview = null;
    previewToken.current = null;
    setPreview(null);
  }
  function denial(reason: unknown) {
    // A late denial from any request in this mounted authority epoch is still decisive.
    if (!retentionDenial(reason) || !alive.current || !parent.accepts(epoch))
      return false;
    parent.update(`retention-denied:${epoch}`, false);
    local.update("denied", false);
    serial.current++;
    queue.clear();
    current.current.preview = null;
    previewToken.current = null;
    setPreview(null);
    setDetail(null);
    setList(null);
    setPending(false);
    setResult(null);
    onDenied(reason);
    return true;
  }
  async function refresh() {
    if (!accepts() || queue.active) return;
    invalidatePreview();
    const sequence = serial.current;
    setLoading(true);
    setError(null);
    setDetail(null);
    try {
      const response = await request<unknown>("/responsibilities/maintenance");
      if (!accepts() || sequence !== serial.current) return;
      if (!validMaintenanceList(response))
        throw { code: "RESPONSIBILITY_RESPONSE_INVALID" };
      dataToken.current = token;
      setList(response);
    } catch (reason) {
      if (!denial(reason) && accepts() && sequence === serial.current) {
        setList(null);
        setError(reason);
      }
    } finally {
      if (accepts() && sequence === serial.current) setLoading(false);
    }
  }
  async function inspect(id: string) {
    if (!accepts() || queue.active) return;
    invalidatePreview();
    const sequence = serial.current;
    setLoading(true);
    setError(null);
    setDetail(null);
    setResult(null);
    try {
      const response = await request<unknown>(
        `/responsibilities/${encodeURIComponent(id)}/maintenance`,
      );
      if (!accepts() || sequence !== serial.current) return;
      if (!validMaintenanceDetail(response, id))
        throw { code: "RESPONSIBILITY_RESPONSE_INVALID" };
      dataToken.current = token;
      setDetail(response);
    } catch (reason) {
      if (!denial(reason) && accepts() && sequence === serial.current)
        setError(reason);
    } finally {
      if (accepts() && sequence === serial.current) setLoading(false);
    }
  }
  async function prepare(row: Responsibility, action: RetentionAction) {
    if (
      !accepts() ||
      queue.pending ||
      queue.active ||
      current.current.detail?.responsibility !== row
    )
      return;
    invalidatePreview();
    const sequence = serial.current;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await request<unknown>(
        `/responsibilities/${encodeURIComponent(row.id)}/maintenance-preview`,
        {
          method: "POST",
          body: JSON.stringify({
            action,
            expected_version: row.version,
            expected_retention_version: row.retention_version,
          }),
        },
      );
      if (!accepts() || sequence !== serial.current) return;
      if (
        !validRetentionPreview(response, row, action) ||
        response.counts.retained_reviews !==
          current.current.detail?.reviews.length
      )
        throw { code: "RESPONSIBILITY_RESPONSE_INVALID" };
      if (Date.parse(response.expires_at) <= Date.now())
        throw { code: "RESPONSIBILITY_PREVIEW_EXPIRED" };
      previewDeadline.current =
        performance.now() +
        Math.min(300000, Date.parse(response.expires_at) - Date.now());
      previewToken.current = token;
      setPreview(response);
    } catch (reason) {
      if (!denial(reason) && accepts() && sequence === serial.current)
        setError(reason);
    } finally {
      if (accepts() && sequence === serial.current) setLoading(false);
    }
  }
  async function finish(work: () => Promise<WatchMutationResult>) {
    setBusy(true);
    setError(null);
    try {
      const saved = await work();
      if (!accepts()) return;
      invalidatePreview();
      setDetail(null);
      setResult(saved);
      // Parent clears any selected ordinary detail before scheduling its current-data refresh.
      onChanged(saved);
      void refresh();
    } catch (reason) {
      if (!denial(reason) && accepts()) {
        invalidatePreview();
        setError(reason);
      }
    } finally {
      if (alive.current) {
        setBusy(false);
        setPending(queue.pending);
      }
    }
  }
  function confirm(expected: RetentionPreview, permanentClick = false) {
    if (
      !accepts() ||
      queue.active ||
      queue.pending ||
      current.current.preview !== expected ||
      Date.parse(expected.expires_at) <= Date.now() ||
      performance.now() >= previewDeadline.current
    )
      return;
    const body = retentionBody(expected, permanentClick);
    if (!body) return;
    // Invalidate synchronously, including captured callbacks before React rerenders.
    invalidatePreview();
    void finish(() => queue.send(expected.responsibility.id, body));
  }
  function retry() {
    if (!accepts() || queue.active || !queue.pending) return;
    void finish(() => queue.retry());
  }
  function cancel() {
    if (!accepts() || queue.active || queue.pending) return;
    invalidatePreview();
    setError(null);
  }
  useEffect(() => {
    alive.current = true;
    const clear = () => {
      parent.update(`retention-authority:${epoch}`, false);
      local.update("invalid", false);
      serial.current++;
      queue.clear();
      current.current.preview = null;
      setPreview(null);
      setDetail(null);
      setList(null);
      setPending(false);
      setResult(null);
      onDenied({ code: "RESPONSIBILITY_CONTEXT_CHANGED" });
    };
    const events = ["desk:session", "desk:personal-context", "offline"];
    events.forEach((event) => window.addEventListener(event, clear));
    return () => {
      alive.current = false;
      local.update("unmounted", false);
      serial.current++;
      queue.clear();
      events.forEach((event) => window.removeEventListener(event, clear));
    };
  }, [parent, epoch, local, queue]);
  useEffect(() => {
    invalidatePreview();
    setDetail(null);
    setList(null);
    setLoading(false);
    if (accepts()) void refresh();
  }, [token]);
  useEffect(() => {
    if (!preview) return;
    const timer = window.setTimeout(
      () => {
        if (current.current.preview === preview) {
          invalidatePreview();
          setError({ code: "RESPONSIBILITY_PREVIEW_EXPIRED" });
        }
      },
      Math.min(
        300000,
        Math.max(0, Date.parse(preview.expires_at) - Date.now()),
      ),
    );
    return () => clearTimeout(timer);
  }, [preview]);
  return {
    list: accepts() && dataToken.current === token ? list : null,
    detail: accepts() && dataToken.current === token ? detail : null,
    preview: accepts() && previewToken.current === token ? preview : null,
    result: accepts() ? result : null,
    error,
    loading,
    busy,
    pending,
    refresh,
    inspect,
    prepare,
    confirm,
    retry,
    cancel,
    available: accepts(),
  };
}
