import type { Translate } from "../types";
import { skillOutcomeNotice } from "./savedSkillState";

export interface SavedSkillRunData {
  id: string;
  status: string;
  version: number;
  input_hash: string;
  inputs: Record<string, string>;
  note: string | null;
  note_provided: boolean;
  result: { system_verified?: boolean } | null;
}

export function SavedSkillRun({
  run,
  t,
  disabled,
  onDecide,
}: {
  run: SavedSkillRunData;
  t: Translate;
  disabled: boolean;
  onDecide: (action: "approve" | "reject") => void;
}) {
  const pending = run.status === "pending";
  return (
    <article className="saved-skill-run" aria-label={t("Prepared skill", "已准备的做法")}>
      <p>{skillOutcomeNotice(run.status, t)}</p>
      <ul>
        {Object.entries(run.inputs).map(([name, value]) => (
          <li key={name}>
            <span>{name}</span> {value}
          </li>
        ))}
      </ul>
      {run.note_provided && run.note ? <p>{run.note}</p> : null}
      {pending && (
        <div className="saved-skill-actions">
          <button type="button" className="primary" disabled={disabled} onClick={() => onDecide("approve")}>
            {t("Approve", "批准")}
          </button>
          <button type="button" className="secondary" disabled={disabled} onClick={() => onDecide("reject")}>
            {t("Stop this one", "停掉这一次")}
          </button>
        </div>
      )}
    </article>
  );
}
