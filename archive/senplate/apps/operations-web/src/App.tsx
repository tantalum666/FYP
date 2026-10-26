import { useEffect, useState, type FormEvent } from "react";
import {
  ChartNoAxesColumnIncreasing,
  FileText,
  Monitor,
  UserRound,
  Globe,
  LogOut,
  RefreshCw,
  Download,
  Check,
  ShoppingBag,
  Utensils,
  GraduationCap,
} from "lucide-react";
import { MenuManager, OrderAttention, OrdersBoard } from "./Ordering";
import { Samples } from "./Samples";
import { APIError, request } from "./api";
import {
  Brand,
  Banner,
  Dialog,
  Empty,
  StationCard,
  TaskList,
} from "./components";
import { clock, LanguagePicker, number, useLabel, useLanguage } from "./i18n";
import { useWorkspace } from "./useWorkspace";
import type { Context, Task, User } from "./types";

export default function App() {
  const [user, setUser] = useState<User | null>(null),
    [loading, setLoading] = useState(true),
    [context, setContext] = useState(""),
    [initError, setInitError] = useState("");
  const { t } = useLanguage();
  const label = useLabel();
  async function loadUser() {
    try {
      const me = await request<User>("/v1/me");
      setUser(me);
      setContext((old) =>
        me.contexts.some((c) => c.id === old)
          ? old
          : (me.contexts.find(
              (c) => c.id === localStorage.getItem(`senplate.context.${me.id}`),
            )?.id ??
            me.contexts.find((c) => c.role !== "personal")?.id ??
            "personal"),
      );
      setInitError("");
    } catch (e) {
      const err = e as APIError;
      if (err.status === 401) setUser(null);
      else setInitError(err.code);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void loadUser();
  }, []);
  async function logout() {
    try {
      await request("/v1/auth/sessions/current", undefined, {
        method: "DELETE",
      });
      setUser(null);
      setContext("");
    } catch (e) {
      setInitError((e as APIError).code);
    }
  }
  function choose(id: string) {
    setContext(id);
    if (user) localStorage.setItem(`senplate.context.${user.id}`, id);
  }
  if (loading)
    return (
      <div className="center-screen">
        <Brand />
        <p>{t("Connecting…", "正在连接…")}</p>
      </div>
    );
  if (!user) return <Login onSignedIn={loadUser} />;
  const selected = user.contexts.find((c) => c.id === context);
  if (!selected)
    return (
      <div className="center-screen">
        <Banner>{label(initError || "FORBIDDEN")}</Banner>
        <button onClick={() => void loadUser()}>{t("Retry", "重试")}</button>
      </div>
    );
  return (
    <>
      {initError && <Banner>{label(initError)}</Banner>}
      <Workspace
        key={`${user.id}:${context}`}
        user={user}
        context={selected}
        onContext={choose}
        onLogout={logout}
        onUnauthorized={loadUser}
      />
    </>
  );
}

