import type { Translate } from "../../types";
import type { AgentRun } from "./types";

export function RunConnectorResults({
  results,
  t,
  locked,
  onReview,
}: {
  results: NonNullable<AgentRun["tool_results"]>;
  t: Translate;
  locked: boolean;
  onReview?: (id: string) => void;
}) {
  const linked = results.filter(
    (result) =>
      typeof result.result?.connector_intent_id === "string" &&
      /^[a-f0-9]{32}$/.test(result.result.connector_intent_id),
  );
  if (!linked.length) return null;
  return (
    <section>
      <h4>{t("Linked connector calls", "关联连接工具调用")}</h4>
      <p className="workspace-hint">
        {t(
          "Every call needs exact-argument review. A returned MCP response is an untrusted observation, not independently verified target completion. Unknown effects must not be replayed.",
          "每次调用都需要审阅确切参数。MCP返回响应是不可信观察，不是已独立核验的目标完成。不得重放结果未知的操作。",
        )}
      </p>
      {linked.map((result) => (
        <article className="agent-review" key={result.operation_key}>
          <strong>{result.tool}</strong>
          <p role="status">
            {result.state === "pending"
              ? t("Waiting for review or execution", "等待审阅或执行")
              : result.state === "observed"
                ? t(
                    "Remote response observed · not independently verified",
                    "已观察远端响应 · 未独立核验",
                  )
                : result.state === "unknown"
                  ? t("Outcome unknown · do not repeat", "结果未知 · 请勿重复")
                  : t(
                      "Call did not complete with a verified result",
                      "调用未取得已核验结果",
                    )}
          </p>
          <small>{result.result.connector_intent_id as string}</small>
          <button
            type="button"
            className="secondary"
            disabled={locked || !onReview}
            onClick={() =>
              onReview?.(result.result.connector_intent_id as string)
            }
          >
            {t(
              "Open exact connector review and result",
              "打开确切连接工具审阅与结果",
            )}
          </button>
        </article>
      ))}
    </section>
  );
}
