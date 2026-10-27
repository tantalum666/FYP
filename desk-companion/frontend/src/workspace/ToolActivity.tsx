import type { Translate } from "../types";

export interface ToolCall {
  id: number;
  at: string;
  channel: string;
  tool: string;
  risk: string;
  arguments: Record<string, unknown>;
  outcome: string;
  saved: boolean;
  ref_kind: string | null;
  ref_id: string | null;
}

function riskLabel(risk: string, t: Translate) {
  if (risk === "read") return t("Read", "读取");
  if (risk === "draft") return t("Needs approval", "待批准");
  if (risk === "cancel") return t("Cancel", "取消");
  if (risk === "stop") return t("Stop", "停止");
  return t("Refused", "已拒绝");
}

export function ToolActivity({
  t,
  calls,
}: {
  t: Translate;
  calls: ToolCall[] | null;
}) {
  if (!calls) return null;
  return (
    <section className="tool-activity" aria-label={t("Tool activity", "工具记录")}>
      <h3>{t("Tool activity", "工具记录")}</h3>
      {calls.length === 0 ? (
        <p className="workspace-hint">
          {t("No tool calls yet.", "还没有工具调用。")}
        </p>
      ) : (
        <ul className="tool-audit">
          {calls.map((call) => (
            <li key={call.id}>
              <div className="tool-audit-row">
                <strong>{call.tool}</strong>
                <span>{riskLabel(call.risk, t)}</span>
                <span>{call.outcome}</span>
                <span>
                  {call.saved
                    ? t("Saved", "已保存")
                    : t("Not saved", "未保存")}
                </span>
                <span>{call.channel}</span>
              </div>
              <details>
                <summary>{t("Arguments", "参数")}</summary>
                <pre>{JSON.stringify(call.arguments, null, 2)}</pre>
              </details>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
