import { useEffect, useState } from "react";
import { Download, FileText } from "lucide-react";
import { APIError, request } from "./api";
import { Banner, Dialog, Empty } from "./components";
import { number, useLabel, useLanguage } from "./i18n";
import { MealSummary } from "./MealSummary";
import type { SampleReport } from "./mealTypes";
import type { Context } from "./types";

export function Samples({ context }: { context: Context }) {
  const { t, language } = useLanguage(),
    label = useLabel();
  const [report, setReport] = useState<SampleReport | null>(null),
    [source, setSource] = useState("simulated"),
    [from, setFrom] = useState(""),
    [to, setTo] = useState("");
  const [error, setError] = useState(""),
    [selected, setSelected] = useState<string | null>(null),
    [downloading, setDownloading] = useState(false),
    [retry, setRetry] = useState(0);
  const params = new URLSearchParams({
    data_origin: source,
    ...(from ? { date_from: from } : {}),
    ...(to ? { date_to: to } : {}),
  }).toString();
  useEffect(() => {
    let disposed = false,
      seq = 0;
    setReport(null);
    setError("");
    async function refresh() {
      const current = ++seq;
      try {
        const data = await request<SampleReport>(
          `/v1/workspaces/${context.id}/samples?${params}`,
          context.id,
        );
        if (!disposed && current === seq) {
          setReport(data);
          setError("");
        }
      } catch (e) {
        if (!disposed && current === seq) {
          setError((e as APIError).code);
          if ([401, 403].includes((e as APIError).status)) setReport(null);
        }
      }
    }
    void refresh();
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, 3000);
    return () => {
      disposed = true;
      seq++;
      clearInterval(timer);
    };
  }, [context.id, params, retry]);
  async function download() {
    setDownloading(true);
    try {
      const response = await fetch(
        `/v1/workspaces/${context.id}/samples.csv?${params}`,
        { headers: { "X-Context-ID": context.id } },
      );
      if (!response.ok)
        throw new APIError(
          (await response.json()).error?.code ?? "NETWORK",
          response.status,
        );
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "senplate-anonymous-samples.csv";
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError((e as APIError).code ?? "NETWORK");
    } finally {
      setDownloading(false);
    }
  }
  const meal = report?.items.find((m) => m.id === selected);
  return (
    <>
      <header className="page-header">
        <div>
          <h1>{t("School samples", "学校样本")}</h1>
          <p>
            {t(
              "Recorded portions, with a clear scope.",
              "以明确的样本范围，记录实际份量。",
            )}
          </p>
        </div>
        {context.role === "manager" && (
          <button
            disabled={downloading || !report || !!error}
            onClick={() => void download()}
          >
            <Download size={18} />
            {t("Export CSV", "导出 CSV")}
          </button>
        )}
      </header>
      <div className="sample-filters">
        <label>
          {t("Data source", "数据来源")}
          <select
            value={source}
            onChange={(e) => {
              setSource(e.target.value);
              setSelected(null);
            }}
          >
            <option value="simulated">{t("Demo", "演示")}</option>
            <option value="replay">{t("Replay", "回放")}</option>
            <option value="hardware">{t("Device", "设备")}</option>
          </select>
        </label>
        <label>
          {t("From", "开始日期")}
          <input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
          />
        </label>
        <label>
          {t("To", "结束日期")}
          <input
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
          />
        </label>
      </div>
      {error && (
        <Banner>
          {label(error)}{" "}
          <button onClick={() => setRetry((n) => n + 1)}>
            {t("Refresh", "刷新")}
          </button>
        </Banner>
      )}
      {report && (
        <>
          <div className="metrics">
            <div>
              <span>{t("Completed samples", "已完成样本")}</span>
              <strong>{report.summary.completed_samples}</strong>
            </div>
            <div>
              <span>{t("Food provided", "已提供食物")}</span>
              <strong>
                {number(report.summary.provided_g)} <small>g</small>
              </strong>
            </div>
            <div>
              <span>{t("Observed remaining", "已记录总剩余")}</span>
              <strong>
                {number(report.summary.remaining_observed_g)} <small>g</small>
              </strong>
            </div>
          </div>
          <p className="sample-scope">
            {t(
              `Remaining weight is available for ${report.summary.samples_with_remaining} completed samples; ${report.summary.samples_without_remaining} have no comparable remaining measurement.`,
              `已完成样本中，${report.summary.samples_with_remaining} 份有总剩余记录，${report.summary.samples_without_remaining} 份没有可比较的剩余测量。`,
            )}
          </p>
          <section className="panel sample-list">
            <div className="menu-panel-heading">
              <h2>{t("Anonymous records", "匿名记录")}</h2>
              <FileText size={22} />
            </div>
            {report.items.length ? (
              report.items.map((m) => (
                <button
                  className="sample-row"
                  key={m.id}
                  onClick={() => setSelected(m.id)}
                >
                  <span>
                    <strong>{m.sample_code}</strong>
                    <small>
                      {new Intl.DateTimeFormat(
                        language === "en" ? "en-GB" : "zh-CN",
                        {
                          dateStyle: "medium",
                          timeStyle: "short",
                          timeZone: "Asia/Hong_Kong",
                        },
                      ).format(new Date(m.created_at))}
                    </small>
                  </span>
                  <span>{number(m.provided_g)} g</span>
                  <span className="status">{label("meal_" + m.state)}</span>
                </button>
              ))
            ) : (
              <Empty>
                {t(
                  "No samples in this selection. Start an anonymous sample on the station screen.",
                  "此筛选下没有样本，可在设备界面开始记录匿名样本。",
                )}
              </Empty>
            )}
          </section>
        </>
      )}
      {!report && !error && (
        <Empty>{t("Loading samples…", "正在载入样本…")}</Empty>
      )}
      <p className="page-footer">
        {t(
          "Latest 100 matching records, separated by source. Samples do not represent the whole school, actual intake or waste. No child identities are collected.",
          "按来源分别显示最近 100 条符合条件的记录。样本不代表全校、实际摄入或浪费，不收集儿童身份。",
        )}
      </p>
      {meal && (
        <Dialog
          title={meal.sample_code ?? t("Sample", "样本")}
          onClose={() => setSelected(null)}
        >
          <span className="status">{label("meal_" + meal.state)}</span>
          <MealSummary meal={meal} />
        </Dialog>
      )}
    </>
  );
}
