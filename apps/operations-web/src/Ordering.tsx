import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowUpRight,
  Check,
  Copy,
  PenLine,
  QrCode,
  ShoppingBag,
} from "lucide-react";
import { Banner, Dialog, Empty } from "./components";
import { clock, number, useLabel, useLanguage } from "./i18n";
import { money } from "./orderLabels";
import type { Context, FoodOrder, MenuItem, User } from "./types";
import type { WorkspaceAPI } from "./useWorkspace";
import "./ordering.css";

type Props = { api: WorkspaceAPI; context: Context; user: User };
function Feedback({ api }: { api: WorkspaceAPI }) {
  const { t } = useLanguage(),
    label = useLabel();
  return (
    <>
      {api.error && (
        <Banner>
          {label(api.error)}{" "}
          <button onClick={() => void api.refresh()}>
            {t("Refresh", "刷新")}
          </button>
        </Banner>
      )}
      {api.pending && !api.busy && (
        <Banner>
          {t(
            "The last action is unconfirmed. Check it before continuing.",
            "上一操作结果尚未确认，请先核查。",
          )}{" "}
          <button disabled={api.busy} onClick={() => void api.retry()}>
            {t("Check and retry", "核查并重试")}
          </button>
        </Banner>
      )}
    </>
  );
}
function Header({
  title,
  subtitle,
  api,
}: {
  title: string;
  subtitle: string;
  api: WorkspaceAPI;
}) {
  const { t } = useLanguage();
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <span className="status">
        {api.menu?.data_origin === "replay"
          ? t("Replay data", "回放数据")
          : api.menu?.data_origin === "hardware"
            ? t("Device data", "设备数据")
            : t("Demo data", "演示数据")}
      </span>
    </header>
  );
}

