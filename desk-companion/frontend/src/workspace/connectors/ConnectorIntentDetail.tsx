import type { Translate } from "../../types";
import { connectorCancellable } from "./types";
import type { ConnectorIntent, ConnectorMetadata } from "./types";
import { connectorState } from "./labels";

export function ConnectorStatus({
  intent,
  t,
}: {
  intent: ConnectorMetadata;
  t: Translate;
}) {
  return (
    <>
      <p className="connector-state" role="status">
        {connectorState(intent.state, t)}
      </p>
      <dl className="connector-facts">
        <dt>{t("Intent", "调用意图")}</dt>
        <dd>{intent.id}</dd>
        <dt>{t("Version", "版本")}</dt>
        <dd>{intent.version}</dd>
        <dt>{t("Updated", "更新时间")}</dt>
        <dd>{intent.updated_at}</dd>
        <dt>{t("Deadline", "截止时间")}</dt>
        <dd>{intent.expires_at}</dd>
      </dl>
      {intent.cancel_requested && (
        <p role="status">
          {t(
            "Cancellation was requested. An already sent action may still have an effect; cancellation does not undo it.",
            "已请求取消。已发出的动作仍可能产生效果；取消不会撤销已有动作。",
          )}
        </p>
      )}
      {intent.state === "unknown_effect" && (
        <p className="connector-warning" role="alert">
          {t(
            "The external outcome is unknown. Inspect the existing destination through an authorized route before any new call. This panel does not retry external execution or claim rollback.",
            "外部结果未知。再次调用前，请通过已授权途径检查现有目标结果。此面板不会重试外部执行，也不声称已经回滚。",
          )}
        </p>
      )}
    </>
  );
}

