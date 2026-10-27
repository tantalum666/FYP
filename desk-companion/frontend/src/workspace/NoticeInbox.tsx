import { useCallback, useEffect, useState } from "react";
import { errorText, request, write } from "../api";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import { openNotices, showBrowserNotice, type DeskNotice } from "./notices";

export function NoticeInbox({
  t,
  language,
}: {
  t: Translate;
  language: "en" | "zh";
}) {
  const { data } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [notices, setNotices] = useState<DeskNotice[]>([]);
  const [error, setError] = useState<unknown>(null);
  const reload = useCallback(async () => {
    if (!owner) return;
    const next = await request<{ notices: DeskNotice[] }>("/notices");
    setNotices(next.notices);
    for (const notice of openNotices(next.notices)) {
      showBrowserNotice(
        notice,
        language,
        typeof Notification === "undefined"
          ? undefined
          : {
              permission: Notification.permission,
              show: (title, options) => {
                new Notification(title, options);
              },
            },
      );
    }
  }, [language, owner]);
  useEffect(() => {
    void reload().catch((reason) => setError(reason));
  }, [reload]);
  if (!owner) return null;
  const open = openNotices(notices);
  if (!open.length && !error) return null;
  return (
    <div className="connection-banner" role="status">
      {open.map((notice) => (
        <p key={notice.id}>
          {t(notice.title_en, notice.title_zh)}
          {". "}
          {t(notice.reason_en, notice.reason_zh)}
          <button
            type="button"
            onClick={() =>
              void write(`/notices/${notice.id}/dismissals`, {})
                .then(() => reload())
                .catch((reason) => setError(reason))
            }
          >
            {t("Dismiss", "知道了")}
          </button>
        </p>
      ))}
      {!!error && <p role="alert">{errorText(error, t)}</p>}
    </div>
  );
}
