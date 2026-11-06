import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "./api";
import { openSession } from "./session";
import type { Session } from "./types";

/** Restore the local owner connection without unmounting unsent work. */
export function useWorkspaceSession(onError: (error: unknown) => void) {
  const [session, updateSession] = useState<Session | null>();
  const [expired, setExpired] = useState(false);
  const current = useRef(session);
  const live = useRef(false);
  const recovering = useRef(false);
  const latestError = useRef(onError);
  latestError.current = onError;
  const setSession = useCallback((value: Session | null) => {
    current.current = value;
    updateSession(value);
    setExpired(false);
  }, []);
  const recoverSession = useCallback(async () => {
    if (recovering.current) return;
    recovering.current = true;
    try {
      const next = await openSession();
      if (live.current) setSession(next);
    } catch (error) {
      if (!live.current) return;
      if (error instanceof ApiError && [401, 403].includes(error.status)) {
        const hadSession = !!current.current;
        setSession(null);
        setExpired(hadSession);
        if (error.status === 403) latestError.current(error);
      } else {
        latestError.current(error);
        if (current.current === undefined) setSession(null);
      }
    } finally {
      recovering.current = false;
    }
  }, [setSession]);
  useEffect(() => {
    live.current = true;
    void recoverSession();
    const expired = () => {
      if (current.current) void recoverSession();
    };
    window.addEventListener("desk:auth-required", expired);
    return () => {
      live.current = false;
      window.removeEventListener("desk:auth-required", expired);
    };
  }, [recoverSession]);
  return { session, setSession, recoverSession, expired };
}
