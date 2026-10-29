import { useCallback, useEffect, useRef, useState } from "react";
import { DateTime } from "luxon";
import {
  Check,
  ChevronLeft,
  Clock3,
  ListTodo,
  LockKeyhole,
  Pause,
  Pencil,
  Plus,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";
import { ApiError, errorText, pendingWrite, request, write } from "../api";
import type { EventInput, Translate } from "../types";
import { useDraftGuard } from "../components/DraftGuard";
import { Modal } from "../components/Dialogs";
import { useWorkspace } from "./WorkspaceContext";
import { TaskJobs } from "./TaskJobs";
import { AssistantPanel } from "./AssistantPanel";
import type { Task, TaskDetail, TaskInput, TaskList } from "./taskTypes";
import "./tasks.css";

export const taskStatus = (value: string, t: Translate) =>
  ({
    todo: t("To do", "待处理"),
    in_progress: t("In progress", "进行中"),
    waiting: t("Waiting", "等待中"),
    completed: t("Completed", "已完成"),
    cancelled: t("Cancelled", "已取消"),
  })[value] ?? value;
const openTask = (task: Task) =>
  !["completed", "cancelled"].includes(task.status);
const dateLabel = (at: string | null, zone: string, t: Translate) =>
  at
    ? DateTime.fromISO(at)
        .setZone(zone)
        .setLocale(t("en-GB", "zh-CN"))
        .toFormat(t("d LLL HH:mm", "M月d日 HH:mm"))
    : t("Not set", "未设置");
function inputOf(task: Task): TaskInput {
  return {
    title: task.title,
    timezone: task.timezone,
    due_local: task.due_local?.slice(0, 16) ?? null,
    status: openTask(task) ? (task.status as TaskInput["status"]) : "todo",
    next_step: task.next_step,
    waiting_for: task.waiting_for,
    steps: task.steps.map((s) => ({ ...s })),
    visibility: task.visibility,
    follow_up_enabled: task.follow_up_enabled,
    check_in_local:
      task.next_check_at &&
      DateTime.fromISO(task.next_check_at) > DateTime.now()
        ? DateTime.fromISO(task.next_check_at)
            .setZone(task.timezone)
            .toFormat("yyyy-MM-dd'T'HH:mm")
        : null,
    interval_minutes: task.interval_minutes,
  };
}

function TaskEditor({
  task,
  zone,
  t,
  close,
  saved,
  concealPrivate = false,
}: {
  task: Task | null;
  zone: string;
  t: Translate;
  close: () => void;
  saved: (task: Task) => void;
  concealPrivate?: boolean;
}) {
  const initial = useRef<TaskInput>(
    task
      ? inputOf(task)
      : {
          title: "",
          timezone: zone,
          due_local: null,
          status: "todo",
          next_step: "",
          waiting_for: "",
          steps: [],
          visibility: "private",
          follow_up_enabled: true,
          check_in_local: null,
          interval_minutes: 1440,
        },
  );
  const [form, setForm] = useState(initial.current),
    [saving, setSaving] = useState(false),
    [error, setError] = useState<unknown>(null),
    [discard, setDiscard] = useState(false);
  const [version, setVersion] = useState(task?.version);
  const [latest, setLatest] = useState<Task | null>(null);
  const [conflictReady, setConflictReady] = useState(false);
  const dirty = JSON.stringify(form) !== JSON.stringify(initial.current);
  const invalidSteps =
    form.steps.filter((s) => s.title.trim()).length > 20 ||
    form.steps.some((s) => s.title.trim().length > 200);
  useDraftGuard(dirty, saving);
  const change = <K extends keyof TaskInput>(key: K, value: TaskInput[K]) =>
    setForm((f) => ({ ...f, [key]: value }));
  const closeEditor = () => {
    if (saving) return;
    if (dirty && !pendingWrite()) setDiscard(true);
    else close();
  };
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (invalidSteps) return;
    setSaving(true);
    setError(null);
    try {
      const payload = {
        ...form,
        steps: form.steps
          .filter((s) => s.title.trim())
          .map((s) => ({ ...s, title: s.title.trim() })),
      };
      const result = await write<{ task: Task }>(
        task ? `/tasks/${task.id}/actions` : "/tasks",
        task
          ? { action: "update", expected_version: version, task: payload }
          : payload,
      );
      saved(result.task);
    } catch (e) {
      setError(e);
      if (task && e instanceof ApiError && e.code === "VERSION_CONFLICT") {
        try {
          const current = await request<{ task: Task }>(`/tasks/${task.id}`);
          setLatest(current.task);
          setConflictReady(false);
          setError(null);
        } catch (readError) {
          setError(readError);
        }
      }
    } finally {
      setSaving(false);
    }
  }
  return (
    <Modal
      title={task ? t("Edit task", "编辑事务") : t("New task", "新建事务")}
      onClose={closeEditor}
      closeLabel={t("Close", "关闭")}
      busy={saving}
    >
      {discard ? (
        <div className="workspace-panel">
          <h3>{t("Keep your changes?", "保留这些修改？")}</h3>
          <p>{t("These edits have not been saved.", "这些修改还没有保存。")}</p>
          <div className="workspace-inline-actions">
            <button className="primary" onClick={() => setDiscard(false)}>
              {t("Continue editing", "继续编辑")}
            </button>
            <button className="secondary" onClick={close}>
              {t("Discard edits", "放弃修改")}
            </button>
          </div>
        </div>
      ) : (
        <>
          <div
            hidden={!(concealPrivate && form.visibility === "private")}
            className="workspace-panel"
          >
            <p>
              {t(
                "Private details are hidden on the desk. Your draft is kept here until you return and the connection is available.",
                "常亮屏已隐藏私人详情。草稿会保留，待你返回且连接恢复后继续。",
              )}
            </p>
          </div>
          <form
            hidden={concealPrivate && form.visibility === "private"}
            className="workspace-panel task-form"
            onSubmit={submit}
          >
            <fieldset disabled={saving || !!pendingWrite()}>
              <label className="field">
                {t("Task title", "事务标题")}
                <input
                  autoFocus
                  data-initial-focus
                  value={form.title}
                  maxLength={160}
                  required
                  onChange={(e) => change("title", e.target.value)}
                  placeholder={t("Finish the project report", "完成项目报告")}
                />
              </label>
              <div className="workspace-form-grid">
                <label className="field">
                  {t("Deadline (optional)", "截止时间（可选）")}
                  <input
                    type="datetime-local"
                    value={form.due_local ?? ""}
                    onInput={(e) =>
                      change("due_local", e.currentTarget.value || null)
                    }
                  />
                </label>
                <label className="field">
                  {t("Status", "状态")}
                  <select
                    value={form.status}
                    onChange={(e) =>
                      change("status", e.target.value as TaskInput["status"])
                    }
                  >
                    {(["todo", "in_progress", "waiting"] as const).map((s) => (
                      <option key={s} value={s}>
                        {taskStatus(s, t)}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <p className="workspace-hint">
                {t("Times use", "时间使用")} {form.timezone}.{" "}
                {t(
                  "A deadline does not reserve time in your calendar.",
                  "截止时间不会自动占用日历时段。",
                )}
              </p>
              {form.status === "waiting" && (
                <label className="field">
                  {t("What are you waiting for?", "正在等待什么？")}
                  <input
                    required
                    maxLength={500}
                    value={form.waiting_for}
                    onChange={(e) => change("waiting_for", e.target.value)}
                  />
                </label>
              )}
              <label className="field">
                {t("Next step", "下一步")}
                <input
                  maxLength={500}
                  value={form.next_step}
                  onChange={(e) => change("next_step", e.target.value)}
                  placeholder={t(
                    "Prepare charts when the data arrives",
                    "收到数据后制作图表",
                  )}
                />
              </label>
              <label className="field">
                {t(
                  "Steps (one per line, up to 20)",
                  "步骤（每行一项，最多20项）",
                )}
                <textarea
                  rows={3}
                  value={form.steps.map((s) => s.title).join("\n")}
                  onChange={(e) =>
                    change(
                      "steps",
                      e.target.value.split("\n").map((title, i) => ({
                        title,
                        done:
                          form.steps[i]?.title === title
                            ? form.steps[i].done
                            : false,
                      })),
                    )
                  }
                />
              </label>
              {invalidSteps && (
                <p className="error-message" role="alert">
                  {t(
                    "Use up to 20 steps, each no longer than 200 characters. Your text has been kept so you can shorten it.",
                    "最多20个步骤，每项不超过200字。已保留全部输入，请精简后保存。",
                  )}
                </p>
              )}
              <label className="workspace-toggle">
                <span>{t("Follow up on this task", "主动跟进这件事")}</span>
                <input
                  type="checkbox"
                  checked={form.follow_up_enabled}
                  onChange={(e) =>
                    change("follow_up_enabled", e.target.checked)
                  }
                />
              </label>
              {form.follow_up_enabled && (
                <>
                  <div className="workspace-form-grid">
                    <label className="field">
                      {t("Next check-in (optional)", "下次检查（可选）")}
                      <input
                        type="datetime-local"
                        value={form.check_in_local ?? ""}
                        onInput={(e) =>
                          change(
                            "check_in_local",
                            e.currentTarget.value || null,
                          )
                        }
                      />
                    </label>
                    <label className="field">
                      {t("Default check-in interval", "默认检查间隔")}
                      <select
                        value={form.interval_minutes}
                        onChange={(e) =>
                          change("interval_minutes", Number(e.target.value))
                        }
                      >
                        {[
                          [60, t("1 hour", "1小时")],
                          [240, t("4 hours", "4小时")],
                          [1440, t("1 day", "1天")],
                          [10080, t("1 week", "1周")],
                        ].map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                  <p className="workspace-hint">
                    {t(
                      "Without a chosen check-in, the next check uses this interval or an earlier upcoming deadline. One pending check-in stays until you respond.",
                      "未指定时间时，按默认间隔或更早的截止时间检查。一次待处理提醒会保留到你回应，不会反复累加。",
                    )}
                  </p>
                </>
              )}
              <label className="field">
                {t("Display privacy", "展示隐私")}
                <select
                  value={form.visibility}
                  onChange={(e) =>
                    change(
                      "visibility",
                      e.target.value as TaskInput["visibility"],
                    )
                  }
                >
                  <option value="private">{t("Private", "私人")}</option>
                  <option value="displayable">
                    {t("May appear on the desk display", "可在常亮屏展示")}
                  </option>
                </select>
              </label>
            </fieldset>
            {!!error && (
              <p className="error-message" role="alert">
                {errorText(error, t)}
              </p>
            )}
            {latest && !conflictReady && (
              <div className="task-checkin" role="alert">
                <strong>
                  {t("Changed on another screen", "另一端已经修改")}
                </strong>
                <p>
                  {latest.title} · {taskStatus(latest.status, t)}
                </p>
                <p>
                  {t("Latest next step: ", "最新下一步：")}
                  {latest.next_step || t("Not set", "未设置")}
                </p>
                <p>
                  {t(
                    "Your input is still here. Load the current task before editing again; it will replace this unsaved draft.",
                    "你的输入仍在。加载当前事务后再编辑；这会替换未保存的草稿。",
                  )}
                </p>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => {
                    if (!openTask(latest)) {
                      saved(latest);
                      return;
                    }
                    const current = inputOf(latest);
                    initial.current = current;
                    setForm(current);
                    setVersion(latest.version);
                    setConflictReady(true);
                    setError(null);
                  }}
                >
                  {t("Load current task", "加载当前事务")}
                </button>
              </div>
            )}
            <div className="workspace-inline-actions">
              <button
                className="primary"
                disabled={
                  saving ||
                  !form.title.trim() ||
                  invalidSteps ||
                  (!!latest && !conflictReady)
                }
              >
                {saving ? t("Saving…", "保存中…") : t("Save task", "保存事务")}
              </button>
              <button
                type="button"
                className="secondary"
                onClick={closeEditor}
                disabled={saving}
              >
                {t("Cancel", "取消")}
              </button>
            </div>
          </form>
        </>
      )}
    </Modal>
  );
}

export function TaskPanel({
  t,
  zone = "Asia/Hong_Kong",
  onPlan,
  onDiscuss,
  displayMode = false,
}: {
  t: Translate;
  zone?: string;
  onPlan?: (event: EventInput) => void;
  onDiscuss?: (id: string, title: string) => void;
  displayMode?: boolean;
}) {
  const workspace = useWorkspace();
  const { refresh: refreshWorkspace } = workspace;
  const [data, setData] = useState<TaskList | null>(null),
    [error, setError] = useState<unknown>(null),
    [offline, setOffline] = useState(false),
    [busy, setBusy] = useState(false);
  const [query, setQuery] = useState(""),
    [filter, setFilter] = useState("active"),
    [selected, setSelected] = useState<string | null>(null),
    [detail, setDetail] = useState<TaskDetail | null>(null);
  const [edit, setEdit] = useState<Task | null | undefined>(undefined),
    [note, setNote] = useState(""),
    [notice, setNotice] = useState(""),
    [confirm, setConfirm] = useState<"complete" | "cancel" | null>(null),
    [assistant, setAssistant] = useState<string | null>(null);
  const alive = useRef(true),
    loading = useRef(false),
    detailVersion = useRef("");
  useDraftGuard(!!note.trim(), busy);
  const [leaveNote, setLeaveNote] = useState(false);
  const load = useCallback(async () => {
    if (loading.current) return;
    loading.current = true;
    try {
      const next = await request<TaskList>(
        `/tasks?include_closed=true&display=${displayMode}`,
      );
      if (alive.current) {
        setData((old) => (!old || next.revision >= old.revision ? next : old));
        setOffline(false);
        setError((old: unknown) =>
          old instanceof ApiError &&
          ["CONNECTION_LOST", "AUTH_REQUIRED"].includes(old.code)
            ? null
            : old,
        );
      }
    } catch (e) {
      if (alive.current) {
        if (!(e instanceof ApiError && e.code === "CONNECTION_LOST"))
          setError(e);
        if (e instanceof ApiError && e.status === 401) {
          setData(null);
          setDetail(null);
          setNote("");
          setSelected(null);
        }
        setOffline(true);
      }
    } finally {
      loading.current = false;
    }
  }, [displayMode]);
  useEffect(() => {
    alive.current = true;
    void load();
    const timer = setInterval(() => {
      if (!document.hidden) void load();
    }, 2000);
    window.addEventListener("desk:tasks", load);
    const resume = () => {
      if (!document.hidden) void load();
    };
    document.addEventListener("visibilitychange", resume);
    window.addEventListener("online", resume);
    return () => {
      alive.current = false;
      clearInterval(timer);
      window.removeEventListener("desk:tasks", load);
      document.removeEventListener("visibilitychange", resume);
      window.removeEventListener("online", resume);
    };
  }, [load]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 6000);
    return () => clearTimeout(timer);
  }, [notice]);
  const posture = workspace.data?.posture;
  const concealPrivate =
    displayMode &&
    (offline ||
      workspace.offline ||
      workspace.stale ||
      !posture ||
      (posture.preferences.enabled &&
        posture.preferences.privacy_when_away &&
        (!posture.connected ||
          ["absent", "unknown", "paused"].includes(posture.status))));
  const tasks = data?.tasks.map((x) =>
    concealPrivate && x.visibility === "private"
      ? {
          ...x,
          title: "",
          next_step: "",
          waiting_for: "",
          steps: [],
          redacted: true,
        }
      : x,
  );
  const task = tasks?.find((x) => x.id === selected);
  useEffect(() => {
    let live = true;
    if (!selected) {
      setDetail(null);
      detailVersion.current = "";
      return;
    }
    if (task?.redacted) {
      setDetail(null);
      detailVersion.current = "";
      setAssistant(null);
      return;
    }
    const key =
      selected +
      "/" +
      task?.version +
      "/" +
      (task?.followup?.id ?? "") +
      "/" +
      data?.revision;
    if (key === detailVersion.current) return;
    request<TaskDetail>(`/tasks/${selected}?display=${displayMode}`)
      .then((d) => {
        if (live) {
          setDetail(d);
          detailVersion.current = key;
        }
      })
      .catch((e) => {
        if (live) setError(e);
      });
    return () => {
      live = false;
    };
  }, [
    selected,
    task?.version,
    task?.redacted,
    task?.followup?.id,
    data?.revision,
    displayMode,
    offline,
  ]);
  async function action(kind: string, minutes?: number) {
    if (!task) return;
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      await write(`/tasks/${task.id}/actions`, {
        action: kind,
        expected_version: task.version,
        note,
        ...(minutes ? { minutes } : {}),
      });
      setNote("");
      setConfirm(null);
      await load();
      await refreshWorkspace();
      setNotice(
        kind === "complete"
          ? t("Completed · confirmed by you", "已完成 · 由你确认")
          : t("Task updated", "事务已更新"),
      );
      window.dispatchEvent(new Event("desk:tasks"));
    } catch (e) {
      setError(e);
      await load();
    } finally {
      setBusy(false);
    }
  }
  async function toggleStep(index: number) {
    if (!task || busy || note.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const input = inputOf(task);
      input.steps[index].done = !input.steps[index].done;
      await write(`/tasks/${task.id}/actions`, {
        action: "update",
        expected_version: task.version,
        task: input,
      });
      await load();
      await refreshWorkspace();
    } catch (e) {
      setError(e);
      await load();
    } finally {
      setBusy(false);
    }
  }
  function back() {
    if (note.trim()) {
      setLeaveNote(true);
      return;
    }
    setSelected(null);
    setConfirm(null);
    setError(null);
  }
  const filtered = (tasks ?? []).filter(
    (x) =>
      (filter === "closed"
        ? !openTask(x)
        : filter === "waiting"
          ? x.status === "waiting"
          : openTask(x)) &&
      (!query ||
        (x.title || t("Private task", "私人事务"))
          .toLocaleLowerCase()
          .includes(query.toLocaleLowerCase())),
  );
  return (
    <div className="workspace-panel task-panel">
      {leaveNote && (
        <Modal
          title={t("Keep your progress note?", "保留进展记录？")}
          closeLabel={t("Close", "关闭")}
          onClose={() => setLeaveNote(false)}
        >
          <p>{t("Your note has not been saved.", "这段记录还没有保存。")}</p>
          <div className="workspace-inline-actions">
            <button className="primary" onClick={() => setLeaveNote(false)}>
              {t("Keep editing", "继续编辑")}
            </button>
            <button
              className="secondary"
              onClick={() => {
                setNote("");
                setSelected(null);
                setLeaveNote(false);
              }}
            >
              {t("Discard note", "放弃记录")}
            </button>
          </div>
        </Modal>
      )}
      {selected && task?.redacted ? (
        <section className="workspace-panel">
          <button className="text-button" onClick={back}>
            {t("All tasks", "全部事务")}
          </button>
          <p>
            {t(
              "Private details are hidden. Your unsaved progress note is kept until this task is visible again.",
              "私人详情已隐藏。未保存的进展会保留，待事务重新可见后继续。",
            )}
          </p>
        </section>
      ) : selected && task && !task.redacted ? (
        <>
          <button
            className="text-button task-back"
            onClick={back}
            disabled={busy}
          >
            <ChevronLeft size={18} />
            {t("All tasks", "全部事务")}
          </button>
          <div className="task-detail-heading">
            <span className={`task-status ${task.status}`}>
              {taskStatus(task.status, t)}
            </span>
            <h2>{task.title || t("Private task", "私人事务")}</h2>
            <p>
              {t("Deadline", "截止")} ·{" "}
              {dateLabel(task.due_at, task.timezone, t)}{" "}
              {task.overdue && (
                <strong className="task-overdue">
                  {t("Overdue", "已逾期")}
                </strong>
              )}
            </p>
          </div>
          {task.followup && (
            <aside className="task-checkin">
              <strong>{t("Time for an update", "更新一下进展")}</strong>
              <p>{t(task.followup.en, task.followup.zh)}</p>
              {task.followup.reason_en && (
                <small>
                  {t(task.followup.reason_en, task.followup.reason_zh ?? "")}
                </small>
              )}
              <small>
                {task.followup.mode === "ai"
                  ? t(
                      "AI suggestion · review before acting",
                      "AI建议 · 行动前请核对",
                    )
                  : t("Based on your saved task", "依据已保存的事务")}
              </small>
            </aside>
          )}
          {task.next_step && (
            <section className="task-next-step">
              <h3>{t("Next step", "下一步")}</h3>
              <p>{task.next_step}</p>
            </section>
          )}
          {task.waiting_for && task.status === "waiting" && (
            <p>
              {t("Waiting for: ", "正在等待：")}
              {task.waiting_for}
            </p>
          )}
          {task.steps.length > 0 && (
            <ul className="task-checklist">
              {task.steps.map((step, index) => (
                <li key={index}>
                  <label>
                    <input
                      type="checkbox"
                      checked={step.done}
                      disabled={
                        busy || offline || !openTask(task) || !!note.trim()
                      }
                      onChange={() => void toggleStep(index)}
                    />
                    <span>{step.title}</span>
                  </label>
                </li>
              ))}
            </ul>
          )}
          <p className="workspace-hint">
            <Clock3 size={15} />{" "}
            {!openTask(task)
              ? t("Follow-ups ended", "跟进已结束")
              : !task.follow_up_enabled
                ? t("Follow-ups off", "跟进未开启")
                : task.paused
                  ? t("Follow-ups paused", "跟进已暂停")
                  : task.followup
                    ? t("Waiting for your update", "等待你更新进展")
                    : t("Next check-in: ", "下次检查：") +
                      dateLabel(task.next_check_at, task.timezone, t)}
          </p>
          {openTask(task) ? (
            <>
              <label className="field">
                {t("Progress update", "进展记录")}
                <textarea
                  rows={3}
                  value={note}
                  maxLength={2000}
                  disabled={busy}
                  onChange={(e) => {
                    setNote(e.target.value);
                    setNotice("");
                  }}
                  placeholder={t(
                    "Data arrived; the charts still need work.",
                    "数据收到了，图表还没做。",
                  )}
                />
              </label>
              <div className="workspace-inline-actions">
                <button
                  className="primary"
                  disabled={busy || !note.trim() || offline}
                  onClick={() => void action("note")}
                >
                  {t("Save progress", "保存进展")}
                </button>
                <button
                  className="secondary"
                  disabled={busy || offline}
                  onClick={() =>
                    onDiscuss
                      ? onDiscuss(task.id, task.title)
                      : setAssistant(task.id)
                  }
                >
                  <Sparkles size={16} />
                  {t("Discuss this task", "讨论这件事")}
                </button>
              </div>
              <p className="workspace-hint">
                {t(
                  "A note records what you report. Use Edit to change the next step or waiting status.",
                  "记录保留你提供的进展；使用编辑修改下一步或等待状态。",
                )}
              </p>
              <div className="workspace-inline-actions">
                <button
                  className="secondary"
                  disabled={busy || offline || !!note.trim()}
                  onClick={() => setEdit(task)}
                >
                  <Pencil size={16} />
                  {t("Edit", "编辑")}
                </button>
                {task.follow_up_enabled && (
                  <>
                    <button
                      className="secondary"
                      disabled={busy || offline}
                      onClick={() => void action("snooze", 60)}
                    >
                      {t("Check in in 1 hour", "1小时后检查")}
                    </button>
                    <button
                      className="secondary"
                      disabled={busy || offline}
                      onClick={() =>
                        void action(task.paused ? "resume" : "pause", 60)
                      }
                    >
                      <Pause size={16} />
                      {task.paused
                        ? t("Resume in 1 hour", "1小时后恢复")
                        : t("Pause follow-ups", "暂停跟进")}
                    </button>
                  </>
                )}
              </div>
              {!task.follow_up_enabled && (
                <p className="workspace-hint">
                  {t(
                    "Use Edit to turn on follow-ups for this task.",
                    "如需定时跟进，可以在编辑中开启。",
                  )}
                </p>
              )}
              {onPlan && (
                <button
                  className="text-button"
                  disabled={busy || offline || !!note.trim()}
                  onClick={() => {
                    const start = DateTime.now()
                      .setZone(task.timezone)
                      .plus({ hours: 1 })
                      .startOf("hour");
                    onPlan({
                      title: task.title,
                      start_local: start.toFormat("yyyy-MM-dd'T'HH:mm"),
                      end_local: start
                        .plus({ minutes: 30 })
                        .toFormat("yyyy-MM-dd'T'HH:mm"),
                      timezone: task.timezone,
                      all_day: false,
                      calendar: "personal",
                      color: "lavender",
                      visibility: task.visibility,
                      busy: true,
                      location: "",
                      notes: task.next_step,
                      recurrence: {
                        frequency: "none",
                        interval: 1,
                        until: null,
                      },
                      reminder_minutes: [10],
                    });
                  }}
                >
                  {t("Choose time in calendar…", "在日历中选择时间…")}
                </button>
              )}
              <div className="workspace-inline-actions">
                <button
                  className="primary"
                  disabled={busy || offline}
                  onClick={() => setConfirm("complete")}
                >
                  <Check size={17} />
                  {t("Mark complete", "标记完成")}
                </button>
                <button
                  className="text-button"
                  disabled={busy || offline}
                  onClick={() => setConfirm("cancel")}
                >
                  <Trash2 size={16} />
                  {t("Cancel task", "取消事务")}
                </button>
              </div>
            </>
          ) : (
            <div className="workspace-inline-actions">
              <button
                className="secondary"
                disabled={busy || offline}
                onClick={() => void action("reopen")}
              >
                {t("Reopen task", "恢复事务")}
              </button>
              <span>
                {task.status === "completed"
                  ? task.completion_source === "owner_policy"
                    ? t(
                        "Completed using your full-access permission.",
                        "已按你的完整权限设置完成。",
                      )
                    : task.completion_source === "backup"
                      ? t(
                          "Completion state restored from backup.",
                          "完成状态从备份恢复。",
                        )
                      : t(
                          "Completion was confirmed by you.",
                          "完成状态由你确认。",
                        )
                  : t(
                      "Cancelled tasks are kept in history.",
                      "已取消事务保留在历史中。",
                    )}
              </span>
            </div>
          )}
          {confirm && (
            <div className="task-confirm" role="alert">
              <p>
                {confirm === "complete"
                  ? t(
                      "Mark this task complete and stop its follow-ups?",
                      "确认这件事已完成，并停止跟进？",
                    )
                  : t(
                      "Cancel this task and stop its follow-ups? You can reopen it later.",
                      "取消事务并停止跟进？以后可以恢复。",
                    )}
              </p>
              <div className="workspace-inline-actions">
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() => void action(confirm)}
                >
                  {t("Confirm", "确认")}
                </button>
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() => setConfirm(null)}
                >
                  {t("Keep working", "继续处理")}
                </button>
              </div>
            </div>
          )}
          {!displayMode && workspace.data?.principal.kind === "owner" && (
            <TaskJobs
              key={task.id}
              t={t}
              onDiscuss={() =>
                onDiscuss
                  ? onDiscuss(task.id, task.title)
                  : setAssistant(task.id)
              }
              timezone={task.timezone}
              jobs={detail?.task.id === task.id ? detail.jobs : undefined}
              blocked={
                busy ||
                offline ||
                workspace.offline ||
                workspace.stale ||
                !!note.trim()
              }
            />
          )}
          <section className="workspace-section">
            <h3>{t("Progress history", "进展历史")}</h3>
            {detail?.evidence.map((e) => (
              <article className="task-history" key={e.id}>
                <small>
                  {dateLabel(e.at, task.timezone, t)} ·{" "}
                  {e.source === "owner_policy"
                    ? t(
                        "With your full-access permission",
                        "根据你的完整权限设置",
                      )
                    : e.source === "user_confirmed"
                      ? t("Confirmed by you", "由你确认")
                      : e.source === "local_rules"
                        ? t("Scheduled check-in", "计划检查")
                        : t("Saved update", "已保存更新")}
                </small>
                <p>
                  {e.note ||
                    ({
                      created: t("Task created", "事务已创建"),
                      complete: t("Marked complete", "标记为完成"),
                      cancel: t("Task cancelled", "事务已取消"),
                      reopen: t("Task reopened", "事务已恢复"),
                      pause: t("Follow-ups paused", "跟进已暂停"),
                      resume: t("Follow-ups resumed", "跟进已恢复"),
                      restored: t("Restored from backup", "从备份恢复"),
                      snooze: t("Check-in postponed", "检查已延后"),
                      update: t("Task details updated", "事务详情已更新"),
                      followup: t("Progress check ready", "已准备进展检查"),
                    }[e.kind] ??
                      taskStatus(e.kind, t))}
                </p>
              </article>
            ))}
          </section>
        </>
      ) : (
        <>
          <div className="task-heading">
            <div>
              <span className="workspace-eyebrow">
                {t("Stay on top of what matters", "持续跟进重要的事")}
              </span>
              <h1>{t("Tasks", "事务")}</h1>
              <p>
                {t(
                  "Keep the next step in view, even between conversations.",
                  "在每次交谈之间，继续记住进展与下一步。",
                )}
              </p>
            </div>
            <button
              className="primary"
              disabled={offline}
              onClick={() => setEdit(null)}
            >
              <Plus size={17} />
              {t("New task", "新建事务")}
            </button>
          </div>
          <div className="task-toolbar">
            <div
              className="task-filters"
              aria-label={t("Task status", "事务状态")}
            >
              {[
                ["active", t("Active", "待处理")],
                ["waiting", t("Waiting", "等待中")],
                ["closed", t("History", "已结束")],
              ].map(([value, label]) => (
                <button
                  key={value}
                  aria-pressed={filter === value}
                  className={filter === value ? "selected" : ""}
                  onClick={() => setFilter(value)}
                >
                  {label}
                </button>
              ))}
            </div>
            <label className="task-search">
              <Search size={17} />
              <input
                aria-label={t("Search tasks", "搜索事务")}
                placeholder={t("Search tasks", "搜索事务")}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
          </div>
          {!data ? (
            <p role="status">
              {offline
                ? t(
                    "Tasks are unavailable. Reconnect to load them.",
                    "事务暂时不可用，重新连接后读取。",
                  )
                : t("Loading tasks…", "正在读取事务…")}
            </p>
          ) : filtered.length === 0 ? (
            <div className="task-empty">
              <ListTodo size={30} />
              <h3>
                {query
                  ? t("No matching tasks", "没有匹配的事务")
                  : filter === "closed"
                    ? t("No completed or cancelled tasks", "还没有已结束的事务")
                    : t("Nothing to follow up yet", "还没有需要跟进的事务")}
              </h3>
              <p>
                {t(
                  "Add a task with a next step and choose when to check in.",
                  "添加一件事、写下下一步，并选择检查时间。",
                )}
              </p>
            </div>
          ) : (
            <div className="task-list">
              {filtered.map((x) => (
                <button
                  key={x.id}
                  className="task-row"
                  disabled={x.redacted}
                  onClick={() => {
                    setSelected(x.id);
                    setNote("");
                    setNotice("");
                    setError(null);
                  }}
                >
                  <span className={`task-status ${x.status}`}>
                    {x.redacted ? (
                      <LockKeyhole size={15} />
                    ) : (
                      taskStatus(x.status, t)
                    )}
                  </span>
                  <span className="task-row-main">
                    <strong>{x.title || t("Private task", "私人事务")}</strong>
                    <small>
                      {x.redacted
                        ? t(
                            "Private details are hidden on this screen.",
                            "此屏幕已隐藏私人详情。",
                          )
                        : x.next_step ||
                          x.waiting_for ||
                          t("Add your next step", "补充下一步")}
                    </small>
                  </span>
                  <span className="task-row-meta">
                    {x.followup ? (
                      <span className="task-attention">
                        {t("Check-in ready", "待更新进展")}
                      </span>
                    ) : x.paused ? (
                      t("Paused", "已暂停")
                    ) : (
                      dateLabel(x.due_at, x.timezone, t)
                    )}
                    {x.overdue && (
                      <small className="task-overdue">
                        {t("Overdue", "已逾期")}
                      </small>
                    )}
                  </span>
                </button>
              ))}
            </div>
          )}
        </>
      )}
      {offline && (
        <p className="error-message" role="status">
          {t(
            "Offline. Showing the last loaded tasks.",
            "已离线，当前显示上次读取的事务。",
          )}{" "}
          <button className="text-button" onClick={() => void load()}>
            {t("Retry", "重试")}
          </button>
        </p>
      )}
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
      {notice && (
        <p className="task-notice" role="status">
          {notice}
        </p>
      )}
      {edit !== undefined && (
        <TaskEditor
          task={edit}
          concealPrivate={
            (concealPrivate && !!edit) ||
            !!(edit && tasks?.find((x) => x.id === edit.id)?.redacted)
          }
          zone={data?.timezone ?? zone}
          t={t}
          close={() => setEdit(undefined)}
          saved={async (saved) => {
            setEdit(undefined);
            setSelected(saved.id);
            setNotice(t("Task saved", "事务已保存"));
            await load();
            await refreshWorkspace();
          }}
        />
      )}
      {assistant && (
        <Modal
          title={t("Discuss this task", "讨论这件事")}
          closeLabel={t("Close", "关闭")}
          onClose={() => {
            setAssistant(null);
            void load();
          }}
        >
          <AssistantPanel t={t} taskId={assistant} />
        </Modal>
      )}
    </div>
  );
}
