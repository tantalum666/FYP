import { useCallback, useEffect, useRef, useState } from "react";
import { request, ApiError } from "../../api";
import { ResponseFence } from "../personal/responseFence";
import {
  CaptureReviewWindow,
  captureDenial,
  captureId,
  captureObject,
  captureUrl,
  validCaptureReview,
  validPublicCapture,
} from "./capturePolicy";
import type { CaptureReview, PublicCapture } from "./capturePolicy";
export type CaptureOperation = {
  path: string;
  body: Readonly<Record<string, unknown>>;
  key: string;
  kind: "prepare" | "approve" | "cancel" | "reconcile";
  epoch: number;
};
const base = "/public-research/captures";
/** Volatile exact-operation recovery. Never stores URLs, approvals or request keys in browser storage. */
export function usePublicCaptures(
  parent: ResponseFence,
  epoch: number,
  fresh: boolean,
  hidden = false,
) {
  const local = useRef(new ResponseFence()).current;
  const boundEpoch = useRef<number | null>(null);
  const live = useRef(false),
    ready = useRef(fresh),
    busyRef = useRef(false);
  ready.current = fresh;
  const [enabled, setEnabled] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null);
  const [records, setRecords] = useState<PublicCapture[]>([]),
    [cursor, setCursor] = useState<string | null>(null);
  const [selected, setSelected] = useState<PublicCapture | null>(null),
    [review, setReview] = useState<CaptureReview | null>(null);
  const [pending, setPending] = useState<CaptureOperation[]>([]);
  const pinned = useRef<CaptureOperation[]>([]),
    current = useRef<PublicCapture | null>(null),
    currentReview = useRef<CaptureReview | null>(null);
  const windows = useRef(new Map<string, CaptureReviewWindow>());
  const [, tickReview] = useState(0);
  const windowKey = (value: CaptureReview) =>
    `${value.id}:${value.intent_hash}`;
  function pinReview(value: CaptureReview | null) {
    if (value && !windows.current.has(windowKey(value)))
      windows.current.set(
        windowKey(value),
        new CaptureReviewWindow(value.expires_at),
      );
    currentReview.current = value;
    setReview(value);
  }
  useEffect(() => {
    if (!review) return;
    const remaining = windows.current.get(windowKey(review))?.remaining() ?? 0;
    if (!remaining) return;
    const timer = setTimeout(
      () => tickReview((n) => n + 1),
      Math.ceil(remaining),
    );
    return () => clearTimeout(timer);
  }, [review]);
  const readSerial = useRef(0),
    capability = useRef(false);
  const accepts = useCallback(
    () =>
      live.current &&
      boundEpoch.current === epoch &&
      ready.current &&
      parent.accepts(epoch) &&
      local.accepts(local.capture()),
    [parent, epoch, local],
  );
  const clear = useCallback(() => {
    boundEpoch.current = null;
    local.update("revoked", false);
    readSerial.current++;
    capability.current = false;
    pinned.current = [];
    current.current = null;
    currentReview.current = null;
    windows.current.clear();
    busyRef.current = false;
    setEnabled(false);
    setRecords([]);
    setSelected(null);
    setReview(null);
    setPending([]);
    setBusy(false);
    setError(null);
  }, [local]);
  const fail = useCallback(
    (e: unknown, captured: number) => {
      // A reordered denial in the same privacy epoch revokes even if a newer read succeeded.
      if (
        captureDenial(e) &&
        live.current &&
        local.accepts(captured) &&
        parent.accepts(epoch)
      ) {
        parent.update(`capture-denied:${epoch}`, false);
        clear();
        setError(e);
      } else if (
        live.current &&
        local.accepts(captured) &&
        parent.accepts(epoch)
      )
        setError(e);
    },
    [parent, epoch, local, clear],
  );
  useEffect(() => {
    live.current = true;
    boundEpoch.current = epoch;
    local.update(`capture:${epoch}:${hidden}`, parent.accepts(epoch));
    const captured = local.capture();
    pinned.current = [];
    current.current = null;
    currentReview.current = null;
    windows.current.clear();
    setRecords([]);
    setSelected(null);
    setReview(null);
    setPending([]);
    setCursor(null);
    setError(null);
    capability.current = false;
    setEnabled(false);
    if (parent.accepts(epoch))
      void request<unknown>("/public-research/capabilities")
        .then((v) => {
          if (
            !live.current ||
            !parent.accepts(epoch) ||
            !local.accepts(captured)
          )
            return;
          if (
            !captureObject(v) ||
            typeof v.enabled !== "boolean" ||
            v.history_limit !== 200 ||
            v.source_cleanup !== false
          )
            throw new ApiError("CAPTURE_RESPONSE_INVALID");
          capability.current = v.enabled;
          setEnabled(v.enabled);
        })
        .catch((e) => fail(e, captured));
    const events = ["desk:session", "desk:personal-context", "offline"];
    events.forEach((event) => window.addEventListener(event, clear));
    return () => {
      live.current = false;
      boundEpoch.current = null;
      local.update("unmounted", false);
      pinned.current = [];
      current.current = null;
      currentReview.current = null;
      readSerial.current++;
      events.forEach((event) => window.removeEventListener(event, clear));
    };
  }, [parent, epoch, hidden, local, accepts, clear, fail]);
  const read = useCallback(
    async (id: string | null = null, next: string | null = null) => {
      if (
        !accepts() ||
        (id !== null && !captureId(id)) ||
        (next !== null && !captureId(next))
      )
        return false;
      const serial = ++readSerial.current,
        captured = local.capture();
      setError(null);
      currentReview.current = null;
      setReview(null);
      try {
        const v = await request<unknown>(
          id
            ? `${base}/${id}?metadata_only=${hidden}`
            : `${base}?limit=20&metadata_only=${hidden}${next ? `&cursor=${next}` : ""}`,
        );
        if (
          !accepts() ||
          !local.accepts(captured) ||
          serial !== readSerial.current
        )
          return false;
        if (!captureObject(v)) throw new ApiError("CAPTURE_RESPONSE_INVALID");
        if (id) {
          if (!validPublicCapture(v.capture, hidden) || v.capture.id !== id)
            throw new ApiError("CAPTURE_RESPONSE_INVALID");
          if (
            v.review !== undefined &&
            v.review !== null &&
            (hidden || !validCaptureReview(v.review, v.capture))
          )
            throw new ApiError("CAPTURE_RESPONSE_INVALID");
          current.current = v.capture;
          setSelected(v.capture);
          pinReview(
            !hidden && validCaptureReview(v.review, v.capture)
              ? v.review
              : null,
          );
        } else {
          if (
            !Array.isArray(v.captures) ||
            v.captures.length > 20 ||
            !v.captures.every((x) => validPublicCapture(x, hidden)) ||
            new Set(v.captures.map((x) => x.id)).size !== v.captures.length ||
            !(v.next_cursor === null || captureId(v.next_cursor))
          )
            throw new ApiError("CAPTURE_RESPONSE_INVALID");
          setRecords(v.captures);
          setCursor(v.next_cursor);
        }
        return true;
      } catch (e) {
        fail(e, captured);
        return false;
      }
    },
    [accepts, hidden, local, fail],
  );
  const send = useCallback(
    async (operation: CaptureOperation) => {
      if (
        !accepts() ||
        !local.accepts(operation.epoch) ||
        busyRef.current ||
        !pinned.current.includes(operation)
      )
        return false;
      busyRef.current = true;
      readSerial.current++;
      currentReview.current = null;
      setReview(null);
      setBusy(true);
      setError(null);
      const captured = operation.epoch;
      try {
        const v = await request<unknown>(operation.path, {
          method: "POST",
          body: JSON.stringify(operation.body),
          headers: { "X-Operation-Id": operation.key },
        });
        if (!accepts() || !local.accepts(captured)) return false;
        if (
          !captureObject(v) ||
          !validPublicCapture(
            v.capture,
            hidden || operation.kind === "cancel",
          ) ||
          v.operation_id !== operation.key ||
          (operation.kind !== "prepare" &&
            operation.path !== `${base}/${v.capture.id}/${operation.kind}`)
        )
          throw new ApiError("CAPTURE_RESPONSE_INVALID");
        if (
          operation.kind === "prepare" &&
          (v.capture.url !== operation.body.url ||
            v.capture.label !== operation.body.label)
        )
          throw new ApiError("CAPTURE_RESPONSE_INVALID");
        if (
          operation.kind === "prepare" &&
          v.capture.state === "review" &&
          !validCaptureReview(v.review, v.capture)
        )
          throw new ApiError("CAPTURE_RESPONSE_INVALID");
        if (
          operation.kind === "reconcile" &&
          !["source_verified", "source_unknown", "no_final_source"].includes(
            String(v.verification),
          )
        )
          throw new ApiError("CAPTURE_RESPONSE_INVALID");
        pinned.current = pinned.current.filter((x) => x !== operation);
        setPending([...pinned.current]);
        if (
          !current.current ||
          current.current.id !== v.capture.id ||
          current.current.version <= v.capture.version
        ) {
          current.current = v.capture;
          setSelected(v.capture);
          pinReview(
            !hidden && validCaptureReview(v.review, v.capture)
              ? v.review
              : null,
          );
        }
        if (operation.kind === "cancel" && !hidden) await read(v.capture.id);
        window.dispatchEvent(new Event("desk:agent-runs"));
        return true;
      } catch (e) {
        fail(e, captured);
        // An explicit client rejection is not an unknown mutation. Never replace its key automatically.
        if (
          !captureDenial(e) &&
          captureObject(e) &&
          typeof e.status === "number" &&
          e.status >= 400 &&
          e.status < 500 &&
          e.status !== 408 &&
          local.accepts(captured)
        ) {
          pinned.current = pinned.current.filter((x) => x !== operation);
          setPending([...pinned.current]);
          currentReview.current = null;
          setReview(null);
        }
        return false;
      } finally {
        busyRef.current = false;
        if (live.current && local.accepts(captured)) setBusy(false);
      }
    },
    [accepts, local, hidden, fail, read],
  );
  function mutate(
    kind: CaptureOperation["kind"],
    body: Record<string, unknown>,
    target?: PublicCapture,
  ) {
    if (
      !accepts() ||
      busyRef.current ||
      (hidden && kind !== "cancel") ||
      ((kind === "prepare" || kind === "approve") && !capability.current)
    )
      return Promise.resolve(false);
    if (
      pinned.current.some((x) => x.kind === kind) ||
      (kind === "prepare" && pinned.current.length)
    )
      return Promise.resolve(false);
    if (
      kind !== "prepare" &&
      (!target ||
        !current.current ||
        target.id !== current.current.id ||
        target.version !== current.current.version)
    )
      return Promise.resolve(false);
    if (kind === "cancel" && !target?.cancel_available)
      return Promise.resolve(false);
    const operation: CaptureOperation = {
      kind,
      body: Object.freeze({ ...body }),
      key: crypto.randomUUID(),
      epoch: local.capture(),
      path: kind === "prepare" ? base : `${base}/${target!.id}/${kind}`,
    };
    pinned.current = [...pinned.current, operation];
    setPending([...pinned.current]);
    return send(operation);
  }
  return {
    enabled: accepts() && enabled,
    available: accepts(),
    hidden,
    busy: accepts() && busy,
    error: parent.accepts(epoch) ? error : null,
    records: accepts() ? records : [],
    cursor: accepts() ? cursor : null,
    selected: accepts() ? selected : null,
    review: accepts() ? review : null,
    reviewReady:
      accepts() &&
      !!review &&
      (windows.current.get(windowKey(review))?.remaining() ?? 0) > 0,
    pending: accepts() ? pending : [],
    read,
    prepare: (url: string, label: string, retain: boolean) =>
      captureUrl(url) &&
      retain === true &&
      (label === "" ||
        (label.length <= 120 && !/[\u0000-\u001f\u007f-\u009f]/.test(label)))
        ? mutate("prepare", {
            url,
            label: label || null,
            retain_capture_record: true,
          })
        : Promise.resolve(false),
    approve: (value: CaptureReview, publicOnly: boolean, retain: boolean) =>
      accepts() &&
      currentReview.current === value &&
      selected &&
      selected.id === value.id &&
      selected.version === value.version &&
      (windows.current.get(windowKey(value))?.remaining() ?? 0) > 0 &&
      publicOnly === true &&
      retain === true
        ? mutate(
            "approve",
            {
              expected_version: value.version,
              intent_hash: value.intent_hash,
              public_only: true,
              retain_snapshot: true,
            },
            selected,
          )
        : Promise.resolve(false),
    stop: (value: PublicCapture) =>
      mutate("cancel", { expected_version: value.version }, value),
    reconcile: (value: PublicCapture) =>
      mutate("reconcile", { expected_version: value.version }, value),
    retry: send,
  };
}
