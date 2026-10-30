import { useEffect, useRef, useState } from "react";
import { request } from "../../api";
import { PrivateWriteQueue } from "./privateWrite";

export function usePrivateMutation() {
  const [queue] = useState(
    () =>
      new PrivateWriteQueue(
        ({ path, serialized, key }) =>
          request(path, {
            method: "POST",
            body: serialized,
            headers: { "X-Operation-Id": key },
          }),
        () => crypto.randomUUID(),
      ),
  );
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const live = useRef(true);
  const working = useRef(false);
  const accepted = useRef<((result: unknown) => void | Promise<void>) | null>(
    null,
  );
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
      queue.clear();
      accepted.current = null;
    };
  }, [queue]);
  async function finish(work: () => Promise<unknown>) {
    if (working.current || queue.active) return false;
    working.current = true;
    setBusy(true);
    setError(null);
    try {
      const result = await work();
      if (live.current) {
        const done = accepted.current;
        accepted.current = null;
        await done?.(result);
      }
      return true;
    } catch (e) {
      if (live.current) setError(e);
      return false;
    } finally {
      working.current = false;
      if (live.current) {
        setBusy(false);
        setPending(queue.pending);
      }
    }
  }
  async function run<T>(
    path: string,
    body: unknown,
    onSuccess: (result: T) => void | Promise<void>,
  ) {
    if (working.current || queue.active || queue.pending) return false;
    accepted.current = (result) => onSuccess(result as T);
    return finish(() => queue.send<T>(path, body));
  }
  function clear() {
    queue.clear();
    accepted.current = null;
    setPending(false);
    setError(null);
  }
  return {
    busy,
    pending,
    error,
    run,
    retry: () => finish(() => queue.retry()),
    clear,
  };
}
export type PrivateMutation = ReturnType<typeof usePrivateMutation>;
