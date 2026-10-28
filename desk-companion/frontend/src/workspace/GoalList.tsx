import { useCallback, useEffect, useState } from "react";
import { errorText, request, write } from "../api";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import { goalLine, knowledgeCopy } from "./knowledge";

interface Goal {
  id: string;
  title: string;
  due_at: string | null;
  state: string;
}

export function GoalList({ t }: { t: Translate }) {
  const { data } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [goals, setGoals] = useState<Goal[]>([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState<unknown>(null);
  const reload = useCallback(async () => {
    if (!owner) return;
    const next = await request<{ goals: Goal[] }>("/goals");
    setGoals(next.goals);
  }, [owner]);
  useEffect(() => {
    void reload().catch((reason) => setError(reason));
  }, [reload]);
  if (!owner) return null;
  const open = goals.map(goalLine).filter((goal) => goal.open);
  return (
    <section className="workspace-panel">
      <h3>{t(knowledgeCopy.goalsTitle[0], knowledgeCopy.goalsTitle[1])}</h3>
      {!open.length && <p>{t(knowledgeCopy.goalsEmpty[0], knowledgeCopy.goalsEmpty[1])}</p>}
      {goals.filter((goal) => goal.state !== "closed").map((goal) => (
        <p key={goal.id}>
          {goal.title}
          {goal.due_at ? ` · ${goal.due_at}` : ""}
          <button
            type="button"
            onClick={() =>
              void write<{ message: string }>(`/goals/${goal.id}/close-drafts`, {})
                .then((result) => {
                  setNote(result.message);
                  return reload();
                })
                .catch((reason) => setError(reason))
            }
          >
            {t(knowledgeCopy.goalClose[0], knowledgeCopy.goalClose[1])}
          </button>
        </p>
      ))}
      {note && <p>{note}</p>}
      <small>{t(knowledgeCopy.goalConfirm[0], knowledgeCopy.goalConfirm[1])}</small>
      {!!error && <p role="alert">{errorText(error, t)}</p>}
    </section>
  );
}
