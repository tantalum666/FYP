import { useState } from "react";
import { Modal } from "../../components/Dialogs";
import { useDraftGuard } from "../../components/DraftGuard";
import { errorText } from "../../api";
import type { Translate } from "../../types";
import { ContextSettingsDialog } from "./ContextSettingsDialog";
import { MemoryPanel } from "./MemoryPanel";
import { MutationFeedback } from "./MutationFeedback";
import type { PersonalContext } from "./usePersonalContext";
import type { PrivateMutation } from "./usePrivateMutation";
import type { Conversation, SavedMessage } from "./types";
import { replyMode } from "./types";
import "./personal.css";

export function ModeLabel({ mode, t }: { mode?: string; t: Translate }) {
  const label = replyMode(mode);
  return (
    <span className="source-badge">
      {label === "local"
        ? t("Local rules", "本地规则")
        : label === "ai"
          ? t("AI reply", "AI回复")
          : t("Mode not recorded", "未记录回复模式")}
    </span>
  );
}
export function ProposalStatus({
  state,
  t,
}: {
  state?: string | null;
  t: Translate;
}) {
  const labels: Record<string, string> = {
    pending: t("Draft awaiting your review", "草稿等待你核对"),
    review: t("Draft awaiting your review", "草稿等待你核对"),
    confirmed: t(
      "Draft approved; check the resulting record",
      "草稿已批准，请检查实际记录",
    ),
    cancelled: t("Draft cancelled", "草稿已取消"),
    expired: t("Draft expired", "草稿已过期"),
  };
  return (
    <small>
      {labels[state ?? ""] ??
        t(
          "Proposal status unavailable; check current drafts",
          "草稿状态不可用，请查看当前草稿",
        )}
    </small>
  );
}
export function ConversationHistory({
  messages,
  t,
}: {
  messages: SavedMessage[];
  t: Translate;
}) {
  return (
    <section
      className="personal-history"
      aria-label={t("Saved conversation messages", "已保存的会话消息")}
      tabIndex={0}
    >
      {!messages.length && (
        <p>
          {t(
            "This conversation is empty. Only text you send here will be saved.",
            "此会话尚无消息，只会保存你在这里发送的文字。",
          )}
        </p>
      )}
      <ol>
        {messages.map((message) => (
          <li key={message.id} className={`personal-message ${message.role}`}>
            <strong>
              {message.role === "user"
                ? t("You", "你")
                : t("Assistant", "助理")}
            </strong>
            {message.role === "assistant" && (
              <ModeLabel mode={message.mode} t={t} />
            )}
            <time dateTime={message.created_at}>
              {new Date(message.created_at).toLocaleString(t("en-GB", "zh-CN"))}
            </time>
            <p className="personal-text">{message.content}</p>
            {message.proposal_id && (
              <ProposalStatus state={message.proposal_state} t={t} />
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
function TitleDialog({
  conversation,
  mutation,
  onClose,
  onSaved,
  t,
}: {
  conversation: Conversation | null;
  mutation: PrivateMutation;
  onClose: () => void;
  onSaved: (id: string) => void | Promise<void>;
  t: Translate;
}) {
  const [baseline] = useState(conversation);
  const [title, setTitle] = useState(baseline?.title ?? "");
  const dirty = title !== (baseline?.title ?? "");
  const locked = mutation.busy || mutation.pending;
  useDraftGuard(dirty || mutation.pending, mutation.busy);
  return (
    <Modal
      title={
        conversation
          ? t("Rename conversation", "重命名会话")
          : t("New saved conversation", "新建持久会话")
      }
      closeLabel={t("Close conversation editor", "关闭会话编辑")}
      onClose={onClose}
      busy={mutation.busy}
      dirty={dirty || mutation.pending}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const path = baseline
            ? `/assistant/conversations/${encodeURIComponent(baseline!.id)}/actions`
            : "/assistant/conversations";
          const body = baseline
            ? {
                action: "rename",
                title,
                expected_version: baseline!.version,
              }
            : { title, language: t("en", "zh") };
          void mutation.run<{ conversation?: Conversation }>(
            path,
            body,
            async (result) => {
              const id = result.conversation?.id ?? baseline?.id;
              if (id) await onSaved(id);
              onClose();
            },
          );
        }}
      >
        <label className="field">
          {t("Conversation title", "会话标题")}
          <input
            required
            maxLength={120}
            value={title}
            disabled={locked}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <p>
          {t(
            "Saved locally on your desk. Creating a conversation does not copy your temporary chat or voice transcript.",
            "保存在你的桌面主机。新建会话不会复制临时聊天或语音转写。",
          )}
        </p>
        <MutationFeedback mutation={mutation} t={t} />
        <button className="primary" disabled={locked || !title.trim()}>
          {conversation
            ? t("Save title", "保存标题")
            : t("Create conversation", "创建会话")}
        </button>
      </form>
    </Modal>
  );
}
export function PersonalContextPanel({
  context,
  selected,
  onSelect,
  mutation,
  draftDirty,
  voiceActive,
  t,
}: {
  context: PersonalContext;
  selected: string | null;
  onSelect: (id: string | null, mutationComplete?: boolean) => void;
  mutation: PrivateMutation;
  draftDirty: boolean;
  voiceActive: boolean;
  t: Translate;
}) {
  const [dialog, setDialog] = useState<
    "settings" | "memories" | "new" | "rename" | "delete" | null
  >(null);
  const locked = mutation.busy || mutation.pending;
  const current =
    context.detail?.conversation ??
    context.conversations.find((x) => x.id === selected);
  const ready = !!context.settings && !context.error;
  return (
    <section
      className="personal-context"
      aria-label={t("Conversation and memory", "会话与记忆")}
    >
      <div className="workspace-inline-actions">
        <button
          type="button"
          className="secondary"
          disabled={!ready || locked}
          onClick={() => setDialog("settings")}
        >
          {t("Privacy choices", "隐私选择")}
        </button>
        <button
          type="button"
          className="secondary"
          disabled={!ready || locked}
          onClick={() => setDialog("memories")}
        >
          {t("Personal memories", "个人记忆")} ({context.memories.length})
        </button>
        <button
          type="button"
          className="text-button"
          disabled={context.loading || mutation.busy}
          onClick={() => void context.reload()}
        >
          {t("Refresh saved records", "刷新保存记录")}
        </button>
      </div>
      {context.loading && !ready && (
        <p role="status">{t("Loading saved context…", "正在读取保存内容…")}</p>
      )}
      {!!context.error && (
        <p className="error-message" role="alert">
          {errorText(context.error, t)}
        </p>
      )}
      <label className="field">
        {t("Text conversation", "文字会话")}
        <select
          value={selected ?? ""}
          disabled={locked || voiceActive || !ready}
          onChange={(e) => onSelect(e.target.value || null)}
        >
          <option value="">
            {t(
              "Temporary chat · not added to history",
              "临时聊天 · 不加入历史",
            )}
          </option>
          {selected &&
            !context.conversations.some((x) => x.id === selected) && (
              <option value={selected}>
                {t("Conversation unavailable", "会话不可用")}
              </option>
            )}
          {context.conversations.map((x) => (
            <option key={x.id} value={x.id}>
              {x.title} ({x.message_count})
            </option>
          ))}
        </select>
      </label>
      <div className="workspace-inline-actions">
        <button
          type="button"
          className="secondary"
          disabled={
            locked ||
            voiceActive ||
            !context.settings?.save_text_history ||
            context.conversations.length >= 30
          }
          onClick={() => setDialog("new")}
        >
          {t("New saved conversation", "新建持久会话")}
        </button>
        {current && (
          <>
            <button
              type="button"
              className="text-button"
              disabled={locked || voiceActive}
              onClick={() => setDialog("rename")}
            >
              {t("Rename", "重命名")}
            </button>
            <button
              type="button"
              className="text-button"
              disabled={locked || voiceActive || draftDirty}
              onClick={() => setDialog("delete")}
            >
              {t("Delete conversation", "删除会话")}
            </button>
          </>
        )}
      </div>
      {!context.settings?.save_text_history && (
        <p className="workspace-hint">
          {t(
            "Saving text is off. Enable it in Privacy choices to create or continue a saved conversation. Existing conversations stay readable.",
            "文字保存已关闭。可在隐私选择中启用，再创建或继续持久会话；已有会话仍可阅读。",
          )}
        </p>
      )}
      {voiceActive && (
        <p className="workspace-hint">
          {t(
            "End voice before changing the text conversation. Voice transcripts are not saved into text history.",
            "切换文字会话前请先结束语音。语音转写不会保存到文字历史。",
          )}
        </p>
      )}
      {context.detail && (
        <>
          <p className="workspace-hint">
            {context.detail.conversation.message_count} / 200 ·{" "}
            {t(
              "saved messages; drafts are not proof of completed actions",
              "已保存消息；草稿不代表动作已完成",
            )}
          </p>
          <ConversationHistory messages={context.detail.messages} t={t} />
        </>
      )}
      {dialog === "settings" && context.settings && (
        <ContextSettingsDialog
          initial={context.settings}
          mutation={mutation}
          onClose={() => setDialog(null)}
          onSaved={() => context.reload(true)}
          t={t}
        />
      )}
      {dialog === "memories" && ready && (
        <MemoryPanel
          memories={context.memories}
          mutation={mutation}
          onClose={() => setDialog(null)}
          onSaved={() => context.reload(true)}
          t={t}
        />
      )}
      {(dialog === "new" || (dialog === "rename" && current)) && (
        <TitleDialog
          conversation={dialog === "rename" ? current! : null}
          mutation={mutation}
          onClose={() => setDialog(null)}
          onSaved={async (id) => {
            await context.reload(true);
            if (dialog === "new") onSelect(id, true);
          }}
          t={t}
        />
      )}
      {dialog === "delete" && current && (
        <Modal
          title={t("Delete this conversation?", "删除此会话？")}
          closeLabel={t("Keep conversation", "保留会话")}
          onClose={() => setDialog(null)}
          busy={mutation.busy}
          dirty={mutation.pending}
        >
          <p className="personal-text">{current.title}</p>
          <p>
            {t(
              "This removes its saved text from this workspace and future conversation context. This cannot be undone here. Separately approved memories and task/calendar records remain; previously sent cloud data or external backups are not recalled.",
              "这会移除此工作空间的已保存文字，后续会话上下文也不再使用，此处无法撤销。独立确认的记忆及事务、日历记录保留；不会撤回已发送云端的数据或外部备份。",
            )}
          </p>
          <MutationFeedback mutation={mutation} t={t} />
          <div className="workspace-inline-actions">
            <button
              type="button"
              className="secondary"
              disabled={mutation.busy}
              onClick={() => setDialog(null)}
            >
              {t("Keep conversation", "保留会话")}
            </button>
            <button
              type="button"
              className="primary"
              disabled={locked}
              onClick={() =>
                void mutation.run(
                  `/assistant/conversations/${encodeURIComponent(current.id)}/actions`,
                  { action: "delete", expected_version: current.version },
                  async () => {
                    setDialog(null);
                    onSelect(null, true);
                    await context.reload(true);
                  },
                )
              }
            >
              {t("Delete saved conversation", "删除已保存会话")}
            </button>
          </div>
        </Modal>
      )}
    </section>
  );
}
