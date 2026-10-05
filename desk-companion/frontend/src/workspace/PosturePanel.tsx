import { useState } from "react";
import { Camera, Pause, Play, RotateCcw } from "lucide-react";
import { errorText, write } from "../api";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import type { PostureSnapshot } from "./types";

export function postureLabel(
  posture: PostureSnapshot | undefined,
  t: Translate,
) {
  const labels: Record<string, [string, string]> = {
    not_connected: ["Camera not connected", "摄像头未连接"],
    paused: ["Observation paused", "观察已暂停"],
    uncalibrated: ["Personal setup needed", "需要个人标定"],
    calibrating: ["Learning your reference", "正在记录个人参考"],
    within_reference: ["Within your reference", "处于个人参考范围"],
    forward: ["Forward leaning observed", "观察到向前偏移"],
    side: ["Sideways leaning observed", "观察到侧向偏移"],
    absent: ["Away from the desk", "已离开画面"],
    unknown: ["Unable to assess", "暂时无法判断"],
  };
  return t(...(labels[posture?.status ?? "not_connected"] ?? labels.unknown));
}
export function feedbackText(kind: string, t: Translate) {
  return kind === "forward"
    ? t(
        "Ease back toward your usual position.",
        "请调整与屏幕的距离，回到平时的位置。",
      )
    : kind === "side"
      ? t(
          "Return toward your usual centred position.",
          "请回到平时较居中的位置。",
        )
      : t(
          "Take a moment to move and change position.",
          "可以起身活动一下，换一换姿势。",
        );
}

