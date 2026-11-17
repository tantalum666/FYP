import { useEffect, useId, useState } from "react";
import { request } from "../api";
import type { Translate } from "../types";
import type { ComputerJob } from "./jobTypes";
import "./computer-use.css";

interface RegisteredForm {
  nonce: string;
  origin: string;
  phase: "waiting" | "received" | "submitted";
  fields: { id: string; label: string; required: boolean; type: string }[];
  options: { id: string; label: string; field_ids: string[] }[];
}
interface AuthReply {
  form: RegisteredForm | null;
  version: number;
}

export function ManagedBrowserSignIn({
  job,
  refreshToken,
  t,
}: {
  job: ComputerJob;
  refreshToken?: number;
  t: Translate;
}) {
  const [reply, setReply] = useState<AuthReply | null>(null);
  const [failed, setFailed] = useState(false);
  const [reload, setReload] = useState(0);
  const path = `/computer/jobs/${job.id}/authentication`;
  useEffect(() => {
    let live = true;
    void request<AuthReply>(path)
      .then((value) => {
        if (live) {
          setReply(value);
          setFailed(false);
        }
      })
      .catch(() => {
        if (live) {
          setReply(null);
          setFailed(true);
        }
      });
    const clear = () => {
      live = false;
      setReply(null);
    };
    window.addEventListener("desk:session", clear);
    return () => {
      live = false;
      window.removeEventListener("desk:session", clear);
    };
  }, [path, job.version, refreshToken, reload]);
  if (failed)
    return (
      <p role="status">
        {t(
          "Sign-in is no longer available here. Return to the window that started this task.",
          "这里暂时无法登录，请回到发起任务的窗口查看状态。",
        )}
      </p>
    );
  if (!reply?.form)
    return <p role="status">{t("Checking sign-in…", "正在检查登录…")}</p>;
  return (
    <SignInForm
      key={reply.form.nonce}
      form={reply.form}
      version={reply.version}
      path={path}
      t={t}
      onRefresh={() => setReload((value) => value + 1)}
    />
  );
}

function SignInForm({
  form,
  version,
  path,
  t,
  onRefresh,
}: {
  form: RegisteredForm;
  version: number;
  path: string;
  t: Translate;
  onRefresh: () => void;
}) {
  const prefix = useId();
  const [selected, setSelected] = useState(form.options[0]?.id ?? "");
  const [values, setValues] = useState<Record<string, string>>({});
  const [allowed, setAllowed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const option = form.options.find((value) => value.id === selected);
  const fields = option
    ? form.fields.filter((field) => option.field_ids.includes(field.id))
    : form.fields;
  useEffect(() => {
    const clear = () => {
      setValues({});
      setAllowed(false);
    };
    const hidden = () => {
      if (document.hidden) clear();
    };
    document.addEventListener("visibilitychange", hidden);
    window.addEventListener("pagehide", clear);
    return () => {
      document.removeEventListener("visibilitychange", hidden);
      window.removeEventListener("pagehide", clear);
    };
  }, []);

  async function submit(action: "submit" | "cancel") {
    if (busy || form.phase !== "waiting" || (action === "submit" && !allowed))
      return;
    const body = {
      nonce: form.nonce,
      expected_version: version,
      action,
      fields:
        action === "submit"
          ? fields
              .filter((field) => values[field.id] !== undefined)
              .map((field) => ({ field_id: field.id, value: values[field.id] }))
          : [],
      selected_option: action === "submit" && option ? option.id : null,
      allow_account_access: action === "submit" && allowed,
    };
    setBusy(true);
    setError(false);
    setValues({});
    setAllowed(false);
    try {
      // Never use write(): its recovery body is saved in sessionStorage.
      // A lost reply is reconciled by reading this same form, not resubmitting.
      await request(path, { method: "POST", body: JSON.stringify(body) });
    } catch {
      setError(true);
    } finally {
      setBusy(false);
      onRefresh();
    }
  }
  return (
    <form
      className="managed-browser-sign-in"
      autoComplete="off"
      onSubmit={(event) => {
        event.preventDefault();
        void submit("submit");
      }}
    >
      <strong>{t("Sign in to continue", "登录后继续")}</strong>
      <p className="computer-use-destination">{form.origin}</p>
      {form.phase === "waiting" ? (
        <>
          {form.options.length > 0 && (
            <label>
              {t("Sign-in method", "登录方式")}
              <select
                value={selected}
                disabled={busy}
                onChange={(event) => {
                  setSelected(event.target.value);
                  setValues({});
                  setAllowed(false);
                }}
              >
                {form.options.map((value) => (
                  <option key={value.id} value={value.id}>
                    {value.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          {fields.map((field, index) => (
            <label key={field.id} htmlFor={`${prefix}-${index}`}>
              {field.label}
              <input
                id={`${prefix}-${index}`}
                type="password"
                autoComplete="off"
                spellCheck={false}
                autoCapitalize="none"
                maxLength={4096}
                required={field.required}
                disabled={busy}
                value={values[field.id] ?? ""}
                onChange={(event) =>
                  setValues((previous) => ({
                    ...previous,
                    [field.id]: event.target.value,
                  }))
                }
              />
            </label>
          ))}
          <label className="computer-use-consent">
            <input
              type="checkbox"
              checked={allowed}
              disabled={busy}
              onChange={(event) => setAllowed(event.target.checked)}
            />
            {t(
            "Allow this task to read my account",
            "允许本次任务读取我的账号页面",
            )}
          </label>
          <small>
            {t(
            "Login details stay out of chat. This browser closes after the task.",
            "登录信息不进入对话，任务结束后浏览器会关闭。",
            )}
          </small>
          <div className="workspace-inline-actions">
            <button
              className="primary"
              disabled={busy || !allowed}
              type="submit"
            >
              {t("Submit and continue", "提交并继续")}
            </button>
            <button
              className="secondary"
              disabled={busy}
              type="button"
              onClick={() => void submit("cancel")}
            >
              {t("Skip sign-in", "跳过登录")}
            </button>
          </div>
        </>
      ) : (
        <p role="status">
          {t("Submitted. Waiting for the website…", "已提交，等待网站响应…")}
        </p>
      )}
      {error && (
        <p role="status">
          {t(
            "Checking whether the sign-in was received. Your details were cleared.",
            "正在核对登录提交状态，输入内容已清除。",
          )}
        </p>
      )}
    </form>
  );
}
