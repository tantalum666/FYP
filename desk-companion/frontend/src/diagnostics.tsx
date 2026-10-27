import { Fragment, useEffect, useState } from "react";
import { request } from "./api";
import { diagnosticsLines, type DiagnosticsReport } from "./diagnostics";
import type { Language, Translate } from "./types";

export function DiagnosticsPanel({
  t,
  language,
}: {
  t: Translate;
  language: Language;
}) {
  const [report, setReport] = useState<DiagnosticsReport | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    request<DiagnosticsReport>("/diagnostics")
      .then((body) => {
        if (!cancelled) setReport(body);
      })
      .catch((reason: { code?: string }) => {
        if (!cancelled) setError(reason.code ?? "REQUEST_FAILED");
      });
    return () => {
      cancelled = true;
    };
  }, []);
  if (error) {
    return (
      <p role="alert">
        {t("Diagnostics are unavailable.", "诊断信息暂不可用。")} {error}
      </p>
    );
  }
  if (!report) {
    return <p role="status">{t("Loading diagnostics", "正在读取诊断")}</p>;
  }
  const lines = diagnosticsLines(report, language);
  return (
    <section className="diagnostics" aria-labelledby="diagnostics-title">
      <h1 id="diagnostics-title">{t("Diagnostics", "诊断")}</h1>
      <p>{t("Read only. Secrets are not shown.", "只读。不显示密钥。")}</p>
      <dl>
        {lines.map((line) => (
          <Fragment key={line.label}>
            <dt>{line.label}</dt>
            <dd>{line.value}</dd>
          </Fragment>
        ))}
      </dl>
    </section>
  );
}
