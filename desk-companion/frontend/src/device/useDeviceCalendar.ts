import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, request } from "../api";
import { classifyFailure } from "../surfaceStatus";
import type { Session, Snapshot } from "../types";
import { useWorkspace } from "../workspace/WorkspaceContext";
import { displayPrivacy } from "./privacy";

export function useDeviceCalendar(start: string, end: string) {
  const status = useWorkspace();
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [authError, setAuthError] = useState<unknown>(null);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loadedKey, setLoadedKey] = useState("");
  const [connection, setConnection] = useState<
    "loading" | "ready" | "offline" | "error"
  >("loading");
  const [loadError, setLoadError] = useState<unknown>(null);
  const [notice, setNotice] = useState<null | "session-expired">(null);
  const hadSession = useRef(false);
  const [nonce, setNonce] = useState(0);
  const revision = useRef(0);
  const shouldReload = useRef(false);
  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const key = start + "/" + end;
  const clearSession = useCallback((reason: "signed-out" | "expired") => {
    setSession(null);
    setSnapshot(null);
    setLoadedKey("");
    setAuthError(null);
    setLoadError(null);
    setNotice(reason === "expired" ? "session-expired" : null);
  }, []);
  const lock = useCallback(() => clearSession("signed-out"), [clearSession]);
  const fail = useCallback(
    (error: unknown) => {
      const kind = classifyFailure(error, hadSession.current);
      if (kind === "session-expired") {
        clearSession("expired");
        return;
      }
      if (kind === "signed-out") {
        clearSession("signed-out");
        return;
      }
      setLoadError(error);
      setConnection(kind === "error" ? "error" : "offline");
    },
    [clearSession],
  );
  const adoptSession = useCallback((value: Session | null) => {
    if (value) {
      hadSession.current = true;
      setNotice(null);
      setAuthError(null);
    }
    setSession(value);
  }, []);
  useEffect(() => {
    let live = true;
    request<Session>("/session")
      .then((s) => {
        if (live) {
          hadSession.current = true;
          setSession(s);
          setAuthError(null);
          setNotice(null);
        }
      })
      .catch((e) => {
        if (live) {
          setSession(null);
          setAuthError(e instanceof ApiError && e.status === 401 ? null : e);
        }
      });
    return () => {
      live = false;
    };
  }, []);
  useEffect(() => {
    if (!session) return;
    let live = true;
    request<Snapshot>(
      `/calendar?display=true&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
    )
      .then((s) => {
        if (!live) return;
        setSnapshot(s);
        setLoadedKey(key);
        revision.current = s.revision;
        shouldReload.current = false;
        setConnection("ready");
        setLoadError(null);
      })
      .catch((e) => {
        if (!live) return;
        shouldReload.current = true;
        fail(e);
      });
    return () => {
      live = false;
    };
  }, [session, start, end, key, nonce, fail]);
  useEffect(() => {
    if (!session) return;
    let live = true,
      working = false;
    const poll = async () => {
      if (working || document.hidden) return;
      working = true;
      try {
        const r = await request<{ revision: number }>("/revision");
        if (live && (r.revision !== revision.current || shouldReload.current)) {
          shouldReload.current = false;
          reload();
        }
        if (live) {
          setConnection("ready");
          setLoadError(null);
        }
      } catch (e) {
        if (live) {
          shouldReload.current = true;
          fail(e);
        }
      } finally {
        working = false;
      }
    };
    const visible = () => {
      if (!document.hidden) reload();
    };
    const timer = setInterval(poll, 1500);
    document.addEventListener("visibilitychange", visible);
    window.addEventListener("focus", visible);
    return () => {
      live = false;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", visible);
      window.removeEventListener("focus", visible);
    };
  }, [session, reload, fail]);
  const reconnect = useCallback(async () => {
    if (session) {
      reload();
      return;
    }
    try {
      const s = await request<Session>("/session");
      hadSession.current = true;
      setSession(s);
      setAuthError(null);
      setNotice(null);
    } catch (e) {
      setAuthError(e instanceof ApiError && e.status === 401 ? null : e);
    }
  }, [session, reload]);
  const safeSnapshot = displayPrivacy(
    snapshot,
    status.data?.posture,
    status.stale || status.offline,
  );
  return {
    session,
    setSession: adoptSession,
    lock,
    snapshot: safeSnapshot,
    reload,
    reconnect,
    loadError,
    data: session && loadedKey === key ? safeSnapshot : null,
    state:
      session === undefined
        ? ("loading" as const)
        : !session
          ? notice === "session-expired"
            ? ("session-expired" as const)
            : authError
              ? ("offline" as const)
              : ("locked" as const)
          : connection,
  };
}
