import { useEffect, useRef, useState } from "react";
import { ApiError, request } from "../../api";
import { ResponseFence } from "../personal/responseFence";
import {
  validWorkSearchResponse,
  workDetailPath,
  workHitKey,
  workSearchDetail,
  WorkSearchFence,
  workSearchInput,
} from "./workSearch";
import type {
  WorkSearchDetail,
  WorkSearchHit,
  WorkSearchInput,
  WorkSearchKind,
  WorkSearchResponse,
} from "./workSearch";

function privateDenial(error: unknown) {
  return (
    error instanceof ApiError &&
    (error.status === 401 ||
      error.status === 403 ||
      /AUTH|SESSION|OWNER|PRIVATE|PRIVACY/.test(error.code))
  );
}
export function useWorkSearch(
  parentFence: ResponseFence,
  epoch: number,
  fresh: boolean,
) {
  const fence = useRef(new ResponseFence()).current;
  const searches = useRef(new WorkSearchFence()).current;
  const selections = useRef(new WorkSearchFence()).current;
  const [scopeEpoch, setScopeEpoch] = useState(epoch);
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<WorkSearchKind>("all");
  const [denied, setDenied] = useState(false);
  const [value, setValue] = useState<{
    epoch: number;
    input: WorkSearchInput;
    page: WorkSearchResponse;
  } | null>(null);
  const [detail, setDetail] = useState<{
    epoch: number;
    record: WorkSearchDetail;
  } | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [detailError, setDetailError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [opening, setOpening] = useState<string | null>(null);
  const active =
    fresh && parentFence.accepts(epoch) && !denied && scopeEpoch === epoch;
  fence.update(`work-search:${epoch}`, active);
  const currentValue = useRef(value);
  currentValue.current = value;
  function clearDetail() {
    selections.invalidate();
    setDetail(null);
    setDetailError(null);
    setOpening(null);
  }
  function clear() {
    searches.invalidate();
    clearDetail();
    setQuery("");
    setKind("all");
    setValue(null);
    currentValue.current = null;
    setError(null);
    setLoading(false);
  }
  function deny(error: unknown) {
    fence.update(`denied:${epoch}`, false);
    clear();
    setDenied(true);
    setError(error);
  }
  useEffect(() => {
    clear();
    setDenied(false);
    setScopeEpoch(epoch);
    fence.update(`work-search:${epoch}`, fresh && parentFence.accepts(epoch));
    // Event invalidation happens before the parent has time to rerender.
    const changed = () => deny(new ApiError("AGENT_UI_SCOPE_CHANGED"));
    window.addEventListener("desk:session", changed);
    window.addEventListener("offline", changed);
    return () => {
      fence.update("unmounted", false);
      searches.invalidate();
      selections.invalidate();
      window.removeEventListener("desk:session", changed);
      window.removeEventListener("offline", changed);
    };
  }, [epoch, fresh, parentFence, fence, searches, selections]);

  async function search(input: WorkSearchInput) {
    if (!active || !parentFence.accepts(epoch)) return;
    const ticket = searches.begin(fence);
    const accepts = () =>
      parentFence.accepts(epoch) && searches.accepts(ticket, fence);
    clearDetail();
    setValue(null);
    currentValue.current = null;
    setLoading(true);
    setError(null);
    try {
      const body = await request<unknown>("/work/search", {
        method: "POST",
        body: JSON.stringify(input),
      });
      if (!accepts()) return;
      if (!validWorkSearchResponse(body, input))
        throw new ApiError("WORK_SEARCH_RESPONSE_INVALID");
      const next = { epoch: ticket.epoch, input, page: body };
      currentValue.current = next;
      setValue(next);
    } catch (e) {
      if (
        parentFence.accepts(epoch) &&
        fence.accepts(ticket.epoch) &&
        privateDenial(e)
      )
        deny(e);
      else if (accepts()) setError(e);
    } finally {
      if (accepts()) setLoading(false);
    }
  }
  function submit() {
    const input = workSearchInput(query, kind);
    if (!input) {
      searches.invalidate();
      clearDetail();
      setValue(null);
      currentValue.current = null;
      setLoading(false);
      setError(new ApiError("WORK_SEARCH_QUERY_LIMIT"));
      return;
    }
    void search(input);
  }
  function nextPage() {
    const current = currentValue.current;
    if (
      !current ||
      !fence.accepts(current.epoch) ||
      current.page.next_offset === null ||
      loading
    )
      return;
    void search({
      ...current.input,
      offset: current.page.next_offset,
      snapshot: current.page.snapshot,
    });
  }
  function previousPage() {
    const current = currentValue.current;
    if (
      !current ||
      !fence.accepts(current.epoch) ||
      current.input.offset === 0 ||
      loading
    )
      return;
    void search({
      ...current.input,
      offset: Math.max(0, current.input.offset - current.input.limit),
      snapshot: current.page.snapshot,
    });
  }
  async function open(hit: WorkSearchHit): Promise<WorkSearchDetail | null> {
    const current = currentValue.current;
    if (
      !active ||
      !parentFence.accepts(epoch) ||
      !current ||
      !fence.accepts(current.epoch) ||
      !current.page.items.some((item) => workHitKey(item) === workHitKey(hit))
    )
      return null;
    const ticket = selections.begin(fence);
    const accepts = () =>
      parentFence.accepts(epoch) &&
      selections.accepts(ticket, fence) &&
      currentValue.current === current;
    setDetail(null);
    setDetailError(null);
    setOpening(workHitKey(hit));
    try {
      const body = await request<unknown>(workDetailPath(hit));
      if (!accepts()) return null;
      const record = workSearchDetail(hit, body);
      if (!record) throw new ApiError("WORK_SEARCH_RESPONSE_INVALID");
      setDetail({ epoch: ticket.epoch, record });
      return record;
    } catch (e) {
      if (
        parentFence.accepts(epoch) &&
        fence.accepts(ticket.epoch) &&
        privateDenial(e)
      )
        deny(e);
      else if (accepts()) setDetailError(e);
      return null;
    } finally {
      if (accepts()) setOpening(null);
    }
  }
  return {
    query: active ? query : "",
    setQuery,
    kind: active ? kind : ("all" as WorkSearchKind),
    setKind,
    value: active && value && fence.accepts(value.epoch) ? value : null,
    detail:
      active && detail && fence.accepts(detail.epoch) ? detail.record : null,
    error,
    detailError: active ? detailError : null,
    loading: active && loading,
    opening: active ? opening : null,
    active,
    fence,
    submit,
    nextPage,
    previousPage,
    open,
    clear,
    clearDetail,
  };
}
