import { useCallback, useEffect, useRef, useState } from "react";
import { APIError, request } from "./api";
import type { DiningMenu, FoodOrder, Overview, Pending, User } from "./types";

export function useWorkspace(
  user: User,
  context: string,
  onUnauthorized: () => void,
) {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [menu, setMenu] = useState<DiningMenu | null>(null);
  const [orders, setOrders] = useState<FoodOrder[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const storageKey = `senplate.pending.${user.id}.${context}`;
  const [pending, setPending] = useState<Pending | null>(() => {
    try {
      return JSON.parse(sessionStorage.getItem(storageKey) ?? "null");
    } catch {
      return null;
    }
  });
  const mounted = useRef(true),
    sequence = useRef(0),
    busyRef = useRef(false);
  const unauthorized = useRef(onUnauthorized);
  unauthorized.current = onUnauthorized;
  const refresh = useCallback(async () => {
    const index = ++sequence.current;
    try {
      const [data, nextMenu, nextOrders] = await Promise.all([
        request<Overview>(`/v1/workspaces/${context}/overview`, context),
        request<DiningMenu>(`/v1/workspaces/${context}/menu`, context),
        request<{ items: FoodOrder[] }>(
          `/v1/workspaces/${context}/orders`,
          context,
        ),
      ]);
      if (mounted.current && index === sequence.current) {
        setOverview(data);
        setMenu(nextMenu);
        setOrders(nextOrders.items);
        setError("");
      }
    } catch (e) {
      if (mounted.current && index === sequence.current) {
        const err = e as APIError;
        setError(err.code);
        if ([401, 403].includes(err.status)) {
          setOverview(null);
          setMenu(null);
          setOrders([]);
          unauthorized.current();
        }
      }
    }
  }, [context]);
  useEffect(() => {
    mounted.current = true;
    void refresh();
    let disposed = false,
      socket: WebSocket | undefined,
      retry: ReturnType<typeof setTimeout> | undefined;
    const connect = () => {
      if (disposed) return;
      socket = new WebSocket(
        `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/v1/events?context_id=${encodeURIComponent(context)}`,
      );
      socket.onmessage = () => {
        if (!disposed) void refresh();
      };
      socket.onclose = () => {
        if (!disposed) retry = setTimeout(connect, 3000);
      };
      socket.onerror = () => socket?.close();
    };
    connect();
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, 5000);
    const foreground = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", foreground);
    window.addEventListener("online", foreground);
    return () => {
      disposed = true;
      mounted.current = false;
      sequence.current++;
      clearInterval(timer);
      clearTimeout(retry);
      socket?.close();
      document.removeEventListener("visibilitychange", foreground);
      window.removeEventListener("online", foreground);
    };
  }, [context, refresh]);
  const persist = (value: Pending | null) => {
    setPending(value);
    if (value) sessionStorage.setItem(storageKey, JSON.stringify(value));
    else sessionStorage.removeItem(storageKey);
  };
  async function execute(operation: Pending, recover = false) {
    if (busyRef.current) return false;
    busyRef.current = true;
    setBusy(true);
    persist(operation);
    try {
      let recovered = false;
      if (recover) {
        try {
          await request(`/v1/operations/${operation.id}`, context);
          recovered = true;
        } catch (e) {
          if ((e as APIError).status !== 404) throw e;
        }
      }
      if (!recovered)
        await request(operation.path, context, {
          method: "POST",
          headers: { "Idempotency-Key": operation.id },
          body: JSON.stringify(operation.body),
        });
      persist(null);
      setError("");
      await refresh();
      return true;
    } catch (e) {
      const err = e as APIError;
      setError(err.code);
      if (err.status >= 400 && err.status < 500) {
        persist(null);
        await refresh();
        setError(err.code);
      }
      return false;
    } finally {
      busyRef.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  async function mutate(path: string, body: Record<string, unknown>) {
    if (pending) return false;
    const id = crypto.randomUUID();
    return execute({ id, path, body: { ...body, client_operation_id: id } });
  }
  return {
    overview,
    menu,
    orders,
    error,
    busy,
    pending,
    refresh,
    mutate,
    retry: () => (pending ? execute(pending, true) : Promise.resolve(false)),
  };
}

export type WorkspaceAPI = ReturnType<typeof useWorkspace>;
