import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "./api";
import { openSession } from "./session";
import type { Session } from "./types";

/** Recover the explicitly enabled local preview without unmounting unsent work. */
export function useWorkspaceSession(onError: (error: unknown) => void) {
  const [session, updateSession] = useState<Session | null>();
  const current = useRef(session);
  const live = useRef(false);
  const recovering = useRef(false);
  const latestError = useRef(onError);
  latestError.current = onError;
  const setSession = useCallback((value: Session | null) => {
    current.current = value;
    updateSession(value);
  }, []);
  const recoverSession = useCallback(async () => {
    if (recovering.current) return;
    recovering.current = true;
    try {
      const next = await openSession();
      if (live.current) setSession(next);
    } catch (error) {
      if (!live.current) return;
      if (error instanceof ApiError && error.status === 401) setSession(null);
      else {
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
  return { session, setSession, recoverSession };
}
