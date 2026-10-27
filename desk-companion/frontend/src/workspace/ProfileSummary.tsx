import { useCallback, useEffect, useState } from "react";
import { errorText, request, write } from "../api";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import { knowledgeCopy } from "./knowledge";

interface ProfileView {
  text: string;
  included: Array<{ id: string; body: string; group: string }>;
  budget: number;
}

export function ProfileSummary({ t }: { t: Translate }) {
  const { data } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [profile, setProfile] = useState<ProfileView | null>(null);
  const [error, setError] = useState<unknown>(null);
  const reload = useCallback(async () => {
    if (!owner) return;
    setProfile(await request<ProfileView>("/profile"));
  }, [owner]);
  useEffect(() => {
    void reload().catch((reason) => setError(reason));
  }, [reload]);
  if (!owner || !profile) return null;
  return (
    <section className="workspace-panel">
      <h3>{t(knowledgeCopy.profileTitle[0], knowledgeCopy.profileTitle[1])}</h3>
      {profile.text ? <pre>{profile.text}</pre> : <p>{t(knowledgeCopy.profileEmpty[0], knowledgeCopy.profileEmpty[1])}</p>}
      {profile.included.map((fact) => (
        <p key={fact.id}>
          {fact.body}
          <button
            type="button"
            onClick={() =>
              void write("/profile/omissions", { memory_id: fact.id })
                .then(() => reload())
                .catch((reason) => setError(reason))
            }
          >
            {t(knowledgeCopy.profileOmit[0], knowledgeCopy.profileOmit[1])}
          </button>
        </p>
      ))}
      {!!error && <p role="alert">{errorText(error, t)}</p>}
    </section>
  );
}
