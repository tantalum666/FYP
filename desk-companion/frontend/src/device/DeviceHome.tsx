import { useState } from "react";
import type { DateTime } from "luxon";
import { CalendarDays, MoreHorizontal, RefreshCw } from "lucide-react";
import { A1Canvas } from "../companion/A1Canvas";
import { useSceneActivity } from "../companion/useSceneActivity";
import { ConversationWorkspace } from "../workspace/ConversationWorkspace";
import type { Language, Translate } from "../types";
import "./device-home.css";

export function DeviceHome({
  t,
  language,
  now,
  connection,
  voiceState,
  obscured,
  onCalendar,
  onMore,
  onReconnect,
  onConversationState,
  task,
  onClearTask,
}: {
  t: Translate;
  language: Language;
  now: DateTime;
  connection: "online" | "offline" | "connecting";
  voiceState: string;
  obscured: boolean;
  onCalendar: () => void;
  onMore: () => void;
  onReconnect: () => void;
  onConversationState: (value: { dirty: boolean; busy: boolean }) => void;
  task?: { id: string; title: string };
  onClearTask: () => void;
}) {
  const scene = useSceneActivity();
  const [renderFailed, setRenderFailed] = useState(false);
  // The assistant's own media/review dialogs must remain usable. Only external
  // navigation suspends the conversation; every modal can pause the avatar.
  const suspended = obscured || !scene.visible;
  return (
    <main className="device-home" aria-label={t("Alice desk", "Alice 桌面")}>
      <header className="device-home-header" inert={obscured}>
        <div className="device-home-identity">
          <strong>Alice</strong>
          <span
            role="status"
            className={`device-home-connection ${connection}`}
          >
            <i />
            {connection === "online"
              ? t("Desk connected", "已连接桌面")
              : connection === "offline"
                ? t("Desk offline", "桌面离线")
                : t("Connecting…", "正在连接…")}
          </span>
        </div>
        <time dateTime={now.toISO() ?? undefined} className="device-home-clock">
          <strong>{now.toFormat("HH:mm")}</strong>
          <span>
            {now
              .setLocale(language === "zh" ? "zh-CN" : "en-GB")
              .toFormat(language === "zh" ? "M月d日 ccc" : "ccc, d MMM")}
          </span>
        </time>
        <nav aria-label={t("Desk navigation", "桌面导航")}>
          <button onClick={onCalendar}>
            <CalendarDays size={20} />
            <span>{t("Calendar", "日历")}</span>
          </button>
          <button onClick={onMore}>
            <MoreHorizontal size={22} />
            <span>{t("More", "更多")}</span>
          </button>
        </nav>
      </header>
      <div className="device-home-content">
        <section className="device-alice-stage" inert={obscured}>
          <div
            className="device-alice-visual"
            aria-label={t("Alice, your desk companion", "Alice，你的桌面伙伴")}
            role="img"
          >
            {renderFailed || !scene.motion ? (
              <img src="/avatars/alice/phone-fallback.jpg" alt="" />
            ) : (
              <A1Canvas
                active={!suspended && !scene.blocked}
                state={voiceState}
                framing="face"
                onError={() => setRenderFailed(true)}
              />
            )}
          </div>
          <a
            className="device-alice-credit"
            href="https://github.com/yuna0x0/AliceChan"
            target="_blank"
            rel="noreferrer"
          >
            AliceChan · yuna0x0 · CC BY-SA 4.0
          </a>
        </section>
        <section className="device-home-chat" inert={obscured}>
          {connection === "offline" && (
            <div className="device-home-reconnect" role="status">
              <span>{t("Connection interrupted", "连接暂时中断")}</span>
              <button onClick={onReconnect}>
                <RefreshCw size={16} />
                {t("Reconnect", "重新连接")}
              </button>
            </div>
          )}
          <ConversationWorkspace
            visible
            suspended={suspended}
            t={t}
            onStateChange={onConversationState}
            taskId={task?.id}
            taskTitle={task?.title}
            onClearTask={onClearTask}
          />
        </section>
      </div>
    </main>
  );
}
