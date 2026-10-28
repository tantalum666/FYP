import type { Translate } from "../types";
import { activityState, type ToolCall } from "./tool-activity-state";

export type { ToolCall };

export function ToolActivity({
  t,
  calls,
}: {
  t: Translate;
  calls: ToolCall[] | null;
}) {
  const state = activityState(calls, t);
  if (state.kind === "hidden") return null;
  return (
    <section
      className="tool-activity"
      aria-label={t("Tool activity", "工具记录")}
    >
      <h3>{t("Tool activity", "工具记录")}</h3>
      {state.kind === "empty" ? (
        <p className="workspace-hint">
          {t("No tool calls yet.", "还没有工具调用。")}
        </p>
      ) : (
        <ul className="tool-audit">
          {state.rows.map((row) => (
            <li key={row.call.id}>
              <div className="tool-audit-row">
                <strong>{row.call.tool}</strong>
                <span>{row.risk}</span>
                <span>{row.call.outcome}</span>
                <span>
                  {row.call.saved
                    ? t("Saved", "已保存")
                    : t("Not saved", "未保存")}
                </span>
                <span>{row.call.channel}</span>
              </div>
              {row.sentence ? (
                <p className="tool-audit-message">{row.sentence}</p>
              ) : null}
              {row.steps.length > 0 ? (
                <ol className="tool-plan">
                  {row.steps.map((step, index) => (
                    <li key={`${index}-${step}`}>{step}</li>
                  ))}
                </ol>
              ) : null}
              <details>
                <summary>{t("Arguments", "参数")}</summary>
                <pre>{JSON.stringify(row.call.arguments, null, 2)}</pre>
              </details>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
