import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../api";
import { classifyFailure } from "../surfaceStatus";
import type { Snapshot } from "../types";
import { useWorkspaceSession } from "../useWorkspaceSession";
import { useWorkspace } from "../workspace/WorkspaceContext";
import { displayPrivacy } from "./privacy";

export function useDeviceCalendar(start: string, end: string) {
  const status = useWorkspace();
  const [authError, setAuthError] = useState<unknown>(null);
  const { session, recoverSession } = useWorkspaceSession(setAuthError);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loadedKey, setLoadedKey] = useState("");
  const [connection, setConnection] = useState<
    "loading" | "ready" | "offline" | "error"
  >("loading");
  const [loadError, setLoadError] = useState<unknown>(null);
  const hadSession = useRef(false);
  const [nonce, setNonce] = useState(0);
  const revision = useRef(0);
  const shouldReload = useRef(false);
  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const key = start + "/" + end;
  const fail = useCallback(
    (error: unknown) => {
      const kind = classifyFailure(error, hadSession.current);
      if (kind === "session-expired" || kind === "signed-out") {
        setSnapshot(null);
        setLoadedKey("");
        void recoverSession();
        return;
      }
      setLoadError(error);
      setConnection(kind === "error" ? "error" : "offline");
    },
    [recoverSession],
  );
  useEffect(() => {
    if (session) {
      hadSession.current = true;
      setAuthError(null);
    } else if (session === null) {
      setSnapshot(null);
      setLoadedKey("");
    }
  }, [session]);
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
    setAuthError(null);
    await recoverSession();
    reload();
  }, [recoverSession, reload]);
  const safeSnapshot = displayPrivacy(
    snapshot,
    status.data?.posture,
    status.stale || status.offline,
  );
  return {
    session,
    authError,
    snapshot: safeSnapshot,
    reload,
    reconnect,
    loadError,
    data: session && loadedKey === key ? safeSnapshot : null,
    state:
      session === undefined
        ? ("loading" as const)
        : !session
          ? ("offline" as const)
          : connection,
  };
}
