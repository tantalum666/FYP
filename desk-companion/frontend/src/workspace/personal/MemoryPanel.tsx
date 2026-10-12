import { useState } from "react";
import { Modal } from "../../components/Dialogs";
import { useDraftGuard } from "../../components/DraftGuard";
import type { Translate } from "../../types";
import type { MemoryCategory, PersonalMemory } from "./types";
import type { PrivateMutation } from "./usePrivateMutation";
import { MutationFeedback } from "./MutationFeedback";

export function memoryCategory(category: MemoryCategory, t: Translate) {
  return {
    fact: t("Fact", "事实"),
    preference: t("Preference", "偏好"),
    decision: t("Decision", "决定"),
  }[category];
}
function MemoryEditor({
  memory,
  mutation,
  onClose,
  onSaved,
  t,
}: {
  memory: PersonalMemory | null;
  mutation: PrivateMutation;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
  t: Translate;
}) {
  const [content, setContent] = useState(memory?.content ?? "");
  const [category, setCategory] = useState<MemoryCategory>(
    memory?.category ?? "fact",
  );
  const dirty =
    content !== (memory?.content ?? "") ||
    category !== (memory?.category ?? "fact");
  const locked = mutation.busy || mutation.pending;
  useDraftGuard(dirty || mutation.pending, mutation.busy);
  return (
    <Modal
      title={
        memory
          ? t("Correct a memory", "更正记忆")
          : t("Add a memory", "添加记忆")
      }
      closeLabel={t("Close memory editor", "关闭记忆编辑")}
      onClose={onClose}
      busy={mutation.busy}
      dirty={dirty || mutation.pending}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const path = memory
            ? `/assistant/memories/${encodeURIComponent(memory.id)}/actions`
            : "/assistant/memories";
          const body = memory
            ? {
                action: "update",
                expected_version: memory.version,
                content,
                category,
              }
            : { content, category };
          void mutation.run(path, body, async () => {
            await onSaved();
            onClose();
          });
        }}
      >
        <p>
          {t(
            "Save only what you want the assistant to remember. This is your explicit record, not a verified external fact. It does not grant permission to take actions.",
            "只保存你希望助理记住的内容。这是你明确提供的记录，不代表外部核实的事实，也不会授予执行动作的权限。",
          )}
        </p>
        <label className="field">
          {t("Category", "类别")}
          <select
            value={category}
            disabled={locked}
            onChange={(e) => setCategory(e.target.value as MemoryCategory)}
          >
            {(["fact", "preference", "decision"] as const).map((c) => (
              <option key={c} value={c}>
                {memoryCategory(c, t)}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          {t("Memory text", "记忆内容")}
          <textarea
            required
            maxLength={1000}
            rows={5}
            value={content}
            disabled={locked}
            onChange={(e) => setContent(e.target.value)}
          />
        </label>
        <MutationFeedback mutation={mutation} t={t} />
        <button className="primary" disabled={locked || !content.trim()}>
          {t("Save this memory", "保存此记忆")}
        </button>
      </form>
    </Modal>
  );
}
export function MemoryPanel({
  memories,
  mutation,
  onClose,
  onSaved,
  t,
}: {
  memories: PersonalMemory[];
  mutation: PrivateMutation;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
  t: Translate;
}) {
  const [editor, setEditor] = useState<PersonalMemory | null | undefined>(
    undefined,
  );
  const [forget, setForget] = useState<PersonalMemory | null>(null);
  const locked = mutation.busy || mutation.pending;
  return (
    <Modal
      title={t("Personal memories", "个人记忆")}
      closeLabel={t("Close memories", "关闭记忆")}
      onClose={onClose}
      busy={mutation.busy}
      dirty={mutation.pending}
    >
      <p>
        {t(
          "Inspect, correct or forget explicit memories. Nothing here is extracted automatically from voice. Stored memory is not a permission to act or proof that a task was completed.",
          "查看、更正或忘记明确保存的记忆。这里不会自动提取语音内容；记忆不是执行授权，也不是事务已完成的证据。",
        )}
      </p>
      <button
        type="button"
        className="secondary"
        disabled={locked || memories.length >= 100}
        onClick={() => setEditor(null)}
      >
        {t("Add memory", "添加记忆")}
      </button>
      <p className="workspace-hint">
        {memories.length} / 100 · {t("active memories", "有效记忆")}
      </p>
      {!memories.length && (
        <p>{t("No memories have been saved.", "尚未保存记忆。")}</p>
      )}
      <ul className="personal-memory-list">
        {memories.map((memory) => (
          <li key={memory.id}>
            <span className="source-badge">
              {memoryCategory(memory.category, t)}
            </span>
            <p className="personal-text">{memory.content}</p>
            <small>
              {memory.source === "confirmed_assistant"
                ? t(
                    "Assistant suggestion approved by you",
                    "你已批准的助理建议",
                  )
                : t("Saved by you", "由你保存")}{" "}
              ·{" "}
              {new Date(memory.updated_at).toLocaleString(t("en-GB", "zh-CN"))}
            </small>
            <div className="workspace-inline-actions">
              <button
                type="button"
                className="secondary"
                disabled={locked}
                onClick={() => setEditor(memory)}
              >
                {t("Correct", "更正")}
              </button>
              <button
                type="button"
                className="text-button"
                disabled={locked}
                onClick={() => setForget(memory)}
              >
                {t("Forget", "忘记")}
              </button>
            </div>
          </li>
        ))}
      </ul>
      <MutationFeedback mutation={mutation} t={t} />
      {editor !== undefined && (
        <MemoryEditor
          memory={editor}
          mutation={mutation}
          onClose={() => setEditor(undefined)}
          onSaved={onSaved}
          t={t}
        />
      )}
      {forget && (
        <Modal
          title={t("Forget this memory?", "忘记这条记忆？")}
          closeLabel={t("Keep memory", "保留记忆")}
          onClose={() => setForget(null)}
          busy={mutation.busy}
          dirty={mutation.pending}
        >
          <p className="personal-text">{forget.content}</p>
          <p>
            {t(
              "This removes the active memory and excludes it from future AI context. Separately saved conversations may still contain the same information; delete those conversations separately. Previously sent provider data and external backups cannot be withdrawn here.",
              "这会移除有效记忆，后续AI上下文不再使用它。单独保存的会话可能仍有相同资料，需另行删除会话；此处无法撤回此前已发送给提供商的数据或外部备份。",
            )}
          </p>
          <MutationFeedback mutation={mutation} t={t} />
          <div className="workspace-inline-actions">
            <button
              type="button"
              className="secondary"
              disabled={mutation.busy}
              onClick={() => setForget(null)}
            >
              {t("Keep memory", "保留记忆")}
            </button>
            <button
              type="button"
              className="primary"
              disabled={locked}
              onClick={() =>
                void mutation.run(
                  `/assistant/memories/${encodeURIComponent(forget.id)}/actions`,
                  { action: "forget", expected_version: forget.version },
                  async () => {
                    setForget(null);
                    await onSaved();
                  },
                )
              }
            >
              {t("Forget this memory", "忘记此记忆")}
            </button>
          </div>
        </Modal>
      )}
    </Modal>
  );
}
