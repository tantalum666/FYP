import { useEffect, useRef, useState } from "react";
import { ApiError, request } from "../../api";
import { apiFetch, isNative, native } from "../../native";
import type { Translate } from "../../types";
import type { ResponseFence } from "../personal/responseFence";
import { agentError } from "./labels";
import { byteVerified } from "./types";
import type { ArtifactRecord } from "./types";
export function ArtifactList({
  artifacts,
  t,
  fence,
}: {
  artifacts: ArtifactRecord[];
  t: Translate;
  fence: ResponseFence;
}) {
  const [preview, setPreview] = useState<{
    id: string;
    content: string;
    truncated: boolean;
  } | null>(null);
  const [error, setError] = useState<unknown>(null),
    [busy, setBusy] = useState<string | null>(null);
  const generation = useRef(0);
  useEffect(
    () => () => {
      generation.current++;
    },
    [],
  );
  async function open(artifact: ArtifactRecord, download: boolean) {
    const token = ++generation.current,
      epoch = fence.capture();
    const valid = () => token === generation.current && fence.accepts(epoch);
    if (!valid()) return;
    setError(null);
    setBusy(artifact.id);
    setPreview(null);
    try {
      if (!download) {
        const body = await request<{
          artifact: ArtifactRecord;
          content: string;
          truncated: boolean;
        }>(`/artifacts/${encodeURIComponent(artifact.id)}/content`);
        if (valid() && body.artifact.id === artifact.id)
          setPreview({
            id: artifact.id,
            content: body.content,
            truncated: body.truncated,
          });
      } else {
        const abort = new AbortController(),
          timer = window.setTimeout(() => abort.abort(), 12000);
        try {
          const response = await apiFetch(
            `/artifacts/${encodeURIComponent(artifact.id)}/download`,
            {
              signal: abort.signal,
              redirect: "error",
              headers: { "X-Desk-Request": "1" },
            },
          );
          if (!response.ok) {
            const body = await response.json();
            throw new ApiError(
              body.error?.code ?? "REQUEST_FAILED",
              response.status,
            );
          }
          const bytes = new Uint8Array(await response.arrayBuffer());
          if (
            bytes.byteLength > 256 * 1024 ||
            bytes.byteLength !== artifact.byte_count
          )
            throw new ApiError("ARTIFACT_VERIFICATION_FAILED");
          const digest = await crypto.subtle.digest("SHA-256", bytes);
          const hash = [...new Uint8Array(digest)]
            .map((x) => x.toString(16).padStart(2, "0"))
            .join("");
          if (hash !== artifact.sha256)
            throw new ApiError("ARTIFACT_VERIFICATION_FAILED");
          if (!valid()) return;
          const ext = { markdown: "md", text: "txt", csv: "csv", json: "json" }[
            artifact.format
          ];
          const filename = `artifact-${artifact.id.replace(/[^a-zA-Z0-9_-]/g, "")}.${ext}`;
          if (isNative) {
            let raw = "";
            for (const value of bytes) raw += String.fromCharCode(value);
            await native.exportFile({ filename, bodyBase64: btoa(raw) });
          } else {
            const url = URL.createObjectURL(
              new Blob([bytes], { type: "application/octet-stream" }),
            );
            const link = document.createElement("a");
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.setTimeout(() => URL.revokeObjectURL(url), 1000);
          }
        } finally {
          clearTimeout(timer);
        }
      }
    } catch (e) {
      if (valid()) setError(e);
    } finally {
      if (valid()) setBusy(null);
    }
  }
  return (
    <section aria-label={t("Report", "报告")} className="agent-artifacts">
      <h4>{t("Report", "报告")}</h4>
      {!artifacts.length && (
        <p>
          {t("No work report has been produced yet.", "尚未生成工作报告。")}
        </p>
      )}
      {artifacts.map((artifact) => (
        <article key={artifact.id} className="agent-artifact">
          <h5>{artifact.display_name}</h5>
          <details>
            <summary>{t("Details & sources", "详情与来源")}</summary>
            <p>
              {artifact.format.toUpperCase()} ·{" "}
              {artifact.byte_count.toLocaleString()} {t("bytes", "字节")} ·{" "}
              {artifact.authorship === "model"
                ? t("Model-authored", "模型撰写")
                : artifact.authorship === "owner"
                  ? t("Owner-authored", "本人撰写")
                  : t("Deterministic output", "确定性输出")}
            </p>
            <p>
              {byteVerified(artifact)
                ? t("Saved bytes independently read back", "已独立读回保存字节")
                : t("Saved bytes not verified", "保存字节尚未核验")}{" "}
              · {t("Content quality not reviewed", "内容质量尚未审阅")}
            </p>
            <small>SHA-256: {artifact.sha256}</small>
            <ul>
              {artifact.provenance.map((ref, i) => (
                <li key={`${ref.source_id}-${i}`}>
                  {ref.source_id} · v{ref.source_revision} · {t("lines", "行")}{" "}
                  {ref.start_line}–{ref.end_line}
                  <small>{ref.sha256}</small>
                </li>
              ))}
            </ul>
          </details>
          <div className="workspace-inline-actions">
            <button
              type="button"
              className="secondary"
              disabled={busy !== null}
              onClick={() => void open(artifact, false)}
            >
              {t("Preview", "预览")}
            </button>
            <button
              type="button"
              className="secondary"
              disabled={busy !== null || !byteVerified(artifact)}
              onClick={() => void open(artifact, true)}
            >
              {t("Download", "下载")}
            </button>
          </div>
          {busy === artifact.id && (
            <p role="status">{t("Loading file…", "正在读取文件…")}</p>
          )}
          {preview?.id === artifact.id && (
            <div className="agent-preview">
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  generation.current++;
                  setPreview(null);
                  setBusy(null);
                }}
              >
                {t("Close preview", "关闭预览")}
              </button>
              <pre tabIndex={0}>{preview.content}</pre>
              {preview.truncated && (
                <p>
                  {t(
                    "Preview is truncated at 32 KiB. Download the file to inspect all content.",
                    "预览截断于32 KiB，请下载文件检查全部内容。",
                  )}
                </p>
              )}
            </div>
          )}
        </article>
      ))}
      {!!error && (
        <p className="error-message" role="alert">
          {agentError(error, t)}
        </p>
      )}
    </section>
  );
}
