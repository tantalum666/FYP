import type { Language } from "./types";

export interface DiagnosticsReport {
  openai_spending?: {
    day: string;
    allocated_usd: number;
    local_budget_used_usd?: number;
    reserved_or_unpriced_usd?: number;
    observed_usage_estimate_usd?: number;
    available_usd: number;
    last_platform_statement?: {
      amount_usd: string;
      utc_day: string;
      scope: string;
      imported_at: string;
    } | null;
  };
  versions: { service: string; python: string };
  provider: {
    configured: boolean;
    name: string;
    background: boolean;
    cap_used: number;
    cap_limit: number;
  };
  backup: {
    last_at: string | null;
    file_name: string | null;
    bytes: number | null;
    retained: number;
  };
  database: { bytes: number };
  scheduler: { ticks: Record<string, string>; backup: string };
}

export function diagnosticsLines(
  report: DiagnosticsReport,
  language: Language,
) {
  const en = language === "en";
  const spending = report.openai_spending;
  const statement = spending?.last_platform_statement;
  const usd = (v: number | string) => `US$${Number(v).toFixed(2)}`;
  const backup = report.backup.last_at
    ? `${report.backup.file_name} · ${report.backup.bytes} B · ${report.backup.retained}`
    : en
      ? "None yet"
      : "还没有";
  const ticks = Object.entries(report.scheduler.ticks)
    .map(([name, status]) => `${name}: ${status}`)
    .join(", ");
  return [
    { label: en ? "Service" : "服务", value: report.versions.service },
    { label: "Python", value: report.versions.python },
    {
      label: en ? "Provider" : "模型",
      value: report.provider.configured
        ? report.provider.name
        : en
          ? "Not configured"
          : "未配置",
    },
    {
      label: en ? "Follow-up requests today" : "今日后续建议请求数",
      value: `${report.provider.cap_used} / ${report.provider.cap_limit}`,
    },
    ...(spending?.reserved_or_unpriced_usd != null
      ? [
          {
            label: en
              ? "Local reservations / unpriced work"
              : "本地预留与待定费用",
            value: usd(spending.reserved_or_unpriced_usd),
          },
          {
            label: en ? "Local usage estimate" : "基于用量的本地估算",
            value: usd(spending.observed_usage_estimate_usd ?? 0),
          },
          {
            label: en
              ? "Available local allowance (Hong Kong day)"
              : "本地可用额度（香港日）",
            value: `${usd(spending.available_usd)} / ${usd(spending.allocated_usd)}`,
          },
          {
            label: en ? "Latest platform cost export" : "最近导入的平台费用",
            value: statement
              ? `${usd(statement.amount_usd)} · ${statement.utc_day} UTC · ${statement.scope}`
              : en
                ? "No imported statement"
                : "尚未导入费用报表",
          },
        ]
      : []),
    { label: en ? "Last backup" : "最近备份", value: backup },
    {
      label: en ? "Database" : "数据库",
      value: `${report.database.bytes} B`,
    },
    {
      label: en ? "Scheduler" : "调度",
      value: ticks || (en ? "No ticks yet" : "还没有调度"),
    },
  ];
}
