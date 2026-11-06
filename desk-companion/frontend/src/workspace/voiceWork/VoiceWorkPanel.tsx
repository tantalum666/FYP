import { useEffect, useRef, useState } from "react";
import { ApiError, request } from "../../api";
import { Modal } from "../../components/Dialogs";
import type { Translate } from "../../types";
import type { ResponseFence } from "../personal/responseFence";
import type { WorkGoalRequest } from "../agent/types";
import { agentError } from "../agent/labels";
import {
  currentVoiceRuns,
  validVoiceDraft,
  validVoiceGoal,
  voiceGoalOrigin,
} from "./types";
import type {
  CurrentWorkRun,
  VoiceBoundary,
  VoiceDraft,
  VoiceInput,
  VoiceInputs,
  VoiceProvenance,
} from "./types";
import "./voiceWork.css";
export function boundaryLabel(boundary: VoiceBoundary, t: Translate) {
  return boundary === "provider_final"
    ? t("Recognized speech; check the wording", "已识别语音，请核对措辞")
    : t(
        "Incomplete transcription; edit and review before use",
        "转写尚未完成，使用前请编辑并审阅",
      );
}
export function VoiceOriginLabel({
  origin,
  t,
}: {
  origin: VoiceProvenance;
  t: Translate;
}) {
  return (
    <div className="voice-origin">
      <strong>{t("Voice input snapshot", "语音输入快照")}</strong>
      <p>{boundaryLabel(origin.boundary, t)}</p>
      <small>
        {origin.provider} · {origin.model} · {origin.observed_at}
      </small>
      <small>
        {t("Voice destination reference", "语音目的地引用")}:{" "}
        {origin.destination_id}
      </small>
      <p>
        {t(
          "This records where the text came from, not who spoke or permission to act.",
          "仅记录文字来源，不证明说话者身份，也不授予执行权限。",
        )}
      </p>
    </div>
  );
}
export function VoiceInputList({
  state,
  owner,
  disabled,
  onSelect,
  t,
}: {
  state: VoiceInputs;
  owner: boolean;
  disabled: boolean;
  onSelect: (input: VoiceInput) => void;
  t: Translate;
}) {
  return (
    <section
      className="voice-inputs"
      aria-label={t("Recognized voice inputs", "识别的语音输入")}
    >
      {state.overflow && (
        <p role="status">
          {t(
            "Only bounded recent input snapshots are shown. Oversize input cannot be used as a goal; no truncated tail is selected.",
            "仅显示有界的近期输入快照。过长输入不能用作目标，不会选择截断后的末尾内容。",
          )}
        </p>
      )}
      {state.inputs.map((input) => (
        <article key={input.input_segment_id} className="voice-input">
          <strong>{t("Voice input", "语音输入")}</strong>
          <p className="personal-text">{input.text}</p>
          <small>{boundaryLabel(input.boundary, t)}</small>
          {!input.eligible && (
            <p role="status">
              {t(
                "This input cannot be selected. It is empty, too large or unavailable.",
                "此输入为空、过长或不可用，不能选择。",
              )}
            </p>
          )}
          {owner && (
            <button
              type="button"
              className="secondary"
              disabled={disabled || !input.eligible}
              onClick={() => onSelect(input)}
            >
              {t("Use this as a work goal…", "作为工作目标…")}
            </button>
          )}
        </article>
      ))}
      {!owner && (
        <p>
          {t("Open Work with an owner sign-in", "请以拥有者身份登录后打开工作")}
        </p>
      )}
    </section>
  );
}
export function VoiceWorkPanel({
  state,
  t,
  fence,
  owner,
  taskId,
  onHandoff,
  onSteered,
  onInvalidated,
}: {
  state: VoiceInputs;
  t: Translate;
  fence: ResponseFence;
  owner: boolean;
  taskId?: string;
  onHandoff: (goal: WorkGoalRequest) => void;
  onSteered?: (reply: { text: string; message: string }) => void;
  onInvalidated?: () => void;
}) {
  const [review, setReview] = useState<{
    draft: VoiceDraft;
    text: string;
  } | null>(null);
  const [pending, setPending] = useState<VoiceInput | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [expired, setExpired] = useState(false);
  const [runs, setRuns] = useState<CurrentWorkRun[] | null>(null);
  const [runsError, setRunsError] = useState(false);
  const [chosen, setChosen] = useState<string | null>(null);
  const [steerError, setSteerError] = useState<unknown>(null);
  const [steerNote, setSteerNote] = useState<string | null>(null);
  const steerKey = useRef<{ id: string; body: string } | null>(null);
  const mountEpoch = useRef(fence.capture());
  const current = useRef({ owner, epoch: mountEpoch.current });
  current.current = { owner, epoch: mountEpoch.current };
  const live = useRef(true),
    inFlight = useRef(false),
    handedOff = useRef(false);
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
    };
  }, []);
  useEffect(() => {
    if (!review) return;
    const timer = setTimeout(
      () => {
        setExpired(true);
        setReview(null);
        setPending(null);
      },
      Math.max(0, Date.parse(review.draft.expires_at) - Date.now()),
    );
    return () => clearTimeout(timer);
  }, [review?.draft]);
  useEffect(() => {
    if (!review) return;
    const epoch = current.current.epoch;
    let cancel = false;
    setRuns(null);
    setRunsError(false);
    setChosen(null);
    request<{ runs?: unknown }>("/agent/runs")
      .then((body) => {
        if (
          cancel ||
          !live.current ||
          !current.current.owner ||
          !fence.accepts(epoch) ||
          current.current.epoch !== epoch
        )
          return;
        if (!body || !Array.isArray(body.runs)) {
          setRunsError(true);
          return;
        }
        setRuns(currentVoiceRuns(body.runs, taskId));
      })
      .catch(() => {
        if (
          !cancel &&
          live.current &&
          current.current.owner &&
          fence.accepts(epoch)
        )
          setRunsError(true);
      });
    return () => {
      cancel = true;
    };
  }, [review?.draft.voice_origin_ref, taskId]);
  async function freeze(input: VoiceInput) {
    const epoch = fence.capture();
    if (
      !current.current.owner ||
      current.current.epoch !== epoch ||
      !input.eligible ||
      inFlight.current ||
      !fence.accepts(epoch)
    )
      return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    setExpired(false);
    setPending(input);
    try {
      const draft = await request<VoiceDraft>("/voice/work-drafts", {
        method: "POST",
        body: JSON.stringify({
          voice_session_ref: input.voice_session_ref,
          input_segment_id: input.input_segment_id,
          expected_revision: input.revision,
        }),
      });
      if (
        !live.current ||
        !current.current.owner ||
        !fence.accepts(epoch) ||
        current.current.epoch !== epoch
      )
        return;
      if (!validVoiceDraft(draft, input))
        throw new ApiError("VOICE_DRAFT_RESPONSE_INVALID");
      handedOff.current = false;
      setReview({ draft, text: draft.text });
      setPending(null);
    } catch (e) {
      if (live.current && current.current.owner && fence.accepts(epoch)) {
        setError(e);
        if (
          e instanceof ApiError &&
          (e.status === 401 ||
            e.status === 403 ||
            [
              "RUN_SESSION_EXPIRED",
              "VOICE_CONTEXT_CHANGED",
              "OWNER_SIGN_IN_REQUIRED",
              "PRIVATE_CONTEXT_HIDDEN",
              "AUTH_REQUIRED",
            ].includes(e.code))
        ) {
          setPending(null);
          setReview(null);
          onInvalidated?.();
        }
      }
    } finally {
      inFlight.current = false;
      if (live.current) setBusy(false);
    }
  }
  async function steer(target: CurrentWorkRun) {
    if (
      !review ||
      handedOff.current ||
      inFlight.current ||
      !current.current.owner ||
      !fence.accepts(current.current.epoch) ||
      !validVoiceGoal(review.draft.text) ||
      review.text.trim() !== review.draft.text.trim() ||
      review.draft.text.length > 3000
    )
      return;
    if (Date.parse(review.draft.expires_at) <= Date.now()) {
      setReview(null);
      setExpired(true);
      return;
    }
    const body = {
      message: review.draft.text,
      language: t("en", "zh") === "zh" ? "zh" : "en",
      task_id: taskId ?? null,
      voice_origin_ref: review.draft.voice_origin_ref,
      voice_steer: true,
      steer_run_id: target.id,
    };
    const encoded = JSON.stringify(body);
    if (!steerKey.current || steerKey.current.body !== encoded)
      steerKey.current = { id: crypto.randomUUID(), body: encoded };
    const epoch = current.current.epoch;
    const snapshot = review.draft.text;
    inFlight.current = true;
    setBusy(true);
    setSteerError(null);
    setSteerNote(null);
    try {
      const reply = await request<{ admitted?: unknown; message?: unknown }>(
        "/assistant/messages",
        {
          method: "POST",
          body: encoded,
          headers: { "X-Operation-Id": steerKey.current.id },
        },
      );
      if (
        !live.current ||
        !current.current.owner ||
        !fence.accepts(epoch) ||
        current.current.epoch !== epoch
      )
        return;
      if (typeof reply?.message !== "string" || typeof reply.admitted !== "boolean")
        throw new ApiError("CONNECTION_LOST");
      if (!reply.admitted) {
        setSteerNote(reply.message);
        return;
      }
      onSteered?.({ text: snapshot, message: reply.message });
      setReview(null);
    } catch (error) {
      if (live.current && current.current.owner && fence.accepts(epoch))
        setSteerError(error);
    } finally {
      inFlight.current = false;
      if (live.current) setBusy(false);
    }
  }
  const steerTarget =
    runs?.length === 1
      ? runs[0]
      : (runs?.find((run) => run.id === chosen) ?? null);
  const wordingMatches =
    !!review && review.text.trim() === review.draft.text.trim();
  const wordingFits = !!review && review.draft.text.length <= 3000;
  return (
    <>
      <VoiceInputList
        state={state}
        owner={owner}
        disabled={busy || !!review}
        onSelect={(input) => void freeze(input)}
        t={t}
      />
      {busy && (
        <p role="status">
          {review
            ? t("Updating the current work…", "正在更新当前工作…")
            : t(
                "Freezing the selected input snapshot…",
                "正在固定所选输入快照…",
              )}
        </p>
      )}
      {!!error && (
        <div role="alert">
          <p>{agentError(error, t)}</p>
          <p>
            {t(
              "Voice has not been ended. Retry this same snapshot or select a current input.",
              "语音未结束。可重试同一快照，或选择当前输入。",
            )}
          </p>
          {pending && (
            <button
              type="button"
              className="secondary"
              disabled={busy}
              onClick={() => void freeze(pending)}
            >
              {t("Retry the same snapshot", "重试同一快照")}
            </button>
          )}
        </div>
      )}
      {expired && (
        <p role="status">
          {t(
            "The temporary voice snapshot expired and was cleared. Select and review a new input; no work was started.",
            "临时语音快照已到期并清除。请重新选择和审阅输入；未开始工作。",
          )}
        </p>
      )}
      {owner && review && (
        <Modal
          title={t("Review a voice-derived goal", "审阅语音目标")}
          closeLabel={t("Keep talking", "继续交谈")}
          onClose={() => setReview(null)}
          dirty={review.text !== review.draft.text}
        >
          <VoiceOriginLabel origin={review.draft} t={t} />
          <label className="field">
            {t("Edit the work goal", "编辑工作目标")}
            <textarea
              rows={5}
              maxLength={4000}
              value={review.text}
              onChange={(event) =>
                setReview({ ...review, text: event.target.value })
              }
            />
          </label>
          <p>
            {t(
              "Ending voice starts new work. You still choose evidence before anything starts. The full conversation and raw audio are not saved.",
              "结束语音会开始新的工作。开始前仍需选择证据。不会保存完整交谈或原始录音。",
            )}
          </p>
          {!!runs?.length && (
            <p>
              {t(
                "Updating current work uses this reviewed wording. Nothing is sent or bought.",
                "更新当前工作会使用这段已复核的措辞。不会发送或购买。",
              )}
            </p>
          )}
          {runs === null && !runsError && (
            <p role="status">
              {t("Checking current work…", "正在查看当前工作…")}
            </p>
          )}
          {runsError && (
            <p role="status">
              {t(
                "Current work could not be read. You can still start new work.",
                "未能读到当前工作。仍可开始新的工作。",
              )}
            </p>
          )}
          {!!runs?.length && !wordingMatches && (
            <p role="status">
              {t(
                "Edited wording starts new work.",
                "改过的措辞会开始新的工作。",
              )}
            </p>
          )}
          {!!runs?.length && wordingMatches && !wordingFits && (
            <p role="status">
              {t(
                "This wording is too long to update current work.",
                "这段措辞太长，不能更新当前工作。",
              )}
            </p>
          )}
          {wordingMatches && wordingFits && runs?.length === 1 && (
            <p>
              {t("Update this work:", "更新这项工作：")}{" "}
              {runs[0].goal?.trim() || t("Current work", "当前工作")}
            </p>
          )}
          {wordingMatches && wordingFits && !!runs && runs.length > 1 && (
            <fieldset className="voice-steer">
              <legend>
                {t("Choose the work to update", "选择要更新的工作")}
              </legend>
              {runs.map((run) => (
                <label key={run.id}>
                  <input
                    type="radio"
                    name="voice-steer-run"
                    checked={chosen === run.id}
                    onChange={() => setChosen(run.id)}
                  />
                  <span>
                    {run.goal?.trim() || t("Current work", "当前工作")}
                  </span>
                </label>
              ))}
            </fieldset>
          )}
          {steerNote && <p role="status">{steerNote}</p>}
          {!!steerError && (
            <div role="alert">
              <p>{agentError(steerError, t)}</p>
              <button
                type="button"
                className="secondary"
                disabled={busy || !steerTarget}
                onClick={() => steerTarget && void steer(steerTarget)}
              >
                {t("Retry the same update", "重试同一次更新")}
              </button>
            </div>
          )}
          <div className="workspace-inline-actions">
            <button
              type="button"
              className="secondary"
              onClick={() => setReview(null)}
            >
              {t("Dismiss and keep talking", "关闭并继续交谈")}
            </button>
            {wordingMatches && wordingFits && runs && runs.length > 0 && (
              <button
                type="button"
                className="secondary"
                disabled={
                  busy || !steerTarget || !validVoiceGoal(review.draft.text)
                }
                onClick={() => steerTarget && void steer(steerTarget)}
              >
                {runs.length === 1
                  ? t("Update this work", "更新这项工作")
                  : t("Update the selected work", "更新所选工作")}
              </button>
            )}
            <button
              type="button"
              className="primary"
              disabled={!validVoiceGoal(review.text)}
              onClick={() => {
                if (
                  handedOff.current ||
                  !current.current.owner ||
                  !fence.accepts(current.current.epoch) ||
                  !validVoiceGoal(review.text)
                )
                  return;
                if (Date.parse(review.draft.expires_at) <= Date.now()) {
                  setReview(null);
                  setExpired(true);
                  return;
                }
                handedOff.current = true;
                onHandoff({
                  id: review.draft.voice_origin_ref,
                  text: review.text.trim(),
                  voiceOrigin: voiceGoalOrigin(review.draft),
                });
                setReview(null);
              }}
            >
              {t("End voice and review work", "结束语音并审阅工作")}
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
