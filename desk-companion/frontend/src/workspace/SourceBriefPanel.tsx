import { useCallback, useEffect, useState } from "react";
import { ApiError, errorText, request, write } from "../api";
import { useDraftGuard } from "../components/DraftGuard";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import {
  canSave,
  citableSources,
  claimBody,
  openBody,
  savedLine,
  sourceBody,
  type SourceBrief,
} from "./sourceBriefState";
import "./source-briefs.css";

interface Listing {
  briefs: SourceBrief[];
  limit: number;
}

function briefError(error: unknown, t: Translate) {
  if (!(error instanceof ApiError)) return errorText(error, t);
  const copy: Record<string, [string, string]> = {
    QUOTE_NOT_IN_SOURCE: ["That quote is not in the source.", "这段引文不在该资料里。"],
    SOURCE_UNAVAILABLE: [
      "That source is missing, so it cannot support a point.",
      "这份资料缺失，不能用来支持一个观点。",
    ],
    BRIEF_CHANGED: ["The comparison changed. Review it again.", "对照已变化，请再看一遍。"],
    BRIEF_SAVED: ["This comparison is already saved.", "这次对照已经保存。"],
    NULL_FIELD: ["Leave a field out instead of clearing it.", "不要清空字段，不填即可。"],
    NOTHING_TO_SAVE: ["Add a point or a missing source first.", "请先添加一个观点或一份缺失资料。"],
  };
  const line = copy[error.code];
  return line ? t(line[0], line[1]) : errorText(error, t);
}

