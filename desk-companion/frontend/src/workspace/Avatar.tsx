import { useWorkspace } from "./WorkspaceContext";
import "./avatar.css";

export function Avatar({
  standalone = false,
  language,
}: {
  standalone?: boolean;
  language?: "en" | "zh";
}) {
  const { data, offline, stale } = useWorkspace();
  const zh =
    (language ?? localStorage.getItem("desk.device.language.v1")) === "zh";
  const labels: Record<string, [string, string]> = {
    idle: ["Your day, at a glance", "从容查看一天的安排"],
    listening: ["Listening", "正在聆听"],
    speaking: ["Speaking", "正在说话"],
    thinking: ["Thinking", "正在思考"],
    confirm: ["Review on your screen", "请在屏幕上确认"],
    connecting: ["Connecting", "正在连接"],
    alert: ["A small adjustment", "调整一下姿势"],
    disconnected: ["Desk not connected", "桌面主机未连接"],
  };
  const posture = data?.posture;
  let state =
    offline || stale || !data
      ? "disconnected"
      : data.voice.active
        ? data.voice.state
        : "idle";
  if (
    !data?.voice.active &&
    posture?.feedback?.outcome === "waiting" &&
    posture.feedback.source === "live" &&
    Date.now() / 1000 - posture.feedback.created_at < 30
  )
    state = "alert";
  const mirrored =
    standalone && new URLSearchParams(location.search).get("mirror") === "1";
  return (
    <div
      className={`companion-stage state-${state} ${standalone ? "standalone" : ""} ${mirrored ? "mirrored" : ""}`}
      aria-label={`Companion: ${state}`}
    >
      <svg
        className="companion-figure"
        viewBox="0 0 320 360"
        role="img"
        aria-label="Desk companion character"
      >
        <defs>
          <radialGradient id="body-light" cx="36%" cy="24%" r="85%">
            <stop offset="0" stopColor="#e8e9db" />
            <stop offset=".58" stopColor="#9daea4" />
            <stop offset="1" stopColor="#485e5a" />
          </radialGradient>
          <radialGradient id="head-light" cx="34%" cy="28%">
            <stop offset="0" stopColor="#f4eee1" />
            <stop offset="1" stopColor="#b7c7bc" />
          </radialGradient>
        </defs>
        <ellipse
          className="companion-shadow"
          cx="160"
          cy="322"
          rx="67"
          ry="10"
          fill="#a9b6a5"
          opacity=".12"
        />
        <g className="companion-body">
          <path
            d="M103 202 Q107 171 160 171 Q213 171 217 202 L231 264 Q234 294 205 299 Q161 309 115 299 Q86 295 89 266Z"
            fill="url(#body-light)"
          />
          <path
            d="M100 216 Q82 219 76 255 Q74 266 83 268 Q96 269 110 241"
            fill="#9fafaa"
          />
          <path
            d="M220 216 Q238 219 244 255 Q246 266 237 268 Q224 269 210 241"
            fill="#9fafaa"
          />
          <rect x="132" y="153" width="56" height="38" rx="18" fill="#a5b5ae" />
          <g className="companion-head">
            <rect
              x="95"
              y="69"
              width="130"
              height="113"
              rx="49"
              fill="url(#head-light)"
            />
            <path
              d="M122 112 Q160 98 198 112 L198 138 Q161 150 122 138Z"
              fill="#253e3c"
            />
            <ellipse
              className="companion-eye"
              cx="142"
              cy="124"
              rx="4"
              ry="6"
              fill="#e5edc4"
            />
            <ellipse
              className="companion-eye"
              cx="178"
              cy="124"
              rx="4"
              ry="6"
              fill="#e5edc4"
            />
          </g>
          <rect
            className="companion-indicator"
            x="147"
            y="216"
            width="26"
            height="5"
            rx="2.5"
            fill="#e4edc9"
          />
        </g>
        <ellipse
          className="companion-ring"
          cx="160"
          cy="322"
          rx="80"
          ry="17"
          fill="none"
          stroke="#a8baa6"
          strokeWidth="1.5"
          opacity=".35"
        />
      </svg>
      {!standalone && (
        <span className="companion-state-label">
          {(labels[state] ?? labels.idle)[zh ? 1 : 0]}
        </span>
      )}
      {standalone && !data && (
        <span className="companion-state-label">
          {zh
            ? "请先在日历界面连接本屏幕。"
            : "Connect this display in the calendar view first."}
        </span>
      )}
    </div>
  );
}
