import { useCallback, useEffect, useRef, useState } from "react";
import { request, write } from "../api";
import type { Language } from "../types";
import {
  newlyArrived,
  openNotices,
  showBrowserNotice,
  type DeskNotice,
} from "./notices";
import { useWorkspace } from "./WorkspaceContext";

type NoticePage = {
  notices: DeskNotice[];
  total?: number;
  next?: string | null;
};
const empty = {
  loaded: false,
  notices: [] as DeskNotice[],
  total: 0,
  next: null as string | null,
};
export function useDeskInbox(
  enabled: boolean,
  revision: number | undefined,
  expanded: boolean,
  language: Language,
) {
  const { data } = useWorkspace();
  const owner = enabled && data?.principal.kind === "owner";
  const scope = owner
    ? JSON.stringify([data.principal.id, data.personal_context_visible])
    : "";
  const [page, setPage] = useState({ ...empty, scope: "" });
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const epoch = useRef(0);
  const previous = useRef<DeskNotice[] | null>(null);
  const activeScope = useRef(scope);
  activeScope.current = scope;
  const pending = useRef(false);
  const locale = useRef(language);
  locale.current = language;
  const refresh = useCallback(
    async (before?: string) => {
      if (!scope) return;
      const sequence = ++epoch.current;
      try {
        const result = await request<NoticePage>(
          "/notices?open_only=true" +
            (before ? "&before=" + encodeURIComponent(before) : ""),
        );
        if (sequence !== epoch.current) return;
        const items = openNotices(result.notices);
        const fresh = before ? [] : newlyArrived(previous.current, items);
        if (!before) previous.current = items;
        setPage((old) => ({
          scope,
          loaded: true,
          total: result.total ?? items.length,
          next: result.next ?? null,
          notices: before ? openNotices([...old.notices, ...items]) : items,
        }));
        setError(null);
        if (
          fresh.length &&
          typeof Notification !== "undefined" &&
          Notification.permission === "granted"
        ) {
          try {
            const worker = await navigator.serviceWorker?.getRegistration();
            const subscription = await worker?.pushManager?.getSubscription();
            if (subscription || sequence !== epoch.current) return;
            for (const item of fresh)
              showBrowserNotice(item, locale.current, {
                permission: Notification.permission,
                show: (title, options) => {
                  new Notification(title, options);
                },
              });
          } catch {
            /* The OS can reject a foreground alert. Its inbox entry is already available. */
          }
        }
      } catch (cause) {
        if (sequence === epoch.current) setError(cause);
      }
    },
    [scope],
  );
  useEffect(() => {
    previous.current = null;
    setPage({ ...empty, scope });
    setError(null);
    return () => {
      epoch.current++;
    };
  }, [scope]);
  // The existing workspace revision refreshes the badge. Keep the reader's place while the inbox is open.
  const watch = expanded ? undefined : revision;
  useEffect(() => {
    void refresh();
  }, [refresh, watch, expanded]);
  const run = async (action: () => Promise<void>) => {
    if (pending.current || !scope) return;
    pending.current = true;
    setBusy(true);
    try {
      await action();
    } catch (cause) {
      if (activeScope.current === scope) setError(cause);
    } finally {
      pending.current = false;
      setBusy(false);
    }
  };
  const visible = scope && page.scope === scope ? page : empty;
  return {
    ...visible,
    enabled: !!scope,
    error: scope ? error : null,
    busy,
    refresh: () => refresh(),
    more: () => visible.next && run(() => refresh(visible.next!)),
    dismiss: (id: string) =>
      run(async () => {
        await write("/notices/" + encodeURIComponent(id) + "/dismissals", {});
        if (activeScope.current !== scope) return;
        epoch.current++;
        setError(null);
        // Keep any older pages and their cursor when one item is handled.
        setPage((old) =>
          old.scope === scope && old.notices.some((item) => item.id === id)
            ? {
                ...old,
                total: Math.max(0, old.total - 1),
                notices: old.notices.filter((item) => item.id !== id),
              }
            : old,
        );
      }),
  };
}
export type DeskInbox = ReturnType<typeof useDeskInbox>;
