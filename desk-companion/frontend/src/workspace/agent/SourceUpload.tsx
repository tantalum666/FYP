import type { WorkCapacity } from "./workCapacity";
import { CapacityLine, capacityBytes } from "./RetainedCapacity";
import { useEffect, useRef, useState } from "react";
import { ApiError } from "../../api";
import { useDraftGuard } from "../../components/DraftGuard";
import type { Translate } from "../../types";
import type { ResponseFence } from "../personal/responseFence";
import { agentError } from "./labels";
import { RequestFeedback } from "./RequestFeedback";
import type { SourceRecord } from "./types";
import { readSourceFile } from "./upload";
import { useUploadMutation } from "./useUploadMutation";
export function SourceUpload({
  t,
  fence,
  fresh,
  onUploaded,
  onDraftChange,
  capacity = null,
}: {
  t: Translate;
  fence: ResponseFence;
  fresh: boolean;
  capacity?: WorkCapacity | null;
  onUploaded: (source: SourceRecord) => void;
  onDraftChange: (dirty: boolean) => void;
}) {
  const [file, setFile] = useState<File | null>(null),
    [retain, setRetain] = useState(false),
    [reading, setReading] = useState(false),
    [error, setError] = useState<unknown>(null);
  const mutation = useUploadMutation();
  const freshNow = useRef(fresh);
  freshNow.current = fresh;
  useEffect(() => {
    freshNow.current = fresh;
    return () => {
      freshNow.current = false;
    };
  }, [fresh]);
  const choosing = useRef(false),
    input = useRef<HTMLInputElement>(null);
  const busy = reading || mutation.busy,
    locked = busy || mutation.pending;
  useDraftGuard(!!file || mutation.pending, busy);
  useEffect(() => {
    onDraftChange(!!file || locked);
  }, [file, locked, onDraftChange]);
  async function upload() {
    if (!freshNow.current || !file || !retain || choosing.current || locked)
      return;
    choosing.current = true;
    setReading(true);
    setError(null);
    const epoch = fence.capture();
    try {
      const prepared = await readSourceFile(file);
      if (!freshNow.current || !fence.accepts(epoch)) return;
      await mutation.run<{ source: SourceRecord }>(
        prepared.path,
        prepared.body,
        ({ source }) => {
          if (!fence.accepts(epoch)) return;
          setFile(null);
          setRetain(false);
          if (input.current) input.current.value = "";
          onUploaded(source);
        },
      );
    } catch (e) {
      if (fence.accepts(epoch))
        setError(
          new ApiError(
            e instanceof Error ? e.message : "SOURCE_FORMAT_INVALID",
          ),
        );
    } finally {
      choosing.current = false;
      if (fence.accepts(epoch)) setReading(false);
    }
  }
  return (
    <details className="agent-upload">
      <summary>{t("Add a selected local source", "添加指定本地来源")}</summary>
      <p className="workspace-hint">
        {t(
          "TXT, Markdown, CSV or JSON in UTF-8. Uploads are retained on this server; there is no delete control in this version. Selecting a file alone does not upload it or authorize sending it to an AI provider.",
          "支持UTF-8的TXT、Markdown、CSV或JSON。上传内容会保留在此服务端，本版尚无删除入口。仅选择文件不会上传，也不授权向AI提供商发送。",
        )}
      </p>
      {capacity ? (
        <div className="workspace-hint">
          <ul>
            <CapacityLine
              label={t("Source slots", "来源位置")}
              value={capacity.sources.count}
              t={t}
            />
            <CapacityLine
              label={t("Source reserved bytes", "来源保留字节")}
              value={capacity.sources.bytes}
              t={t}
              bytes
            />
          </ul>
          <p>
            {t("Per-file limit", "单文件上限")}:{" "}
            {capacityBytes(capacity.sources.file_bytes, t)}
          </p>
          {file &&
            (file.size > capacity.sources.file_bytes ||
              (capacity.sources.bytes.remaining !== null &&
                file.size > capacity.sources.bytes.remaining)) && (
              <p role="status">
                {t(
                  "The selected file exceeds the observed available bytes or per-file limit. The server makes the saving decision; your selection and retry data are preserved.",
                  "所选文件超过观察到的剩余字节或单文件上限。保存时由服务端判定；文件选择与重试资料保留。",
                )}
              </p>
            )}
        </div>
      ) : (
        <p>
          {t(
            "Capacity unavailable; the server checks limits when saving.",
            "容量不可用；保存时由服务端检查上限。",
          )}
        </p>
      )}
      <label>
        {t("Source file", "来源文件")}
        <input
          ref={input}
          type="file"
          accept=".txt,.md,.markdown,.csv,.json"
          disabled={!fresh || locked}
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setRetain(false);
            setError(null);
          }}
        />
      </label>
      <label className="agent-check">
        <input
          type="checkbox"
          checked={retain}
          disabled={!fresh || locked || !file}
          onChange={(e) => setRetain(e.target.checked)}
        />
        {t(
          "Store this selected file persistently on this server",
          "在此服务端持久保存所选文件",
        )}
      </label>
      <div className="workspace-inline-actions">
        <button
          type="button"
          className="secondary"
          disabled={!fresh || !file || !retain || locked}
          onClick={() => void upload()}
        >
          {busy
            ? t("Uploading…", "正在上传…")
            : t("Upload selected source", "上传所选来源")}
        </button>
        {file && !locked && (
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setFile(null);
              setRetain(false);
              if (input.current) input.current.value = "";
            }}
          >
            {t("Clear selection", "清除选择")}
          </button>
        )}
      </div>
      {!!error && (
        <p role="alert" className="error-message">
          {agentError(error, t)}
        </p>
      )}
      <RequestFeedback
        mutation={{
          ...mutation,
          busy: mutation.busy || !fresh,
          retry: () =>
            freshNow.current && fence.accepts(fence.capture())
              ? mutation.retry()
              : Promise.resolve(false),
        }}
        t={t}
      />
    </details>
  );
}
