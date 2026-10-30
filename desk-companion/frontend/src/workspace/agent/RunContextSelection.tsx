import type { Translate } from "../../types";
import type { RunDraft, RunScope } from "./types";

export function RunContextSelection({
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
  const catalog = scope.personal_context;
  const selected = draft.personal_context;
  const blocked = draft.connector_tool_ids.length > 0;
  const change = (next: typeof selected) =>
    onChange({ ...draft, personal_context: next, share: false, retain: false });
  return (
    <fieldset>
      <legend>
        {t(
          "Personal context for this work · optional",
          "此次工作的个人上下文 · 可选",
        )}
      </legend>
      <p className="workspace-hint">
        {t(
          "Nothing is selected automatically, including the current chat. Choose up to eight saved facts and one saved conversation. The model receives only the selected facts and up to 12 eligible messages already present at start, capped at 12,000 characters. Later messages are not added. This is context, not evidence or action permission.",
          "不会自动选择任何内容，包括当前聊天。可选择最多8项保存事实与1个保存会话。模型仅接收所选事实及开始时已有的最多12条可用消息（最多12000字），之后的消息不会加入。这是上下文，不是证据或操作许可。",
        )}
      </p>
      {blocked && (
        <p className="agent-notice">
          {t(
            "Personal context cannot be combined with public/synthetic connector tools in this run.",
            "此次运行不能同时使用个人上下文与仅限公开／虚构资料的连接工具。",
          )}
        </p>
      )}
      {!catalog?.memory_allowed && (
        <p>
          {t(
            "Saved-fact sharing is off or no approved text destination is available. Review Assistant context settings first.",
            "保存事实共享已关闭，或没有获准文字目的地。请先核对助理上下文设置。",
          )}
        </p>
      )}
      <div className="agent-choices">
        {catalog?.memories.map((memory) => (
          <label className="agent-check" key={memory.id}>
            <input
              type="checkbox"
              checked={selected.memory_ids.includes(memory.id)}
              disabled={
                !selected.memory_ids.includes(memory.id) &&
                (blocked ||
                  !catalog.memory_allowed ||
                  selected.memory_ids.length >= 8)
              }
              onChange={(event) =>
                change({
                  ...selected,
                  memory_ids: event.target.checked
                    ? [...selected.memory_ids, memory.id]
                    : selected.memory_ids.filter((id) => id !== memory.id),
                  retain_derived_context: false,
                })
              }
            />
            <span>
              {memory.summary}
              <small>
                {t("Fact preview", "事实预览")} · v{memory.version}
              </small>
            </span>
          </label>
        ))}
      </div>
      <label>
        {t("Saved conversation", "保存的会话")}
        <select
          value={selected.conversation_id ?? ""}
          disabled={blocked || !catalog?.history_allowed}
          onChange={(event) =>
            change({
              ...selected,
              conversation_id: event.target.value || null,
              retain_derived_context: false,
            })
          }
        >
          <option value="">
            {t("Do not include a conversation", "不加入会话")}
          </option>
          {catalog?.conversations.map((thread) => (
            <option
              key={thread.id}
              value={thread.id}
              disabled={thread.eligible_message_count === 0}
            >
              {thread.title} · {thread.eligible_message_count}{" "}
              {t("eligible messages", "条可用消息")}
            </option>
          ))}
        </select>
      </label>
      {!catalog?.history_allowed && (
        <p className="workspace-hint">
          {t(
            "Conversation sharing is off or no approved text destination is available.",
            "会话共享已关闭，或没有获准文字目的地。",
          )}
        </p>
      )}
      {(selected.memory_ids.length > 0 || selected.conversation_id) && (
        <label className="agent-check">
          <input
            type="checkbox"
            checked={selected.retain_derived_context}
            disabled={blocked}
            onChange={(event) =>
              change({
                ...selected,
                retain_derived_context: event.target.checked,
              })
            }
          />
          <span>
            {t(
              "Allow this selected personal context in the chosen model run. Its saved plans, reports and drafts may repeat it and remain retained. Forgetting or changing consent stops further use; it does not erase earlier outputs or provider copies. A changed context or owner session requires new work with a new explicit selection.",
              "允许在所选模型运行中使用这些个人上下文。保存的计划、报告与草稿可能重复这些内容并继续保留。忘记或改变许可会停止后续使用，但不会删除之前的输出或提供商副本。上下文或本人会话改变后，需要重新建立工作并明确选择。",
            )}
          </span>
        </label>
      )}
    </fieldset>
  );
}