export function SourceBriefPanel({ t }: { t: Translate }) {
  const { data } = useWorkspace();
  const owner = data?.principal.kind === "owner";
  const [briefs, setBriefs] = useState<SourceBrief[]>([]);
  const [limit, setLimit] = useState(8);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [composing, setComposing] = useState(true);
  const [question, setQuestion] = useState("");
  const [note, setNote] = useState("");
  const [label, setLabel] = useState("");
  const [locator, setLocator] = useState("");
  const [body, setBody] = useState("");
  const [missing, setMissing] = useState(false);
  const [gap, setGap] = useState("");
  const [point, setPoint] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [quote, setQuote] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const active = briefs.find((brief) => brief.id === activeId) ?? null;
  const dirty = Boolean(
    question.trim() ||
      note.trim() ||
      label.trim() ||
      locator.trim() ||
      body.trim() ||
      gap.trim() ||
      point.trim() ||
      quote.trim(),
  );
  useDraftGuard(Boolean(owner) && dirty, busy);

  const adopt = useCallback((brief: SourceBrief) => {
    setBriefs((current) => {
      const next = [...current.filter((item) => item.id !== brief.id), brief];
      next.sort((a, b) => a.created_at.localeCompare(b.created_at) || a.id.localeCompare(b.id));
      return next;
    });
    setActiveId(brief.id);
    setComposing(false);
  }, []);

  const load = useCallback(async () => {
    const listing = await request<Listing>("/source-briefs");
    setLimit(listing.limit);
    setBriefs(listing.briefs);
    setActiveId((current) => {
      if (current && listing.briefs.some((brief) => brief.id === current)) return current;
      const draft = [...listing.briefs].reverse().find((brief) => brief.status === "draft");
      return (draft ?? listing.briefs[listing.briefs.length - 1])?.id ?? null;
    });
    setComposing(listing.briefs.length === 0);
  }, []);

  useEffect(() => {
    if (!owner) return;
    void load().catch((reason) => setError(reason));
  }, [owner, load]);

  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await task();
    } catch (reason) {
      setError(reason);
      if (reason instanceof ApiError && reason.code === "BRIEF_CHANGED") {
        await load().catch((next) => setError(next));
      }
    } finally {
      setBusy(false);
    }
  }

  if (!owner) return null;
  const language = t("en", "zh") === "en" ? "en" : "zh";

  return (
    <section className="source-brief" aria-label={t("Compare sources", "对照资料")}>
      <h2>{t("Compare sources", "对照资料")}</h2>
      {active && (!composing || active.status === "saved") && (
        <>
          <p>{active.question}</p>
          {active.note && <p>{active.note}</p>}
          {active.status === "saved" && (
            <p role="status">{savedLine(active, language)}</p>
          )}
          {!!active.sources.length && (
            <ul>
              {active.sources.map((source) => (
                <li key={source.id}>
                  {source.available
                    ? source.label
                    : t(`${source.label} is missing. ${source.gap ?? ""}`, `${source.label} 缺失。${source.gap ?? ""}`)}
                </li>
              ))}
            </ul>
          )}
          {!!active.claims.length && (
            <ul>
              {active.claims.map((claim) => {
                const source = active.sources.find((item) => item.id === claim.source_id);
                return (
                  <li key={claim.id}>
                    {claim.text}{" "}
                    {claim.kind === "cited" && source
                      ? t(`From ${source.label}: “${claim.quote}”`, `来自${source.label}：“${claim.quote}”`)
                      : t("Not in these sources", "这些资料里没有")}
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}
      {active?.status === "draft" && !composing && (
        <>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void run(async () => {
                const saved = await write<{ brief: SourceBrief }>(
                  `/source-briefs/${active.id}/sources`,
                  sourceBody({
                    label: label.trim(),
                    available: !missing,
                    ...(locator.trim() ? { locator: locator.trim() } : {}),
                    ...(missing ? { gap: gap.trim() } : { body: body.trim() }),
                  }),
                );
                adopt(saved.brief);
                setLabel("");
                setLocator("");
                setBody("");
                setGap("");
                setMissing(false);
              });
            }}
          >
            <label className="field">
              {t("Source", "资料")}
              <input value={label} maxLength={80} onChange={(event) => setLabel(event.target.value)} />
            </label>
            <details>
              <summary>{t("Where it came from", "来源说明")}</summary>
              <label className="field">
                {t("Locator", "位置")}
                <input
                  value={locator}
                  maxLength={200}
                  onChange={(event) => setLocator(event.target.value)}
                />
              </label>
            </details>
            <label className="check">
              <input
                type="checkbox"
                checked={missing}
                onChange={(event) => setMissing(event.target.checked)}
              />
              {t("This source is missing", "这份资料缺失")}
            </label>
            {missing ? (
              <label className="field">
                {t("Why it is missing", "缺失原因")}
                <textarea
                  value={gap}
                  rows={2}
                  maxLength={200}
                  onChange={(event) => setGap(event.target.value)}
                />
              </label>
            ) : (
              <label className="field">
                {t("Text", "正文")}
                <textarea
                  value={body}
                  rows={3}
                  maxLength={4000}
                  onChange={(event) => setBody(event.target.value)}
                />
              </label>
            )}
            <div className="workspace-inline-actions">
              <button
                className="secondary"
                type="submit"
                disabled={busy || !label.trim() || (missing ? !gap.trim() : !body.trim())}
              >
                {t("Add source", "添加资料")}
              </button>
            </div>
          </form>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void run(async () => {
                const saved = await write<{ brief: SourceBrief }>(
                  `/source-briefs/${active.id}/claims`,
                  sourceId
                    ? claimBody({
                        kind: "cited",
                        text: point.trim(),
                        sourceId,
                        quote: quote.trim(),
                      })
                    : claimBody({ kind: "unknown", text: point.trim() }),
                );
                adopt(saved.brief);
                setPoint("");
                setQuote("");
                setSourceId("");
              });
            }}
          >
            <label className="field">
              {t("Point", "观点")}
              <textarea
                value={point}
                rows={2}
                maxLength={400}
                onChange={(event) => setPoint(event.target.value)}
              />
            </label>
            <label className="field">
              {t("Supports this point", "支持这个观点")}
              <select value={sourceId} onChange={(event) => setSourceId(event.target.value)}>
                <option value="">{t("Not in these sources", "这些资料里没有")}</option>
                {citableSources(active).map((source) => (
                  <option key={source.id} value={source.id}>
                    {source.label}
                  </option>
                ))}
              </select>
            </label>
            {sourceId && (
              <label className="field">
                {t("Quote", "引文")}
                <textarea
                  value={quote}
                  rows={2}
                  maxLength={400}
                  onChange={(event) => setQuote(event.target.value)}
                />
              </label>
            )}
            <div className="workspace-inline-actions">
              <button
                className="secondary"
                type="submit"
                disabled={busy || !point.trim() || (!!sourceId && !quote.trim())}
              >
                {t("Add point", "添加观点")}
              </button>
              {canSave(active) && (
                <button
                  className="primary"
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    void run(async () => {
                      const saved = await write<{ brief: SourceBrief }>(
                        `/source-briefs/${active.id}/approval`,
                        { expected_digest: active.digest },
                      );
                      adopt(saved.brief);
                    })
                  }
                >
                  {t("Save this comparison", "保存这次对照")}
                </button>
              )}
            </div>
          </form>
        </>
      )}
      {(composing || !active) && briefs.length < limit && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void run(async () => {
              const saved = await write<{ brief: SourceBrief }>(
                "/source-briefs",
                openBody({
                  question: question.trim(),
                  ...(note.trim() ? { note: note.trim() } : {}),
                }),
              );
              adopt(saved.brief);
              setQuestion("");
              setNote("");
            });
          }}
        >
          <label className="field">
            {t("Question", "问题")}
            <input
              value={question}
              maxLength={200}
              onChange={(event) => setQuestion(event.target.value)}
            />
          </label>
          <details>
            <summary>{t("Note", "备注")}</summary>
            <label className="field">
              {t("Note", "备注")}
              <input value={note} maxLength={200} onChange={(event) => setNote(event.target.value)} />
            </label>
          </details>
          <div className="workspace-inline-actions">
            <button className="primary" type="submit" disabled={busy || !question.trim()}>
              {t("Open comparison", "开始对照")}
            </button>
          </div>
        </form>
      )}
      {active?.status === "saved" && !composing && briefs.length < limit && (
        <button
          className="secondary"
          type="button"
          disabled={busy}
          onClick={() => {
            setComposing(true);
            setQuestion("");
            setNote("");
          }}
        >
          {t("New comparison", "新的对照")}
        </button>
      )}
      {!!error && (
        <p className="error-message" role="alert">
          {briefError(error, t)}
        </p>
      )}
    </section>
  );
}
