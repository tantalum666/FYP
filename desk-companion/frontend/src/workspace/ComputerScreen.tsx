import { useEffect, useRef, useState } from "react";
import { apiFetch } from "../native";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import { ResponseFence } from "./personal/responseFence";
import { Modal } from "../components/Dialogs";
import "./computer-use.css";

export function ComputerScreen({
  jobId,
  refresh,
  t,
}: {
  jobId: string;
  refresh: number;
  t: Translate;
}) {
  const { data, offline, stale } = useWorkspace();
  const fence = useRef(new ResponseFence()).current;
  const visible = !!(
    data?.principal.kind === "owner" &&
    data.personal_context_visible &&
    !offline &&
    !stale
  );
  fence.update(`${data?.principal.kind}:${data?.principal.id}`, visible);
  const epoch = fence.capture();
  const [image, setImage] = useState<{ url: string; epoch: number } | null>(
    null,
  );
  const current = useRef<string | null>(null);
  const [zoom, setZoom] = useState(false);
  const etag = useRef("");
  const imageEpoch = useRef(epoch);
  useEffect(() => {
    return () => {
      if (current.current) URL.revokeObjectURL(current.current);
      current.current = null;
    };
  }, []);
  useEffect(() => {
    let live = true;
    const controller = new AbortController();
    if (!visible || imageEpoch.current !== epoch) {
      if (current.current) URL.revokeObjectURL(current.current);
      current.current = null;
      etag.current = "";
      setImage(null);
      imageEpoch.current = epoch;
      if (!visible) return;
    }
    void (async () => {
      try {
        const response = await apiFetch(
          `/computer/computer-use/jobs/${jobId}/screen`,
          {
            signal: controller.signal,
            headers: { "X-Desk-Request": "1", "If-None-Match": etag.current },
          },
        );
        if (!live || response.status === 304 || !response.ok) return;
        const blob = await response.blob();
        if (!live || blob.size > 2_000_000 || blob.type !== "image/png") return;
        const next = URL.createObjectURL(blob);
        if (current.current) URL.revokeObjectURL(current.current);
        current.current = next;
        etag.current = response.headers.get("etag") ?? "";
        setImage({ url: next, epoch });
      } catch {
        /* The job card retains authoritative error/unknown status. */
      }
    })();
    return () => {
      live = false;
      controller.abort();
    };
  }, [jobId, refresh, visible, epoch]);
  return image && image.epoch === epoch && visible ? (
    <figure className="computer-use-screen">
      <img
        src={image.url}
        alt={t("Last observed browser screen", "最近观察到的浏览器画面")}
      />
      <figcaption>
        {t(
          "Last observed screen · review before continuing",
          "最近的操作画面 · 继续前请核对",
        )}
        {" · "}
        <button
          type="button"
          className="text-button"
          onClick={() => setZoom(true)}
        >
          {t("View full size", "原尺寸查看")}
        </button>
      </figcaption>
      {zoom && (
        <Modal
          title={t("Observed browser screen", "浏览器观察画面")}
          closeLabel={t("Close screen", "关闭画面")}
          onClose={() => setZoom(false)}
        >
          <div className="computer-use-zoom">
            <img
              className="computer-full-image"
              src={image.url}
              alt={t("Read-only browser observation", "只读浏览器观察画面")}
            />
          </div>
        </Modal>
      )}
    </figure>
  ) : null;
}
