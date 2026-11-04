import type { Dispatch, SetStateAction } from "react";
import type { Translate } from "../../types";
import type { RunDraft, RunScope, RunCreateInput } from "./types";

export function RunApplicationSelection({
  draft,
  scope,
  t,
  onChange,
}: {
  draft: RunDraft;
  scope: RunScope;
  t: Translate;
  onChange: Dispatch<SetStateAction<RunDraft>>;
}) {
  const ready = scope.applications?.enabled && scope.applications.configured;
  const change = (patch: Partial<RunDraft>) =>
    onChange((old) => ({ ...old, ...patch, share: false, retain: false }));
  return (
    <fieldset>
      <legend>{t("Applications", "应用")}</legend>
      <label className="agent-check">
        <input
          type="checkbox"
          checked={draft.allow_application_jobs}
          disabled={
            !ready ||
            !draft.task_ids.length ||
            !!draft.connector_tool_ids.length
          }
          onChange={(e) =>
            change({
              allow_application_jobs: e.target.checked,
              application_source_ids: [],
            })
          }
        />
        {t("Use apps for these tasks", "使用应用处理这些事务")}
      </label>
      {!ready ? (
        <p>
          {t(
            "No application workspace is connected.",
            "尚未连接应用工作空间。",
          )}
        </p>
      ) : !draft.task_ids.length ? (
        <p>{t("Select a task first.", "先选择一项事务。")}</p>
      ) : null}
      {draft.allow_application_jobs && (
        <>
          <p>
            {scope.applications?.permission_mode === "full"
              ? t(
                  "Full access: new file actions can run automatically.",
                  "完整权限：新文件操作可自动执行。",
                )
              : t(
                  "Ask first: approve each file change.",
                  "每次询问：文件修改需由你确认。",
                )}
          </p>
          <label>
            {t("Maximum file actions", "最多文件操作次数")}
            <input
              type="number"
              min={1}
              max={8}
              step={1}
              value={draft.application_job_budget}
              onChange={(e) =>
                change({ application_job_budget: Number(e.target.value) })
              }
            />
          </label>
          <details className="workspace-details">
            <summary>
              {t("Workspace files", "工作空间文件")} ·{" "}
              {draft.application_source_ids.length}
            </summary>
            <div className="agent-choices">
              {scope.applications?.sources.map((source) => (
                <label className="agent-check" key={source.source_id}>
                  <input
                    type="checkbox"
                    checked={draft.application_source_ids.includes(
                      source.source_id,
                    )}
                    disabled={
                      !draft.application_source_ids.includes(
                        source.source_id,
                      ) && draft.application_source_ids.length >= 10
                    }
                    onChange={(e) =>
                      change({
                        application_source_ids: e.target.checked
                          ? [...draft.application_source_ids, source.source_id]
                          : draft.application_source_ids.filter(
                              (id) => id !== source.source_id,
                            ),
                      })
                    }
                  />
                  <span>
                    {source.source_id}
                    <small>
                      {source.bytes.toLocaleString()} {t("bytes", "字节")}
                    </small>
                  </span>
                </label>
              ))}
            </div>
          </details>
        </>
      )}
    </fieldset>
  );
}

export function RunApplicationReview({
  input,
  scope,
  t,
}: {
  input: RunCreateInput;
  scope: RunScope;
  t: Translate;
}) {
  if (!input.allow_application_jobs) return null;
  return (
    <section className="agent-notice">
      <strong>{t("File actions", "文件操作")}</strong>
      <p>
        {t(
          `Up to ${input.application_job_budget} file actions.`,
          `最多 ${input.application_job_budget} 次文件操作。`,
        )}
      </p>
      <p>
        {scope.applications?.permission_mode === "full"
          ? t("Full access.", "完整权限。")
          : t("Ask before each change.", "每次修改前询问。")}
      </p>
      <ul>
        {input.application_source_ids?.map((id) => (
          <li key={id}>{id}</li>
        ))}
      </ul>
    </section>
  );
}
