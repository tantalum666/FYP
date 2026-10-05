import type { ReactNode } from "react";
import { isNative } from "../native";
import { downloadFile } from "../api";

export function ExportLink({
  path,
  filename,
  children,
  onError,
  disabled = false,
}: {
  path: string;
  filename: string;
  children: ReactNode;
  onError: (error: unknown) => void;
  disabled?: boolean;
}) {
  if (isNative)
    return (
      <button
        type="button"
        className="secondary"
        disabled={disabled}
        onClick={() => void downloadFile(path, filename).catch(onError)}
      >
        {children}
      </button>
    );
  return (
    <a
      className="secondary export-link"
      href={"/api" + path}
      download={filename}
      aria-disabled={disabled}
      onClick={(event) => {
        if (disabled) event.preventDefault();
      }}
    >
      {children}
    </a>
  );
}
