import {
  Bell,
  Brain,
  ChevronRight,
  FileText,
  RefreshCw,
  Settings,
  Sparkles,
} from "lucide-react";
import type {
  Language,
  Settings as WorkspaceSettings,
  Translate,
} from "../types";
import { useDraftState } from "../components/DraftGuard";
import { DeviceView, RecordsView } from "../components/Views";
import { MemoryPanel } from "../workspace/MemoryPanel";
import { PersonaPanel } from "../workspace/PersonaPanel";
import { DataPanel } from "../workspace/DataPanel";
import { ExtrasPanel } from "../workspace/ExtrasPanel";
import { PosturePanel } from "../workspace/PosturePanel";
import { ConnectionsPanel } from "../workspace/ConnectionsPanel";

export type PhonePanel =
  | "plan"
  | "more"
  | "memory"
  | "persona"
  | "records"
  | "device"
  | "data"
  | "posture"
  | "connections"
  | "extras";
export const phoneHeadings = (t: Translate): Record<PhonePanel, string> => ({
  plan: t("Calendar & tasks", "日历与事务"),
  more: t("Your workspace", "你的工作空间"),
  memory: t("Saved memories", "已保存记忆"),
  persona: t("Assistant style", "助理风格"),
  records: t("Activity", "活动记录"),
  device: t("Settings", "设置"),
  data: t("Import & share", "导入与分享"),
  posture: t("Posture & feedback", "坐姿与反馈"),
  connections: t("Connections", "连接"),
  extras: t("Calendar preferences", "日历偏好"),
});

export function PhoneMore({
  t,
  language,
  setLanguage,
  onNavigate,
  onConversation,
  onReminders,
}: {
  t: Translate;
  language: Language;
  setLanguage: (value: Language) => void;
  onNavigate: (panel: PhonePanel) => void;
  onConversation: () => void;
  onReminders: () => void;
}) {
  const headings = phoneHeadings(t);
  return (
    <div className="phone-more-list">
      <p>{t("Conversation & you", "对话与你")}</p>
      <button onClick={onConversation}>
        <Sparkles />
        <span>{t("This conversation", "本次对话")}</span>
        <ChevronRight />
      </button>
      {(
        [
          ["memory", Brain],
          ["persona", Sparkles],
        ] as const
      ).map(([key, Icon]) => (
        <button key={key} onClick={() => onNavigate(key)}>
          <Icon />
          <span>{headings[key]}</span>
          <ChevronRight />
        </button>
      ))}
      <p>{t("Your desk", "你的桌面")}</p>
      <button onClick={onReminders}>
        <Bell />
        <span>{t("Reminders", "提醒")}</span>
        <ChevronRight />
      </button>
      {(
        [
          ["connections", RefreshCw],
          ["records", FileText],
          ["device", Settings],
        ] as const
      ).map(([key, Icon]) => (
        <button key={key} onClick={() => onNavigate(key)}>
          <Icon />
          <span>{headings[key]}</span>
          <ChevronRight />
        </button>
      ))}
      <label className="phone-language">
        {t("Language", "语言")}
        <select
          aria-label="Language"
          value={language}
          onChange={(e) => setLanguage(e.target.value as Language)}
        >
          <option value="en">English</option>
          <option value="zh">简体中文</option>
        </select>
      </label>
      <p className="phone-credits">
        AliceChan · edisonlee55 / yuna0x0
        <br />
        <a
          href="https://github.com/yuna0x0/AliceChan"
          target="_blank"
          rel="noreferrer"
        >
          {t("CC BY-SA 4.0 · Source", "CC BY-SA 4.0 · 来源")}
        </a>
      </p>
    </div>
  );
}

export function PhoneManagement({
  panel,
  t,
  language,
  setLanguage,
  settings,
  revision,
  onNavigate,
  onConversation,
  onRefresh,
  onNotice,
}: {
  panel: Exclude<PhonePanel, "plan" | "more">;
  t: Translate;
  language: Language;
  setLanguage: (value: Language) => void;
  settings: WorkspaceSettings;
  revision: number;
  onNavigate: (panel: PhonePanel) => void;
  onConversation: () => void;
  onRefresh: () => void;
  onNotice: (message: string) => void;
}) {
  const guard = useDraftState();
  return (
    <>
      {panel === "memory" && <MemoryPanel t={t} />}
      {panel === "persona" && <PersonaPanel t={t} />}
      {panel === "records" && (
        <RecordsView
          revision={revision}
          zone={settings.timezone}
          language={language}
          t={t}
        />
      )}
      {panel === "device" && (
        <DeviceView
          settings={settings}
          language={language}
          setLanguage={setLanguage}
          onSaved={onRefresh}
          onDeviceLayout={() =>
            onNotice(
              t(
                "The desk display opens on your host computer.",
                "常亮屏布局请在桌面主机打开。",
              ),
            )
          }
          onOpenWorkspace={(value) => {
            if (guard.dirty || guard.busy) {
              onNotice(
                t(
                  "Save or cancel your current changes first.",
                  "请先保存或取消当前修改。",
                ),
              );
              return;
            }
            if (value === "assistant") onConversation();
            else onNavigate(value);
          }}
          t={t}
        />
      )}
      {panel === "connections" && <ConnectionsPanel t={t} />}
      {panel === "posture" && <PosturePanel t={t} />}
      {panel === "extras" && <ExtrasPanel t={t} />}
      {panel === "data" && <DataPanel t={t} />}
    </>
  );
}