export function OrdersBoard({ api, context, user }: Props) {
  const { t } = useLanguage(),
    label = useLabel();
  const [filter, setFilter] = useState("active"),
    [selected, setSelected] = useState<string | null>(null);
  const active = api.orders.filter((o) =>
    ["submitted", "accepted", "preparing", "ready"].includes(o.state),
  );
  const orders = api.orders.filter(
    (o) =>
      filter === "all" ||
      (filter === "active" && active.includes(o)) ||
      (filter === "closed" && !active.includes(o)) ||
      o.state === filter,
  );
  const order = api.orders.find((o) => o.id === selected);
  return (
    <>
      <Header
        title={t("Orders", "订单工作台")}
        subtitle={t("From acceptance to collection.", "从接单到取餐。")}
        api={api}
      />
      <Feedback api={api} />
      <div className="metrics">
        <div>
          <span>{t("Awaiting acceptance", "待接单")}</span>
          <strong>
            {api.orders.filter((o) => o.state === "submitted").length}
          </strong>
        </div>
        <div>
          <span>{t("Portioning", "配餐中")}</span>
          <strong>
            {api.orders.filter((o) => o.state === "preparing").length}
          </strong>
        </div>
        <div>
          <span>{t("Ready to collect", "待取餐")}</span>
          <strong>
            {api.orders.filter((o) => o.state === "ready").length}
          </strong>
        </div>
      </div>
      <section className="panel">
        <div className="filters">
          {[
            ["active", t("Active", "进行中")],
            ["submitted", t("New", "新订单")],
            ["ready", t("Ready", "待取餐")],
            ["closed", t("Closed", "已结束")],
            ["all", t("All", "全部")],
          ].map(([id, name]) => (
            <button
              key={id}
              className={filter === id ? "selected" : ""}
              aria-pressed={filter === id}
              onClick={() => setFilter(id)}
            >
              {name}
            </button>
          ))}
        </div>
        {orders.length ? (
          <div className="orders-list">
            {orders.map((o) => (
              <button
                className="order-row"
                key={o.id}
                onClick={() => setSelected(o.id)}
              >
                <span className="order-number">#{o.number}</span>
                <div className="order-summary">
                  <strong>
                    {o.lines
                      .map((l) => `${l.quantity} × ${t(l.name_en, l.name_zh)}`)
                      .join(" · ")}
                  </strong>
                  <span className="caption">
                    {clock(o.created_at)} ·{" "}
                    {o.assignee_name ?? t("Unassigned", "尚未分配")}
                    {o.cancellation === "pending"
                      ? " · " + t("Cancellation requested", "申请取消")
                      : ""}
                  </span>
                </div>
                <strong>{money(o.total_minor, o.currency)}</strong>
                <span
                  className={`status ${o.cancellation === "pending" ? "warning" : ""}`}
                >
                  {label("order_state_" + o.state)}
                </span>
                <ArrowUpRight size={18} />
              </button>
            ))}
          </div>
        ) : (
          <Empty>
            {t(
              "Orders placed in the iPhone app will appear here.",
              "顾客通过 iPhone App 提交的订单将在这里显示。",
            )}
          </Empty>
        )}
      </section>
      <p className="page-footer">
        {t(
          "Accepting reserves stock. Collection does not deduct it again.",
          "接单后预留供应，取餐时不再重复扣量。",
        )}
      </p>
      {selected && (
        <Dialog
          title={t("Order", "订单") + " #" + (order?.number ?? "")}
          onClose={() => {
            if (!api.busy) setSelected(null);
          }}
        >
          {order ? (
            <OrderDetails
              key={order.id}
              order={order}
              api={api}
              context={context}
              user={user}
            />
          ) : (
            <Empty>
              {t(
                "This order is no longer in the current service.",
                "此订单已不属于当前餐期。",
              )}
            </Empty>
          )}
        </Dialog>
      )}
    </>
  );
}
function OrderDetails({
  order: o,
  api,
  context,
  user,
}: Props & { order: FoodOrder }) {
  const { t } = useLanguage(),
    label = useLabel();
  const [note, setNote] = useState(""),
    [code, setCode] = useState(""),
    [events, setEvents] = useState<string[]>([]),
    [allowVariance, setAllowVariance] = useState(false),
    [failedVersion, setFailedVersion] = useState<number | null>(null);
  const canAct =
    ["manager", "staff"].includes(context.role) &&
    (context.role === "manager" || !o.assignee_id || o.assignee_id === user.id);
  const disabled = api.busy || !!api.pending || !!api.error;
  const selected = o.eligible_events.filter((e) => events.includes(e.id));
  const actual = selected.reduce((sum, e) => sum - (e.delta_g ?? 0), 0),
    variance = actual !== o.expected_g;
  async function act(action: string) {
    setFailedVersion(null);
    const ok = await api.mutate(`/v1/orders/${o.id}/actions`, {
      expected_version: o.version,
      action,
      note,
      ...(action === "confirm_fulfillment"
        ? {
            physical_event_ids: selected.map((e) => e.id),
            allow_variance: allowVariance,
          }
        : {}),
      ...(action === "collect" ? { pickup_code: code } : {}),
    });
    if (ok) {
      setNote("");
      setCode("");
      setEvents([]);
      setAllowVariance(false);
    } else setFailedVersion(o.version);
  }
  const primary = (name: string, action: string, extraDisabled = false) => (
    <button
      className="primary"
      disabled={disabled || extraDisabled}
      onClick={() => void act(action)}
    >
      {name}
    </button>
  );
  return (
    <div className="order-detail">
      <Feedback api={api} />
      {failedVersion === o.version && !api.error && !api.pending && (
        <Banner>
          {t(
            "The action was not completed. Review the current state and try again.",
            "操作尚未完成，请复核最新状态后重试。",
          )}
        </Banner>
      )}
      <div className="batch-summary">
        <span className="status">{label("order_state_" + o.state)}</span>
        <strong>{money(o.total_minor, o.currency)}</strong>
      </div>
      <div className="receipt-lines">
        {o.lines.map((l) => (
          <div key={l.id}>
            <div>
              <strong>
                {l.quantity} × {t(l.name_en, l.name_zh)}
              </strong>
              <small>
                {l.stock_source === "measured"
                  ? `${number((l.portion_g ?? 0) * l.quantity)} g · ${t("Measured", "称重")}`
                  : t("Kitchen stock", "人工份数")}
              </small>
            </div>
            <span>{money(l.quantity * l.unit_price_minor, o.currency)}</span>
          </div>
        ))}
      </div>
      <dl className="facts">
        <div>
          <dt>{t("Reserved weight", "已预留重量")}</dt>
          <dd>{number(o.reserved_g)} g</dd>
        </div>
        {o.expected_g > 0 && (
          <div>
            <dt>{t("Measured portion", "实测配出")}</dt>
            <dd>{number(o.actual_g)} g</dd>
          </div>
        )}
        <div>
          <dt>{t("Payment", "结算")}</dt>
          <dd>{t("At counter · unverified", "现场结算 · 未核实")}</dd>
        </div>
      </dl>
      {o.cancellation === "pending" && (
        <Banner>
          {t(
            "The customer requested cancellation. Decide before portioning.",
            "顾客申请取消，请在配餐前处理。",
          )}
        </Banner>
      )}
      {o.note && <p className="muted">{o.note}</p>}
      {canAct && (
        <div className="order-actions">
          {o.state === "submitted" && (
            <>
              {primary(t("Accept order", "接受订单"), "accept")}
              <details>
                <summary>{t("Decline this order", "拒绝此订单")}</summary>
                <label>
                  {t("Reason", "原因")}
                  <textarea
                    value={note}
                    maxLength={500}
                    onChange={(e) => setNote(e.target.value)}
                  />
                </label>
                <button
                  disabled={disabled || !note.trim()}
                  onClick={() => void act("reject")}
                >
                  {t("Decline order", "拒绝订单")}
                </button>
              </details>
            </>
          )}
          {o.state === "accepted" &&
            (o.cancellation === "pending" ? (
              <>
                <label>
                  {t("Response reason", "处理原因")}
                  <textarea
                    value={note}
                    maxLength={500}
                    onChange={(e) => setNote(e.target.value)}
                  />
                </label>
                <div className="button-pair">
                  {primary(
                    t("Approve cancellation", "同意取消"),
                    "approve_cancel",
                    !note.trim(),
                  )}
                  <button
                    disabled={disabled || !note.trim()}
                    onClick={() => void act("deny_cancel")}
                  >
                    {t("Keep order", "保留订单")}
                  </button>
                </div>
              </>
            ) : (
              primary(t("Begin portioning", "开始配餐"), "begin_preparation")
            ))}
          {o.state === "preparing" && (
            <>
              {o.expected_g > 0 ? (
                <>
                  <p className="muted">
                    {t(
                      `Portion ${number(o.expected_g)} g, then select the matching weight decreases.`,
                      `配出 ${number(o.expected_g)} 克后，选择对应的减重记录。`,
                    )}
                  </p>
                  <fieldset className="event-options">
                    <legend>{t("Weight decreases", "减重记录")}</legend>
                    {o.eligible_events.length ? (
                      o.eligible_events.map((e) => (
                        <label key={e.id} className="check-row">
                          <input
                            type="checkbox"
                            checked={events.includes(e.id)}
                            onChange={(ev) =>
                              setEvents((old) =>
                                ev.target.checked
                                  ? [...old, e.id]
                                  : old.filter((v) => v !== e.id),
                              )
                            }
                          />
                          <span>
                            {clock(e.at)} · {number(-(e.delta_g ?? 0))} g
                          </span>
                        </label>
                      ))
                    ) : (
                      <p className="caption">
                        {t(
                          "Waiting for a new valid weight decrease.",
                          "等待新的有效减重。",
                        )}
                      </p>
                    )}
                  </fieldset>
                  <p>
                    {t("Selected", "已选择")} {number(actual)} g /{" "}
                    {number(o.expected_g)} g
                  </p>
                  {variance && selected.length > 0 && (
                    <>
                      {context.role === "manager" ? (
                        <>
                          <label className="check-row">
                            <input
                              type="checkbox"
                              checked={allowVariance}
                              onChange={(e) =>
                                setAllowVariance(e.target.checked)
                              }
                            />
                            <span>
                              {t(
                                "I have checked this portion variance",
                                "我已核对这次份量偏差",
                              )}
                            </span>
                          </label>
                          <label>
                            {t("Review reason", "复核原因")}
                            <textarea
                              maxLength={500}
                              value={note}
                              onChange={(e) => setNote(e.target.value)}
                            />
                          </label>
                        </>
                      ) : (
                        <Banner>
                          {t(
                            "The amount differs. Ask a manager to review it.",
                            "份量存在偏差，请管理员复核。",
                          )}
                        </Banner>
                      )}
                    </>
                  )}
                </>
              ) : (
                <p className="muted">
                  {t(
                    "Confirm only after these portions have been prepared. Kitchen stock will be reduced once.",
                    "请在实际配餐后确认，人工库存只扣减一次。",
                  )}
                </p>
              )}
              {primary(
                t("Confirm portioning", "确认配出"),
                "confirm_fulfillment",
                o.expected_g > 0 &&
                  (!selected.length ||
                    (variance &&
                      !(
                        context.role === "manager" &&
                        allowVariance &&
                        note.trim()
                      ))),
              )}
            </>
          )}
          {o.state === "ready" && (
            <>
              <label>
                {t("Customer collection code", "顾客取餐码")}
                <input
                  inputMode="numeric"
                  autoComplete="off"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                />
              </label>
              {primary(
                t("Confirm collection", "确认取餐"),
                "collect",
                code.length !== 6,
              )}
            </>
          )}
        </div>
      )}
      {!canAct &&
        ["submitted", "accepted", "preparing", "ready"].includes(o.state) && (
          <p className="caption">
            {t(
              "Only the assigned staff member or a manager can update this order.",
              "仅负责人或管理员可以更新此订单。",
            )}
          </p>
        )}
      <details className="order-history">
        <summary>{t("Order history", "订单记录")}</summary>
        {o.history.map((h) => (
          <div key={h.id}>
            <time>{clock(h.at)}</time>
            <span>
              {label("order_" + h.action)}
              {h.note && <small>{h.note}</small>}
            </span>
          </div>
        ))}
      </details>
    </div>
  );
}

