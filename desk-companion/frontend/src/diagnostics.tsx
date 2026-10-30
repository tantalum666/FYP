import { Fragment, useEffect, useState } from "react";
import { request, errorText } from "./api";
import { diagnosticsLines, type DiagnosticsReport } from "./diagnosticsData";
import type { Language, Translate } from "./types";

export function DiagnosticsPanel({
  t,
  language,
}: {
  t: Translate;
  language: Language;
}) {
  const [report, setReport] = useState<DiagnosticsReport | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    let cancelled = false;
    request<DiagnosticsReport>("/diagnostics")
      .then((body) => {
        if (!cancelled) setReport(body);
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason);
      });
    return () => {
      cancelled = true;
    };
  }, []);
  if (error) {
    return <p role="alert">{errorText(error, t)}</p>;
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
