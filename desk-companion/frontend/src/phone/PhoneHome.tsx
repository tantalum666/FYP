import { useState } from "react";
import { DateTime } from "luxon";
import { CalendarDays, ChevronRight, MoreHorizontal } from "lucide-react";
import { A1Canvas } from "../companion/A1Canvas";
import { locale, title } from "../dates";
import type { Language, Occurrence, Translate } from "../types";

export function PhoneHome({
  t,
  active,
  motion,
  voiceState,
  obscured,
  connection,
  onPlan,
  onMore,
}: {
  t: Translate;
  active: boolean;
  motion: boolean;
  voiceState: string;
  obscured: boolean;
  connection: "online" | "offline" | "connecting";
  onPlan: () => void;
  onMore: () => void;
}) {
  const [renderFailed, setRenderFailed] = useState(false);
  return (
    <>
      <div
        className="phone-scene"
        aria-hidden={obscured}
        aria-label={t("Alice, your desk companion", "Alice，你的桌面伙伴")}
        role="img"
      >
        {renderFailed || !motion ? (
          <img src="/avatars/alice/phone-fallback.jpg" alt="" />
        ) : (
          <A1Canvas
            active={active}
            state={voiceState}
            onError={() => setRenderFailed(true)}
          />
        )}
      </div>
      <div className="phone-scene-shade" />
      <header className="phone-header" inert={obscured}>
        <div className="phone-identity">
          <strong>
            Alice<span>Desk Companion</span>
          </strong>
          <p role="status">
            <i className={connection !== "online" ? "offline" : ""} />
            {connection === "offline"
              ? t("Desk offline", "桌面离线")
              : connection === "online"
                ? t("Desk connected", "已连接桌面")
                : t("Connecting…", "正在连接…")}
          </p>
        </div>
        <nav aria-label={t("Phone navigation", "手机导航")}>
          <button onClick={() => onPlan()}>
            <CalendarDays size={20} />
            <span>{t("Plan", "计划")}</span>
          </button>
          <button onClick={() => onMore()}>
            <MoreHorizontal size={22} />
            <span>{t("More", "更多")}</span>
          </button>
        </nav>
      </header>
    </>
  );
}

export function UpcomingHint({
  next,
  today,
  zone,
  language,
  t,
  onOpen,
}: {
  next?: Occurrence;
  today: DateTime;
  zone: string;
  language: Language;
  t: Translate;
  onOpen: (event: Occurrence) => void;
}) {
  return (
    <div className="phone-day-hint">
      <span>
        {today
          .setLocale(locale(language))
          .toFormat(language === "zh" ? "M月d日 EEEE" : "EEEE, d MMM")}
      </span>
      {next && (
        <button onClick={() => onOpen(next)}>
          <span>
            {t("Coming up", "接下来")} ·{" "}
            {DateTime.fromISO(next.start)
              .setZone(zone)
              .setLocale(locale(language))
              .toFormat("ccc HH:mm")}
          </span>
          <strong>{title(next, language)}</strong>
          <ChevronRight size={18} />
        </button>
      )}
    </div>
  );
}
