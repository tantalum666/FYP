import { useEffect, useRef, useState } from "react";
import { apiOrigin } from "../../native";
import type { Translate } from "../../types";
import { Modal } from "../../components/Dialogs";
import { useDraftGuard } from "../../components/DraftGuard";
import { useWorkspace } from "../WorkspaceContext";
import { ResponseFence } from "../personal/responseFence";
import { usePrivateMutation } from "../personal/usePrivateMutation";
import type { WorkGoalRequest } from "../agent/types";
import { actionLabel, fieldLabel, statusLabel, watchError } from "./labels";
import {
  watchedFields,
  watchActions,
  newWatchDraft,
  prepareWatch,
  scopePath,
} from "./types";
import type { Responsibility, WatchAction, WatchDraft } from "./types";
import { useResponsibilities } from "./useResponsibilities";
import { WatchReviewCard } from "./WatchReviewCard";
import { CurrentTask } from "./CurrentTask";
import { WatchRetention, WatchUsage } from "./WatchRetention";
import { validWatchMutationResult } from "./retention";
import "./responsibilities.css";
export function ResponsibilitiesPanel({
  t,
  visibleOverride = true,
  onCompile,
}: {
  t: Translate;
  visibleOverride?: boolean;
  onCompile: (goal: WorkGoalRequest) => void;
}) {
  const { data, offline, stale } = useWorkspace();
  const available =
    data?.principal.kind === "owner" && !offline && !stale && visibleOverride;
  const hidden = data?.personal_context_visible !== true;
  const [open, setOpen] = useState(false),
    [session, setSession] = useState(0);
  const fence = useRef(new ResponseFence());
  fence.current.update(
    `${data?.principal.kind}:${data?.principal.id}:${session}:${apiOrigin()}:${hidden}`,
    available,
  );
  const epoch = fence.current.version;
  useEffect(() => {
    const changed = () => {
      fence.current.update(`invalid:${crypto.randomUUID()}`, false);
      setOpen(false);
      setSession((n) => n + 1);
    };
    window.addEventListener("desk:session", changed);
    window.addEventListener("desk:personal-context", changed);
    window.addEventListener("offline", changed);
    return () => {
      window.removeEventListener("desk:session", changed);
      window.removeEventListener("desk:personal-context", changed);
      window.removeEventListener("offline", changed);
    };
  }, []);
  useEffect(() => {
    setOpen(false);
  }, [epoch]);
  return (
    <div className="agent-entry">
      <button
        type="button"
        className="secondary"
        disabled={!available}
        onClick={() => setOpen(true)}
      >
        {t("Watch task changes", "关注事务变化")}
      </button>
      <small>
        {hidden
          ? t(
              "Private details hidden · stop controls only",
              "私人详情已隐藏 · 仅可停止关注",
            )
          : t(
              "Selected saved fields · local change reviews",
              "明确选择保存字段 · 本地变化审阅",
            )}
      </small>
      {open && available && (
        <Modal
          title={t("Watch task changes", "关注事务变化")}
          closeLabel={t("Close", "关闭")}
          onClose={() => setOpen(false)}
          wide
        >
          <WatchWorkspace
            key={epoch}
            fence={fence.current}
            epoch={epoch}
            hidden={hidden}
            t={t}
            onCompile={(goal) => {
              if (fence.current.accepts(epoch) && !hidden) {
                setOpen(false);
                onCompile(goal);
              }
            }}
          />
        </Modal>
      )}
    </div>
  );
}
export function WatchWorkspace({
  fence,
  epoch,
  hidden,
  t,
  onCompile,
}: {
  fence: ResponseFence;
  epoch: number;
  hidden: boolean;
  t: Translate;
  onCompile: (goal: WorkGoalRequest) => void;
}) {
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const [selected, setSelected] = useState<string | null>(null),
    [create, setCreate] = useState(false),
    [maintenance, setMaintenance] = useState(false);
  const [draft, setDraft] = useState<WatchDraft>(newWatchDraft);
  const [confirm, setConfirm] = useState<{
    row: Responsibility;
    action: WatchAction;
  } | null>(null);
  const [inspect, setInspect] = useState<string | null>(null);
  const path =
    create && draft.task_ids.length && draft.fields.length
      ? scopePath(draft.task_ids, draft.fields)
      : null;
  const { value, fresh, error, loading, reload } = useResponsibilities(
    fence,
    epoch,
    hidden,
    selected,
    path,
  );
  const mutation = usePrivateMutation(),
    locked = mutation.busy || mutation.pending;
  const [sourceDenial, setSourceDenial] = useState<unknown>(null);
  const accessDenied = [error, mutation.error, sourceDenial].some(
    (reason) =>
      reason &&
      typeof reason === "object" &&
      "code" in reason &&
      /AUTH|SESSION|OWNER|PRIVATE|PRIVACY|CONTEXT_HIDDEN|CONTEXT_CHANGED/.test(
        String(reason.code),
      ),
  );
  useEffect(() => {
    if (!accessDenied) return;
    fence.update(`denied:${crypto.randomUUID()}`, false);
    mutation.clear();
    setDraft(newWatchDraft());
    setCreate(false);
    setSelected(null);
    setInspect(null);
    setConfirm(null);
  }, [accessDenied, fence]);

  const dirty =
    create && JSON.stringify(draft) !== JSON.stringify(newWatchDraft());
  useDraftGuard(dirty || mutation.pending || !!confirm, mutation.busy);
  const viewKey = JSON.stringify([
    selected,
    maintenance,
    path,
    value?.scope?.scope_revision,
    value?.detail?.revision,
    value?.list.revision,
  ]);
  const current = useRef({ fresh, hidden, viewKey });
  current.current = { fresh, hidden, viewKey };
  const acceptsAction = () =>
    mounted.current &&
    current.current.fresh &&
    current.current.viewKey === viewKey &&
    fence.accepts(epoch);

  const input = prepareWatch(draft, value?.scope ?? null);
  const scopeToken = value?.scope?.scope_revision;
  const previousScope = useRef<string | null | undefined>(undefined);
  useEffect(() => {
    if (
      scopeToken &&
      previousScope.current &&
      scopeToken !== previousScope.current
    )
      setDraft((old) => ({ ...old, retain_change_history: false }));
    if (scopeToken) previousScope.current = scopeToken;
  }, [scopeToken]);
  useEffect(() => {
    setInspect(null);
  }, [selected]);
  function update<K extends keyof WatchDraft>(key: K, field: WatchDraft[K]) {
    setDraft((old) => ({
      ...old,
      [key]: field,
      ...(key !== "retain_change_history"
        ? { retain_change_history: false }
        : {}),
    }));
  }
  async function write(path: string, body: unknown, created = false) {
    if (!acceptsAction() || locked) return;
    await mutation.run(path, body, (result: unknown) => {
      if (!fence.accepts(epoch)) return;
      setConfirm(null);
      if (!validWatchMutationResult(result)) {
        fence.update(`invalid-response:${epoch}`, false);
        setSourceDenial({ code: "RESPONSIBILITY_RESPONSE_INVALID" });
        return;
      }
      if ("kind" in result) {
        setSelected(null);
        setInspect(null);
        setCreate(false);
        if (!selected) void reload(true);
        return;
      }
      if (created) {
        setCreate(false);
        setDraft(newWatchDraft());
      }
      void reload(true);
    });
  }
  function choose(id: string) {
    if (!acceptsAction() || locked || dirty || confirm) return;
    setSelected(id);
    setCreate(false);
    setInspect(null);
    mutation.clear();
  }
  const blocked = !fresh || locked;
  if (accessDenied || !fence.accepts(epoch))
    return (
      <p role="status">
        {t(
          "Owner access changed. Reconnect and restore visibility before reopening. A sent action may already have saved; inspect current history before repeating it.",
          "本人访问权限已变化，请重新连接并恢复可见性后重新打开。已发送操作可能已保存；重复操作前请查看当前历史。",
        )}
      </p>
    );
  return (
    <div className="watch-workspace">
      <p>
        {t(
          "Only committed changes to the tasks and fields you choose are checked while this local service runs. No initial alert, AI reasoning, audio or external notification. New tasks are never added automatically.",
          "仅在本地服务运行时检查明确选择的事务与字段的已保存变化。不会首次提醒、进行AI推理、播放语音或发送外部通知；新事务不会自动加入。",
        )}
      </p>
      <div className="workspace-inline-actions">
        {!hidden && (
          <button
            type="button"
            className="primary"
            disabled={blocked || create || !!confirm || maintenance}
            onClick={() => {
              if (!acceptsAction() || locked) return;
              setCreate(true);
              setSelected(null);
              setInspect(null);
              mutation.clear();
            }}
          >
            {t("New task watch", "新建事务关注")}
          </button>
        )}
        <button
          type="button"
          className="secondary"
          disabled={loading || mutation.busy}
          onClick={() => void reload(true)}
        >
          {t("Refresh", "刷新")}
        </button>
      </div>
      {!!error && <p role="alert">{watchError(error, t)}</p>}
      {!fresh && (
        <p role="status">
          {t(
            "Waiting for current records. Actions and retries are disabled; same-view drafts and original retry data survive temporary read failures.",
            "等待当前记录；操作与重试已停用。同一视图中的草稿和原始重试资料会在临时读取失败时保留。",
          )}
        </p>
      )}
      {!!mutation.error && <p role="alert">{watchError(mutation.error, t)}</p>}
      {mutation.pending && (
        <div role="status" className="watch-review">
          <p>
            {t(
              "The save response is unknown. Inspect saved records before retrying the same request. Its original operation ID stays only in this open view; after closing, check history rather than repeating it.",
              "保存回执未知。请先检查保存记录，再重试同一请求。原操作ID仅保留在此打开的视图中；关闭后请检查历史，不要重复操作。",
            )}
          </p>
          <button
            type="button"
            className="secondary"
            disabled={!fresh || mutation.busy}
            onClick={() => {
              if (
                mounted.current &&
                current.current.fresh &&
                fence.accepts(epoch)
              )
                void mutation.retry();
            }}
          >
            {t("Retry the same request", "重试同一请求")}
          </button>
        </div>
      )}
      {value && (
        <>
          <p>
            {t("Pending reviews", "待查看变化")}: {value.list.pending_count}
          </p>
          <WatchUsage
            usage={value.list.maintenance_usage}
            limit={value.list.limits.definitions}
            t={t}
          />
          {!hidden && (
            <button
              type="button"
              className="secondary"
              disabled={blocked || dirty || !!confirm || create || maintenance}
              onClick={() => {
                if (acceptsAction() && !locked) setMaintenance(true);
              }}
            >
              {t("Manage terminal history and Trash", "整理已终止历史与废纸篓")}
            </button>
          )}
          <div className="watch-list">
            {value.list.responsibilities.map((row) => (
              <article key={row.id} className="watch-review">
                <strong>{hidden ? row.id : row.title}</strong>
                <p>
                  {statusLabel(row.status, t)} · {t("Reviews", "审阅次数")}:{" "}
                  {row.reviews_used}/{row.review_budget} ·{" "}
                  {t("Budget day (UTC)", "额度记账日（UTC）")}: {row.budget_day}{" "}
                  · {row.daily_used}/{row.daily_review_budget}
                </p>
                <small>
                  {t("Expires", "到期")}: {row.expires_at}
                </small>
                <div className="workspace-inline-actions">
                  {!hidden && (
                    <button
                      type="button"
                      className="secondary"
                      disabled={blocked || dirty || !!confirm || maintenance}
                      onClick={() => choose(row.id)}
                    >
                      {t("Open reviews", "打开审阅")}
                    </button>
                  )}
                  {watchActions(row.status, hidden).map((action) => (
                    <button
                      key={action}
                      type="button"
                      className="secondary"
                      disabled={blocked || dirty || !!confirm || maintenance}
                      onClick={() => {
                        if (acceptsAction() && !locked)
                          setConfirm({ row, action });
                      }}
                    >
                      {actionLabel(action, t)}
                    </button>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </>
      )}
      {!hidden && maintenance && (
        <WatchRetention
          fence={fence}
          epoch={epoch}
          fresh={fresh && !accessDenied}
          revision={value?.list.revision}
          rows={value?.list.responsibilities ?? []}
          limit={value?.list.limits.definitions}
          t={t}
          onChanged={() => {
            if (!fence.accepts(epoch)) return;
            setSelected(null);
            setInspect(null);
            // Selection change drives a new hook read; never reload a closure for the removed detail.
            if (!selected) void reload(true);
          }}
          onDenied={(reason) => setSourceDenial(reason)}
          onClose={() => setMaintenance(false)}
        />
      )}
      {confirm && (
        <div className="watch-review" role="alert">
          <h4>{actionLabel(confirm.action, t)}</h4>
          <p>
            {confirm.action === "resume"
              ? t(
                  "Resume establishes a new baseline now and discards changes made while paused. Retained earlier reviews remain readable.",
                  "恢复会以当前状态建立新基线，并丢弃暂停期间的变化；以前保存的审阅仍可读取。",
                )
              : confirm.action === "cancel"
                ? t(
                    "Cancel permanently stops this watch and dismisses pending delivery. Saved reviews remain; independently started Work is separate.",
                    "取消会永久停止此关注并撤销待查看提醒。保存的审阅仍保留；独立开始的工作另行管理。",
                  )
                : confirm.action === "pause"
                  ? t(
                      "Pause stops comparisons and dismisses pending delivery. Saved reviews remain readable.",
                      "暂停会停止比较并撤销待查看提醒，保存的审阅仍可读取。",
                    )
                  : t(
                      "Recheck exactly these enrolled sources. No substitute task or wider scope is authorized.",
                      "重新检查已关注的确切来源，不授权替代事务或扩大范围。",
                    )}
          </p>
          <button
            type="button"
            className="primary"
            disabled={blocked}
            onClick={() =>
              void write(
                `/responsibilities/${encodeURIComponent(confirm.row.id)}/actions`,
                {
                  action: confirm.action,
                  expected_version: confirm.row.version,
                  ...(confirm.action === "resume"
                    ? { resume_policy: "baseline_now" }
                    : {}),
                },
              )
            }
          >
            {t("Confirm control", "确认操作")}
          </button>
          <button
            type="button"
            className="secondary"
            disabled={locked}
            onClick={() => {
              setConfirm(null);
              mutation.clear();
            }}
          >
            {t("Keep unchanged", "保持不变")}
          </button>
        </div>
      )}
      {create && !hidden && (
        <form
          className="watch-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (input) void write("/responsibilities", input, true);
          }}
        >
          <h3>{t("Choose exactly what to watch", "明确选择关注范围")}</h3>
          <fieldset disabled={locked}>
            <label>
              {t("Watch title", "关注名称")}
              <input
                required
                maxLength={160}
                value={draft.title}
                onChange={(event) => update("title", event.target.value)}
              />
            </label>
            <fieldset>
              <legend>
                {t(
                  "Selected saved tasks (up to 10)",
                  "所选保存事务（最多10项）",
                )}
              </legend>
              {(value?.catalog?.tasks ?? []).map((task) => (
                <label key={task.id} className="agent-check">
                  <input
                    type="checkbox"
                    checked={draft.task_ids.includes(task.id)}
                    disabled={
                      !draft.task_ids.includes(task.id) &&
                      draft.task_ids.length >= 10
                    }
                    onChange={(event) =>
                      update(
                        "task_ids",
                        event.target.checked
                          ? [...draft.task_ids, task.id]
                          : draft.task_ids.filter((id) => id !== task.id),
                      )
                    }
                  />
                  <span>
                    {task.title}
                    <small>
                      {task.id} · v{task.version}
                    </small>
                  </span>
                </label>
              ))}
              {draft.task_ids
                .filter(
                  (id) => !value?.catalog?.tasks.some((task) => task.id === id),
                )
                .map((id) => (
                  <p key={id}>
                    {t(
                      "Selected ID awaiting current availability",
                      "所选ID等待当前可用性检查",
                    )}
                    : {id}
                  </p>
                ))}
            </fieldset>
            <fieldset>
              <legend>{t("Watched fields", "关注字段")}</legend>
              {watchedFields.map((field) => (
                <label key={field} className="agent-check">
                  <input
                    type="checkbox"
                    checked={draft.fields.includes(field)}
                    onChange={(event) =>
                      update(
                        "fields",
                        event.target.checked
                          ? [...draft.fields, field]
                          : draft.fields.filter((item) => item !== field),
                      )
                    }
                  />
                  {fieldLabel(field, t)}
                </label>
              ))}
            </fieldset>
            <label>
              {t("Expiry in UTC (within 30 days)", "UTC到期时间（30天内）")}
              <input
                required
                type="datetime-local"
                value={draft.expires_at}
                onChange={(event) => update("expires_at", event.target.value)}
              />
            </label>
            <label>
              {t("Lifetime review limit (1–100)", "总审阅次数上限（1–100）")}
              <input
                required
                type="number"
                min={1}
                max={100}
                step={1}
                value={draft.review_budget}
                onChange={(event) =>
                  update("review_budget", Number(event.target.value))
                }
              />
            </label>
            <label>
              {t("Daily review limit, UTC (1–20)", "每日审阅上限，UTC（1–20）")}
              <input
                required
                type="number"
                min={1}
                max={20}
                step={1}
                value={draft.daily_review_budget}
                onChange={(event) =>
                  update("daily_review_budget", Number(event.target.value))
                }
              />
            </label>
            <p>
              {t(
                "One pending review coalesces later observed changes. A new review uses one allowance; elapsed time does not create repeated alerts. Paused backlog is skipped on resume. The baseline is saved atomically when you enroll.",
                "一个待查看审阅会合并后续观察到的变化。新建审阅使用一次额度；不会因为时间经过而反复提醒。恢复时跳过暂停期间积压变化，建立关注时原子保存基线。",
              )}
            </p>
            <p>
              {t(
                "Local retention: definition, selected IDs, field hashes and change metadata; newest 50 reviews plus pending/linked reviews. No copied before/after note text. Cancellation does not delete history. Terminal history can be moved to Trash, restored without resuming, or separately confirmed for permanent removal. Opaque retry metadata remains; no forensic-erasure promise.",
                "本地保留定义、所选ID、字段哈希与变化元数据；最新50项审阅及待处理／关联审阅。不复制变化前后的进展正文。取消不会删除历史。已终止历史可移到废纸篓、恢复但不重新开始，或单独确认永久移除。不含正文的重试元数据仍保留，不承诺法证擦除。",
              )}
            </p>
            <label className="agent-check">
              <input
                type="checkbox"
                checked={draft.retain_change_history}
                onChange={(event) =>
                  update("retain_change_history", event.target.checked)
                }
              />
              {t(
                "Retain this watch and its bounded change history locally",
                "在本地保留此关注及有界变化历史",
              )}
            </label>
          </fieldset>
          <button className="primary" disabled={blocked || !input}>
            {t("Enroll selected task changes", "开始关注所选事务变化")}
          </button>
          <button
            type="button"
            className="secondary"
            disabled={locked}
            onClick={() => {
              if (
                !dirty ||
                window.confirm(
                  t("Discard this unsaved watch?", "放弃此未保存关注？"),
                )
              ) {
                setCreate(false);
                setDraft(newWatchDraft());
                mutation.clear();
              }
            }}
          >
            {t("Discard watch draft", "放弃关注草稿")}
          </button>
        </form>
      )}
      {!hidden && value?.detail && (
        <section>
          <h3>{value.detail.responsibility.title}</h3>
          <p>
            {t("Baseline", "基线")}: {value.detail.responsibility.baseline_at} ·{" "}
            {t("Expires", "到期")}: {value.detail.responsibility.expires_at}
          </p>
          <p>
            {value.detail.responsibility.fields
              ?.map((field) => fieldLabel(field, t))
              .join(" · ")}
          </p>
          <ul>
            {value.detail.selected_tasks.map((task) => (
              <li key={task.id}>
                {task.available
                  ? task.title
                  : t("Unavailable task", "不可用事务")}{" "}
                <small>{task.id}</small>
              </li>
            ))}
          </ul>
          {value.detail.responsibility.blocked_code && (
            <p role="status">
              {watchError(
                { code: value.detail.responsibility.blocked_code },
                t,
              )}
            </p>
          )}
          {!value.detail.reviews.length && (
            <p>
              {t(
                "No saved change reviews. Enrollment alone produces none.",
                "暂无保存的变化审阅，建立关注本身不会生成审阅。",
              )}
            </p>
          )}
          {value.detail.reviews.map((review) => (
            <WatchReviewCard
              key={review.id}
              review={review}
              detail={value.detail!}
              t={t}
              disabled={blocked || dirty || !!confirm || maintenance}
              onInspect={(id) => {
                if (acceptsAction() && !locked) setInspect(id);
              }}
              onAcknowledge={() =>
                void write(
                  `/responsibilities/${encodeURIComponent(selected!)}/reviews/${encodeURIComponent(review.id)}/acknowledge`,
                  { expected_review_version: review.version },
                )
              }
              onCompile={(ids) => {
                if (
                  !acceptsAction() ||
                  current.current.hidden ||
                  locked ||
                  !fence.accepts(epoch)
                )
                  return;
                onCompile({
                  id: crypto.randomUUID(),
                  text: t(
                    "Compile current task evidence into a Markdown report and CSV evidence register. Use current saved records; do not claim historical snapshots or complete tasks.",
                    "将当前事务证据整理为Markdown报告和CSV证据表。使用当前保存记录，不声称历史快照，也不完成事务。",
                  ),
                  exactTaskIds: ids,
                });
              }}
            />
          ))}
          {inspect && (
            <CurrentTask
              key={inspect}
              id={inspect}
              fence={fence}
              epoch={epoch}
              fresh={fresh}
              t={t}
              close={() => setInspect(null)}
              onAccessDenied={(reason) => {
                fence.update(`source-denied:${crypto.randomUUID()}`, false);
                setSourceDenial(reason);
              }}
            />
          )}
        </section>
      )}
    </div>
  );
}
