import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../../api";
import { ResponseFence } from "../personal/responseFence";
import { validWorkCapacity } from "./workCapacity";
import type { WorkCapacity } from "./workCapacity";

/** Mounted only in the visible owner workspace. No scope reads, polling or mutations. */
export function useWorkCapacity(parent: ResponseFence, epoch: number) {
  const local = useRef(new ResponseFence()).current;
  const sequence = useRef(0);
  const [value, setValue] = useState<{
    epoch: number;
    data: WorkCapacity;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const refresh = useCallback(async () => {
    const captured = local.capture();
    if (!local.accepts(captured) || !parent.accepts(epoch)) return;
    const serial = ++sequence.current;
    const accepts = () =>
      local.accepts(captured) &&
      parent.accepts(epoch) &&
      sequence.current === serial;
    setValue(null);
    setLoading(true);
    try {
      const result = await request<unknown>("/work/capacity");
      if (accepts() && validWorkCapacity(result))
        setValue({ epoch: captured, data: result });
    } catch (error) {
      const denial =
        error &&
        typeof error === "object" &&
        (("status" in error &&
          (error.status === 401 || error.status === 403)) ||
          ("code" in error &&
            /AUTH|SESSION|OWNER|PRIVATE|PRIVACY|CONTEXT_HIDDEN|CONTEXT_CHANGED/.test(
              String(error.code),
            )));
      if (denial && local.accepts(captured) && parent.accepts(epoch)) {
        // Actual access revocation is shared authority, not a capacity failure.
        // Even a reordered denial in this same epoch must mask private views.
        parent.update(`capacity-denied:${epoch}`, false);
        local.update("denied", false);
        sequence.current++;
        setValue(null);
        setLoading(false);
      } else if (accepts()) {
        // Ordinary capacity failures never change work scope or a retry queue.
        setValue(null);
      }
    } finally {
      if (accepts()) setLoading(false);
    }
  }, [local, parent, epoch]);
  useEffect(() => {
    local.update(`capacity:${epoch}`, parent.accepts(epoch));
    setValue(null);
    void refresh();
    const clear = () => {
      local.update("invalid", false);
      sequence.current++;
      setValue(null);
      setLoading(false);
    };
    const events = ["desk:session", "desk:personal-context", "offline"];
    events.forEach((event) => window.addEventListener(event, clear));
    return () => {
      local.update("unmounted", false);
      sequence.current++;
      events.forEach((event) => window.removeEventListener(event, clear));
    };
  }, [local, parent, epoch, refresh]);
  return {
    value:
      parent.accepts(epoch) && value && local.accepts(value.epoch)
        ? value.data
        : null,
    loading: parent.accepts(epoch) && loading,
    refresh,
  };
}
