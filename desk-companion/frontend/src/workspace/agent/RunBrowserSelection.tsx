import type { Translate } from "../../types";
import { browserError, browserSourceLabel } from "../browser/labels";
import { browserReady } from "../browser/types";
import type { RunDraft, RunScope } from "./types";

export function RunBrowserSelection({
  draft,
  scope,
  t,
  onChange,
}: {
  draft: RunDraft;
  scope: RunScope;
  t: Translate;
  onChange: (next: RunDraft) => void;
}) {
  const browser = scope.browser;
  const ready = browserReady(browser ?? null, true);
  return (
    <fieldset>
      <legend>
        {t("Public browser sources · experimental", "公开浏览器来源 · 实验性")}
      </legend>
      <p className="workspace-hint">
        {t(
          "The model may read only the public pages you select and prepare a code-built public source brief. Any StackEdit edit/export needs your separate exact review. Your goal, files, tasks and answers are not sent to StackEdit.",
          "模型仅可读取您选择的公开页面，并准备由程序生成的公开来源简报。任何 StackEdit 编辑／导出都需另外审阅确切内容。目标、文件、事务与回答不会发送至 StackEdit。",
        )}
      </p>
      {!ready && (
        <p role="status">
          {browser?.reason
            ? browserError({ code: browser.reason }, t)
            : t(
                "Public browser tools are not currently available.",
                "公开浏览器工具当前不可用。",
              )}
        </p>
      )}
      {browser?.sources.map((source) => (
        <label className="agent-check" key={source.id}>
          <input
            type="checkbox"
            checked={draft.browser_source_ids.includes(source.id)}
            disabled={!ready && !draft.browser_source_ids.includes(source.id)}
            onChange={(event) =>
              onChange({
                ...draft,
                browser_source_ids: event.target.checked
                  ? [...draft.browser_source_ids, source.id]
                  : draft.browser_source_ids.filter((id) => id !== source.id),
                browser_public_only: false,
                share: false,
                retain: false,
              })
            }
          />
          <span>
            {browserSourceLabel(source.id, source.label, t)}
            <small>{source.url}</small>
          </span>
        </label>
      ))}
      {draft.browser_source_ids.length > 0 && (
        <>
          <label className="agent-check">
            <input
              type="checkbox"
              checked={draft.browser_public_only}
              disabled={!ready}
              onChange={(event) =>
                onChange({
                  ...draft,
                  browser_public_only: event.target.checked,
                  retain: false,
                })
              }
            />
            <span>
              {t(
                "Allow these public source reads and preparation of a public-only brief for later review",
                "允许读取这些公开来源，并准备仅含公开内容的简报以供之后审阅",
              )}
            </span>
          </label>
          <p className="workspace-hint">
            {t(
              "This uses a fresh, temporary browser session. Request filtering is not a proven network sandbox. No sign-in, private browser profile, publishing or sync. A ready runtime does not prove live-app acceptance.",
              "使用独立临时浏览器会话。请求过滤不等于已验证的网络沙箱。不登录账号、不使用私人浏览器资料、不发布或同步。环境就绪不代表实际应用验收通过。",
            )}
          </p>
        </>
      )}
    </fieldset>
  );
}