function Login({ onSignedIn }: { onSignedIn: () => Promise<void> }) {
  const { t } = useLanguage();
  const label = useLabel();
  const [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await request("/v1/auth/sessions", undefined, {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setPassword("");
      await onSignedIn();
    } catch (e) {
      setError((e as APIError).code);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-shell">
      <div className="login-panel">
        <Brand />
        <h1>
          {t("A clearer view of every serving.", "让每一份食物清晰可见。")}
        </h1>
        <p className="muted">
          {t(
            "Sign in to your Senplate workspace.",
            "登录你的 Senplate 工作区。",
          )}
        </p>
        <form onSubmit={submit}>
          <label>
            {t("Username", "用户名")}
            <input
              autoComplete="username"
              autoCapitalize="none"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          <label>
            {t("Password", "密码")}
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && <Banner>{label(error)}</Banner>}
          <button className="primary" disabled={busy}>
            {busy ? t("Signing in…", "正在登录…") : t("Sign in", "登录")}
          </button>
        </form>
        <div className="login-footer">
          <span>{t("Local prototype", "本地原型")}</span>
          <LanguagePicker />
        </div>
      </div>
    </div>
  );
}

function Workspace({
  user,
  context,
  onContext,
  onLogout,
  onUnauthorized,
}: {
  user: User;
  context: Context;
  onContext: (id: string) => void;
  onLogout: () => void;
  onUnauthorized: () => void;
}) {
  const { t } = useLanguage();
  const [page, setPage] = useState<
    "board" | "events" | "station" | "orders" | "menu" | "samples"
  >("board");
  const personal = context.role === "personal";
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand />
        <nav aria-label={t("Main navigation", "主导航")}>
          {(
            [
              {
                id: "board",
                en: "Kitchen board",
                zh: "厨房看板",
                shortEn: "Kitchen",
                shortZh: "看板",
                Icon: ChartNoAxesColumnIncreasing,
              },
              {
                id: "events",
                en: "Event log",
                zh: "事件记录",
                shortEn: "Events",
                shortZh: "事件",
                Icon: FileText,
              },
              {
                id: "orders",
                en: "Orders",
                zh: "订单",
                shortEn: "Orders",
                shortZh: "订单",
                Icon: ShoppingBag,
              },
              {
                id: "menu",
                en: "Menu & service",
                zh: "菜单与供餐",
                shortEn: "Menu",
                shortZh: "菜单",
                Icon: Utensils,
              },
              {
                id: "station",
                en: "Station display",
                zh: "设备界面",
                shortEn: "Station",
                shortZh: "设备",
                Icon: Monitor,
              },
              { id: "samples", en: "School samples", zh: "学校样本", shortEn: "School", shortZh: "样本", Icon: GraduationCap },
            ] as const
          ).map(({ id, en, zh, shortEn, shortZh, Icon }) => (
            <button
              key={id}
              className={page === id ? "selected" : ""}
              aria-current={page === id ? "page" : undefined}
              aria-label={t(en, zh)}
              onClick={() => setPage(id)}
              disabled={personal}
            >
              <Icon size={22} />
              <span className="nav-full" aria-hidden="true">
                {t(en, zh)}
              </span>
              <span className="nav-compact" aria-hidden="true">
                {t(shortEn, shortZh)}
              </span>
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <label className="context-picker">
            <UserRound size={22} />
            <span>
              <span className="caption">
                {user.name} ·{" "}
                {context.role === "manager"
                  ? t("Manager", "管理员")
                  : context.role === "viewer"
                    ? t("View only", "只读")
                    : context.role === "staff"
                      ? t("Staff mode", "员工模式")
                      : t("Personal", "个人")}
              </span>
              <select
                aria-label={t("Workspace", "工作区")}
                value={context.id}
                onChange={(e) => onContext(e.target.value)}
              >
                {user.contexts.map((c) => (
                  <option key={c.id} value={c.id}>
                    {t(c.name_en, c.name)}
                  </option>
                ))}
              </select>
            </span>
          </label>
          <div className="language-row">
            <Globe size={21} />
            <LanguagePicker />
          </div>
          <button className="quiet" onClick={onLogout}>
            <LogOut size={19} />
            {t("Sign out", "退出登录")}
          </button>
        </div>
      </aside>
      <main>
        {personal ? (
          <>
            <header className="page-header">
              <div>
                <h1>{t("Personal space", "个人空间")}</h1>
                <p>
                  {t("Your meals belong to you.", "你的餐食记录由你掌握。")}
                </p>
              </div>
            </header>
            <section className="panel">
              <Empty>
                {t(
                  "Use the Senplate iPhone app to open menus and manage your orders. Personal meals remain separate from this workspace.",
                  "请使用 Senplate iPhone App 查看菜单和管理订单。个人餐食与工作区独立。",
                )}
              </Empty>
              {user.contexts.some((c) => c.role !== "personal") && (
                <button
                  className="primary"
                  onClick={() =>
                    onContext(
                      user.contexts.find((c) => c.role !== "personal")!.id,
                    )
                  }
                >
                  {t("Open workspace", "进入工作区")}
                </button>
              )}
            </section>
          </>
        ) : (
          <Operations
            user={user}
            context={context}
            page={page}
            onUnauthorized={onUnauthorized}
            onOrders={() => setPage("orders")}
            onSamples={() => setPage("samples")}
          />
        )}
      </main>
    </div>
  );
}

function Operations({
  user,
  context,
  page,
  onUnauthorized,
  onOrders,
  onSamples,
}: {
  user: User;
  context: Context;
  page: "board" | "events" | "station" | "orders" | "menu" | "samples";
  onUnauthorized: () => void;
  onOrders: () => void;
  onSamples: () => void;
}) {
  const { t } = useLanguage(),
    label = useLabel();
  const api = useWorkspace(user, context.id, onUnauthorized);
  const [modal, setModal] = useState<
      { kind: "adjust" | "reject" } | { kind: "task"; id: string } | null
    >(null),
    [filter, setFilter] = useState("all"),
    [amount, setAmount] = useState("1000"),
    [reason, setReason] = useState(""),
    [eventId, setEventId] = useState(""),
    [source, setSource] = useState("all"),
    [exportError, setExportError] = useState("");
  const s = api.overview?.station,
    canWrite = context.role === "manager" || context.role === "staff",
    disabled = api.busy || !!api.pending || !!api.error;
  const selectedTask =
    modal?.kind === "task"
      ? s?.tasks.find((v) => v.id === modal.id)
      : undefined;
  function openTask(task: Task) {
    setReason("");
    setEventId("");
    setModal({ kind: "task", id: task.id });
  }
  async function decide(choice: "accept" | "adjust" | "reject") {
    if (!s?.recommendation) return;
    const rec = s.recommendation;
    const ok = await api.mutate(`/v1/recommendations/${rec.id}/decisions`, {
      expected_version: rec.version,
      decision: choice,
      ...(choice === "adjust" ? { accepted_g: Number(amount) } : {}),
      ...(choice !== "accept" ? { reason_code: reason } : {}),
    });
    if (ok) setModal(null);
  }
  async function act(action: string) {
    if (!selectedTask) return;
    const ok = await api.mutate(`/v1/tasks/${selectedTask.id}/actions`, {
      expected_version: selectedTask.version,
      action,
      note: reason,
      ...(action === "confirm_replenishment"
        ? { physical_event_id: eventId }
        : {}),
    });
    if (ok) {
      setEventId("");
      setReason("");
      if (
        ["confirm_replenishment", "cancel", "close_unverified"].includes(action)
      )
        setModal(null);
    }
  }
  async function exportCSV() {
    try {
      const r = await fetch(`/v1/workspaces/${context.id}/events.csv`, {
        headers: { "X-Context-ID": context.id },
      });
      if (!r.ok) throw new Error();
      const url = URL.createObjectURL(await r.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = "senplate-events.csv";
      a.click();
      URL.revokeObjectURL(url);
      setExportError("");
    } catch {
      setExportError("NETWORK");
    }
  }
  if (page === "samples") return <Samples context={context} />;
  if (s && s.mode !== "foodservice") return <>
    <header className="page-header"><div><h1>{t("Station mode", "设备用途")}</h1><p>{t(context.name_en,context.name)}</p></div><span className="status">{t("Demo data","演示数据")}</span></header>
    <section className="panel mode-message"><Utensils size={32}/><h2>{s.mode==='personal'?t("Personal meal mode","个人餐食模式"):t("Anonymous sample mode","匿名样本模式")}</h2><p className="muted">{s.mode==='personal'?t("Personal food records stay private. Use the station screen to manage its current recording.","个人餐食记录保持私密，请在设备界面管理当前记录。"):t("This station is set up for school sample recording. Its portions and reference estimates appear in School samples.","此设备用于记录学校样本，份量与参考估算可在学校样本中查看。")}</p><a className="button-link" href="/device" target="_blank" rel="noreferrer">{t("Open station screen","打开设备界面")}</a><button onClick={onSamples}>{t("View school samples","查看学校样本")}</button></section>
  </>;
  if (page === "orders")
    return <OrdersBoard api={api} user={user} context={context} />;
  if (page === "menu")
    return <MenuManager api={api} user={user} context={context} />;
  const pageTitle =
    page === "board"
      ? t("Kitchen board", "厨房看板")
      : page === "events"
        ? t("Event log", "事件记录")
        : t("Station display", "设备界面");
  const title = (
    <header className="page-header">
      <div>
        <h1>{pageTitle}</h1>
        <p>
          {t(context.name_en, context.name)} · {t("Lunch", "午餐")}
        </p>
      </div>
      <div className="update">
        <span className="status">
          {s?.data_origin === "hardware"
            ? t("Device data", "设备数据")
            : s?.data_origin === "replay"
              ? t("Replay data", "回放数据")
              : t("Demo data", "演示数据")}
        </span>
        <span>
          {t("Updated", "更新于")} {clock(s?.observed_at ?? null)}
        </span>
      </div>
    </header>
  );
  if (!s)
    return (
      <>
        {title}
        {api.error ? (
          <Banner>
            {label(api.error)}{" "}
            <button onClick={() => void api.refresh()}>
              {t("Retry", "重试")}
            </button>
          </Banner>
        ) : (
          <p>{t("Loading station…", "正在载入餐位…")}</p>
        )}
      </>
    );
  const tasks = s.tasks.filter(
    (task) =>
      filter === "all" ||
      (filter === "closed" &&
        ["completed", "closed_unverified", "cancelled"].includes(task.state)) ||
      filter === task.state,
  );
  const owned =
    selectedTask &&
    (context.role === "manager" ||
      selectedTask.assignee_id === null ||
      selectedTask.assignee_id === user.id);
  return (
    <>
      {title}
      {api.error && (
        <Banner>
          {label(api.error)}{" "}
          <button className="quiet" onClick={() => void api.refresh()}>
            <RefreshCw size={16} />
            {t("Refresh", "刷新")}
          </button>
        </Banner>
      )}
      {api.pending && (
        <Banner>
          {t(
            "The last action has not been confirmed. Check its result before continuing.",
            "上一操作的结果尚未确认，请先核查后再继续。",
          )}{" "}
          <button disabled={api.busy} onClick={() => void api.retry()}>
            {t("Check and retry", "核查并重试")}
          </button>
        </Banner>
      )}
      {page === "board" && (
        <>
          <OrderAttention api={api} onOpen={onOrders} />
          <div className="metrics">
            <div>
              <span>{t("Monitored stations", "监测餐位")}</span>
              <strong>{api.overview?.station_count}</strong>
            </div>
            <div>
              <span>{t("Suggestions", "待处理建议")}</span>
              <strong className={s.recommendation ? "amber" : ""}>
                {s.recommendation ? 1 : 0}
              </strong>
            </div>
            <div>
              <span>{t("Active batches", "进行中批次")}</span>
              <strong>{api.overview?.active_task_count}</strong>
            </div>
          </div>
          <div className="board-grid">
            <StationCard station={s} disconnected={!!api.error} />
            <section className="panel recommendation">
              <h2>{t("Replenishment suggestion", "补餐建议")}</h2>
              {s.recommendation ? (
                <>
                  <div className="recommend-amount">
                    {number(s.recommendation.amount_g)} <span>g</span>
                  </div>
                  <p className="muted">
                    {t(
                      `Unreserved stock has reached the ${number(s.threshold_g)} g threshold.`,
                      `未预留余量已达到 ${number(s.threshold_g)} 克阈值。`,
                    )}
                  </p>
                  <div className="rule">
                    <strong>{t("Rule-based baseline", "规则基线")}</strong>
                    <p>
                      {t(
                        `Suggest ${number(s.batch_g)} g when unreserved stock is ${number(s.threshold_g)} g or less.`,
                        `未预留余量不超过 ${number(s.threshold_g)} 克时，建议补入 ${number(s.batch_g)} 克。`,
                      )}
                    </p>
                  </div>
                  <div className="incoming">
                    <strong>
                      {s.incoming_g
                        ? t("Batch in progress", "已有在制批次")
                        : t("No batch in progress", "暂无在制批次")}
                    </strong>
                    <p>
                      {t("Ready to create a kitchen task.", "可创建厨房任务。")}
                    </p>
                  </div>
                  {canWrite ? (
                    <div className="recommend-actions">
                      <button
                        className="primary"
                        disabled={disabled}
                        onClick={() => void decide("accept")}
                      >
                        {t("Accept suggestion", "接受建议")}
                      </button>
                      <div className="button-pair">
                        <button
                          disabled={disabled}
                          onClick={() => {
                            setAmount(String(s.recommendation!.amount_g));
                            setReason("");
                            setModal({ kind: "adjust" });
                          }}
                        >
                          {t("Adjust amount", "调整份量")}
                        </button>
                        <button
                          disabled={disabled}
                          onClick={() => {
                            setReason("");
                            setModal({ kind: "reject" });
                          }}
                        >
                          {t("Not now", "暂不补餐")}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="muted">
                      {t("View-only access", "当前为只读权限")}
                    </p>
                  )}
                </>
              ) : (
                <div className="no-suggestion">
                  <Check size={30} />
                  <h3>{label(s.suggestion_reason)}</h3>
                  <p className="muted">
                    {s.incoming_g
                      ? `${t("Incoming", "在制量")} ${number(s.incoming_g)} g`
                      : t(
                          "Suggestions update with each reliable reading.",
                          "建议将随可靠读数更新。",
                        )}
                  </p>
                  <p className="caption">
                    {t("Rule-based baseline", "规则基线")}
                  </p>
                </div>
              )}
            </section>
          </div>
          <section className="panel tasks-panel">
            <h2>{t("Kitchen tasks", "厨房任务")}</h2>
            <div className="filters" aria-label={t("Task filters", "任务筛选")}>
              {[
                ["all", t("All", "全部")],
                ["planned", t("Planned", "待制作")],
                ["in_progress", t("Preparing", "制作中")],
                ["ready", t("Ready", "待补入")],
                ["awaiting_reconciliation", t("Verify refill", "待核对")],
                ["closed", t("Closed", "已关闭")],
              ].map(([id, title]) => (
                <button
                  key={id}
                  className={filter === id ? "selected" : ""}
                  aria-pressed={filter === id}
                  onClick={() => setFilter(id)}
                >
                  {title}
                </button>
              ))}
            </div>
            {tasks.length ? (
              <TaskList tasks={tasks} onOpen={openTask} />
            ) : (
              <Empty>
                {s.tasks.length
                  ? t("No batches match this filter.", "此筛选条件下没有批次。")
                  : t(
                      "No replenishment tasks yet. Accepted suggestions appear here.",
                      "暂无补餐任务，接受建议后将在此显示。",
                    )}
              </Empty>
            )}
          </section>
        </>
      )}
      {page === "station" && (
        <div className="station-display">
          <StationCard station={s} display disconnected={!!api.error} />
          <p className="muted">
            {t("Food identity is manually confirmed.", "菜品身份由人工确认。")}
          </p>
        </div>
      )}
      {page === "events" && (
        <section className="panel">
          <div className="section-tools">
            <label>
              {t("Data source", "数据来源")}
              <select
                value={source}
                onChange={(e) => setSource(e.target.value)}
              >
                <option value="all">{t("All sources", "全部来源")}</option>
                <option value="simulated">{t("Demo", "演示")}</option>
                <option value="replay">{t("Replay", "回放")}</option>
                <option value="hardware">{t("Device", "设备")}</option>
              </select>
            </label>
            {context.role === "manager" && (
              <button onClick={() => void exportCSV()}>
                <Download size={17} />
                {t("Export CSV", "导出 CSV")}
              </button>
            )}
          </div>
          {exportError && <Banner>{label(exportError)}</Banner>}
          <p className="caption">
            {t(
              "Most recent 100 events in this monitoring session. Weight decreases are not proof of consumption or waste.",
              "当前监测会话最近 100 条事件。重量下降不等于实际摄入或浪费。",
            )}
          </p>
          <div className="event-list">
            {s.events
              .filter((e) => source === "all" || e.data_origin === source)
              .map((e) => (
                <div className="event-row" key={e.id}>
                  <time>{clock(e.at)}</time>
                  <span>{label(e.kind)}</span>
                  <strong>
                    {e.delta_g === null
                      ? "—"
                      : `${e.delta_g > 0 ? "+" : ""}${number(e.delta_g)} g`}
                  </strong>
                  <span className="caption">
                    {e.data_origin === "simulated"
                      ? t("Demo", "演示")
                      : e.data_origin === "replay"
                        ? t("Replay", "回放")
                        : t("Device", "设备")}
                  </span>
                </div>
              ))}
          </div>
          {!s.events.some(
            (e) => source === "all" || source === e.data_origin,
          ) && (
            <Empty>{t("No matching events.", "没有符合条件的事件。")}</Empty>
          )}
        </section>
      )}
      <footer className="page-footer">
        {s.data_origin === "hardware"
          ? t(
              "Measurements update from the connected device.",
              "测量来自已连接设备。",
            )
          : t("Demo time advances with each step.", "演示时间随每次输入推进。")}
      </footer>
      {modal && (
        <Dialog
          title={
            modal.kind === "task"
              ? t("Kitchen batch", "厨房批次")
              : modal.kind === "adjust"
                ? t("Adjust amount", "调整份量")
                : t("Not now", "暂不补餐")
          }
          onClose={() => {
            if (!api.busy) setModal(null);
          }}
        >
          {api.error && <Banner>{label(api.error)}</Banner>}
          {api.pending && (
            <Banner>
              {t(
                "Action unconfirmed. Close this window to check and retry.",
                "操作结果未确认，请关闭此窗口后核查并重试。",
              )}
            </Banner>
          )}
          {modal.kind !== "task" ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void decide(modal.kind === "adjust" ? "adjust" : "reject");
              }}
            >
              {modal.kind === "adjust" && (
                <label>
                  {t("Batch amount (g)", "批次份量（克）")}
                  <input
                    type="number"
                    min="100"
                    max="5000"
                    step="50"
                    required
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                  />
                </label>
              )}
              <label>
                {t("Reason", "原因")}
                <input
                  required
                  maxLength={100}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </label>
              <button className="primary" disabled={disabled || !reason.trim()}>
                {t("Confirm", "确认")}
              </button>
            </form>
          ) : selectedTask ? (
            <>
              <div className="batch-summary">
                <strong>{number(selectedTask.planned_g)} g</strong>
                <span className="status">{label(selectedTask.state)}</span>
              </div>
              <dl className="facts">
                <div>
                  <dt>{t("Assigned to", "负责人")}</dt>
                  <dd>
                    {selectedTask.assignee_name ?? t("Unassigned", "尚未分配")}
                  </dd>
                </div>
                <div>
                  <dt>{t("Measured addition", "实测补入")}</dt>
                  <dd>{number(selectedTask.actual_added_g)} g</dd>
                </div>
              </dl>
              {selectedTask.state === "ready" && (
                <Banner>
                  {t(
                    "Preparation is ready. The measured remaining amount has not changed. Begin refill before adding food.",
                    "制作已完成，实测余量尚未改变。加料前请先点击开始补入。",
                  )}
                </Banner>
              )}
              {["awaiting_reconciliation", "needs_review"].includes(
                selectedTask.state,
              ) && (
                <>
                  <p className="muted">
                    {t(
                      "Add the food, then link the measured increase to this batch.",
                      "补入食物后，将实测增重关联至此批次。",
                    )}
                  </p>
                  <label>
                    {t("Measured increase", "实测增重")}
                    <select
                      value={eventId}
                      onChange={(e) => setEventId(e.target.value)}
                    >
                      <option value="">
                        {t("Select a measurement", "选择测量记录")}
                      </option>
                      {selectedTask.eligible_events.map((e) => (
                        <option key={e.id} value={e.id}>
                          {clock(e.at)} · +{number(e.delta_g)} g
                        </option>
                      ))}
                    </select>
                  </label>
                  {!selectedTask.eligible_events.length && (
                    <p className="caption">
                      {t(
                        "Waiting for a new, valid weight increase.",
                        "等待新的有效增重。",
                      )}
                    </p>
                  )}
                </>
              )}
              {selectedTask.note && <p>{selectedTask.note}</p>}
              {canWrite && owned && (
                <div className="batch-actions">
                  {selectedTask.state === "planned" && (
                    <button
                      className="primary"
                      disabled={disabled}
                      onClick={() => void act("start")}
                    >
                      {label("start")}
                    </button>
                  )}
                  {selectedTask.state === "in_progress" && (
                    <button
                      className="primary"
                      disabled={disabled}
                      onClick={() => void act("mark_ready")}
                    >
                      {label("mark_ready")}
                    </button>
                  )}
                  {selectedTask.state === "ready" && (
                    <button
                      className="primary"
                      disabled={disabled || s.availability === "unknown"}
                      onClick={() => void act("begin_replenishment")}
                    >
                      {label("begin_replenishment")}
                    </button>
                  )}
                  {(selectedTask.state === "awaiting_reconciliation" ||
                    (selectedTask.state === "needs_review" &&
                      context.role === "manager")) && (
                    <button
                      className="primary"
                      disabled={disabled || !eventId}
                      onClick={() => void act("confirm_replenishment")}
                    >
                      {label("confirm_replenishment")}
                    </button>
                  )}
                  {[
                    "planned",
                    "in_progress",
                    "ready",
                    "awaiting_reconciliation",
                    "needs_review",
                  ].includes(selectedTask.state) && (
                    <details>
                      <summary>{t("Other actions", "其他操作")}</summary>
                      <label>
                        {t("Reason", "原因")}
                        <textarea
                          maxLength={500}
                          value={reason}
                          onChange={(e) => setReason(e.target.value)}
                        />
                      </label>
                      {["planned", "in_progress", "ready"].includes(
                        selectedTask.state,
                      ) && (
                        <button
                          disabled={disabled || !reason.trim()}
                          onClick={() => void act("cancel")}
                        >
                          {label("cancel")}
                        </button>
                      )}
                      {selectedTask.state === "awaiting_reconciliation" && (
                        <button
                          disabled={disabled || !reason.trim()}
                          onClick={() => void act("request_review")}
                        >
                          {label("request_review")}
                        </button>
                      )}
                      {selectedTask.state === "needs_review" &&
                        context.role === "manager" && (
                          <button
                            disabled={disabled || !reason.trim()}
                            onClick={() => void act("close_unverified")}
                          >
                            {label("close_unverified")}
                          </button>
                        )}
                    </details>
                  )}
                </div>
              )}
              {!owned && canWrite && (
                <p className="muted">
                  {t(
                    "Another team member is responsible for this batch.",
                    "此批次由另一位成员负责。",
                  )}
                </p>
              )}
            </>
          ) : (
            <Empty>
              {t(
                "This batch is no longer in the current session.",
                "此批次已不属于当前会话。",
              )}
            </Empty>
          )}
        </Dialog>
      )}
    </>
  );
}
