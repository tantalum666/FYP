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
}: {
  t: Translate;
  fence: ResponseFence;
  fresh: boolean;
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
          "TXT, Markdown, CSV or JSON in UTF-8, up to 1 MiB. Uploads are retained on this server; there is no delete control in this version. 100 sources / 64 MiB total. Selecting a file alone does not upload it or authorize sending it to an AI provider.",
          "支持UTF-8的TXT、Markdown、CSV或JSON，最多1 MiB。上传内容会保留在此服务端，本版尚无删除入口；总上限100份／64 MiB。仅选择文件不会上传，也不授权向AI提供商发送。",
        )}
      </p>
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
