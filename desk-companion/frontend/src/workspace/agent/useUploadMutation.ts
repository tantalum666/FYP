import { useEffect, useRef, useState } from "react";
import { request } from "../../api";
import { PrivateWriteQueue } from "../personal/privateWrite";
import { rawUpload } from "./upload";
export function useUploadMutation() {
  const [queue] = useState(
    () =>
      new PrivateWriteQueue(
        async (operation) => {
          const upload = rawUpload(operation);
          return request(upload.path, {
            method: "POST",
            body: upload.body,
            headers: upload.headers,
          });
        },
        () => crypto.randomUUID(),
      ),
  );
  const [busy, setBusy] = useState(false),
    [pending, setPending] = useState(false),
    [error, setError] = useState<unknown>(null);
  const live = useRef(true),
    active = useRef(false),
    accepted = useRef<((result: unknown) => void) | null>(null);
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
      queue.clear();
      accepted.current = null;
    };
  }, [queue]);
  async function finish(work: () => Promise<unknown>) {
    if (active.current) return false;
    active.current = true;
    setBusy(true);
    setError(null);
    try {
      const result = await work();
      if (live.current) {
        const callback = accepted.current;
        accepted.current = null;
        callback?.(result);
      }
      return true;
    } catch (e) {
      if (live.current) setError(e);
      return false;
    } finally {
      active.current = false;
      if (live.current) {
        setBusy(false);
        setPending(queue.pending);
      }
    }
  }
  function run<T>(path: string, body: unknown, done: (result: T) => void) {
    if (active.current || queue.pending) return Promise.resolve(false);
    accepted.current = (result) => done(result as T);
    return finish(() => queue.send(path, body));
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
    clear,
    retry: () => finish(() => queue.retry()),
  };
}
