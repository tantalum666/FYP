import { useEffect, useState } from "react";
import { isNative, native } from "../native";
import type { PhoneStatus } from "../native";
import { request } from "../api";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";

export async function syncPhone() {
  const snapshot = await request<Record<string, unknown>>("/phone/snapshot");
  return native.syncPhone({
    snapshot: {
      ...snapshot,
      language: localStorage.getItem("desk.language") === "zh" ? "zh" : "en",
    },
  });
}
export function PhoneSync() {
  const { data } = useWorkspace();
  const identity = data?.principal.id;
  useEffect(() => {
    if (!isNative || !identity) return;
    let busy = false;
    const tick = async () => {
      if (busy || document.hidden) return;
      busy = true;
      try {
        await syncPhone();
      } catch {
        /* Cached snapshot expires locally. */
      } finally {
        busy = false;
      }
    };
    void tick();
    const timer = setInterval(() => void tick(), 60000);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [identity]);
  return null;
}
export function PhoneFeatures({ t }: { t: Translate }) {
  const [status, setStatus] = useState<PhoneStatus | null>(null),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  useEffect(() => {
    if (isNative) void native.phoneStatus().then(setStatus);
  }, []);
  if (!isNative) return null;
  return (
    <section className="settings-section">
      <h2>{t("On this iPhone", "在这台iPhone上")}</h2>
      <div className="setting-row">
        <div>
          <strong>{t("Calendar notifications", "日程通知")}</strong>
          <small>
            {status?.enabled
              ? t(
                  `${status.scheduled} cached reminders`,
                  `${status.scheduled}条缓存提醒`,
                )
              : t("Not enabled", "未启用")}
          </small>
        </div>
        <button
          className="secondary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setNotice("");
            try {
              let next = await native.enableNotifications({
                enabled: !status?.enabled,
              });
              if (next.enabled) next = await syncPhone();
              setStatus(next);
              if (next.permission === "denied")
                setNotice(
                  t(
                    "Notifications are disabled in iPhone Settings.",
                    "iPhone系统设置中未允许通知。",
                  ),
                );
            } catch {
              setNotice(t("Could not update notifications.", "未能更新通知。"));
            } finally {
              setBusy(false);
            }
          }}
        >
          {status?.enabled ? t("Turn off", "关闭") : t("Enable", "启用")}
        </button>
      </div>
      <p className="footnote">
        {t(
          "Up to 64 reminders for the next seven days are cached on this phone. Reopen the app to refresh after remote edits; offline reminders may be out of date.",
          "手机缓存未来七天内最多64条提醒。其他终端修改后请重新打开App同步，离线提醒可能不是最新安排。",
        )}
      </p>
      <div className="setting-row">
        <div>
          <strong>{t("Calendar widget", "日历小组件")}</strong>
          <small>
            {status?.widgetAvailable
              ? t(
                  "Available in the Home Screen widget gallery",
                  "可在主屏幕的小组件库中添加",
                )
              : t("Not available in this build", "当前构建不可用")}
          </small>
        </div>
        <button
          className="text-button"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              setStatus(await syncPhone());
              setNotice(t("Phone snapshot refreshed.", "已刷新手机摘要。"));
            } catch {
              setNotice(
                t(
                  "Reconnect to your desk to refresh.",
                  "请重新连接桌面主机后刷新。",
                ),
              );
            } finally {
              setBusy(false);
            }
          }}
        >
          {t("Refresh", "刷新")}
        </button>
      </div>
      <p className="footnote">
        {t(
          "Private titles stay hidden. The widget asks you to refresh when its snapshot is older than 20 minutes.",
          "私人标题始终隐藏，摘要超过20分钟后，小组件会提示刷新。",
        )}
      </p>
      {notice && <p role="status">{notice}</p>}
    </section>
  );
}