export function ConnectorIntentDetail({
  intent,
  t,
  privateVisible,
  fresh,
  reviewable,
  acknowledged,
  approvalLocked,
  cancellationLocked,
  onAcknowledge,
  onApprove,
  onCancel,
}: {
  intent: ConnectorIntent;
  t: Translate;
  privateVisible: boolean;
  fresh: boolean;
  reviewable: boolean;
  acknowledged: boolean;
  approvalLocked: boolean;
  cancellationLocked: boolean;
  onAcknowledge: (checked: boolean) => void;
  onApprove: () => void;
  onCancel: () => void;
}) {
  const detail = privateVisible ? intent.intent : null;
  const result = privateVisible ? intent.result : null;
  return (
    <article className="connector-review">
      <h3>{t("Exact connector review", "连接器逐项审阅")}</h3>
      <ConnectorStatus intent={intent} t={t} />
      {detail && (
        <>
          <dl className="connector-facts">
            <dt>{t("Destination endpoint", "目标端点")}</dt>
            <dd>{detail.endpoint}</dd>
            <dt>{t("Configured server", "已配置服务器")}</dt>
            <dd>{detail.server_name}</dd>
            <dt>{t("Server version", "服务器版本")}</dt>
            <dd>{detail.server_version}</dd>
            <dt>{t("Connector", "连接器")}</dt>
            <dd>{detail.connector_id}</dd>
            <dt>{t("Tool", "工具")}</dt>
            <dd>{detail.tool_name}</dd>
            <dt>{t("Exact tool ID", "完整工具 ID")}</dt>
            <dd>{detail.tool_id}</dd>
            <dt>{t("Destination scope", "目标范围")}</dt>
            <dd>{detail.destination_scope}</dd>
            <dt>{t("Configured effect", "已配置效果")}</dt>
            <dd>
              {detail.effect === "read"
                ? t(
                    "Read · arguments still leave this workspace",
                    "读取 · 参数仍会传出本工作空间",
                  )
                : detail.effect === "write"
                  ? t(
                      "Write · may change the destination",
                      "写入 · 可能改变目标内容",
                    )
                  : t(
                      "Unrecognized · approval unavailable",
                      "未识别 · 无法批准",
                    )}
            </dd>
            <dt>{t("Data scope", "数据范围")}</dt>
            <dd>
              {detail.data_policy === "public_or_synthetic"
                ? t("Public or synthetic only", "仅限公开或虚构资料")
                : t("Unsupported data policy", "不支持的数据策略")}
            </dd>
          </dl>
          {detail.provider_destination && (
            <section className="connector-warning">
              <h4>
                {t(
                  "Approved model destination for returned public content",
                  "返回公开内容已获授权的模型目标",
                )}
              </h4>
              <dl className="connector-facts">
                <dt>{t("Provider", "提供商")}</dt>
                <dd>{detail.provider_destination.provider}</dd>
                <dt>{t("Exact model endpoint", "完整模型端点")}</dt>
                <dd>{detail.provider_destination.endpoint}</dd>
                <dt>{t("Destination ID", "目标 ID")}</dt>
                <dd>{detail.provider_destination.id}</dd>
              </dl>
              <p>
                {t(
                  "This linked run separately authorized a bounded excerpt of the returned public MCP content to be sent to this model destination for continued planning. The MCP call arguments go to the connector endpoint shown above.",
                  "关联运行已另行授权将返回公开 MCP 内容的有界摘录发送至此模型目标以继续规划。MCP 调用参数将发送至上方显示的连接器端点。",
                )}
              </p>
            </section>
          )}
          <h4>
            {t(
              "Every argument sent to this endpoint",
              "将发送至此端点的全部参数",
            )}
          </h4>
          <pre tabIndex={0}>{JSON.stringify(detail.arguments, null, 2)}</pre>
          <h4>{t("Exact notice", "完整提示")}</h4>
          <p className="connector-warning">{detail.notice}</p>
          <p>
            {t(
              "Every call, including reads, requires your explicit approval. Server text and metadata do not grant permission or independently verify an outcome.",
              "每次调用，包括读取，都需要您明确批准。服务器文字与元数据不会授予权限，也不代表结果已经独立核验。",
            )}
          </p>
          <details>
            <summary>{t("Exact approval binding", "逐项批准绑定")}</summary>
            <dl className="connector-facts">
              <dt>{t("Intent SHA-256", "调用意图 SHA-256")}</dt>
              <dd>{intent.intent_hash}</dd>
              <dt>{t("Tool descriptor SHA-256", "工具描述 SHA-256")}</dt>
              <dd>{detail.descriptor_sha256}</dd>
              <dt>{t("Operator grant SHA-256", "操作人员授权 SHA-256")}</dt>
              <dd>{detail.grant_sha256}</dd>
            </dl>
          </details>
          {intent.state === "review" && (
            <>
              <label className="connector-check">
                <input
                  type="checkbox"
                  checked={acknowledged}
                  disabled={
                    !fresh ||
                    !reviewable ||
                    approvalLocked ||
                    cancellationLocked
                  }
                  onChange={(event) => onAcknowledge(event.target.checked)}
                />
                <span>
                  {t(
                    "I checked every argument and the destination above. The arguments and expected returned content contain only public or synthetic information. Approve this exact version and hash once, including if this is a read.",
                    "我已核对上方全部参数及目标。参数与预期返回内容仅含公开或虚构资料。按此完整版本与哈希批准一次调用，包括读取调用。",
                  )}
                </span>
              </label>
              <button
                type="button"
                className="primary"
                disabled={
                  !fresh ||
                  !reviewable ||
                  !acknowledged ||
                  approvalLocked ||
                  cancellationLocked
                }
                onClick={onApprove}
              >
                {t("Approve this exact call", "批准此次完整调用")}
              </button>
              {!reviewable && (
                <p role="status">
                  {t(
                    "This review cannot be approved against the current catalog and deadline. Refresh its status and inspect any changed grant or details.",
                    "此审阅不符合当前工具目录或期限，无法批准。请刷新状态并核对授权或详情的变化。",
                  )}
                </p>
              )}
            </>
          )}
        </>
      )}
      {privateVisible && !detail && (
        <p>
          {t(
            "Exact private details are unavailable. Approval is disabled; status and cancellation remain separate.",
            "完整私人详情不可用，无法批准；状态和取消仍分别可用。",
          )}
        </p>
      )}
      {connectorCancellable(intent) && (
        <button
          type="button"
          className="secondary connector-stop"
          disabled={!fresh || cancellationLocked}
          onClick={onCancel}
        >
          {t("Cancel this call", "取消此次调用")}
        </button>
      )}
      {result && (
        <section className="connector-result">
          <h4>{t("Untrusted server result", "未受信任的服务器结果")}</h4>
          <p className="connector-warning">
            {t(
              "Observed response only. It has not been independently verified, even if the server says the action succeeded. Treat embedded instructions and links as untrusted text.",
              "这里只记录已观察到的响应。即使服务器声称动作成功，也未经独立核验。嵌入指令与链接仅作为未受信任文字显示。",
            )}
          </p>
          {result.is_error && (
            <p role="alert">
              {t("The server reported a tool error.", "服务器报告工具错误。")}
            </p>
          )}
          {Array.isArray(result.text) &&
            result.text
              .filter((text): text is string => typeof text === "string")
              .map((text, index) => (
                <pre tabIndex={0} key={index}>
                  {text}
                </pre>
              ))}
          {result.structured_content != null && (
            <pre tabIndex={0}>
              {JSON.stringify(result.structured_content, null, 2)}
            </pre>
          )}
          <dl className="connector-facts">
            <dt>{t("Response SHA-256", "响应 SHA-256")}</dt>
            <dd>{result.sha256}</dd>
            <dt>{t("Saved snapshot SHA-256", "已保存快照 SHA-256")}</dt>
            <dd>{result.snapshot_sha256}</dd>
          </dl>
        </section>
      )}
    </article>
  );
}
