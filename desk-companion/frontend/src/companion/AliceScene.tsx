import { useState } from "react";
import { CalendarDays, MoreHorizontal } from "lucide-react";
import { A1Canvas } from "./A1Canvas";
import type { Translate } from "../types";

/** One licensed avatar and navigation treatment for all three home surfaces. */
export function AliceScene({
  t,
  active,
  motion,
  voiceState,
  listening = false,
  obscured,
  connection,
  onPlan,
  onMore,
  onReconnect,
}: {
  t: Translate;
  active: boolean;
  motion: boolean;
  voiceState: string;
  listening?: boolean;
  obscured: boolean;
  connection: "online" | "offline" | "connecting";
  onPlan: () => void;
  onMore: () => void;
  onReconnect?: () => void;
}) {
  const [failed, setFailed] = useState(false);
  return (
    <>
      <div
        className="alice-scene"
        role="img"
        aria-hidden={obscured}
        aria-label={t("Alice, your desk companion", "Alice，你的桌面伙伴")}
      >
        {failed || !motion ? (
          <img src="/avatars/alice/phone-fallback.jpg" alt="" />
        ) : (
          <A1Canvas
            active={active}
            state={voiceState}
            onError={() => setFailed(true)}
          />
        )}
      </div>
      <div className="alice-scene-shade" />
      <header className="alice-home-header" inert={obscured}>
        <div className="alice-home-identity">
          <strong>Alice</strong>
          <span role="status">
            <i className={connection} />
            {connection === "online"
              ? listening
                ? t("Listening for Alice", "等待你叫 Alice")
                : t("Desk connected", "已连接桌面")
              : connection === "offline"
                ? t("Desk offline", "桌面离线")
                : t("Connecting…", "正在连接…")}
          </span>
          {connection === "offline" && onReconnect && (
            <button className="alice-reconnect" onClick={onReconnect}>
              {t("Reconnect", "重新连接")}
            </button>
          )}
        </div>
        <nav aria-label={t("Home navigation", "首页导航")}>
          <button onClick={onPlan}>
            <CalendarDays size={20} />
            <span>{t("Plan", "计划")}</span>
          </button>
          <button className="alice-more-button" onClick={onMore}>
            <MoreHorizontal size={22} />
            <span>{t("More", "更多")}</span>
          </button>
        </nav>
      </header>
    </>
  );
}
