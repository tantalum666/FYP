import type { Translate } from "../../types";
import type { CapacityDimension, WorkCapacity } from "./workCapacity";
export function capacityBytes(value: number, t: Translate) {
  const unit = value >= 1024 * 1024 ? "MiB" : value >= 1024 ? "KiB" : null;
  if (!unit) return `${value} ${t("bytes", "字节")}`;
  const scaled = value / (unit === "MiB" ? 1024 * 1024 : 1024);
  return `${Number(scaled.toFixed(2))} ${unit}${Number.isInteger(scaled) ? "" : ` (${value} ${t("bytes", "字节")})`}`;
}
export function CapacityLine({
  label,
  value,
  t,
  bytes = false,
}: {
  label: string;
  value: CapacityDimension;
  t: Translate;
  bytes?: boolean;
}) {
  const format = (n: number) => (bytes ? capacityBytes(n, t) : String(n));
  return (
    <li>
      {label}:{" "}
      {value.state === "unavailable"
        ? t(
            "Unavailable; the server checks limits when saving",
            "不可用；保存时由服务端检查上限",
          )
        : value.state === "over_limit"
          ? t(
              "Over limit; accounting needs inspection",
              "已超上限；需要检查保留记录计量",
            ) +
            (value.used === null
              ? ""
              : ` (${format(value.used)}/${format(value.limit)})`)
          : `${format(value.used!)}/${format(value.limit)} · ${format(value.remaining!)} ${t("remaining", "剩余")}`}
      {value.state === "known" && value.remaining === 0 && (
        <> · {t("No remaining capacity", "无剩余额度")}</>
      )}
    </li>
  );
}
export function WorkCapacitySummary({
  value,
  t,
  refresh,
  loading = false,
}: {
  value: WorkCapacity | null;
  t: Translate;
  refresh?: () => void;
  loading?: boolean;
}) {
  const dimensions = value
    ? [
        value.sources.count,
        value.sources.bytes,
        value.runs.count,
        value.artifacts.count,
        value.artifacts.bytes,
        value.watches.count,
      ]
    : [];
  const unavailable =
    !value || dimensions.some((d) => d.state === "unavailable");
  const over = dimensions.some((d) => d.state === "over_limit");
  const full = dimensions.some((d) => d.state === "known" && d.remaining === 0);
  const counts = value
    ? ([
        [t("Sources", "来源"), value.sources.count],
        [t("Work", "工作"), value.runs.count],
        [t("Outputs", "成果"), value.artifacts.count],
        [t("Watches", "关注"), value.watches.count],
      ] as const)
    : [];
  return (
    <details className="agent-capacity">
      <summary>
        <strong>{t("Saved work storage", "已保存内容容量")}</strong>
        {value && (
          <span className="agent-capacity-counts">
            {counts
              .map(
                ([label, dimension]) =>
                  `${label}: ${dimension.used === null ? t("unknown", "未知") : dimension.used}/${dimension.limit}`,
              )
              .join(" · ")}
          </span>
        )}
        {loading ? (
          <span>{t("Reading capacity…", "正在读取容量…")}</span>
        ) : (
          <>
            {unavailable && (
              <span>
                {t(
                  "Capacity unavailable; the server checks limits when saving.",
                  "容量不可用；保存时由服务端检查上限。",
                )}
              </span>
            )}
            {over && (
              <span>
                {t(
                  "Over limit; accounting needs inspection",
                  "已超上限；需要检查保留记录计量",
                )}
              </span>
            )}
            {full && (
              <span>
                {t(
                  "No remaining capacity in one or more limits",
                  "一项或多项额度已无剩余",
                )}
              </span>
            )}
          </>
        )}
      </summary>
      {refresh && (
        <button
          type="button"
          className="secondary"
          disabled={loading}
          onClick={refresh}
        >
          {t("Refresh capacity", "刷新容量")}
        </button>
      )}
      {value && (
        <>
          <ul>
            <CapacityLine
              label={t("Sources", "来源")}
              value={value.sources.count}
              t={t}
            />
            <CapacityLine
              label={t("Source reserved bytes", "来源保留字节")}
              value={value.sources.bytes}
              t={t}
              bytes
            />
            <CapacityLine
              label={t("Work", "工作")}
              value={value.runs.count}
              t={t}
            />
            <CapacityLine
              label={t("Outputs", "成果")}
              value={value.artifacts.count}
              t={t}
            />
            <CapacityLine
              label={t("Output reserved bytes", "成果保留字节")}
              value={value.artifacts.bytes}
              t={t}
              bytes
            />
            <CapacityLine
              label={t("Watch definitions", "关注定义")}
              value={value.watches.count}
              t={t}
            />
          </ul>
          <small>
            {t("Observed", "观察时间")}: {value.observed_at}
          </small>
        </>
      )}
      <p>
        {t(
          "Advisory retained reservations, not disk usage or guaranteed space. Pending or unknown files, earlier outputs and completed work still count. Cancel, archive or download does not free capacity. Existing work and files remain available under their usual access checks; this version has no deletion control.",
          "仅供参考的保留记录计量，并非磁盘使用量或保证可用空间。待处理或状态未知的文件、较早成果和已完成工作仍计入；取消、归档或下载不会释放容量。已有工作与文件仍按原访问检查使用；本版无删除入口。",
        )}
      </p>
    </details>
  );
}

export function OutputCapacityHint({
  value,
  t,
  deterministic,
}: {
  value: WorkCapacity | null;
  t: Translate;
  deterministic: boolean;
}) {
  if (!value)
    return (
      <p>
        {t(
          "Output limits unavailable; the server checks when saving.",
          "成果上限不可用；保存时由服务端检查。",
        )}
      </p>
    );
  return (
    <div className="workspace-hint">
      <p>
        {t(
          "Report-file limits (application files are separate)",
          "报告文件上限（应用文件另计）",
        )}
        : {capacityBytes(value.artifacts.file_bytes, t)}{" "}
        {t("per file", "／文件")} · {value.artifacts.per_run_count}{" "}
        {t("files per run", "文件／运行")} ·{" "}
        {capacityBytes(value.artifacts.per_run_bytes, t)}{" "}
        {t("per run", "／运行")}
      </p>
      {deterministic &&
        value.artifacts.count.remaining !== null &&
        value.artifacts.count.remaining < 2 && (
          <p role="status">
            {t(
              "This observation has fewer than two output slots. The report and evidence pair cannot both receive new reservations. Existing-operation retries remain available; free slots alone never guarantee output capacity.",
              "此次观察剩余成果位置不足两个，报告与证据表无法同时取得新保留位置。同一操作仍可重试；仅有空位也不保证成果容量。",
            )}
          </p>
        )}
    </div>
  );
}
