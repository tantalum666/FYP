import { useEffect, useId, useRef, useState } from "react";
import {
  GuardContextProvider,
  useGuardRegistry,
  useDraftGuard,
} from "./DraftGuard";
import type { ReactNode } from "react";
import { DateTime } from "luxon";
import {
  Bell,
  Check,
  CircleAlert,
  LockKeyhole,
  MapPin,
  Pencil,
  Repeat2,
  Trash2,
  X,
} from "lucide-react";
import { errorText, pendingWrite, write } from "../api";
import { eventTime, inZone, locale, title } from "../dates";
import { editable } from "../types";
import type {
  EventColor,
  EventInput,
  Frequency,
  Language,
  Occurrence,
  Reminder,
  Translate,
} from "../types";

export function Modal({
  title: heading,
  onClose,
  children,
  wide = false,
  busy = false,
  closeLabel,
  dirty = false,
  docked = false,
  className = "",
  footer,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
  busy?: boolean;
  closeLabel: string;
  dirty?: boolean;
  docked?: boolean;
  className?: string;
  footer?: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const guard = useGuardRegistry();
  const [discard, setDiscard] = useState(false);
  const locked = busy || guard.busy;
  const zh = document.documentElement.lang.startsWith("zh");
  const focusField = () => {
    Array.from(
      ref.current?.querySelectorAll<HTMLElement>(
        "[data-initial-focus], input[required]:not([type=checkbox]), textarea",
      ) ?? [],
    )
      .find((field) => field.getClientRects().length > 0)
      ?.focus();
  };
  const close = () => {
    if (locked) return;
    if (dirty || guard.dirty) setDiscard(true);
    else onClose();
  };
  useEffect(() => {
    const dialog = ref.current!;
    const previous = document.activeElement as HTMLElement | null;
    if (docked) dialog.show();
    else dialog.showModal();
    window.dispatchEvent(new Event("desk:modal-state"));
    queueMicrotask(focusField);
    return () => {
      dialog.close();
      window.dispatchEvent(new Event("desk:modal-state"));
      if (previous?.isConnected) previous.focus();
    };
  }, [docked]);
  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      className={`dialog ${wide ? "wide" : ""} ${docked ? "docked" : ""} ${className}`}
      aria-modal={docked ? undefined : true}
      data-companion-blocking={docked ? "false" : "true"}
      onKeyDown={(event) => {
        if (
          docked &&
          event.key === "Escape" &&
          !event.nativeEvent.isComposing &&
          !event.defaultPrevented
        ) {
          event.preventDefault();
          close();
        }
      }}
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
    >
      <header className="dialog-header">
        <h2 id={titleId}>{heading}</h2>
        <button
          className="icon-button"
          disabled={locked}
          aria-label={closeLabel}
          onClick={close}
        >
          <X />
        </button>
      </header>
      <GuardContextProvider value={guard}>
        <div className="dialog-body">
          {discard && (
            <div className="discard-prompt" role="alert">
              <h3>{zh ? "放弃未保存的修改？" : "Discard unsaved changes?"}</h3>
              <p>
                {zh
                  ? "继续编辑可以保留当前输入。"
                  : "Continue editing to keep your current input."}
              </p>
              <div className="workspace-inline-actions">
                <button
                  autoFocus
                  className="primary"
                  onClick={() => {
                    setDiscard(false);
                    requestAnimationFrame(focusField);
                  }}
                >
                  {zh ? "继续编辑" : "Continue editing"}
                </button>
                <button className="secondary" onClick={onClose}>
                  {zh ? "放弃修改" : "Discard edits"}
                </button>
              </div>
            </div>
          )}
          <div hidden={discard}>{children}</div>
        </div>
      </GuardContextProvider>
      {footer && <div className="dialog-footer">{footer}</div>}
    </dialog>
  );
}

export interface EditorState {
  initial: EventInput;
  id?: string;
  version?: number;
  occurrenceKey?: string;
  scope: "occurrence" | "series";
  repeating?: boolean;
}

