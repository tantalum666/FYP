import { captureDenial } from "./capturePolicy";
import { CaptureProvenance } from "./CaptureProvenance";
import { useEffect, useRef, useState } from "react";
import { request } from "../../api";
import { Modal } from "../../components/Dialogs";
import type { Translate } from "../../types";
import type { ResponseFence } from "../personal/responseFence";
import { agentError } from "./labels";
import type { SourceRecord } from "./types";
interface Content {
  id: string;
  name: string;
  content: string;
  start_line: number;
  end_line: number;
  total_lines: number;
  truncated: boolean;
  sha256: string;
  revision: number;
}
export function SourcePreview({
  source,
  t,
  fence,
  onClose,
}: {
  source: SourceRecord;
  t: Translate;
  fence: ResponseFence;
  onClose: () => void;
}) {
  const [start, setStart] = useState(1),
    [value, setValue] = useState<Content | null>(null),
    [error, setError] = useState<unknown>(null),
    [loading, setLoading] = useState(false);
  const sequence = useRef(0),
    live = useRef(true),
    mountEpoch = useRef(fence.capture());
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
      sequence.current++;
    };
  }, []);
  useEffect(() => {
    if (!live.current || !fence.accepts(mountEpoch.current)) return;
    const token = ++sequence.current,
      epoch = fence.capture();
    setValue(null);
    setError(null);
    setLoading(true);
    void request<Content>(
      `/sources/${encodeURIComponent(source.id)}/content?start_line=${start}&max_lines=200`,
    )
      .then((body) => {
        if (
          live.current &&
          sequence.current === token &&
          fence.accepts(epoch) &&
          body.id === source.id
        )
          setValue(body);
      })
      .catch((e) => {
        if (live.current && fence.accepts(epoch) && captureDenial(e)) {
          fence.update(`source-preview-denied:${epoch}`, false);
          sequence.current++;
          setValue(null);
          setLoading(false);
          setError(e);
        } else if (
          live.current &&
          sequence.current === token &&
          fence.accepts(epoch)
        )
          setError(e);
      })
      .finally(() => {
        if (sequence.current === token && fence.accepts(epoch))
          setLoading(false);
      });
    return () => {
      sequence.current++;
    };
  }, [source.id, start, fence]);
  if (!live.current || !fence.accepts(mountEpoch.current)) return null;
  return (
    <Modal
      title={t("Source preview", "来源预览")}
      closeLabel={t("Close", "关闭")}
      onClose={onClose}
      wide
    >
      <h3>{source.name}</h3>
      <small>
        {source.id} · SHA-256: {source.sha256}
      </small>
      {source.provenance_kind === "public_web_snapshot" && (
        <CaptureProvenance value={source.acquisition} t={t} />
      )}
      {loading && <p role="status">{t("Loading source…", "正在读取来源…")}</p>}
      {!!error && (
        <p role="alert" className="error-message">
          {agentError(error, t)}
        </p>
      )}
      {value && (
        <div className="agent-preview">
          <p>
            {t("Lines", "行")} {value.start_line}–{value.end_line} /{" "}
            {value.total_lines}
          </p>
          <pre tabIndex={0}>{value.content}</pre>
          {value.truncated && (
            <p>
              {t(
                "This preview is incomplete. The run must record its own source coverage.",
                "此预览不完整，运行仍须记录实际来源覆盖范围。",
              )}
            </p>
          )}
          <div className="workspace-inline-actions">
            <button
              type="button"
              className="secondary"
              disabled={start === 1}
              onClick={() => {
                if (live.current && fence.accepts(mountEpoch.current))
                  setStart(1);
              }}
            >
              {t("First lines", "首段")}
            </button>
            <button
              type="button"
              className="secondary"
              disabled={
                value.end_line >= value.total_lines ||
                value.end_line < value.start_line
              }
              onClick={() => {
                if (live.current && fence.accepts(mountEpoch.current))
                  setStart(value.end_line + 1);
              }}
            >
              {t("Next lines", "下一段")}
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}