export function MenuManager({ api, context }: Props) {
  const { t } = useLanguage();
  const [editing, setEditing] = useState<MenuItem | null>(null),
    [qr, setQr] = useState(""),
    [copied, setCopied] = useState(false),
    [qrError, setQrError] = useState(false);
  const menu = api.menu,
    isManager = context.role === "manager";
  useEffect(() => {
    let current = true,
      url = "";
    setQr("");
    setQrError(false);
    fetch(`/v1/workspaces/${context.id}/menu-qr.svg`, {
      headers: { "X-Context-ID": context.id },
    })
      .then((r) => {
        if (!r.ok) throw Error();
        return r.blob();
      })
      .then((blob) => {
        url = URL.createObjectURL(blob);
        if (current) setQr(url);
        else URL.revokeObjectURL(url);
      })
      .catch(() => {
        if (current) setQrError(true);
      });
    return () => {
      current = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [context.id, menu?.menu_code]);
  async function service(value: string) {
    if (!menu) return;
    await api.mutate(`/v1/workspaces/${context.id}/service`, {
      expected_version: menu.service_version,
      service_type: value,
    });
  }
  return (
    <>
      <Header
        title={t("Menu & service", "菜单与供餐")}
        subtitle={t(
          "What guests see. What the kitchen can serve.",
          "让顾客看到厨房能够供应的菜品。",
        )}
        api={api}
      />
      <Feedback api={api} />
      {menu ? (
        <>
          <div className="menu-service">
            <div>
              <strong>{t("Monitored station", "监测餐位")}</strong>
              <p className="caption">
                {t(
                  "Choose one serving workflow for the current pan.",
                  "为当前餐盘选择一种供餐方式。",
                )}
              </p>
            </div>
            <select
              aria-label={t("Serving workflow", "供餐方式")}
              disabled={!isManager || api.busy || !!api.pending || !!api.error}
              value={menu.service_type}
              onChange={(e) => void service(e.target.value)}
            >
              <option value="buffet_self_service">
                {t("Buffet · guests serve themselves", "自助餐 · 顾客自取")}
              </option>
              <option value="staff_portioned">
                {t("Counter · staff portion orders", "自选快餐 · 员工配餐")}
              </option>
            </select>
          </div>
          <div className="menu-management">
            <section className="panel">
              <div className="menu-panel-heading">
                <h2>{t("Current menu", "当前菜单")}</h2>
                <span className="caption">
                  {menu.items.length} {t("items", "项")}
                </span>
              </div>
              {menu.items.map((item) => (
                <div className="menu-item-row" key={item.id}>
                  <img
                    src={`/menu/${item.slug}.png`}
                    alt={t(item.name_en, item.name_zh)}
                  />
                  <div className="menu-item-info">
                    <h3>{t(item.name_en, item.name_zh)}</h3>
                    <p>{t(item.description_en, item.description_zh)}</p>
                    <div className="menu-tags">
                      <span className="status">
                        {item.stock_source === "measured"
                          ? t("Measured", "称重估算")
                          : t("Kitchen stock", "人工份数")}
                      </span>
                      {!item.published && (
                        <span className="status warning">
                          {t("Unpublished", "未发布")}
                        </span>
                      )}
                      {!item.enabled && (
                        <span className="status warning">
                          {t("Paused", "暂停供应")}
                        </span>
                      )}
                    </div>
                    <p className="caption">
                      {item.available_portions === null
                        ? t("Availability unknown", "供应待确认")
                        : t(
                            `${item.available_portions} portions available`,
                            `${item.available_portions} 份可供`,
                          )}
                      {item.reserved_portions > 0
                        ? ` · ${item.reserved_portions} ${t("reserved", "已预留")}`
                        : ""}{" "}
                      · {t("Updated", "更新于")} {clock(item.updated_at)}
                    </p>
                  </div>
                  <div className="menu-item-price">
                    <strong>{money(item.price_minor, item.currency)}</strong>
                    {isManager && (
                      <button
                        aria-label={t(
                          `Edit ${item.name_en}`,
                          `编辑${item.name_zh}`,
                        )}
                        disabled={api.busy || !!api.pending}
                        onClick={() => setEditing(item)}
                      >
                        <PenLine size={16} />
                        {t("Edit", "编辑")}
                      </button>
                    )}
                  </div>
                </div>
              ))}
              <p className="caption menu-image-note">
                {t(
                  "Illustrative dish photos. Demonstration prices.",
                  "菜品图片为示意，价格为演示数据。",
                )}
              </p>
            </section>
            <aside className="panel qr-panel">
              <QrCode size={25} />
              <h2>{t("Open the menu", "进入菜单")}</h2>
              <p className="muted">
                {t(
                  "Scan in the Senplate iPhone app, or enter the menu code.",
                  "在 Senplate iPhone App 扫码，或输入菜单代码。",
                )}
              </p>
              {qr ? (
                <img
                  src={qr}
                  alt={t("Restaurant menu QR code", "餐厅菜单二维码")}
                />
              ) : (
                <p>
                  {qrError
                    ? t(
                        "QR code could not load. Use the code below.",
                        "二维码暂未载入，可使用下方代码。",
                      )
                    : t("Loading…", "正在载入…")}
                </p>
              )}
              <code>{menu.menu_code}</code>
              <button
                onClick={() => {
                  void navigator.clipboard
                    .writeText(menu.menu_code)
                    .then(() => setCopied(true))
                    .catch(() => setCopied(false));
                }}
              >
                {copied ? <Check size={16} /> : <Copy size={16} />}{" "}
                {copied ? t("Copied", "已复制") : t("Copy code", "复制代码")}
              </button>
              <p className="caption">
                {t(
                  "This code opens the menu. It does not grant staff access.",
                  "此代码只用于进入菜单，不授予工作权限。",
                )}
              </p>
            </aside>
          </div>
        </>
      ) : (
        <Empty>{t("Loading menu…", "正在载入菜单…")}</Empty>
      )}
      {editing && (
        <Dialog
          title={t("Edit menu item", "编辑菜品")}
          onClose={() => {
            if (!api.busy) setEditing(null);
          }}
        >
          <MenuEditor
            key={`${editing.id}:${editing.version}`}
            item={editing}
            api={api}
            onDone={() => setEditing(null)}
            onReload={() => {
              const current = api.menu?.items.find((x) => x.id === editing.id);
              if (current) setEditing(current);
            }}
          />
        </Dialog>
      )}
    </>
  );
}
function MenuEditor({
  item,
  api,
  onDone,
  onReload,
}: {
  item: MenuItem;
  api: WorkspaceAPI;
  onDone: () => void;
  onReload: () => void;
}) {
  const { t } = useLanguage(),
    label = useLabel();
  const [draft, setDraft] = useState(item),
    [price, setPrice] = useState((item.price_minor / 100).toFixed(2));
  const field = (
    key:
      | "name_en"
      | "name_zh"
      | "description_en"
      | "description_zh"
      | "allergens_en"
      | "allergens_zh",
    name: string,
  ) => (
    <label>
      {name}
      <input
        maxLength={
          key.startsWith("name") ? 120 : key.startsWith("allergens") ? 200 : 500
        }
        required={key.startsWith("name")}
        value={draft[key]}
        onChange={(e) => setDraft({ ...draft, [key]: e.target.value })}
      />
    </label>
  );
  async function submit(e: FormEvent) {
    e.preventDefault();
    const {
      name_en,
      name_zh,
      description_en,
      description_zh,
      allergens_en,
      allergens_zh,
      published,
      enabled,
      manual_stock,
    } = draft;
    const ok = await api.mutate(`/v1/menu-items/${item.id}/actions`, {
      expected_version: item.version,
      name_en,
      name_zh,
      description_en,
      description_zh,
      allergens_en,
      allergens_zh,
      published,
      enabled,
      manual_stock,
      price_minor: Math.round(Number(price) * 100),
    });
    if (ok) onDone();
  }
  return (
    <form className="menu-editor" onSubmit={(e) => void submit(e)}>
      {api.error && (
        <Banner>
          {label(api.error)}{" "}
          <button type="button" onClick={onReload}>
            {t("Reload latest values", "重新载入最新内容")}
          </button>
        </Banner>
      )}
      <div className="form-pair">
        {field("name_en", t("Name · English", "名称 · 英文"))}
        {field("name_zh", t("Name · Simplified Chinese", "名称 · 简体中文"))}
      </div>
      {field("description_en", t("Description · English", "说明 · 英文"))}
      {field(
        "description_zh",
        t("Description · Simplified Chinese", "说明 · 简体中文"),
      )}
      <div className="form-pair">
        <label>
          {t("Price (HKD)", "价格（港元）")}
          <input
            type="number"
            min="0"
            max="1000"
            step="0.01"
            required
            value={price}
            onChange={(e) => setPrice(e.target.value)}
          />
        </label>
        {item.stock_source === "manual" && (
          <label>
            {t("Kitchen stock (portions)", "厨房库存（份）")}
            <input
              type="number"
              min="0"
              max="10000"
              step="1"
              required
              value={draft.manual_stock}
              onChange={(e) =>
                setDraft({ ...draft, manual_stock: Number(e.target.value) })
              }
            />
          </label>
        )}
      </div>
      {field(
        "allergens_en",
        t("Allergen information · English", "过敏原资料 · 英文"),
      )}
      {field(
        "allergens_zh",
        t("Allergen information · Simplified Chinese", "过敏原资料 · 简体中文"),
      )}
      <label className="check-row">
        <input
          type="checkbox"
          checked={draft.published}
          onChange={(e) => setDraft({ ...draft, published: e.target.checked })}
        />
        <span>{t("Published on the menu", "发布到菜单")}</span>
      </label>
      <label className="check-row">
        <input
          type="checkbox"
          checked={draft.enabled}
          onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
        />
        <span>{t("Available for service", "开放供应")}</span>
      </label>
      <button className="primary" disabled={api.busy || !!api.pending}>
        {t("Save changes", "保存修改")}
      </button>
    </form>
  );
}

export function OrderAttention({
  api,
  onOpen,
}: {
  api: WorkspaceAPI;
  onOpen: () => void;
}) {
  const { t } = useLanguage();
  const count = api.orders.filter(
    (o) => o.state === "submitted" || o.cancellation === "pending",
  ).length;
  if (!count) return null;
  return (
    <button className="order-attention" onClick={onOpen}>
      <ShoppingBag size={21} />
      <span>
        {t(
          `${count} ${count === 1 ? "order needs" : "orders need"} attention`,
          `${count} 个订单需要处理`,
        )}
      </span>
      <ArrowUpRight size={19} />
    </button>
  );
}
