import { useEffect, useId, useRef } from "react";
import type { RefObject } from "react";
import { CalendarDays, Globe, Paperclip } from "lucide-react";
import type { Translate } from "../types";

export function ComposerMenu({
  onFiles,
  onBrowser,
  onBriefing,
  onClose,
  trigger,
  filesEnabled,
  t,
}: {
  onFiles: () => void;
  onBrowser: () => void;
  onBriefing: () => void;
  onClose: () => void;
  trigger: RefObject<HTMLButtonElement | null>;
  filesEnabled: boolean;
  t: Translate;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const id = useId();
  useEffect(() => {
    panel.current
      ?.querySelector<HTMLButtonElement>("button:not(:disabled)")
      ?.focus();
    const dismiss = (event: PointerEvent) => {
      if (
        !panel.current?.contains(event.target as Node) &&
        !trigger.current?.contains(event.target as Node)
      )
        onClose();
    };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, [onClose, trigger]);
  return (
    <div
      className="composer-menu"
      id={id}
      role="menu"
      ref={panel}
      aria-label={t("Add to your message", "添加到消息")}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.preventDefault();
          event.stopPropagation();
          onClose();
          trigger.current?.focus();
        }
        if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
          event.preventDefault();
          const buttons = Array.from(
            panel.current?.querySelectorAll<HTMLButtonElement>(
              "button:not(:disabled)",
            ) ?? [],
          );
          const index = buttons.indexOf(
            document.activeElement as HTMLButtonElement,
          );
          buttons[
            event.key === "Home"
              ? 0
              : event.key === "End"
                ? buttons.length - 1
                : (index +
                    (event.key === "ArrowUp" ? -1 : 1) +
                    buttons.length) %
                  buttons.length
          ]?.focus();
        }
        if (event.key === "Tab") onClose();
      }}
    >
      <button
        type="button"
        role="menuitem"
        disabled={!filesEnabled}
        onClick={onFiles}
        title={
          filesEnabled
            ? t(
                "PDF, Office documents, text and images · 2 MB each, 4 per chat",
                "PDF、Office文档、文本和图片 · 每个2MB，每段对话4个",
              )
            : t(
                "File reading is unavailable on this connection",
                "当前连接暂不支持读取附件",
              )
        }
      >
        <Paperclip size={18} />
        {t("Add files or photos", "添加文件或照片")}
      </button>
      <button type="button" role="menuitem" onClick={onBrowser}>
        <Globe size={18} />
        {t("Browse the web", "浏览网页")}
      </button>
      <button type="button" role="menuitem" onClick={onBriefing}>
        <CalendarDays size={18} />
        {t("Today’s briefing", "今日简报")}
      </button>
    </div>
  );
}
