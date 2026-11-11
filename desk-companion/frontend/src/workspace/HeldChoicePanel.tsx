import { useCallback, useEffect, useState } from "react";
import { errorText, request, write } from "../api";
import type { Translate } from "../types";
import { useDraftGuard } from "../components/DraftGuard";
import { useWorkspace } from "./WorkspaceContext";
import { heldAssumption, type HeldLine, type HeldVersion } from "./heldChoice";
import "./tasks.css";

const empty = { title: "", assumption: "", choice: "", reason: "" };

export function HeldChoicePanel({ t }: { t: Translate }) {
  const { data } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [lines, setLines] = useState<HeldLine[]>([]);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState<string | null>(null);
  const [nextAssumption, setNextAssumption] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const dirty =
    Object.values(form).some((value) => value.trim()) ||
    (editing !== null && nextAssumption.trim() !== "");
  useDraftGuard(dirty, busy);
  const reload = useCallback(async () => {
    if (!owner) return;
    const next = await request<{ choices: HeldLine[] }>("/held-choices");
    setLines(next.choices);
  }, [owner]);
  useEffect(() => {
    void reload().catch((reason) => setError(reason));
  }, [reload]);
  if (!owner) return null;

  const run = async (work: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await work();
      await reload();
    } catch (reason) {
      setError(reason);
    } finally {
      setBusy(false);
    }
  };
  const approve = (id: string, pending: HeldVersion) =>
    run(async () => {
      await write(`/held-choices/${id}/approval`, {
        expected_version: pending.version,
        title: pending.title,
        assumption: pending.assumption,
        choice: pending.choice,
        reason: pending.reason,
      });
    });

  return (
    <section className="held-choice workspace-panel" aria-label={t("Choices you are holding", "你记下的选择")}>
      <h2>{t("Choices you are holding", "你记下的选择")}</h2>
      <p>{t("Saving a choice does not send mail, buy, or book anything.", "保存选择不会发信、购买或预订。")}</p>
      {!lines.length && <p>{t("No choice is held yet.", "还没有记下的选择。")}</p>}
      {lines.map((line) => {
        const view = heldAssumption(line);
        return (
          <article key={line.id}>
            <h3>{(line.current ?? line.pending)?.title}</h3>
            {line.current && (
              <p>
                <strong>{t("Current choice.", "当前选择。")}</strong> {line.current.choice}
                <br />
                {t("Assumption:", "依据：")} {view.held}
              </p>
            )}
            {line.pending && (
              <p>
                {t(
                  "Not the current choice until you approve this wording.",
                  "在你批准这句之前，这还不是当前选择。",
                )}{" "}
                {line.pending.choice}
                <br />
                {t("Assumption:", "依据：")} {view.waiting}
              </p>
            )}
            {line.previous.map((item) => (
              <p key={item.id}>
                {t("Previous wording.", "先前的写法。")} {item.choice}
                <br />
                {t("Assumption:", "依据：")} {item.assumption}
              </p>
            ))}
            <div className="held-actions">
              {line.pending && (
                <>
                  <button type="button" disabled={busy} onClick={() => void approve(line.id, line.pending as HeldVersion)}>
                    {t("Approve this wording", "批准这句")}
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() =>
                      void run(async () => {
                        await write(`/held-choices/${line.id}/withdrawal`, {
                          target: "pending",
                          expected_version: line.pending?.version,
                        });
                      })
                    }
                  >
                    {t("Drop this draft", "放下这份草稿")}
                  </button>
                </>
              )}
              {line.current && !line.pending && editing !== line.id && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    setEditing(line.id);
                    setNextAssumption("");
                  }}
                >
                  {t("Change the assumption", "更改依据")}
                </button>
              )}
            </div>
            {line.current && editing === line.id && (
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  void run(async () => {
                    await write(`/held-choices/${line.id}/replacements`, {
                      expected_version: line.current?.version,
                      assumption: nextAssumption,
                    });
                    setEditing(null);
                    setNextAssumption("");
                  });
                }}
              >
                <label>
                  {t("New assumption", "新的依据")}
                  <input
                    value={nextAssumption}
                    onChange={(event) => setNextAssumption(event.target.value)}
                    required
                  />
                </label>
                <div className="held-actions">
                  <button type="submit" disabled={busy}>
                    {t("Save the new assumption", "保存新的依据")}
                  </button>
                </div>
              </form>
            )}
          </article>
        );
      })}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void run(async () => {
            await write("/held-choices", form);
            setForm(empty);
          });
        }}
      >
        {(
          [
            ["title", "What this is", "这是什么"],
            ["assumption", "Assumption", "依据"],
            ["choice", "Choice", "选择"],
            ["reason", "Why", "原因"],
          ] as const
        ).map(([name, en, zh]) => (
          <label key={name}>
            {t(en, zh)}
            <input
              name={name}
              value={form[name]}
              onChange={(event) => setForm({ ...form, [name]: event.target.value })}
              required
            />
          </label>
        ))}
        <div className="held-actions">
          <button type="submit" disabled={busy}>
            {t("Save this choice", "保存这个选择")}
          </button>
        </div>
      </form>
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
    </section>
  );
}
