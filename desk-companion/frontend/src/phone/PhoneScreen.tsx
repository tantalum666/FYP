import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  ArrowLeft,
  CalendarDays,
  Inbox,
  LayoutGrid,
  ListTodo,
} from "lucide-react";
import {
  GuardContextProvider,
  useGuardRegistry,
} from "../components/DraftGuard";
import type { Translate } from "../types";

/** A phone navigation surface, with the same draft guard used by shared editors. */
export function PhoneScreen({
  title,
  backLabel,
  onBack,
  t,
  children,
  footer,
  onReminders,
  notificationCount,
  currentTab,
  onTab,
}: {
  title: string;
  backLabel: string;
  onBack: () => void;
  t: Translate;
  children: ReactNode;
  footer?: ReactNode;
  onReminders: (canNavigate: boolean) => void;
  notificationCount: number;
  currentTab: "calendar" | "tasks" | "more";
  onTab: (tab: "calendar" | "tasks" | "more") => void;
}) {
  const guard = useGuardRegistry();
  const [leaving, setLeaving] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const id = useId();
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    heading.current?.focus();
    return () => {
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  const back = () => {
    if (guard.busy) return;
    if (guard.dirty) setLeaving(true);
    else onBack();
  };
  return (
    <section className="phone-screen workspace-surface" aria-labelledby={id}>
      <header className="phone-screen-header">
        <button
          className="icon-button"
          aria-label={backLabel}
          disabled={guard.busy}
          onClick={back}
        >
          <ArrowLeft size={21} />
        </button>
        <h1 ref={heading} tabIndex={-1} id={id}>
          {title}
        </h1>
      </header>
      <GuardContextProvider value={guard}>
        <div className="phone-screen-content">
          {leaving && (
            <div className="phone-leave-prompt" role="alert">
              <h2>{t("Keep your changes?", "保留当前修改吗？")}</h2>
              <p>
                {t(
                  "Continue editing, or leave without saving.",
                  "你可以继续编辑，或放弃未保存的修改后返回。",
                )}
              </p>
              <div className="workspace-inline-actions">
                <button className="primary" onClick={() => setLeaving(false)}>
                  {t("Continue editing", "继续编辑")}
                </button>
                <button className="secondary" onClick={onBack}>
                  {t("Discard and go back", "放弃并返回")}
                </button>
              </div>
            </div>
          )}
          <div hidden={leaving}>{children}</div>
        </div>
      </GuardContextProvider>
      {footer && <div className="phone-screen-footer">{footer}</div>}
      <nav
        className="phone-work-tabs"
        aria-label={t("Workspace tabs", "工作空间分页")}
      >
        {(
          [
            { id: "calendar", name: t("Calendar", "日历"), Icon: CalendarDays },
            { id: "tasks", name: t("Tasks", "待办"), Icon: ListTodo },
            { id: "inbox", name: t("Inbox", "通知"), Icon: Inbox },
            { id: "more", name: t("More", "更多"), Icon: LayoutGrid },
          ] as const
        ).map(({ id, name, Icon }) => (
          <button
            key={id}
            type="button"
            disabled={
              guard.busy || (guard.dirty && id !== currentTab && id !== "inbox")
            }
            aria-label={name}
            aria-current={id === currentTab ? "page" : undefined}
            onClick={() =>
              id === "inbox"
                ? onReminders(!guard.dirty && !guard.busy)
                : onTab(id)
            }
          >
            <span className="dock-icon">
              <Icon size={18} />
              {id === "inbox" && notificationCount > 0 && (
                <small>{notificationCount}</small>
              )}
            </span>
            <span>{name}</span>
          </button>
        ))}
      </nav>
    </section>
  );
}
