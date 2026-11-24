import type { ReactNode } from "react";
import {
  Activity,
  BookOpen,
  CalendarDays,
  Globe,
  Inbox,
  ListTodo,
  MessagesSquare,
  NotebookText,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  SlidersHorizontal,
  Sparkles,
  Sun,
  X,
} from "lucide-react";
import type { Language, Page, Translate } from "../types";

export const destinations = [
  { id: "assistant", en: "Chat", zh: "对话", Icon: MessagesSquare },
  { id: "today", en: "Today", zh: "今天", Icon: Sun },
  { id: "tasks", en: "Tasks", zh: "待办", Icon: ListTodo },
  { id: "calendar", en: "Calendar", zh: "日历", Icon: CalendarDays },
  { id: "inbox", en: "Inbox", zh: "通知中心", Icon: Inbox },
  { id: "memory", en: "Saved memories", zh: "已保存记忆", Icon: BookOpen },
  {
    id: "persona",
    en: "Assistant style",
    zh: "助理风格",
    Icon: SlidersHorizontal,
  },
  { id: "records", en: "Records", zh: "记录", Icon: NotebookText },
  { id: "device", en: "Settings", zh: "设置", Icon: Settings },
  { id: "diagnostics", en: "Diagnostics", zh: "诊断", Icon: Activity },
] as const;

export function WorkspaceNav({
  page,
  visible,
  drawer,
  collapsed,
  onCollapse,
  count,
  connection,
  showDiagnostics,
  language,
  onLanguage,
  onPage,
  onClose,
  children,
  t,
}: {
  page: Page;
  visible: boolean;
  drawer: boolean;
  collapsed: boolean;
  onCollapse: () => void;
  count: number;
  connection: "connecting" | "online" | "offline";
  showDiagnostics: boolean;
  language: Language;
  onLanguage: (language: Language) => void;
  onPage: (page: Page) => void;
  onClose: () => void;
  children: ReactNode;
  t: Translate;
}) {
  function link(item: (typeof destinations)[number]) {
    if (item.id === "diagnostics" && !showDiagnostics) return null;
    const name = t(item.en, item.zh);
    return (
      <button
        type="button"
        key={item.id}
        title={name}
        aria-label={name}
        aria-current={page === item.id ? "page" : undefined}
        className={page === item.id ? "selected" : undefined}
        onClick={() => onPage(item.id)}
      >
        <item.Icon size={18} />
        <span className="nav-label">{name}</span>
        {item.id === "inbox" && count > 0 && (
          <span className="nav-count">{count}</span>
        )}
      </button>
    );
  }
  return (
    <aside
      className="sidebar workspace-sidebar"
      id="workspace-navigation"
      inert={!visible}
      aria-label={t("Workspace navigation", "工作空间导航")}
      onKeyDown={(event) => {
        if (!drawer || event.key !== "Tab") return;
        const nodes = Array.from(
          event.currentTarget.querySelectorAll<HTMLElement>(
            "button,select,summary,input",
          ),
        ).filter(
          (el) => el.getClientRects().length && !el.matches(":disabled"),
        );
        const first = nodes[0],
          last = nodes.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }}
    >
      <div className="workspace-brand-row">
        <button
          className="workspace-brand"
          title={t("Back to Alice", "返回 Alice")}
          aria-label={t("Back to Alice", "返回 Alice")}
          onClick={() => onPage("assistant")}
        >
          <span className="workspace-brand-mark">
            <Sparkles size={18} />
          </span>
          <span className="nav-label">Alice</span>
        </button>
        {drawer ? (
          <button
            className="workspace-nav-close"
            aria-label={t("Close navigation", "关闭导航")}
            onClick={onClose}
          >
            <X size={16} />
          </button>
        ) : (
          <button
            className="nav-collapse"
            aria-label={
              collapsed
                ? t("Expand sidebar", "展开侧栏")
                : t("Collapse sidebar", "收起侧栏")
            }
            onClick={onCollapse}
          >
            {collapsed ? (
              <PanelLeftOpen size={16} />
            ) : (
              <PanelLeftClose size={16} />
            )}
          </button>
        )}
      </div>
      <div className="sidebar-scroll">
        <nav aria-label={t("Main navigation", "主导航")}>
          <div className="nav-section">
            {destinations.slice(0, 5).map(link)}
          </div>
          <div className="nav-section">
            {destinations.slice(5, 8).map(link)}
          </div>
        </nav>
        {children}
      </div>
      <footer className="sidebar-footer">
        <div
          className={`rail-connection ${connection}`}
          role="status"
          title={
            connection === "online"
              ? t("Desk connected", "已连接桌面")
              : t("Desk connection", "桌面连接")
          }
        >
          <i aria-hidden="true" />
          <span className="nav-label">
            {connection === "online"
              ? t("Desk connected", "已连接桌面")
              : connection === "offline"
                ? t("Desk offline", "桌面已离线")
                : t("Connecting…", "正在连接…")}
          </span>
        </div>
        <nav aria-label={t("Workspace settings", "工作空间设置")}>
          {destinations.slice(8).map(link)}
        </nav>
        <label className="nav-language">
          <Globe size={15} />
          <select
            aria-label={t("Language", "语言")}
            value={language}
            onChange={(e) => onLanguage(e.target.value as Language)}
          >
            <option value="en">English</option>
            <option value="zh">简体中文</option>
          </select>
        </label>
      </footer>
    </aside>
  );
}
