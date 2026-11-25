import { useState } from "react";
import { ApiError, errorText } from "../api";
import type { Translate } from "../types";
import type { ComputerJob } from "./jobTypes";
import { sendOwnerPageAction } from "./jobRequests";
import { ComputerScreen } from "./ComputerScreen";

/** Clicks and typing go to the Playwright page Alice already opened. */
export function OwnerPageControls({
  job,
  refreshToken,
  t,
}: {
  job: ComputerJob;
  refreshToken?: number;
  t: Translate;
}) {
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [current, setCurrent] = useState(job);

  async function send(action: {
    type: "click" | "type";
    x?: number;
    y?: number;
    text?: string;
  }) {
    setBusy(true);
    setError(null);
    try {
      const result = await sendOwnerPageAction(current, action);
      setCurrent(result.job);
      if (action.type === "type") setDraft("");
      window.dispatchEvent(new Event("desk:jobs"));
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="owner-page-controls">
      <p>
        {t(
          "You are using the same page Alice opened. Alice waits until you hand it back.",
          "你正在使用 Alice 已打开的同一页面。交还之前 Alice 会等待。",
        )}
      </p>
      <ComputerScreen
        jobId={current.id}
        refresh={refreshToken ?? Date.parse(current.updated_at)}
        t={t}
        onPoint={(point) => void send({ type: "click", ...point })}
      />
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (!draft.trim()) return;
          void send({ type: "type", text: draft });
        }}
      >
        <label>
          {t("Type on this page", "在这个页面输入")}
          <input
            value={draft}
            autoComplete="off"
            maxLength={80}
            disabled={busy}
            onChange={(event) => setDraft(event.target.value)}
          />
        </label>
        <button className="secondary" type="submit" disabled={busy || !draft.trim()}>
          {t("Send to the page", "发送到页面")}
        </button>
      </form>
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error instanceof ApiError ? error : new ApiError("REQUEST_FAILED"), t)}
        </p>
      )}
    </div>
  );
}
