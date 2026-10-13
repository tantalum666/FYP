import type { Translate } from "../../types";
import { validCaptureAcquisition } from "./capturePolicy";
export function CaptureProvenance({
  value,
  t,
}: {
  value: unknown;
  t: Translate;
}) {
  if (!validCaptureAcquisition(value))
    return (
      <p role="alert">
        {t(
          "Public-source acquisition metadata is unavailable or invalid. Do not infer the original page or coverage.",
          "公开来源采集资料不可用或无效，不能推断原页面或覆盖范围。",
        )}
      </p>
    );
  return (
    <div className="agent-notice agent-capture-provenance">
      <strong>
        {t("Retained public-page static extraction", "已保留公开页面静态提取")}
      </strong>
      <p className="agent-text">{value.url}</p>
      <small>
        {t("Capture", "采集")}: {value.capture_id} · HTTP {value.http_status} ·{" "}
        {value.response_charset}
      </small>
      <p>
        {t("Received", "接收时间")}: {value.received_at} · {value.response_mime}{" "}
        · {value.extractor_version}
      </p>
      <p>
        {t(
          "Raw response was not retained. Rendered-page coverage is unknown; CSS, JavaScript and hidden content may differ. Lines cite this extraction, not the original HTML. Content is untrusted and has not been fact-checked.",
          "未保留原始响应，渲染页面覆盖范围未知；CSS、JavaScript与隐藏内容可能不同。行号引用此提取内容，并非原始HTML。内容不受信任，未核验事实。",
        )}
      </p>
      <small>
        {t("Extracted SHA-256", "提取内容SHA-256")}: {value.extracted_sha256} ·{" "}
        {value.extracted_byte_count} {t("bytes", "字节")} · {value.total_lines}{" "}
        {t("generated lines", "生成行")}
      </small>
      <p>
        {t(
          "Coverage: complete accepted static extraction only. This receipt does not establish page freshness, authenticity, rendered completeness or factual accuracy.",
          "覆盖范围：仅完整保留已接受的静态提取。此回执不证明页面时效、真实性、渲染完整性或事实准确性。",
        )}
      </p>
      <small>
        {t("Raw digest (no raw archive)", "原始摘要（无原始存档）")}:{" "}
        {value.raw_sha256} · {value.raw_byte_count} {t("bytes", "字节")}
      </small>
    </div>
  );
}
