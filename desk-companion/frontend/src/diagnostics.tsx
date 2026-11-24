import { useEffect, useState } from "react";
import { Activity, Database, Gauge, RefreshCw } from "lucide-react";
import { request, errorText } from "./api";
import { diagnosticsSections, type DiagnosticsReport } from "./diagnosticsData";
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
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let live = true;
    setLoading(true);
    setError(null);
    request<DiagnosticsReport>("/diagnostics")
      .then((next) => {
        if (live) setReport(next);
      })
      .catch((cause) => {
        if (live) setError(cause);
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [refresh]);
  const icons = [Activity, Gauge, Database];
  return (
    <section
      className="diagnostics workspace-page"
      aria-labelledby="diagnostics-title"
      aria-busy={loading}
    >
      <header className="page-heading">
        <h1 id="diagnostics-title">{t("Diagnostics", "诊断")}</h1>
        <button
          className="secondary"
          disabled={loading}
          onClick={() => setRefresh((n) => n + 1)}
        >
          <RefreshCw size={16} />
          {t("Refresh", "刷新")}
        </button>
      </header>
      {!!error && (
        <p role="alert" className="error-message">
          {errorText(error, t)}
        </p>
      )}
      {!report && loading && (
        <p role="status">{t("Loading diagnostics…", "正在读取诊断…")}</p>
      )}
      {report && (
        <div className="diagnostic-groups">
          {diagnosticsSections(report, language).map((section, index) => {
            const Icon = icons[index];
            return (
              <section key={section.title}>
                <h2>
                  <Icon size={19} />
                  {section.title}
                </h2>
                <dl>
                  {section.lines.map((line) => (
                    <div key={line.label}>
                      <dt>{line.label}</dt>
                      <dd>{line.value}</dd>
                    </div>
                  ))}
                </dl>
              </section>
            );
          })}
        </div>
      )}
    </section>
  );
}