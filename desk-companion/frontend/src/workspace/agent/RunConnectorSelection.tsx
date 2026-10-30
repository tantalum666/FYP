import type { Translate } from "../../types";
import type { RunDraft, RunScope } from "./types";

export function RunConnectorSelection({
  draft,
  scope,
  t,
  onChange,
}: {
  draft: RunDraft;
  scope: RunScope;
  t: Translate;
  onChange: (next: RunDraft) => void;
}) {
  const tools = scope.connectors?.tools ?? [];
  const privateSelected =
    draft.source_ids.length +
      draft.task_ids.length +
      draft.event_ids.length +
      draft.personal_context.memory_ids.length >
      0 || !!draft.personal_context.conversation_id;
  return (
    <fieldset>
      <legend>
        {t(
          "Connected tools · public or synthetic data only",
          "已连接工具 · 仅公开或虚构资料",
        )}
      </legend>
      <p className="workspace-hint">
        {t(
          "Choose which operator-configured tools the model may propose. Every call, including a read, pauses for your exact endpoint, arguments and destination review. Selection does not approve sending data or executing a call.",
          "选择允许模型提出调用的已配置工具。每次调用（包括读取）都会暂停，供您审阅确切端点、参数与目的地。选择工具不等于批准发送数据或执行调用。",
        )}
      </p>
      {!tools.length && (
        <p>
          {t(
            "No connector tools are configured. Connecting a tool requires separate operator setup; no account access is created here.",
            "尚未配置连接工具。连接工具需另外由操作人员设置，此处不会创建账号访问权限。",
          )}
        </p>
      )}
      {privateSelected && tools.length > 0 && (
        <p className="agent-notice">
          {t(
            "Connector work cannot include local files, tasks, calendar records, saved facts or conversation history. Clear those selections or create separate work.",
            "连接工具工作不能同时包含本地文件、事务、日历、保存事实或会话历史。请取消这些选择，或另建工作。",
          )}
        </p>
      )}
      <div className="agent-choices">
        {tools.map((tool) => (
          <label className="agent-check" key={tool.tool_id}>
            <input
              type="checkbox"
              checked={draft.connector_tool_ids.includes(tool.tool_id)}
              disabled={
                !draft.connector_tool_ids.includes(tool.tool_id) &&
                (privateSelected ||
                  draft.connector_tool_ids.length >= 8 ||
                  tool.review_required !== true ||
                  tool.data_policy !== "public_or_synthetic")
              }
              onChange={(event) =>
                onChange({
                  ...draft,
                  connector_tool_ids: event.target.checked
                    ? [...draft.connector_tool_ids, tool.tool_id]
                    : draft.connector_tool_ids.filter(
                        (id) => id !== tool.tool_id,
                      ),
                  share_connector_results_with_provider: false,
                  share: false,
                  retain: false,
                })
              }
            />
            <span>
              {tool.connector_id} · {tool.tool_name}
              <small>
                {tool.effect === "write"
                  ? t("May change the target", "可能修改目标")
                  : t(
                      "Read request still sends arguments",
                      "读取请求仍会发送参数",
                    )}
              </small>
              <small>{tool.endpoint}</small>
              <small>{tool.destination_scope}</small>
            </span>
          </label>
        ))}
      </div>
      {draft.connector_tool_ids.length > 0 && (
        <label className="agent-check">
          <input
            type="checkbox"
            checked={draft.share_connector_results_with_provider}
            onChange={(event) =>
              onChange({
                ...draft,
                share_connector_results_with_provider: event.target.checked,
                retain: false,
              })
            }
          />
          <span>
            {t(
              "Allow the reviewed tools’ public or synthetic responses to be sent to the exact model destination selected below so this run can continue. Remote responses are untrusted and are not independently verified.",
              "允许将已审阅工具返回的公开或虚构响应发送至下方选择的确切模型目的地，使此次运行继续。远端响应不可信，也未经独立核验。",
            )}
          </span>
        </label>
      )}
    </fieldset>
  );
}
