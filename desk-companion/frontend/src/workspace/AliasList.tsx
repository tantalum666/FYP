import { useEffect, useState, type FormEvent } from "react";
import { errorText, request, write } from "../api";
import type { Translate } from "../types";

interface AliasGroup {
  id: string;
  terms: string[];
  builtin: boolean;
}

export function AliasList({ t }: { t: Translate }) {
  const [groups, setGroups] = useState<AliasGroup[]>([]);
  const [left, setLeft] = useState("");
  const [right, setRight] = useState("");
  const [error, setError] = useState<unknown>(null);

  async function load() {
    const data = await request<{ groups: AliasGroup[] }>("/memory/aliases");
    setGroups(data.groups);
  }

  useEffect(() => {
    void load().catch((reason) => setError(reason));
  }, []);

  async function add(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const data = await write<{ groups: AliasGroup[] }>("/memory/aliases", {
        terms: [left, right],
      });
      setGroups(data.groups);
      setLeft("");
      setRight("");
    } catch (reason) {
      setError(reason);
    }
  }

  async function remove(id: string) {
    setError(null);
    try {
      const data = await write<{ groups: AliasGroup[] }>(
        `/memory/aliases/${id}/deletions`,
        {},
      );
      setGroups(data.groups);
    } catch (reason) {
      setError(reason);
    }
  }

  return (
    <section className="workspace-section">
      <h3>{t("Same-meaning words", "相同意思的词")}</h3>
      <p className="workspace-hint">
        {t(
          "Recall treats these as the same word. Built-in pairs stay. Add a pair to extend them. No model is called.",
          "引用时把这些词当成同一个。内置词对会保留。可以再加一对。不会调用模型。",
        )}
      </p>
      <ul>
        {groups.map((group) => (
          <li key={group.id}>
            {group.terms.join(" = ")}
            {!group.builtin && (
              <button type="button" onClick={() => void remove(group.id)}>
                {t("Remove", "移除")}
              </button>
            )}
          </li>
        ))}
      </ul>
      <form onSubmit={(event) => void add(event)}>
        <label className="field">
          {t("Word", "词")}
          <input value={left} onChange={(event) => setLeft(event.target.value)} required />
        </label>
        <label className="field">
          {t("Same as", "等同于")}
          <input value={right} onChange={(event) => setRight(event.target.value)} required />
        </label>
        <button className="secondary" type="submit">
          {t("Add pair", "添加一对")}
        </button>
      </form>
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
    </section>
  );
}
