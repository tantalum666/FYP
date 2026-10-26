import { useCallback, useEffect, useRef, useState } from "react";
import { APIError, request } from "./api";
import type { Pending } from "./types";
import type { FoodReference, StationConsole } from "./mealTypes";

export function useStationConsole() {
  const [data, setData] = useState<StationConsole | null>(null),
    [foods, setFoods] = useState<FoodReference[]>([]);
  const [loading, setLoading] = useState(true),
    [needsSetup, setNeedsSetup] = useState(false);
  const [readError, setReadError] = useState(""),
    [actionError, setActionError] = useState(""),
    [referenceError, setReferenceError] = useState(""),
    [referenceRetry, setReferenceRetry] = useState(0);
  const [busy, setBusy] = useState(false),
    [pending, setPending] = useState<Pending | null>(null);
  const sequence = useRef(0),
    alive = useRef(true),
    inFlight = useRef(false),
    scope = useRef(""),
    pendingRef = useRef<Pending | null>(null);
  const persist = (operation: Pending | null, workspace = scope.current) => {
    if (workspace === scope.current) {
      pendingRef.current = operation;
      setPending(operation);
    }
    if (operation)
      sessionStorage.setItem(
        "senplate.console.pending." + workspace,
        JSON.stringify(operation),
      );
    else sessionStorage.removeItem("senplate.console.pending." + workspace);
  };
  const refresh = useCallback(async () => {
    const current = ++sequence.current;
    try {
      const next = await request<StationConsole>("/v1/device-console/active");
      if (!alive.current || current !== sequence.current) return;
      if (scope.current !== next.workspace_id) {
        scope.current = next.workspace_id;
        try {
          pendingRef.current = JSON.parse(
            sessionStorage.getItem(
              "senplate.console.pending." + scope.current,
            ) ?? "null",
          );
        } catch {
          pendingRef.current = null;
        }
        setPending(pendingRef.current);
      }
      setData(next);
      setNeedsSetup(false);
      setReadError("");
    } catch (e) {
      if (!alive.current || current !== sequence.current) return;
      if ((e as APIError).status === 401) {
        setData(null);
        setNeedsSetup(true);
        setReadError("");
      } else setReadError((e as APIError).code);
    } finally {
      if (alive.current && current === sequence.current) setLoading(false);
    }
  }, []);
  useEffect(() => {
    alive.current = true;
    void refresh();
    const poll = setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, 1500);
    const foreground = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", foreground);
    window.addEventListener("online", foreground);
    return () => {
      alive.current = false;
      sequence.current++;
      clearInterval(poll);
      document.removeEventListener("visibilitychange", foreground);
      window.removeEventListener("online", foreground);
    };
  }, [refresh]);
  useEffect(() => {
    if (!data?.workspace_id) return;
    let cancelled = false;
    request<{ items: FoodReference[] }>("/v1/device-console/references")
      .then((r) => {
        if (!cancelled) {
          setFoods(r.items);
          setReferenceError("");
        }
      })
      .catch((e) => {
        if (!cancelled) setReferenceError((e as APIError).code);
      });
    return () => {
      cancelled = true;
    };
  }, [data?.workspace_id, referenceRetry]);
  async function connect(key: string) {
    if (inFlight.current) return false;
    inFlight.current = true;
    setBusy(true);
    setActionError("");
    try {
      await request("/v1/device-console/session", undefined, {
        method: "POST",
        body: JSON.stringify({ setup_key: key }),
      });
      await refresh();
      return true;
    } catch (e) {
      setActionError((e as APIError).code);
      return false;
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  async function disconnect() {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    try {
      await request("/v1/device-console/session", undefined, {
        method: "DELETE",
      });
      sequence.current++;
      setData(null);
      setFoods([]);
      setNeedsSetup(true);
      setActionError("");
      scope.current = "";
      setPending(null);
      pendingRef.current = null;
    } catch (e) {
      setActionError((e as APIError).code);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  async function execute(operation: Pending, recover = false) {
    if (inFlight.current || !data) return false;
    inFlight.current = true;
    setBusy(true);
    setActionError("");
    const workspace = data.workspace_id;
    persist(operation, workspace);
    try {
      let found = false;
      if (recover) {
        try {
          await request("/v1/device-console/operations/" + operation.id);
          found = true;
        } catch (e) {
          if ((e as APIError).status !== 404) throw e;
        }
      }
      if (!found)
        await request(operation.path, undefined, {
          method: "POST",
          headers: { "Idempotency-Key": operation.id },
          body: JSON.stringify(operation.body),
        });
      persist(null, workspace);
      await refresh();
      return true;
    } catch (e) {
      const problem = e as APIError;
      if (problem.status >= 400 && problem.status < 500)
        persist(null, workspace);
      await refresh();
      setActionError(problem.code);
      return false;
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  async function mutate(path: string, body: Record<string, unknown>) {
    if (pendingRef.current || readError || referenceError) return false;
    const id = crypto.randomUUID();
    return execute({ id, path, body: { ...body, client_operation_id: id } });
  }
  return {
    data,
    foods,
    loading,
    needsSetup,
    busy,
    pending,
    error: readError || referenceError || actionError,
    readError: readError || referenceError,
    refresh: async () => {
      setReferenceRetry((n) => n + 1);
      await refresh();
    },
    connect,
    disconnect,
    mutate,
    retry: () => (pending ? execute(pending, true) : Promise.resolve(false)),
  };
}
