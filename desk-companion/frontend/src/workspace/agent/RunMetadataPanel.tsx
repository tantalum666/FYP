import { useState } from "react";
import { useDraftGuard } from "../../components/DraftGuard";
import type { Translate } from "../../types";
import type { ResponseFence } from "../personal/responseFence";
import { usePrivateMutation } from "../personal/usePrivateMutation";
import { agentError, stateLabel } from "./labels";
import { RequestFeedback } from "./RequestFeedback";
import { metadataActions } from "./runMetadata";
import type { RunMetadata } from "./runMetadata";
import { useRunMetadata } from "./useRunMetadata";

export function RunMetadataPanel({
  t,
  fence,
  epoch,
}: {
  t: Translate;
  fence: ResponseFence;
  epoch: number;
}) {
  const { runs, error, fresh, loading, reload } = useRunMetadata(fence, epoch);
  return (
    <div className="agent-workspace">
      <p className="agent-notice" role="status">
        {t(
          "Private content is hidden. You can inspect current status and pause or cancel work without opening its goal, sources, reviews or files. Show private content to start or continue work.",
          "私人内容已隐藏。您仍可查看当前状态并暂停或取消工作，无需打开目标、来源、审阅或文件。显示私人内容后才能开始或恢复工作。",
        )}
      </p>
      <button
        className="secondary"
        disabled={loading}
        onClick={() => void reload(true)}
      >
        {t("Refresh status", "刷新状态")}
      </button>
      {!!error && (
        <p role="alert" className="error-message">
          {agentError(error, t)}
        </p>
      )}
      {!fresh && runs && (
        <p role="status">
          {t(
            "Status could not be refreshed. Controls are unavailable until the connection recovers.",
            "状态未能刷新。连接恢复前操作不可用。",
          )}
        </p>
      )}
      {loading && !runs && (
        <p role="status">{t("Loading work status…", "正在读取工作状态…")}</p>
      )}
      {runs?.length === 0 && (
        <p>{t("No retained work tasks.", "尚无保留的工作任务。")}</p>
      )}
      {runs?.map((run) => (
        <MetadataControls
          key={run.id}
          run={run}
          t={t}
          fence={fence}
          fresh={fresh}
          onChanged={() => void reload(true)}
        />
      ))}
    </div>
  );
}

export function MetadataControls({
  run,
  t,
  fence,
  fresh,
  onChanged,
}: {
  run: RunMetadata;
  t: Translate;
  fence: ResponseFence;
  fresh: boolean;
  onChanged: () => void;
}) {
  const pause = usePrivateMutation(),
    cancellation = usePrivateMutation();
  const [pauseVersion, setPauseVersion] = useState<number | null>(null),
    [cancelVersion, setCancelVersion] = useState<number | null>(null);
  const pauseLocked = pause.busy || pause.pending,
    cancelLocked = cancellation.busy || cancellation.pending;
  const actions = metadataActions(run.state);
  const viewEpoch = fence.capture();
  useDraftGuard(
    pauseVersion !== null ||
      cancelVersion !== null ||
      pause.pending ||
      cancellation.pending,
    pause.busy || cancellation.busy,
  );
  async function perform(action: "pause" | "cancel", version: number) {
    const mutation = action === "pause" ? pause : cancellation;
    const captured = fence.capture();
    if (
      !fresh ||
      !fence.accepts(captured) ||
      version !== run.version ||
      mutation.busy ||
      mutation.pending ||
      !actions.includes(action)
    )
      return;
    await mutation.run(
      `/agent-runs/${encodeURIComponent(run.id)}/actions`,
      { action, expected_version: version },
      () => {
        if (!fence.accepts(captured)) return;
        if (action === "pause") setPauseVersion(null);
        else setCancelVersion(null);
        onChanged();
      },
    );
  }
  return (
    <article className="agent-review">
      <h3>{t("Private work", "私人工作")}</h3>
      <small>
        {t("Run", "运行")}: {run.id} · v{run.version}
      </small>
      <p className="agent-state" role="status">
        {stateLabel(run.state, t)}
      </p>
      <small>
        {t("Created", "创建时间")}: {run.created_at}
      </small>
      <small>
        {t("Updated", "更新时间")}: {run.updated_at}
      </small>
      <div className="workspace-inline-actions">
        {actions.includes("pause") && (
          <button
            className="secondary"
            disabled={!fresh || pauseLocked || cancelLocked}
            onClick={() => setPauseVersion(run.version)}
          >
            {t("Pause", "暂停")}
          </button>
        )}
        {actions.includes("cancel") && (
          <button
            className="secondary agent-stop"
            disabled={!fresh || cancelLocked}
            onClick={() => setCancelVersion(run.version)}
          >
            {t("Cancel work", "取消工作")}
          </button>
        )}
      </div>
      {pauseVersion !== null && (
        <div className="agent-notice">
          <p>
            {t(
              "Pause new work for this run? Actions already sent may still complete and need verification.",
              "暂停此次运行的新工作？已发出的操作仍可能完成，需要核验。",
            )}
          </p>
          {pauseVersion !== run.version && (
            <p role="alert">
              {t(
                "The run changed. Choose Pause again to review the current version.",
                "运行已变化，请再次选择暂停以审阅当前版本。",
              )}
            </p>
          )}
          <div className="workspace-inline-actions">
            <button
              className="secondary"
              disabled={pauseLocked}
              onClick={() => setPauseVersion(null)}
            >
              {t("Dismiss pause review", "关闭暂停审阅")}
            </button>
            <button
              className="secondary"
              disabled={
                !fresh ||
                pauseLocked ||
                cancelLocked ||
                pauseVersion !== run.version ||
                !actions.includes("pause")
              }
              onClick={() => void perform("pause", pauseVersion)}
            >
              {t("Confirm pause", "确认暂停")}
            </button>
          </div>
        </div>
      )}
      <RequestFeedback
        mutation={{
          ...pause,
          busy: pause.busy || !fresh,
          retry: () =>
            fresh && fence.accepts(viewEpoch)
              ? pause.retry()
              : Promise.resolve(false),
        }}
        t={t}
      />
      {cancelVersion !== null && (
        <div className="agent-notice" role="alert">
          <p>
            {t(
              "Cancel future work for this run? Stored files and completed actions remain; unknown effects still need verification.",
              "取消此次运行的后续工作？保存文件与已完成操作仍保留；结果未知的操作仍需核验。",
            )}
          </p>
          {cancelVersion !== run.version && (
            <p>
              {t(
                "The run changed. Choose Cancel work again to review the current version.",
                "运行已变化，请再次选择取消工作以审阅当前版本。",
              )}
            </p>
          )}
          <div className="workspace-inline-actions">
            <button
              className="secondary"
              disabled={cancelLocked}
              onClick={() => setCancelVersion(null)}
            >
              {t("Keep working", "继续工作")}
            </button>
            <button
              className="secondary agent-stop"
              disabled={
                !fresh ||
                cancelLocked ||
                cancelVersion !== run.version ||
                !actions.includes("cancel")
              }
              onClick={() => void perform("cancel", cancelVersion)}
            >
              {t("Confirm cancellation", "确认取消")}
            </button>
          </div>
        </div>
      )}
      <RequestFeedback
        mutation={{
          ...cancellation,
          busy: cancellation.busy || !fresh,
          retry: () =>
            fresh && fence.accepts(viewEpoch)
              ? cancellation.retry()
              : Promise.resolve(false),
        }}
        t={t}
      />
    </article>
  );
}
