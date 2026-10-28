import {
  createContext,
  Fragment,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import { ApiError, request, clearPending } from "../api";
import type { WorkspaceSnapshot } from "./types";

const WorkspaceContext = createContext<{
  data: WorkspaceSnapshot | null;
  offline: boolean;
  stale: boolean;
  refresh: () => Promise<void>;
}>({ data: null, offline: false, stale: true, refresh: async () => {} });

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<WorkspaceSnapshot | null>(null);
  const [offline, setOffline] = useState(false);
  const [stale, setStale] = useState(true);
  const lastSuccess = useRef(0);
  const principal = useRef<string | null>(null);
  const [principalKey, setPrincipalKey] = useState("initial");
  const live = useRef(false),
    busy = useRef(false);
  const refresh = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      const next = await request<WorkspaceSnapshot>("/workspace");
      if (live.current) {
        const identity = `${next.principal.kind}:${next.principal.id}`;
        if (principal.current !== identity) {
          if (principal.current !== null) {
            clearPending();
            setPrincipalKey(identity);
          }
          principal.current = identity;
        }
        setData(next);
        setOffline(false);
        lastSuccess.current = Date.now();
        setStale(false);
      }
    } catch (e) {
      if (live.current) {
        if (e instanceof ApiError && e.status === 401) {
          setData(null);
          setOffline(false);
        } else setOffline(true);
      }
    } finally {
      busy.current = false;
    }
  }, []);
  useEffect(() => {
    live.current = true;
    void refresh();
    const tick = () => {
      if (!document.hidden) {
        setStale(Date.now() - lastSuccess.current > 2500);
        void refresh();
      }
    };
    const timer = setInterval(tick, 1500);
    window.addEventListener("desk:session", tick);
    document.addEventListener("visibilitychange", tick);
    return () => {
      live.current = false;
      clearInterval(timer);
      window.removeEventListener("desk:session", tick);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [refresh]);
  return (
    <WorkspaceContext.Provider value={{ data, offline, stale, refresh }}>
      <Fragment key={principalKey}>{children}</Fragment>
    </WorkspaceContext.Provider>
  );
}
export function useWorkspace() {
  return useContext(WorkspaceContext);
}
