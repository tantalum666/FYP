import { useMemo, useSyncExternalStore } from "react";
import { pendingWrite } from "./api";

function subscribe(changed: () => void) {
  window.addEventListener("desk:write-recovered", changed);
  window.addEventListener("desk:session", changed);
  return () => {
    window.removeEventListener("desk:write-recovered", changed);
    window.removeEventListener("desk:session", changed);
  };
}
const snapshot = () => pendingWrite()?.key ?? null;

/** Child-panel recovery must also clear the surrounding app's stale banner. */
export function usePendingWrite() {
  const key = useSyncExternalStore(subscribe, snapshot, () => null);
  return useMemo(() => pendingWrite(), [key]);
}
