import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import { ApiError, request } from "../api";
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
  const live = useRef(false),
    busy = useRef(false);
  const refresh = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      const next = await request<WorkspaceSnapshot>("/workspace");
      if (live.current) {
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
      {children}
    </WorkspaceContext.Provider>
  );
}
export function useWorkspace() {
  return useContext(WorkspaceContext);
}