export function EventEditor({
  state,
  onClose,
  onSaved,
  t,
  progressive = false,
}: {
  state: EditorState;
  onClose: () => void;
  onSaved: (event: EventInput) => void;
  t: Translate;
  progressive?: boolean;
}) {
  const formId = useId();
  const formRef = useRef<HTMLFormElement>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [form, setForm] = useState<EventInput>(() => editable(state.initial));
  const [dates, setDates] = useState<string[]>([]),
    [extraDate, setExtraDate] = useState("");
  const [saving, setSaving] = useState(false),
    [error, setError] = useState<unknown>(null);
  const dirty =
    JSON.stringify(form) !== JSON.stringify(editable(state.initial)) ||
    dates.length > 0 ||
    !!extraDate;
  useDraftGuard(dirty, saving);
  const [discard, setDiscard] = useState(false);
  const closeEditor = () => {
    if (saving) return;
    if (dirty && !pendingWrite()) setDiscard(true);
    else onClose();
  };
  const pending = pendingWrite();
  const locked = saving || !!pending;
  const update = <K extends keyof EventInput>(key: K, value: EventInput[K]) =>
    setForm((f) => ({ ...f, [key]: value }));
  const start = DateTime.fromISO(form.start_local),
    end = DateTime.fromISO(form.end_local);

  function changeStart(value: string) {
    const next = DateTime.fromISO(value);
    if (!next.isValid) return;
    const length = end.diff(start).as("minutes");
    setForm((f) => ({
      ...f,
      start_local: next.toFormat("yyyy-MM-dd'T'HH:mm"),
      end_local: next
        .plus({ minutes: length > 0 ? length : 60 })
        .toFormat("yyyy-MM-dd'T'HH:mm"),
    }));
  }
  function setAllDay(allDay: boolean) {
    const next = start.startOf("day");
    setForm((f) => ({
      ...f,
      all_day: allDay,
      start_local: (allDay ? next : next.set({ hour: 9 })).toFormat(
        "yyyy-MM-dd'T'HH:mm",
      ),
      end_local: (allDay
        ? next.plus({ days: 1 })
        : next.set({ hour: 10 })
      ).toFormat("yyyy-MM-dd'T'HH:mm"),
    }));
  }
  function addDate() {
    if (
      extraDate &&
      extraDate !== form.start_local.slice(0, 10) &&
      !dates.includes(extraDate) &&
      dates.length < 59
    ) {
      setDates([...dates, extraDate].sort());
      setExtraDate("");
    }
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (state.id)
        await write(`/events/${state.id}/actions`, {
          action: "update",
          expected_version: state.version,
          scope: state.scope,
          occurrence_key: state.occurrenceKey ?? null,
          event: form,
        });
      else await write("/events", { event: form, additional_dates: dates });
      onSaved(form);
    } catch (e) {
      setError(e);
    } finally {
      setSaving(false);
    }
  }
  const reminders: [
    [number, string, string],
    ...Array<[number, string, string]>,
  ] = [
    [0, "At event time", "到时"],
    [10, "10 min before", "提前10分钟"],
    [60, "1 hour before", "提前1小时"],
    [1440, "1 day before", "提前1天"],
    [10080, "1 week before", "提前1周"],
  ];
  const actions = (
    <footer className="dialog-actions">
      <button
        type="button"
        className="secondary"
        disabled={saving}
        onClick={closeEditor}
      >
        {t("Cancel", "取消")}
      </button>
      <button form={formId} type="submit" className="primary" disabled={saving}>
        {saving
          ? t("Saving…", "保存中…")
          : pending
            ? t("Retry save", "重试保存")
            : t("Save event", "保存日程")}
      </button>
    </footer>
  );
  return (
    <Modal
      title={
        state.id ? t("Edit event", "编辑日程") : t("New event", "新建日程")
      }
      onClose={closeEditor}
      closeLabel={t("Close", "关闭")}
      wide
      busy={saving}
      className={progressive ? "event-editor-dialog" : ""}
      footer={progressive && !discard ? actions : undefined}
    >
      {discard && (
        <div role="alert">
          <h3>{t("Discard unsaved changes?", "放弃未保存的修改？")}</h3>
          <div className="workspace-inline-actions">
            <button
              autoFocus
              className="primary"
              onClick={() => {
                setDiscard(false);
                requestAnimationFrame(() =>
                  formRef.current
                    ?.querySelector<HTMLElement>("[data-initial-focus]")
                    ?.focus(),
                );
              }}
            >
              {t("Continue editing", "继续编辑")}
            </button>
            <button className="secondary" onClick={onClose}>
              {t("Discard edits", "放弃修改")}
            </button>
          </div>
        </div>
      )}
      <form
        id={formId}
        ref={formRef}
        onSubmit={save}
        className="event-form"
        hidden={discard}
        onInvalid={(event) => {
          if ((event.target as HTMLElement).closest(".event-options"))
            setAdvancedOpen(true);
        }}
      >
        <fieldset disabled={locked}>
          <label className="field title-field">
            {t("Title", "标题")}
            <input
              autoFocus
              data-initial-focus
              required
              maxLength={160}
              value={form.title}
              placeholder={t("What are you planning?", "准备安排什么？")}
              onChange={(e) => update("title", e.target.value)}
            />
          </label>
          {state.id && state.repeating && (
            <p className="form-note">
              <Repeat2 size={14} />
              {state.scope === "series"
                ? t(
                    "Editing the series. Individual exceptions are kept.",
                    "正在编辑整个系列，单次例外会保留。",
                  )
                : t("Only this occurrence will change.", "只修改本次日程。")}
            </p>
          )}
          <label className="check-field">
            <input
              type="checkbox"
              checked={form.all_day}
              onChange={(e) => setAllDay(e.target.checked)}
            />
            {t("All day", "全天")}
          </label>
          <div className="form-grid">
            <label className="field">
              {t("Starts", "开始")}
              <input
                required
                type={form.all_day ? "date" : "datetime-local"}
                value={
                  form.all_day
                    ? form.start_local.slice(0, 10)
                    : form.start_local
                }
                onInput={(e) =>
                  changeStart(
                    form.all_day
                      ? e.currentTarget.value + "T00:00"
                      : e.currentTarget.value,
                  )
                }
              />
            </label>
            <label className="field">
              {t("Ends", "结束")}
              <input
                required
                type={form.all_day ? "date" : "datetime-local"}
                value={
                  form.all_day
                    ? end.minus({ days: 1 }).toISODate()!
                    : form.end_local
                }
                onInput={(e) =>
                  update(
                    "end_local",
                    form.all_day
                      ? DateTime.fromISO(e.currentTarget.value)
                          .plus({ days: 1 })
                          .toFormat("yyyy-MM-dd'T'00:00")
                      : e.currentTarget.value,
                  )
                }
              />
            </label>
          </div>
          {progressive && (
            <p className="form-note">
              {t("Times in ", "时间采用 ")}
              {form.timezone.replaceAll("_", " ")}
            </p>
          )}
          <details
            className="event-options"
            open={!progressive || advancedOpen}
            onToggle={(event) => {
              if (progressive) setAdvancedOpen(event.currentTarget.open);
            }}
          >
            <summary hidden={!progressive}>
              <span>{t("Details & reminders", "详情与提醒")}</span>
              <small>
                {form.calendar === "personal"
                  ? t("Personal", "个人")
                  : t("Study", "学习")}{" "}
                ·{" "}
                {form.visibility === "private"
                  ? t("Private", "私人")
                  : t("Displayable", "可展示")}
                <br />
                {form.reminder_minutes.length
                  ? reminders
                      .filter(([value]) =>
                        form.reminder_minutes.includes(value),
                      )
                      .map(([, en, zh]) => t(en, zh))
                      .join(" · ")
                  : t("No reminders", "无提醒")}
                {form.recurrence.frequency !== "none" &&
                  ` · ${t("Repeating", "重复日程")}`}
              </small>
            </summary>
            <div className="form-grid">
              <label className="field">
                {t("Timezone", "时区")}
                <select
                  value={form.timezone}
                  onChange={(e) => update("timezone", e.target.value)}
                >
                  {Array.from(
                    new Set([
                      form.timezone,
                      "Asia/Hong_Kong",
                      "Asia/Shanghai",
                      "Asia/Tokyo",
                      "Europe/London",
                      "America/New_York",
                      "UTC",
                    ]),
                  ).map((z) => (
                    <option key={z}>{z}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                {t("Calendar", "日历分类")}
                <select
                  value={form.calendar}
                  onChange={(e) =>
                    update("calendar", e.target.value as EventInput["calendar"])
                  }
                >
                  <option value="personal">{t("Personal", "个人")}</option>
                  <option value="study">{t("Study", "学习")}</option>
                </select>
              </label>
            </div>
            <label className="field">
              {t("Repeat", "重复")}
              <select
                disabled={
                  (!!state.id && state.scope === "occurrence") ||
                  dates.length > 0
                }
                value={form.recurrence.frequency}
                onChange={(e) =>
                  update("recurrence", {
                    frequency: e.target.value as Frequency,
                    interval: 1,
                    until: null,
                  })
                }
              >
                {(
                  [
                    "none",
                    "daily",
                    "weekly",
                    "monthly",
                    "yearly",
                  ] as Frequency[]
                ).map((v, i) => (
                  <option value={v} key={v}>
                    {t(
                      [
                        "Does not repeat",
                        "Daily",
                        "Weekly",
                        "Monthly",
                        "Yearly",
                      ][i],
                      ["不重复", "每日", "每周", "每月", "每年"][i],
                    )}
                  </option>
                ))}
              </select>
            </label>
            {form.recurrence.frequency !== "none" && (
              <>
                <div className="form-grid">
                  <label className="field">
                    {t("Repeat interval", "重复间隔")}
                    <input
                      type="number"
                      min={1}
                      max={52}
                      required
                      value={form.recurrence.interval}
                      onChange={(e) =>
                        update("recurrence", {
                          ...form.recurrence,
                          interval: Number(e.target.value),
                        })
                      }
                    />
                  </label>
                  <label className="field">
                    {t("Repeat until (optional)", "重复结束日期（可留空）")}
                    <input
                      type="date"
                      min={form.start_local.slice(0, 10)}
                      value={form.recurrence.until ?? ""}
                      onInput={(e) =>
                        update("recurrence", {
                          ...form.recurrence,
                          until: e.currentTarget.value || null,
                        })
                      }
                    />
                  </label>
                </div>
                <p className="form-note">
                  {t(
                    "Uses the Gregorian calendar. Dates that do not exist are skipped; repeated clock-change times use the first occurrence.",
                    "按公历重复，不存在的日期会跳过；夏令时重复时刻采用第一次发生。",
                  )}
                </p>
              </>
            )}
            {!state.id && form.recurrence.frequency === "none" && (
              <details className="form-details">
                <summary>
                  {t("Add this event on more dates", "将此安排添加到更多日期")}
                  {dates.length > 0 && ` (${dates.length + 1})`}
                </summary>
                <div className="batch-entry">
                  <input
                    type="date"
                    value={extraDate}
                    aria-label={t("Additional date", "额外日期")}
                    onInput={(e) => setExtraDate(e.currentTarget.value)}
                  />
                  <button
                    className="secondary"
                    type="button"
                    onClick={addDate}
                    disabled={
                      !extraDate ||
                      extraDate === form.start_local.slice(0, 10) ||
                      dates.includes(extraDate)
                    }
                  >
                    {t("Add date", "添加日期")}
                  </button>
                </div>
                <div className="date-chips">
                  {dates.map((d) => (
                    <button
                      key={d}
                      type="button"
                      className="date-chip"
                      onClick={() => setDates(dates.filter((v) => v !== d))}
                    >
                      {d}
                      <X size={13} />
                    </button>
                  ))}
                </div>
                <p className="form-note">
                  {t(
                    "Each chosen date becomes an independent event.",
                    "每个所选日期会创建一条独立日程。",
                  )}
                </p>
              </details>
            )}
            <div className="field">
              <span>
                {t("Reminders (choose up to four)", "提醒（最多四项）")}
              </span>
              <div className="reminder-options">
                {reminders.map(([value, en, zh]) => (
                  <label key={value}>
                    <input
                      type="checkbox"
                      checked={form.reminder_minutes.includes(value)}
                      disabled={
                        !form.reminder_minutes.includes(value) &&
                        form.reminder_minutes.length >= 4
                      }
                      onChange={(e) =>
                        update(
                          "reminder_minutes",
                          e.target.checked
                            ? [...form.reminder_minutes, value]
                            : form.reminder_minutes.filter((v) => v !== value),
                        )
                      }
                    />
                    {t(en, zh)}
                  </label>
                ))}
              </div>
            </div>
            <div className="form-grid">
              <label className="field">
                {t("Display privacy", "展示隐私")}
                <select
                  value={form.visibility}
                  onChange={(e) =>
                    update(
                      "visibility",
                      e.target.value as EventInput["visibility"],
                    )
                  }
                >
                  <option value="private">{t("Private", "私人")}</option>
                  <option value="displayable">
                    {t("May show details", "允许展示详情")}
                  </option>
                </select>
              </label>
              <label className="field">
                {t("Availability", "忙闲")}
                <select
                  value={form.busy ? "busy" : "free"}
                  onChange={(e) => update("busy", e.target.value === "busy")}
                >
                  <option value="busy">{t("Busy", "忙碌")}</option>
                  <option value="free">{t("Free", "空闲")}</option>
                </select>
              </label>
            </div>
            <div
              className="color-options"
              aria-label={t("Event color", "日程颜色")}
            >
              {(["lavender", "blue", "sage", "peach"] as EventColor[]).map(
                (c, i) => (
                  <button
                    key={c}
                    type="button"
                    aria-label={t(
                      ["Lavender", "Blue", "Sage", "Peach"][i],
                      ["紫", "蓝", "绿", "桃"][i],
                    )}
                    aria-pressed={form.color === c}
                    className={`color-choice ${c} ${form.color === c ? "selected" : ""}`}
                    onClick={() => update("color", c)}
                  >
                    {form.color === c && <Check size={15} />}
                  </button>
                ),
              )}
            </div>
            <details className="form-details">
              <summary>{t("Location & notes", "地点与备注")}</summary>
              <label className="field">
                {t("Location", "地点")}
                <input
                  maxLength={300}
                  value={form.location}
                  onChange={(e) => update("location", e.target.value)}
                />
              </label>
              <label className="field">
                {t("Notes", "备注")}
                <textarea
                  rows={3}
                  maxLength={2000}
                  value={form.notes}
                  onChange={(e) => update("notes", e.target.value)}
                />
              </label>
            </details>
          </details>
        </fieldset>
        {!!error && (
          <p className="error-message" role="alert">
            {errorText(error, t)}
          </p>
        )}
        {!progressive && actions}
      </form>
    </Modal>
  );
}

export function EventDetail({
  event,
  language,
  zone,
  onClose,
  onEdit,
  onChange,
  t,
}: {
  event: Occurrence;
  language: Language;
  zone: string;
  onClose: () => void;
  onEdit: (scope: "series" | "occurrence") => void;
  onChange: () => void;
  t: Translate;
}) {
  const [scope, setScope] = useState<"series" | "occurrence">("occurrence"),
    [confirm, setConfirm] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null);
  const repeating = event.series_recurrence.frequency !== "none";
  async function action(kind: "delete" | "complete" | "reopen") {
    setBusy(true);
    setError(null);
    try {
      await write(`/events/${event.id}/actions`, {
        action: kind,
        expected_version: event.version,
        scope:
          kind === "delete" ? (repeating ? scope : "series") : "occurrence",
        occurrence_key: event.occurrence_key,
      });
      onChange();
      onClose();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={t("Event details", "日程详情")}
      closeLabel={t("Close", "关闭")}
      onClose={onClose}
      busy={busy}
    >
      <div className="event-detail">
        <div className={`detail-color ${event.color}`} />
        <h3>{title(event, language)}</h3>
        <p>
          {inZone(event.start, zone)
            .setLocale(locale(language))
            .toFormat("cccc, d LLLL yyyy")}
        </p>
        <p className="detail-time">
          {eventTime(event, zone, language)}
          {!event.all_day &&
            inZone(event.start, zone).toISODate() !==
              inZone(event.end, zone).toISODate() &&
            ` · ${inZone(event.end, zone).toFormat("d LLL")}`}
        </p>
        <p className="form-note">{event.timezone}</p>
        {event.location && (
          <p className="detail-line">
            <MapPin size={16} />
            {event.location}
          </p>
        )}
        {event.notes && <p className="event-notes">{event.notes}</p>}
        <p className="detail-line">
          <LockKeyhole size={15} />
          {event.visibility === "private"
            ? t("Private", "私人")
            : t("May show details", "允许展示详情")}{" "}
          · {event.busy ? t("Busy", "忙碌") : t("Free", "空闲")}
        </p>
        {event.reminder_minutes.length > 0 && (
          <p className="detail-line">
            <Bell size={15} />
            {event.reminder_minutes
              .map((v) =>
                v === 0
                  ? t("At time", "到时")
                  : `${v} ${t("min early", "分钟前")}`,
              )
              .join(" · ")}
          </p>
        )}
        {event.origin === "sample" && (
          <p className="form-note">
            {t("Example event · editable", "示例日程 · 可以编辑")}
          </p>
        )}
        {event.conflicts.length > 0 && (
          <p className="conflict-note">
            <CircleAlert size={17} />
            {t(
              "Overlaps another event in this view.",
              "与当前视图内的其他日程重叠。",
            )}
          </p>
        )}
        {event.redacted ? (
          <p className="form-note">
            {t(
              "Turn off “Hide private details” in Device to view or edit this event.",
              "在设备设置中关闭“隐藏私人详情”后，可查看或编辑此日程。",
            )}
          </p>
        ) : (
          <>
            {repeating && (
              <label className="field scope-field">
                <span>
                  <Repeat2 size={15} />
                  {t("Edit or delete scope", "编辑或删除范围")}
                </span>
                <select
                  value={scope}
                  onChange={(e) => {
                    setScope(e.target.value as typeof scope);
                    setConfirm(false);
                  }}
                >
                  <option value="occurrence">
                    {t("This occurrence only", "仅本次")}
                  </option>
                  <option value="series">
                    {t("Entire series", "整个系列")}
                  </option>
                </select>
              </label>
            )}
            <div className="detail-actions">
              <button
                className="secondary"
                disabled={busy}
                onClick={() => onEdit(repeating ? scope : "series")}
              >
                <Pencil size={16} />
                {t("Edit", "编辑")}
              </button>
              <button
                className="secondary"
                disabled={busy}
                onClick={() => action(event.completed ? "reopen" : "complete")}
              >
                <Check size={16} />
                {event.completed
                  ? t("Reopen", "取消完成")
                  : repeating
                    ? t("Complete this occurrence", "完成本次")
                    : t("Complete", "完成")}
              </button>
              <button
                className="danger text-button"
                disabled={busy}
                onClick={() => setConfirm(true)}
              >
                <Trash2 size={16} />
                {t("Delete", "删除")}
              </button>
            </div>
            {confirm && (
              <div className="delete-confirm">
                <p>
                  {repeating && scope === "series"
                    ? t(
                        "Delete the entire series and its individual changes?",
                        "删除整个系列及其单次改动？",
                      )
                    : t("Delete this event?", "删除这条日程？")}
                </p>
                <button
                  className="danger-button"
                  disabled={busy}
                  onClick={() => action("delete")}
                >
                  {t("Confirm delete", "确认删除")}
                </button>
                <button
                  className="text-button"
                  onClick={() => setConfirm(false)}
                >
                  {t("Keep event", "保留日程")}
                </button>
              </div>
            )}
          </>
        )}
        {!!error && (
          <p className="error-message" role="alert">
            {errorText(error, t)}
          </p>
        )}
      </div>
    </Modal>
  );
}

export function ReminderDialog({
  reminders,
  language,
  zone,
  onClose,
  onSaved,
  t,
}: {
  reminders: Reminder[];
  language: Language;
  zone: string;
  onClose: () => void;
  onSaved: () => void;
  t: Translate;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null);
  async function act(r: Reminder, action: "acknowledge" | "snooze") {
    setBusy(true);
    setError(null);
    try {
      await write(`/reminders/${r.id}/actions`, {
        action,
        expected_version: r.version,
        minutes: 10,
      });
      onSaved();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={t("Reminders", "提醒")}
      closeLabel={t("Close", "关闭")}
      onClose={onClose}
      busy={busy}
    >
      {reminders.length === 0 && (
        <div className="empty-reminders">
          <Bell />
          <h3>{t("All caught up.", "暂时没有待处理提醒。")}</h3>
          <p>
            {t(
              "Upcoming reminders will appear here.",
              "到时提醒会显示在这里。",
            )}
          </p>
        </div>
      )}
      {reminders.map((r) => (
        <div className="reminder-row" key={r.id}>
          <strong>{title(r, language)}</strong>
          <p>
            {r.status === "snoozed"
              ? t("Snoozed until ", "延后至 ")
              : t("Due ", "提醒时间 ")}
            {inZone(r.snooze_until ?? r.due_at, zone).toFormat("d LLL, HH:mm")}
          </p>
          <div>
            <button
              className="secondary"
              disabled={busy}
              onClick={() => act(r, "snooze")}
            >
              {t("Snooze 10 min", "延后10分钟")}
            </button>
            <button
              className="primary"
              disabled={busy}
              onClick={() => act(r, "acknowledge")}
            >
              {t("Acknowledge", "知道了")}
            </button>
          </div>
        </div>
      ))}
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
    </Modal>
  );
}
