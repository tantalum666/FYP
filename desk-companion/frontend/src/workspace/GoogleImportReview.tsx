import type { EventInput, Translate } from "../types";

export interface RefreshResult {
  at: string;
  start: string;
  end: string;
  updated: number;
  removed: number;
  kept: number;
  conflicts: number;
  unresolved: number;
}

export interface GoogleStatus {
  configured: boolean;
  connected: boolean;
  version: string;
  review_version: string | null;
  connected_at: string | null;
  last_refresh: RefreshResult | null;
}

export function refreshCounts(
  result: Pick<RefreshResult, "updated" | "removed" | "kept">,
  t: Translate,
) {
  return t(
    `${result.updated} updated · ${result.removed} removed · ${result.kept} kept`,
    `更新 ${result.updated} 项 · 移除 ${result.removed} 项 · 保留 ${result.kept} 项`,
  );
}

export function refreshPlan(rows: Array<{ status: string }>, t: Translate) {
  if (!rows.length)
    return t("No verified Google imports in these dates.", "所选日期内没有已核实来源的 Google 副本。");
  const updates = rows.filter((r) => r.status === "changed").length;
  const removals = rows.filter((r) => r.status === "deleted").length;
  const kept = rows.length - updates - removals;
  return t(
    `${updates} to update · ${removals} to remove · ${kept} to keep`,
    `将更新 ${updates} 项 · 移除 ${removals} 项 · 保留 ${kept} 项`,
  );
}

export function importStatus(status: string, t: Translate) {
  switch (status) {
    case "new": return t("New", "新增");
    case "changed": return t("Changed", "已有变化");
    case "deleted": return t("Cancelled on Google · remove local copy", "Google 已取消 · 将移除本地副本");
    case "unavailable": return t("Unavailable on Google · keep local copy", "Google 已无法访问 · 保留本地副本");
    case "conflict": return t("Locally edited · keep local copy", "本地已编辑 · 保留本地副本");
    case "unresolved": return t("Older copy not found in these dates · keep", "在所选日期内未找到旧副本 · 保留");
    case "unsupported": return t("Unsupported Google details · keep", "Google 详情暂不支持 · 保留");
    case "unchanged": return t("Unchanged", "无变化");
    default: return t("Needs review", "需要核实");
  }
}

export function ChangedDetails({ previous, event, t }: {
  previous: EventInput; event: EventInput; t: Translate;
}) {
  const kind = (e: EventInput) => e.all_day ? t("All day", "全天") : t("Timed", "有具体时间");
  const availability = (e: EventInput) => e.busy ? t("Busy", "忙碌") : t("Free", "空闲");
  const fields = [
    [t("Title", "标题"), previous.title, event.title],
    [t("Start", "开始"), previous.start_local.replace("T", " "), event.start_local.replace("T", " ")],
    [t("End", "结束"), previous.end_local.replace("T", " "), event.end_local.replace("T", " ")],
    [t("Time zone", "时区"), previous.timezone, event.timezone],
    [t("Event type", "事项类型"), kind(previous), kind(event)],
    [t("Location", "地点"), previous.location, event.location],
    [t("Notes", "备注"), previous.notes, event.notes],
    [t("Availability", "忙闲"), availability(previous), availability(event)],
  ];
  return (
    <details>
      <summary>{t("Changed details", "查看具体变化")}</summary>
      <dl>
        {fields.map(([label, before, after]) => before !== after && (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{before || "—"} → {after || "—"}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
