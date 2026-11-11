import { FileText, X } from "lucide-react";
import type { Translate } from "../types";
import { fileBytesLabel, type PickedChatFile } from "./chatFiles";

export function ComposerFiles({
  files,
  locked,
  onRemove,
  t,
}: {
  files: PickedChatFile[];
  locked: boolean;
  onRemove: (key: string) => void;
  t: Translate;
}) {
  if (!files.length) return null;
  return (
    <div
      className="composer-files"
      aria-label={t("Attached files", "已添加的文件")}
    >
      <div className="composer-files-list">
        {files.map((item) => (
          <div className="composer-file" key={item.key}>
            {item.preview ? (
              <img src={item.preview} alt="" />
            ) : (
              <FileText size={21} aria-hidden="true" />
            )}
            <span>
              <strong title={item.file.name}>{item.file.name}</strong>
              <small>{fileBytesLabel(item.file.size)}</small>
            </span>
            <button
              type="button"
              disabled={locked}
              onClick={() => onRemove(item.key)}
              aria-label={t(
                `Remove ${item.file.name}`,
                `移除 ${item.file.name}`,
              )}
            >
              <X size={15} />
            </button>
          </div>
        ))}
      </div>
      <small className="composer-files-note">
        {t(
          "Files are shared with the cloud assistant when you send.",
          "发送消息时，附件会一并交给云端助手处理。",
        )}
      </small>
    </div>
  );
}