export function PosturePanel({ t }: { t: Translate }) {
  const workspace = useWorkspace();
  const p = workspace.data?.posture;
  const [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null);
  async function act(body: unknown) {
    setBusy(true);
    setError(null);
    try {
      await write("/posture/actions", body);
      await workspace.refresh();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  if (!p) return <p>{t("Connecting to your desk…", "正在连接桌面设备…")}</p>;
  const phases = [
    {
      key: "reference",
      en: "Your usual position",
      zh: "平时的位置",
      instruction: t(
        "Sit comfortably and keep your head and both shoulders visible for five seconds.",
        "自然坐好，让头部和双肩保持可见约五秒。",
      ),
    },
    {
      key: "forward",
      en: "A small forward lean",
      zh: "轻微向前偏移",
      instruction: t(
        "Gently lean a little toward the screen and hold still for five seconds.",
        "轻轻向屏幕靠近一点，并保持约五秒。",
      ),
    },
    {
      key: "side",
      en: "A small sideways lean",
      zh: "轻微向侧面偏移",
      instruction: t(
        "Gently lean a little to one side and hold still for five seconds.",
        "轻轻向一侧偏移一点，并保持约五秒。",
      ),
    },
  ];
  const reasons: Record<string, [string, string]> = {
    unsuitable_distance: [
      "Move the camera so your head and shoulders fit clearly in view.",
      "请调整机位，让头部与双肩清晰地进入画面。",
    ],
    stale_or_out_of_order: [
      "Waiting for a fresh observation.",
      "等待新的有效观察。",
    ],
    too_dark: ["More light is needed.", "光线不足。"],
    low_confidence: [
      "Keep your head and shoulders visible.",
      "请让头部与双肩保持可见。",
    ],
    head_shoulders_not_visible: [
      "Your head and shoulders need to be in view.",
      "需要看清头部与双肩。",
    ],
    multiple_people: ["More than one person is visible.", "画面中不止一人。"],
    outside_frame: ["Move back into the camera view.", "请回到摄像头视野内。"],
    calibration_does_not_match: [
      "Repeat setup after changing the camera or input.",
      "摄像头或输入改变后需要重新标定。",
    ],
    outside_calibrated_examples: [
      "This position differs from your setup examples.",
      "当前位置与标定样例差异较大。",
    ],
    camera_stream_lost: [
      "Waiting for a current camera observation.",
      "等待新的摄像头观察。",
    ],
  };
  return (
    <div className="workspace-panel posture-panel">
      <div className="workspace-state">
        <Camera />
        <div>
          <h3>
            {workspace.offline
              ? t("Desk connection lost", "桌面连接中断")
              : postureLabel(p, t)}
          </h3>
          <p>
            {p.source === "replay"
              ? t(
                  "Replay input · not a live camera result",
                  "回放输入 · 不是实时摄像头结果",
                )
              : p.connected
                ? t(
                    "Local observation · no video recording",
                    "本地观察 · 不保存录像",
                  )
                : t(
                    "Connect your camera to continue setup.",
                    "连接摄像头后可继续标定。",
                  )}
          </p>
        </div>
      </div>
      <label className="workspace-toggle">
        <span>{t("Allow posture observation", "允许坐姿观察")}</span>
        <input
          type="checkbox"
          checked={p.preferences.enabled}
          disabled={busy || workspace.offline}
          onChange={(e) =>
            void act({
              action: "configure",
              preferences: { ...p.preferences, enabled: e.target.checked },
            })
          }
        />
      </label>
      {p.preferences.enabled && (
        <div className="workspace-inline-actions">
          <button
            className="secondary"
            disabled={busy}
            onClick={() => void act({ action: p.paused ? "resume" : "pause" })}
          >
            {p.paused ? <Play size={16} /> : <Pause size={16} />}{" "}
            {p.paused
              ? t("Resume", "继续")
              : t("Pause observation", "暂停观察")}
          </button>
          <button
            className="secondary"
            disabled={busy}
            onClick={() => void act({ action: "snooze", minutes: 10 })}
          >
            {t("Quiet for 10 minutes", "安静十分钟")}
          </button>
        </div>
      )}
      {p.reason && reasons[p.reason] && (
        <p className="workspace-hint">{t(...reasons[p.reason])}</p>
      )}
      <section className="workspace-section">
        <h3>{t("Personal camera setup", "个人摄像头标定")}</h3>
        <p>
          {t(
            "Three short positions help distinguish your movements. Repeat setup if the camera moves.",
            "记录三个短暂姿势来区分你的动作。移动摄像头后请重新标定。",
          )}
        </p>
        <ol className="calibration-steps">
          {phases.map((step, i) => (
            <li
              key={step.key}
              className={p.calibration.phase === step.key ? "active" : ""}
            >
              <span className="step-number">{i + 1}</span>
              <div>
                <strong>{t(step.en, step.zh)}</strong>
                <p>{step.instruction}</p>
                {p.calibration.phase === step.key && (
                  <>
                    <progress
                      max={20}
                      value={Math.min(20, p.calibration.samples)}
                      aria-label={t("Setup progress", "标定进度")}
                    />
                    <small>
                      {t(
                        "Keep still while the reference is captured.",
                        "记录参考时请保持不动。",
                      )}
                    </small>
                  </>
                )}
              </div>
              <button
                className="secondary"
                disabled={
                  busy ||
                  !p.connected ||
                  !p.preferences.enabled ||
                  p.paused ||
                  !!p.calibration.phase ||
                  (i > 0 && !p.calibration.completed.includes("reference"))
                }
                onClick={() =>
                  void act({ action: "calibrate", pose: step.key })
                }
              >
                {p.calibration.completed.includes(step.key) ? (
                  <RotateCcw size={16} />
                ) : null}
                {p.calibration.completed.includes(step.key)
                  ? t("Repeat", "重做")
                  : t("Start", "开始")}
              </button>
            </li>
          ))}
        </ol>
        {p.calibration.phase && (
          <button
            className="text-button"
            onClick={() => void act({ action: "cancel_calibration" })}
          >
            {t("Cancel setup", "取消标定")}
          </button>
        )}
        {p.calibration.result === "poses_not_distinct" && (
          <p className="error-message">
            {t(
              "The positions look too similar from this angle. Reposition the camera and repeat setup.",
              "当前角度看不出足够差异，请调整机位后重新标定。",
            )}
          </p>
        )}
        {p.calibration.result === "keep_still" && (
          <p>
            {t(
              "Too much movement. Hold the position a little longer.",
              "动作变化较大，请再保持一会儿。",
            )}
          </p>
        )}
      </section>
      <section className="workspace-section">
        <h3>{t("When to prompt", "提示时机")}</h3>
        <p>
          {t("Observed at this desk: ", "已观察到的在桌时间：")}
          {Math.floor(p.continuous_presence_seconds / 60)}{" "}
          {t("minutes", "分钟")}
        </p>
        <p className="workspace-hint">
          {t(
            "Uncertain frames do not count as a confirmed break.",
            "无法判断的画面不会被计为已确认休息。",
          )}
        </p>
        <div className="workspace-form-grid">
          <label className="field">
            {t("Deviation must last (seconds)", "偏离持续多久（秒）")}
            <select
              value={p.preferences.persistence_seconds}
              disabled={busy}
              onChange={(e) =>
                void act({
                  action: "configure",
                  preferences: {
                    ...p.preferences,
                    persistence_seconds: Number(e.target.value),
                  },
                })
              }
            >
              {[5, 10, 15, 30, 60].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            {t("Movement reminder (minutes)", "活动提醒间隔（分钟）")}
            <select
              value={p.preferences.movement_minutes}
              disabled={busy}
              onChange={(e) =>
                void act({
                  action: "configure",
                  preferences: {
                    ...p.preferences,
                    movement_minutes: Number(e.target.value),
                  },
                })
              }
            >
              {[15, 30, 45, 60, 90, 120].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="check-field">
          <input
            type="checkbox"
            checked={p.preferences.privacy_when_away}
            disabled={busy}
            onChange={(e) =>
              void act({
                action: "configure",
                preferences: {
                  ...p.preferences,
                  privacy_when_away: e.target.checked,
                },
              })
            }
          />
          {t("Hide private titles when away", "离桌时隐藏私人标题")}
        </label>
      </section>
      {p.feedback && (
        <section className="workspace-section">
          <h3>{t("Latest feedback", "最近一次反馈")}</h3>
          <small>
            {new Date(p.feedback.created_at * 1000).toLocaleTimeString(
              t("en-GB", "zh-CN"),
            )}{" "}
            ·{" "}
            {p.feedback.source === "replay"
              ? t("Replay", "回放")
              : t("Live observation", "实时观察")}
          </small>
          <p>{feedbackText(p.feedback.kind, t)}</p>
          <strong>
            {p.feedback.outcome === "waiting"
              ? t("Rechecking your position…", "正在重新观察…")
              : p.feedback.outcome === "adjusted"
                ? t("Back within your reference", "已回到个人参考范围")
                : p.feedback.outcome === "still_deviated"
                  ? t("Deviation still observed", "仍观察到偏离")
                  : t("Unable to reassess", "无法完成复测")}
          </strong>
        </section>
      )}
      {p.movement_feedback && (
        <section className="workspace-section">
          <h3>{t("Movement reminder", "活动提醒")}</h3>
          <p>
            {p.movement_feedback.outcome === "observed_away"
              ? t(
                  "No person was visible for at least 30 seconds after the reminder.",
                  "提醒后观察到画面中至少30秒无人。",
                )
              : feedbackText("movement", t)}
          </p>
          <small>
            {p.movement_feedback.source === "replay"
              ? t("Replay input", "回放输入")
              : t("Based on visible presence", "依据可见在桌状态")}
          </small>
        </section>
      )}
      <p className="workspace-hint">
        {t(
          "These are visible movement cues relative to your setup, not a health score.",
          "这些是相对个人参考的可见动作线索，不是健康评分。",
        )}
      </p>
      {!!error && (
        <p role="alert" className="error-message">
          {errorText(error, t)}
        </p>
      )}
    </div>
  );
}
