import { useState } from "react";
import type { Translate } from "../types";
import type { Proposal, ProposalDecisionOptions } from "./assistantTypes";
import "./computer-use.css";

export function BrowserResearchReview({
  proposal,
  t,
  busy,
  onDecision,
}: {
  proposal: Proposal;
  t: Translate;
  busy: boolean;
  onDecision: (
    action: "confirm" | "cancel",
    options?: ProposalDecisionOptions,
  ) => void;
}) {
  const [shared, setShared] = useState(false);
  const browser = proposal.data.browser;
  if (!browser) return null;
  return (
    <article className="assistant-action-card assistant-proposal browser-research-review">
      <span className="workspace-eyebrow">
        {t("Browse the web", "浏览网页")}
      </span>
      <h3>{browser.title}</h3>
      <p style={{ overflowWrap: "anywhere" }}>
        {browser.start_url.startsWith("demo:")
          ? t("Local rehearsal", "本地演练")
          : browser.allowed_origins.join(" · ")}
      </p>
      <details>
        <summary>{t("Task details", "任务详情")}</summary>
        <p style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
          {browser.goal}
        </p>
        <p style={{ overflowWrap: "anywhere" }}>{browser.start_url}</p>
        <p>
          {t(
            "Research and comparison only. Purchases and bookings need a separate supported step.",
            "本次用于查找与比较；下单和预订需要另行处理。",
          )}
        </p>
      </details>
      <label className="computer-use-consent">
        <input
          type="checkbox"
          checked={shared}
          disabled={busy}
          onChange={(event) => setShared(event.target.checked)}
        />
        {t(
          "Allow this task and page screenshots to be processed in the cloud",
          "允许本次任务和网页截图用于云端处理",
        )}
      </label>
      <small>
        {t(
          "Uses your assistant allowance. You can stop at any time.",
          "会使用助理额度，你可以随时停止。",
        )}
      </small>
      <div className="workspace-inline-actions">
        <button
          className="primary"
          disabled={busy || !shared}
          onClick={() => onDecision("confirm", { share_screen: true })}
        >
          {t("Allow and start", "允许并开始")}
        </button>
        <button
          className="secondary"
          disabled={busy}
          onClick={() => onDecision("cancel")}
        >
          {t("Cancel", "取消")}
        </button>
      </div>
    </article>
  );
}
