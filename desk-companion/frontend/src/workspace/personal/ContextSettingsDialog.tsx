import { useState } from "react";
import { Modal } from "../../components/Dialogs";
import { useDraftGuard } from "../../components/DraftGuard";
import type { Translate } from "../../types";
import { contextChoices } from "./types";
import type { ContextSettings } from "./types";
import type { PrivateMutation } from "./usePrivateMutation";
import { MutationFeedback } from "./MutationFeedback";

export function ContextSettingsDialog({
  initial,
  mutation,
  onClose,
  onSaved,
  t,
}: {
  initial: ContextSettings;
  mutation: PrivateMutation;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
  t: Translate;
}) {
  const [baseline] = useState(initial);
  const [form, setForm] = useState(baseline);
  const dirty =
    JSON.stringify(contextChoices(form)) !==
    JSON.stringify(contextChoices(baseline));
  const locked = mutation.busy || mutation.pending;
  useDraftGuard(dirty || mutation.pending, mutation.busy);
  const destinations = form.destinations.filter((x) => x.configured);
  return (
    <Modal
      title={t("Conversation and memory privacy", "会话与记忆隐私")}
      closeLabel={t("Close privacy settings", "关闭隐私设置")}
      onClose={onClose}
      busy={mutation.busy}
      dirty={dirty || mutation.pending}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void mutation.run(
            "/assistant/context-settings",
            contextChoices(form),
            async () => {
              await onSaved();
              onClose();
            },
          );
        }}
      >
        <p>
          {t(
            "Choose separately what is saved locally and what a configured AI service may receive. All options start off. Turning an option on does not call a provider.",
            "分别选择本地保存范围，以及已配置AI服务可接收的资料。默认全部关闭，开启选项本身不会调用服务。",
          )}
        </p>
        <label className="workspace-toggle">
          <span>{t("Allow saved text conversations", "允许保存文字会话")}</span>
          <input
            type="checkbox"
            checked={form.save_text_history}
            disabled={locked}
            onChange={(e) =>
              setForm({ ...form, save_text_history: e.target.checked })
            }
          />
        </label>
        <p className="workspace-hint">
          {t(
            "Only text sent in a selected saved conversation is retained. Temporary chats and voice transcripts are not added automatically. Turning this off keeps existing conversations until you delete them.",
            "仅保存你在已选择的持久会话中发送的文字。临时聊天与语音转写不会自动加入；关闭后，既有会话仍保留，直到你主动删除。",
          )}
        </p>
        <label className="workspace-toggle">
          <span>
            {t(
              "Let AI use saved conversation context",
              "允许AI使用已保存会话作为上下文",
            )}
          </span>
          <input
            type="checkbox"
            checked={form.use_text_history_in_ai}
            disabled={locked}
            onChange={(e) =>
              setForm({ ...form, use_text_history_in_ai: e.target.checked })
            }
          />
        </label>
        <label className="workspace-toggle">
          <span>
            {t("Let AI use approved memories", "允许AI使用已确认记忆")}
          </span>
          <input
            type="checkbox"
            checked={form.use_memory_in_ai}
            disabled={locked}
            onChange={(e) =>
              setForm({ ...form, use_memory_in_ai: e.target.checked })
            }
          />
        </label>
        <label className="workspace-toggle">
          <span>
            {t(
              "Share saved tasks, progress and calendar with configured AI providers",
              "向已配置AI提供商分享已保存事务、进展与日历",
            )}
          </span>
          <input
            type="checkbox"
            checked={form.share_business_context}
            disabled={locked}
            onChange={(e) =>
              setForm({ ...form, share_business_context: e.target.checked })
            }
          />
        </label>
        <p className="workspace-hint">
          {t(
            "These permissions are separate from private-screen visibility. If enabled, relevant saved text, memories, tasks or calendar details may be sent to the services listed below for your requests. Provider charges and retention policies still apply.",
            "这些授权独立于屏幕隐私显示。启用后，处理请求时可将相关已保存文字、记忆、事务或日历内容发送至下列服务，仍适用提供商费用与保留政策。",
          )}
        </p>
        <h3>{t("Approved destinations", "授权目的地")}</h3>
        {destinations.length ? (
          <ul className="personal-destinations">
            {destinations.map((x) => (
              <li key={x.id}>
                <strong>
                  {x.provider} ·{" "}
                  {x.kind === "text" ? t("Text", "文字") : t("Voice", "语音")}
                </strong>
                <span>{x.endpoint}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p>
            {t(
              "No AI provider is configured. No saved context can be sent until a destination is configured and approved.",
              "尚未配置AI提供商。配置并批准目的地之前，不能发送已保存上下文。",
            )}
          </p>
        )}
        {!baseline.authorization_current &&
          (baseline.use_memory_in_ai ||
            baseline.use_text_history_in_ai ||
            baseline.share_business_context) && (
            <p role="status">
              {t(
                "Provider access needs renewed approval. Saved context is not currently authorized for the changed destination.",
                "提供商访问需要重新批准。已有授权不适用于变化后的目的地。",
              )}
            </p>
          )}
        <p>
          {t(
            "Saving with an AI option enabled approves only the displayed destinations. A provider or endpoint change requires review again.",
            "勾选AI选项后保存，只批准当前列出的目的地。更换提供商或端点后需要重新核对。",
          )}
        </p>
        <MutationFeedback mutation={mutation} t={t} />
        <button className="primary" disabled={locked}>
          {mutation.busy
            ? t("Saving…", "保存中…")
            : t("Save privacy choices", "保存隐私选择")}
        </button>
      </form>
    </Modal>
  );
}
