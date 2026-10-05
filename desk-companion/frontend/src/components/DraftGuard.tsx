import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";
type Guard = { dirty: boolean; busy: boolean };
const Context = createContext<{
  dirty: boolean;
  busy: boolean;
  register: (id: string, value: Guard | null) => void;
}>({ dirty: false, busy: false, register: () => {} });
export function useGuardRegistry() {
  const [entries, setEntries] = useState<Record<string, Guard>>({});
  const register = useCallback(
    (id: string, value: Guard | null) =>
      setEntries((old) => {
        if (
          value &&
          old[id]?.dirty === value.dirty &&
          old[id]?.busy === value.busy
        )
          return old;
        if (!value && !old[id]) return old;
        const next = { ...old };
        if (value) next[id] = value;
        else delete next[id];
        return next;
      }),
    [],
  );
  return useMemo(
    () => ({
      dirty: Object.values(entries).some((x) => x.dirty),
      busy: Object.values(entries).some((x) => x.busy),
      register,
    }),
    [entries, register],
  );
}
export const GuardContextProvider = Context.Provider;
export function DraftGuardProvider({ children }: { children: ReactNode }) {
  const guard = useGuardRegistry();
  return <Context.Provider value={guard}>{children}</Context.Provider>;
}
export function useDraftGuard(dirty: boolean, busy = false) {
  const { register } = useContext(Context);
  const id = useId();
  useEffect(() => {
    register(id, { dirty, busy });
    return () => register(id, null);
  }, [id, dirty, busy, register]);
  useEffect(() => {
    if (!dirty && !busy) return;
    const protect = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", protect);
    return () => window.removeEventListener("beforeunload", protect);
  }, [dirty, busy]);
}
export const useDraftState = () => useContext(Context);
