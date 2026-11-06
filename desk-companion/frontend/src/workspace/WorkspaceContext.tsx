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
import { openSession } from "../session";
import type { WorkspaceSnapshot, PermissionState } from "./types";

const WorkspaceContext = createContext<{
  data: WorkspaceSnapshot | null;
  offline: boolean;
  stale: boolean;
  refresh: () => Promise<void>;
  acceptPermissions: (permissions: PermissionState) => void;
}>({
  data: null,
  offline: false,
  stale: true,
  refresh: async () => {},
  acceptPermissions: () => {},
});

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<WorkspaceSnapshot | null>(null);
  const [offline, setOffline] = useState(false);
  const [stale, setStale] = useState(true);
  const lastSuccess = useRef(0);
  const snapshotEpoch = useRef(0);
  const acceptPermissions = useCallback((permissions: PermissionState) => {
    snapshotEpoch.current += 1;
    setData((current) =>
      current?.principal.kind === "owner" &&
      (!current.permissions ||
        permissions.version >= current.permissions.version)
        ? { ...current, permissions }
        : current,
    );
  }, []);
  const principal = useRef<string | null>(null);
  const [principalKey, setPrincipalKey] = useState("initial");
  const live = useRef(false),
    busy = useRef(false);
  const refresh = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    const epoch = snapshotEpoch.current;
    try {
      let next: WorkspaceSnapshot;
      try {
        next = await request<WorkspaceSnapshot>("/workspace");
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401) throw error;
        // Resolve an expired local session before removing the current identity;
        // this preserves mounted drafts without retrying a business write.
        await openSession();
        next = await request<WorkspaceSnapshot>("/workspace");
      }
      if (live.current && epoch === snapshotEpoch.current) {
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
      if (live.current && epoch === snapshotEpoch.current) {
        if (e instanceof ApiError && [401, 403].includes(e.status)) {
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
    <WorkspaceContext.Provider
      value={{ data, offline, stale, refresh, acceptPermissions }}
    >
      <Fragment key={principalKey}>{children}</Fragment>
    </WorkspaceContext.Provider>
  );
}
export function useWorkspace() {
  return useContext(WorkspaceContext);
}
