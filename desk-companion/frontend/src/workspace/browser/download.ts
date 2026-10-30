import { ApiError } from "../../api";
import { apiFetch, isNative, native } from "../../native";
import { browserExportVerified } from "./types";
import type { BrowserJob } from "./types";
import { BrowserExportError, verifiedExportBytes } from "./exportVerification";

/** The owner explicitly chooses download; stale private responses never open a file. */
export async function downloadBrowserExport(
  job: BrowserJob,
  current: () => boolean,
) {
  if (!current()) throw new ApiError("BROWSER_VIEW_CHANGED");
  if (!browserExportVerified(job))
    throw new ApiError("BROWSER_EXPORT_MISMATCH");
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 12000);
  try {
    const response = await apiFetch(
      `/browser/jobs/${encodeURIComponent(job.id)}/export`,
      {
        signal: controller.signal,
        headers: { "X-Desk-Request": "1" },
      },
    );
    const bytes = await verifiedExportBytes(
      response,
      { byte_count: job.result!.byte_count!, sha256: job.result!.sha256! },
      current,
    );
    if (!current()) throw new ApiError("BROWSER_VIEW_CHANGED");
    const filename = /^fyp-source-[a-f0-9]{32}$/.test(
      job.request?.document_name ?? "",
    )
      ? `${job.request!.document_name}.md`
      : `source-brief-${job.id.replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 80)}.md`;
    if (isNative) {
      let binary = "";
      for (const byte of bytes) binary += String.fromCharCode(byte);
      await native.exportFile({ filename, bodyBase64: btoa(binary) });
    } else {
      const url = URL.createObjectURL(
        new Blob([bytes], { type: "text/markdown;charset=utf-8" }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  } catch (error) {
    if (error instanceof ApiError || error instanceof BrowserExportError)
      throw error;
    throw new ApiError("CONNECTION_LOST");
  } finally {
    window.clearTimeout(timer);
  }
}
