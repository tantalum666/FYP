import { useCallback, useEffect, useId, useRef, useState } from "react";
import { DateTime } from "luxon";
import { ApiError, errorText, request } from "../api";
import { useDraftGuard } from "../components/DraftGuard";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import { personalContextVisible } from "./personal/types";
import { usePrivateMutation } from "./personal/usePrivateMutation";
import {
  canRevealRoutines,
  routineActions,
  routineItemTitle,
  uniqueDeliveries,
} from "./routineTypes";
import type {
  Routine,
  RoutineAction,
  RoutineClaim,
  RoutineDetail,
  RoutineInput,
  RoutineList,
  RoutineRun,
} from "./routineTypes";
import "./routines.css";

function statusLabel(status: string, t: Translate) {
  return (
    {
      active: t("Active", "启用中"),
      paused: t("Paused", "已暂停"),
      completed: t("Completed", "已完成"),
      cancelled: t("Cancelled", "已取消"),
      pending: t("Pending", "待查看"),
      claimed: t("Received", "已接收"),
      suppressed: t("Stored without another delivery", "仅保存，不重复通知"),
      dismissed: t("Delivery dismissed", "已撤销通知"),
    }[status] ?? status
  );
}
function actionLabel(action: RoutineAction, t: Translate) {
  return {
    pause: t("Pause", "暂停"),
    resume: t("Resume", "恢复"),
    cancel: t("Cancel routine", "取消定时事务"),
  }[action];
}
function skillLabel(skill: string, t: Translate) {
  return skill === "day_briefing"
    ? t("Day briefing", "每日简报")
    : t("Task review", "事务回顾");
}
function frequencyLabel(value: string, t: Translate) {
  return (
    {
      once: t("Once", "单次"),
      daily: t("Daily", "每天"),
      weekly: t("Weekly", "每周"),
    }[value] ?? value
  );
}
function atLabel(value: string | null, zone: string, t: Translate) {
  return value
    ? DateTime.fromISO(value)
        .setZone(zone)
        .setLocale(t("en-GB", "zh-CN"))
        .toFormat("yyyy-MM-dd HH:mm ZZZZ")
    : t("No next run", "无下一次运行");
}
function routineError(error: unknown, t: Translate) {
  const messages: Record<string, string> = {
    ROUTINE_START_IN_PAST: t(
      "Choose a future first run in the selected timezone.",
      "请按所选时区设置未来的首次运行时间。",
    ),
    ROUTINE_LIMIT: t(
      "This desk has reached its limit of 50 saved routine definitions.",
      "本桌面已达到50项定时事务定义上限。",
    ),
    ROUTINE_NOT_FOUND: t(
      "This routine is no longer available. Refresh the list.",
      "此定时事务已不存在，请刷新列表。",
    ),
    ROUTINE_CLOSED: t(
      "This routine is already completed or cancelled. Create another to start again.",
      "此定时事务已完成或取消，请新建一项重新开始。",
    ),
    ROUTINE_ALREADY_ACTIVE: t(
      "This routine is already active. Refresh its status.",
      "此定时事务已启用，请刷新状态。",
    ),
    ROUTINE_ALREADY_PAUSED: t(
      "This routine is already paused. Refresh its status.",
      "此定时事务已暂停，请刷新状态。",
    ),
  };
  return error instanceof ApiError && messages[error.code]
    ? messages[error.code]
    : errorText(error, t);
}
function ResultCard({ run, t }: { run: RoutineRun; t: Translate }) {
  const r = run.result;
  return (
    <article className="routine-result">
      <h5>
        {skillLabel(r.skill, t)} · {r.local_date}
      </h5>
      <p className="workspace-hint">
        {t("Local rules", "本地规则")} · {atLabel(r.as_of, r.timezone, t)} ·{" "}
        {statusLabel(run.delivery_state, t)}
      </p>
      {r.status === "failed" ? (
        <p role="status">
          {t(
            "The local sources could not be reviewed. Check Calendar and Tasks; this occurrence will not keep retrying.",
            "未能回顾本地数据，请检查日历与事务；本次运行不会反复重试。",
          )}
        </p>
      ) : (
        <>
          <p>
            {r.counts.events} {t("events", "项日程")} · {r.counts.tasks}{" "}
            {t("tasks", "项事务")} · {r.counts.overdue_tasks}{" "}
            {t("overdue", "项已逾期")} · {r.counts.waiting_tasks}{" "}
            {t("waiting", "项等待中")}
          </p>
          {r.items.length > 0 ? (
            <ul>
              {r.items.map((item) => (
                <li
                  key={`${item.kind}-${item.id}-${item.occurrence_key ?? ""}`}
                >
                  <strong>
                    {routineItemTitle(
                      item,
                      t("Private item", "私人事项"),
                      t("Removed item", "已移除事项"),
                    )}
                  </strong>
                  <span>
                    {" "}
                    ·{" "}
                    {item.kind === "event"
                      ? t("Calendar", "日历")
                      : t("Task", "事务")}
                    {item.overdue ? t(" · Overdue", " · 已逾期") : ""}
                    {item.status === "waiting"
                      ? t(" · Waiting", " · 等待中")
                      : ""}
                  </span>
                  {(item.start || item.due_at) && (
                    <span>
                      {" "}
                      ·{" "}
                      {atLabel(
                        item.start ?? item.due_at ?? null,
                        r.timezone,
                        t,
                      )}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p>
              {t(
                "No matching open items at this check.",
                "本次检查没有符合条件的待办事项。",
              )}
            </p>
          )}
          <p>
            {r.suggested_action === "review_tasks"
              ? t(
                  "Review the open and waiting items in Tasks, then choose your next step.",
                  "请在事务中核对待办与等待事项，再选择下一步。",
                )
              : t(
                  "Review Calendar and Tasks before planning the rest of your day.",
                  "请先核对日历与事务，再安排今天剩余时间。",
                )}
          </p>
        </>
      )}
      {r.truncated && (
        <p className="workspace-hint">
          {t(
            "Showing up to 20 events and 20 tasks. Counts include all matching items.",
            "最多显示20项日程与20项事务，计数包含全部符合条件的事项。",
          )}
        </p>
      )}
      {(r.catch_up || run.coalesced_delivery) && (
        <p className="workspace-hint">
          {t(
            "Missed checks or pending deliveries were combined into this latest result.",
            "错过的检查或待查看通知已合并为此最新结果。",
          )}
        </p>
      )}
      <p className="workspace-hint">
        {t(
          "Counts and status describe the check time; titles come from current records.",
          "计数与状态反映检查时的情况，标题来自当前记录。",
        )}
      </p>
    </article>
  );
}
export function RoutinesPanel({
  t,
  visibleOverride = true,
}: {
  t: Translate;
  visibleOverride?: boolean;
}) {
  const { data, offline, stale } = useWorkspace();
  const visible =
    visibleOverride &&
    personalContextVisible(
      data?.principal.kind === "owner",
      data?.personal_context_visible,
      offline,
      stale,
    );
  const visibleRef = useRef(visible);
  visibleRef.current = visible;
  const scopeKey = `${data?.principal.kind ?? "none"}:${data?.principal.id ?? "none"}:${visible}`;
  const scope = useRef({ key: scopeKey, epoch: 0 });
  if (scope.current.key !== scopeKey) {
    scope.current = { key: scopeKey, epoch: scope.current.epoch + 1 };
  }
  const [list, setList] = useState<RoutineList | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const selectedRef = useRef(selected);
  selectedRef.current = selected;
  const [detail, setDetail] = useState<RoutineDetail | null>(null);
  const [deliveries, setDeliveries] = useState<RoutineRun[]>([]);
  const [readError, setReadError] = useState<unknown>(null);
  const [reading, setReading] = useState(false);
  const [notice, setNotice] = useState("");
  const [confirmCancel, setConfirmCancel] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [discardForm, setDiscardForm] = useState(false);
  const [form, setForm] = useState<RoutineInput>(() => ({
    title: "",
    skill: "day_briefing",
    frequency: "daily",
    start_local: DateTime.now()
      .setZone("Asia/Hong_Kong")
      .plus({ days: 1 })
      .startOf("day")
      .set({ hour: 9 })
      .toFormat("yyyy-MM-dd'T'HH:mm"),
    timezone: "Asia/Hong_Kong",
  }));
  const mutation = usePrivateMutation();
  const locked = mutation.busy || mutation.pending;
  useDraftGuard(
    (showForm && !!form.title.trim()) || mutation.pending,
    mutation.busy,
  );
  const generation = useRef(0);
  const headingId = useId();
  const reload = useCallback(async () => {
    if (!visibleRef.current) return;
    const selection = selectedRef.current;
    const token = ++generation.current;
    setReading(true);
    try {
      const [next, nextDetail] = await Promise.all([
        request<RoutineList>("/routines"),
        selection
          ? request<RoutineDetail>(`/routines/${selection}`)
          : Promise.resolve(null),
      ]);
      if (
        visibleRef.current &&
        token === generation.current &&
        selection === selectedRef.current
      ) {
        setList(next);
        setDetail(nextDetail);
        setReadError(null);
      }
    } catch (e) {
      if (visibleRef.current && token === generation.current) {
        setReadError(e);
        setList(null);
        setDetail(null);
        setDeliveries([]);
      }
    } finally {
      if (token === generation.current) setReading(false);
    }
  }, []);
  useEffect(() => {
    if (!visible) {
      generation.current++;
      setList(null);
      setDetail(null);
      setDeliveries([]);
      setNotice("");
      setReadError(null);
      setReading(false);
      return;
    }
    void reload();
    const timer = window.setInterval(() => {
      if (!document.hidden) void reload();
    }, 15000);
    return () => {
      clearInterval(timer);
      generation.current++;
    };
  }, [visible, reload, selected]);
  function choose(id: string) {
    setSelected((old) => (old === id ? null : id));
    setDetail(null);
  }
  async function perform(routine: Routine, action: RoutineAction) {
    if (!visible || readError || locked) return;
    setNotice("");
    await mutation.run<{ routine: Routine }>(
      `/routines/${routine.id}/actions`,
      { action, expected_version: routine.version },
      async () => {
        setConfirmCancel(null);
        if (visibleRef.current) {
          setNotice(t("Routine updated.", "定时事务已更新。"));
          await reload();
        }
      },
    );
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!visible || locked || !form.title.trim()) return;
    await mutation.run<{ routine: Routine }>(
      "/routines",
      { ...form, title: form.title.trim() },
      async () => {
        setForm((old) => ({ ...old, title: "" }));
        setShowForm(false);
        if (visibleRef.current) {
          setNotice(
            t(
              "Routine saved. It will run while this desk service is running.",
              "定时事务已保存，会在桌面服务运行时执行。",
            ),
          );
          await reload();
        }
      },
    );
  }
  async function reveal() {
    if (
      !canRevealRoutines(
        visible,
        !!list && !readError,
        locked,
        list?.pending_count ?? 0,
      )
    )
      return;
    const epoch = scope.current.epoch;
    await mutation.run<RoutineClaim>(
      "/routines/deliveries/claim",
      { limit: 20 },
      async (reply) => {
        if (!visibleRef.current || scope.current.epoch !== epoch) return;
        setDeliveries(uniqueDeliveries(reply.deliveries));
        setNotice(
          reply.unavailable_delivery_ids.length
            ? t(
                "Some old result details expired. Inspect newer run history.",
                "部分旧结果详情已过期，请查看较新的运行记录。",
              )
            : t(
                `${reply.claimed} results received. Run history stays available.`,
                `已接收${reply.claimed}项结果，运行记录仍可查看。`,
              ),
        );
        await reload();
      },
    );
  }
  if (data?.principal.kind !== "owner") return null;
  return (
    <section className="routine-panel" aria-labelledby={headingId}>
      <h3 id={headingId}>{t("Routines", "定时事务")}</h3>
      {!visible ? (
        <p className="workspace-hint">
          {t(
            "Private routines are hidden until owner context is visible and the connection is current.",
            "拥有者的私人内容可见且连接恢复后，才会显示定时事务。",
          )}
        </p>
      ) : (
        <>
          <p>
            {t(
              "Schedule a local day briefing or task review. Checks use saved data and no AI credits.",
              "定时生成本地简报或事务回顾，使用已保存的数据，不消耗AI额度。",
            )}
          </p>
          <p className="workspace-hint">
            {t(
              "Runs while the desk service is on. After downtime, missed checks combine into one current result.",
              "桌面服务运行时才会执行，停机期间错过的检查会合并为一次当前结果。",
            )}
          </p>
          <div className="workspace-inline-actions">
            <button
              type="button"
              className="secondary"
              disabled={reading}
              onClick={() => void reload()}
            >
              {reading
                ? t("Refreshing…", "刷新中…")
                : t("Refresh routines", "刷新定时事务")}
            </button>
            <button
              type="button"
              className="secondary"
              disabled={
                locked ||
                showForm ||
                !!readError ||
                !list ||
                list.routines.length >= list.limits.routines
              }
              onClick={() => setShowForm(true)}
            >
              {t("New routine", "新建定时事务")}
            </button>
          </div>
          {!!readError && (
            <p className="error-message" role="alert">
              {routineError(readError, t)}
            </p>
          )}
          {!!mutation.error && (
            <p className="error-message" role="alert">
              {routineError(mutation.error, t)}
            </p>
          )}
          {mutation.pending && (
            <div className="routine-recovery" role="status">
              <p>
                {t(
                  "The result is unknown. Keep this panel open and retry the same request. After closing or reloading, inspect saved routines and run history before making another change. A lost delivery reply needs the same request ID.",
                  "结果尚不确定，请保持面板打开并重试同一请求。关闭或刷新后，请先核对已保存的定时事务和运行记录，再做新修改。丢失的通知回复需使用相同请求ID恢复。",
                )}
              </p>
              <button
                type="button"
                className="secondary"
                disabled={mutation.busy}
                onClick={() => void mutation.retry()}
              >
                {t("Retry the same request", "重试同一请求")}
              </button>
            </div>
          )}
          <p role="status" aria-live="polite">
            {notice}
          </p>
          {showForm && (
            <form className="routine-form" onSubmit={(e) => void submit(e)}>
              <fieldset disabled={locked}>
                <legend>{t("New routine", "新建定时事务")}</legend>
                <label className="field">
                  {t("Routine title", "定时事务标题")}
                  <input
                    value={form.title}
                    maxLength={160}
                    required
                    onChange={(e) =>
                      setForm({ ...form, title: e.target.value })
                    }
                  />
                </label>
                <label className="field">
                  {t("Review", "回顾内容")}
                  <select
                    value={form.skill}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        skill: e.target.value as RoutineInput["skill"],
                      })
                    }
                  >
                    <option value="day_briefing">
                      {skillLabel("day_briefing", t)}
                    </option>
                    <option value="task_review">
                      {skillLabel("task_review", t)}
                    </option>
                  </select>
                </label>
                <label className="field">
                  {t("Repeat", "重复")}
                  <select
                    value={form.frequency}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        frequency: e.target.value as RoutineInput["frequency"],
                      })
                    }
                  >
                    {["once", "daily", "weekly"].map((value) => (
                      <option key={value} value={value}>
                        {frequencyLabel(value, t)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  {t("First run (local time)", "首次运行（本地时间）")}
                  <input
                    type="datetime-local"
                    step={60}
                    required
                    value={form.start_local}
                    onChange={(e) =>
                      setForm({ ...form, start_local: e.target.value })
                    }
                  />
                </label>
                <label className="field">
                  {t("Timezone (IANA)", "时区（IANA）")}
                  <input
                    value={form.timezone}
                    required
                    maxLength={80}
                    placeholder="Asia/Hong_Kong"
                    onChange={(e) =>
                      setForm({ ...form, timezone: e.target.value })
                    }
                  />
                </label>
                <p className="workspace-hint">
                  {t(
                    "Weekly repeats use this weekday. Later clock-change gaps are skipped; repeated hours run once. To change a saved schedule, cancel it and create another.",
                    "每周按首次运行的星期重复。后续夏令时不存在的时刻跳过，重复时段仅运行一次。修改已保存的计划需先取消再新建。",
                  )}
                </p>
                <button
                  type="submit"
                  className="primary"
                  disabled={!form.title.trim()}
                >
                  {t("Save routine", "保存定时事务")}
                </button>
                <button
                  type="button"
                  className="secondary"
                  onClick={() =>
                    form.title.trim()
                      ? setDiscardForm(true)
                      : setShowForm(false)
                  }
                >
                  {t("Cancel editing", "取消编辑")}
                </button>
                {discardForm && (
                  <div
                    role="group"
                    aria-label={t(
                      "Discard routine draft?",
                      "放弃定时事务草稿？",
                    )}
                  >
                    <p>
                      {t(
                        "Discard this unsaved routine?",
                        "放弃这项未保存的定时事务？",
                      )}
                    </p>
                    <div className="workspace-inline-actions">
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => {
                          setForm((old) => ({ ...old, title: "" }));
                          setShowForm(false);
                          setDiscardForm(false);
                        }}
                      >
                        {t("Discard draft", "放弃草稿")}
                      </button>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => setDiscardForm(false)}
                      >
                        {t("Keep editing", "继续编辑")}
                      </button>
                    </div>
                  </div>
                )}
              </fieldset>
            </form>
          )}
          {list && (
            <>
              <div className="routine-inbox">
                <h4>
                  {t("Pending results", "待查看结果")} ({list.pending_count})
                </h4>
                <p className="workspace-hint">
                  {t(
                    "Reveal explicitly marks pending results received. Reading run history does not. At most one pending delivery per routine and 20 overall; newer checks stay in history.",
                    "主动查看会将待查看结果标为已接收，阅读运行记录则不会。每项定时事务最多一条待查看通知，总计20条，较新检查仍保存在记录中。",
                  )}
                </p>
                <button
                  type="button"
                  className="secondary"
                  disabled={
                    !canRevealRoutines(
                      visible,
                      !readError,
                      locked,
                      list.pending_count,
                    )
                  }
                  onClick={() => void reveal()}
                >
                  {t("Reveal pending results", "查看待接收结果")}
                </button>
                {deliveries.map((run) => (
                  <div key={run.id}>
                    <h4>
                      {list.routines.find((r) => r.id === run.routine_id)
                        ?.title ?? t("Routine result", "定时事务结果")}
                    </h4>
                    <ResultCard run={run} t={t} />
                  </div>
                ))}
              </div>
              {list.routines.length === 0 && (
                <p>
                  {t(
                    "No routines yet. Create one to start a recurring review.",
                    "暂无定时事务，新建一项即可开始定时回顾。",
                  )}
                </p>
              )}
              <ul className="routine-list">
                {list.routines.map((routine) => (
                  <li key={routine.id}>
                    <h4>{routine.title}</h4>
                    <p>
                      {skillLabel(routine.skill, t)} ·{" "}
                      {frequencyLabel(routine.frequency, t)} ·{" "}
                      {statusLabel(routine.status, t)}
                    </p>
                    <p className="workspace-hint">
                      {t("Next", "下次")} ·{" "}
                      {atLabel(routine.next_run_at, routine.timezone, t)} ·{" "}
                      {routine.timezone}
                    </p>
                    <div className="workspace-inline-actions">
                      <button
                        type="button"
                        className="secondary"
                        aria-expanded={selected === routine.id}
                        onClick={() => choose(routine.id)}
                      >
                        {selected === routine.id
                          ? t("Close run history", "收起运行记录")
                          : t("View run history", "查看运行记录")}
                      </button>
                      {routineActions(routine.status).map((action) => (
                        <button
                          type="button"
                          className="secondary"
                          key={action}
                          disabled={locked || !!readError}
                          onClick={() =>
                            action === "cancel"
                              ? setConfirmCancel(routine.id)
                              : void perform(routine, action)
                          }
                        >
                          {actionLabel(action, t)}
                        </button>
                      ))}
                    </div>
                    {confirmCancel === routine.id && (
                      <div className="routine-recovery">
                        <p>
                          {t(
                            "Cancel future runs and dismiss this routine’s pending delivery? Saved results remain.",
                            "取消未来运行并撤销此定时事务的待查看通知？已保存的结果会保留。",
                          )}
                        </p>
                        <div className="workspace-inline-actions">
                          <button
                            type="button"
                            className="secondary"
                            disabled={locked}
                            onClick={() => void perform(routine, "cancel")}
                          >
                            {t("Confirm cancellation", "确认取消")}
                          </button>
                          <button
                            type="button"
                            className="secondary"
                            disabled={locked}
                            onClick={() => setConfirmCancel(null)}
                          >
                            {t("Keep routine", "保留定时事务")}
                          </button>
                        </div>
                      </div>
                    )}
                    {selected === routine.id && (
                      <section aria-label={t("Run history", "运行记录")}>
                        {detail?.routine.id === routine.id ? (
                          <>
                            {detail.runs.length === 0 ? (
                              <p>
                                {t(
                                  "No completed checks yet.",
                                  "尚无检查记录。",
                                )}
                              </p>
                            ) : (
                              <>
                                <p className="workspace-hint">
                                  {t(
                                    "Newest 50 results. Reading here does not consume pending delivery.",
                                    "显示最新50项结果，在此阅读不会消耗待查看通知。",
                                  )}
                                </p>
                                {detail.runs.map((run) => (
                                  <ResultCard key={run.id} run={run} t={t} />
                                ))}
                              </>
                            )}
                          </>
                        ) : (
                          <p>
                            {readError
                              ? t(
                                  "Refresh to try loading history again.",
                                  "请刷新以重新读取记录。",
                                )
                              : t("Loading history…", "正在读取记录…")}
                          </p>
                        )}
                      </section>
                    )}
                  </li>
                ))}
              </ul>
              <p className="workspace-hint">
                {t(
                  "Pausing dismisses pending delivery. Resume skips paused recurring checks; an overdue one-off runs once. Saved definitions, including cancelled ones, count toward the limit of 50.",
                  "暂停会撤销待查看通知。恢复时跳过暂停期间的重复检查，逾期单次计划则运行一次。已保存定义（含已取消）共用50项上限。",
                )}
              </p>
            </>
          )}
        </>
      )}
    </section>
  );
}
