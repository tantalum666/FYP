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
      <legend>{t("Work across applications", "跨应用处理")}</legend>
      <p className="workspace-hint">
        {t(
          "Create and revise spreadsheets, documents and PDFs for the tasks you select. Files and verified results stay linked to this work.",
          "为所选事务制作和修订表格、文档与 PDF，文件及核验结果会保留在这项工作中。",
        )}
      </p>
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
        {t(
          "Use connected applications for the selected tasks",
          "为所选事务使用已连接的应用",
        )}
      </label>
      {!ready ? (
        <p>
          {t(
            "The application workspace is not connected.",
            "应用工作空间尚未连接。",
          )}
        </p>
      ) : !draft.task_ids.length ? (
        <p>
          {t(
            "Select a task above to keep its files together.",
            "先在上方选择事务，文件会归入对应事务。",
          )}
        </p>
      ) : null}
      {draft.allow_application_jobs && (
        <>
          <p>
            {scope.applications?.permission_mode === "full"
              ? t(
                  "Full access is on. New file actions in this work can proceed using that permission; switching back to Ask first stops queued automatic actions.",
                  "完整权限已开启。这项工作中的新文件操作可按此权限继续；切回每次询问会阻止尚未执行的自动操作。",
                )
              : t(
                  "Ask first is on. Review each proposed file change here, then work continues from its verified result.",
                  "当前为每次询问。请在工作详情中核对文件修改，允许后会根据核验结果继续。",
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
          <p>
            {t(
              "Input files for this work (optional)",
              "此次工作可读取的资料（可选）",
            )}
          </p>
          <div className="agent-choices">
            {scope.applications?.sources.map((source) => (
              <label className="agent-check" key={source.source_id}>
                <input
                  type="checkbox"
                  checked={draft.application_source_ids.includes(
                    source.source_id,
                  )}
                  disabled={
                    !draft.application_source_ids.includes(source.source_id) &&
                    draft.application_source_ids.length >= 10
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
      <strong>{t("Application work", "应用操作")}</strong>
      <p>
        {t(
          `Up to ${input.application_job_budget} file actions for the selected tasks.`,
          `为所选事务执行最多 ${input.application_job_budget} 次文件操作。`,
        )}
      </p>
      <p>
        {scope.applications?.permission_mode === "full"
          ? t(
              "Uses your current Full access setting.",
              "使用你当前的完整权限设置。",
            )
          : t(
              "Each file change needs your approval.",
              "每项文件修改都需要你允许。",
            )}
      </p>
      <ul>
        {input.application_source_ids?.map((id) => (
          <li key={id}>{id}</li>
        ))}
      </ul>
    </section>
  );
}
