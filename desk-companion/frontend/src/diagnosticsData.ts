import type { Language } from "./types";

export interface DiagnosticsReport {
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
      label: en ? "Daily cap used" : "今日已用额度",
      value: `${report.provider.cap_used} / ${report.provider.cap_limit}`,
    },
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
