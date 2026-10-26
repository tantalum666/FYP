import { useEffect, useRef, type ReactNode } from "react";
import {
  Check,
  ChevronRight,
  CircleAlert,
  ClipboardList,
  X,
} from "lucide-react";
import { clock, number, useLabel, useLanguage } from "./i18n";
import type { Station, Task } from "./types";

export function Brand() {
  return (
    <img className="brand" src="/brand/horizontal-green.svg" alt="Senplate" />
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="empty">
      <ClipboardList size={28} />
      <p>{children}</p>
    </div>
  );
}
export function Banner({ children }: { children: ReactNode }) {
  return (
    <div className="banner" role="status">
      <CircleAlert size={20} />
      <div>{children}</div>
    </div>
  );
}
export function Dialog({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const { t } = useLanguage();
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      aria-label={title}
    >
      <div className="dialog-top">
        <h2>{title}</h2>
        <button
          className="icon-button"
          aria-label={t("Close", "关闭")}
          onClick={onClose}
        >
          <X size={22} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function WeightChart({ station }: { station: Station }) {
  const { t } = useLanguage();
  const points = station.history.slice(-12),
    max = Math.max(1800, ...points.map((p) => p.net_g ?? 0));
  const top = Math.ceil(max / 600) * 600,
    width = 560,
    height = 190;
  const x = (i: number) =>
      60 + (i * (width - 80)) / Math.max(points.length - 1, 1),
    y = (v: number) => 16 + (height - 48) * (1 - v / top);
  return (
    <div className="chart">
      <p className="caption">{t("Remaining (g)", "余量（克）")}</p>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={t("Remaining weight over time", "余量变化趋势")}
      >
        {[0, 1, 2, 3].map((i) => {
          const v = (top * i) / 3;
          return (
            <g key={i}>
              <line
                x1="46"
                x2={width - 6}
                y1={y(v)}
                y2={y(v)}
                className="grid-line"
              />
              <text x="36" y={y(v) + 4} textAnchor="end">
                {number(v)}
              </text>
            </g>
          );
        })}
        {points.map((p, i) => {
          const prev = points[i - 1];
          return (
            <g key={p.id}>
              {prev?.net_g != null && p.net_g != null && (
                <line
                  x1={x(i - 1)}
                  y1={y(prev.net_g)}
                  x2={x(i)}
                  y2={y(p.net_g)}
                  stroke="var(--green)"
                  strokeWidth="2"
                />
              )}
              {p.net_g != null && (
                <>
                  <circle
                    cx={x(i)}
                    cy={y(p.net_g)}
                    r="4.5"
                    fill="var(--green)"
                  />
                  {(points.length <= 5 || i === points.length - 1) && (
                    <text
                      className="point-label"
                      x={x(i)}
                      y={y(p.net_g) - 12}
                      textAnchor="middle"
                    >
                      {number(p.net_g)}
                    </text>
                  )}
                </>
              )}
              {(points.length <= 5 || i === 0 || i === points.length - 1) && (
                <text x={x(i)} y={height - 6} textAnchor="middle">
                  {clock(p.at)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
export function StationCard({
  station: s,
  display = false,
  disconnected = false,
}: {
  station: Station;
  display?: boolean;
  disconnected?: boolean;
}) {
  const { t } = useLanguage();
  const reliable =
    !disconnected &&
    s.measurement_status === "valid" &&
    s.freshness === "fresh" &&
    s.connectivity === "online" &&
    !s.paused;
  const status = disconnected
    ? t("Last snapshot", "最后快照")
    : s.paused
      ? t("Paused", "已暂停")
      : s.connectivity === "offline"
        ? t("Device offline", "设备离线")
        : s.measurement_status === "absent"
          ? t("Pan removed", "容器离位")
          : s.measurement_status !== "valid"
            ? t("Weight unstable", "重量不稳定")
            : s.freshness !== "fresh"
              ? t("Reading is stale", "读数已过时")
              : t("Monitoring", "监测中");
  return (
    <section className={`panel station ${display ? "station-large" : ""}`}>
      <div className="station-header">
        <div>
          <h2>{t("Station 01", "餐位 01")}</h2>
          <p className="food">{t(s.food_name_en, s.food_name)}</p>
        </div>
        <span className={`status ${!reliable ? "warning" : ""}`}>
          <span className="dot" />
          {status}
        </span>
      </div>
      <div className="weight-line">
        <div>
          <div className="weight">
            {number(reliable ? s.net_g : null)} <span>g</span>
          </div>
          <p>{t("Remaining", "当前余量")}</p>
        </div>
        {reliable && (
          <span
            className={`status ${s.availability === "low" ? "warning" : ""}`}
          >
            {s.availability === "low"
              ? t("Refill needed", "需要补餐")
              : s.incoming_g > 0
                ? t("Batch in progress", "批次制作中")
                : t("Available", "供应中")}
          </span>
        )}
      </div>
      {!reliable && (
        <p className="muted">
          {t("Last valid reading", "最后有效读数")} {number(s.last_valid_g)} g ·{" "}
          {clock(s.last_valid_at)}
        </p>
      )}
      {!display && <WeightChart station={s} />}
      <dl className="facts">
        {s.reserved_g > 0 && (
          <>
            <div>
              <dt>{t("Reserved for orders", "订单已预留")}</dt>
              <dd>{number(s.reserved_g)} g</dd>
            </div>
            <div>
              <dt>{t("Unreserved", "未预留")}</dt>
              <dd>{number(reliable ? s.available_to_promise_g : null)} g</dd>
            </div>
          </>
        )}
        <div>
          <dt>{t("Food confirmed", "已确认菜品")}</dt>
          <dd>
            {s.food_binding === "confirmed" ? (
              <>
                <Check size={15} />
                {t("Yes", "是")}
              </>
            ) : (
              t("No", "否")
            )}
          </dd>
        </div>
        <div>
          <dt>{t("Weight stable", "重量稳定")}</dt>
          <dd>
            {s.measurement_status === "valid" ? t("Yes", "是") : t("No", "否")}
          </dd>
        </div>
        {s.vision_status === "occluded" && (
          <div>
            <dt>{t("Camera", "相机")}</dt>
            <dd>{t("View obstructed", "视野被遮挡")}</dd>
          </div>
        )}
      </dl>
      {display && (
        <p className="muted">
          {t("Updated", "更新于")} {clock(s.observed_at)}
        </p>
      )}
    </section>
  );
}
export function TaskList({
  tasks,
  onOpen,
}: {
  tasks: Task[];
  onOpen: (task: Task) => void;
}) {
  const label = useLabel();
  const { t } = useLanguage();
  return (
    <div className="task-list">
      {tasks.map((task) => (
        <button className="task-row" key={task.id} onClick={() => onOpen(task)}>
          <div>
            <strong>{number(task.planned_g)} g</strong>
            <span className="caption">
              {task.assignee_name ?? t("Unassigned", "尚未分配")}
            </span>
          </div>
          <span className="status">{label(task.state)}</span>
          <ChevronRight size={19} aria-hidden="true" />
        </button>
      ))}
    </div>
  );
}
