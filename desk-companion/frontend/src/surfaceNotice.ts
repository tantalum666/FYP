import { createElement, type ReactNode } from "react";

export function loadingNotice(label: string, icon?: ReactNode) {
  return createElement(
    "div",
    { className: "app-loading", role: "status", "aria-live": "polite" },
    icon ?? null,
    createElement("span", null, label),
  );
}

export function offlineNotice(
  message: string,
  retryLabel: string,
  onRetry: () => void,
  icon?: ReactNode,
) {
  return createElement(
    "div",
    { className: "connection-banner", role: "status" },
    message,
    createElement(
      "button",
      { type: "button", onClick: onRetry },
      icon ?? null,
      retryLabel,
    ),
  );
}

export function failureNotice(
  message: string,
  dismissLabel: string,
  onDismiss: () => void,
) {
  return createElement(
    "div",
    { className: "global-error", role: "alert" },
    message,
    createElement(
      "button",
      { type: "button", onClick: onDismiss },
      dismissLabel,
    ),
  );
}

export function sessionExpiredNotice(message: string) {
  return createElement("div", { className: "global-error", role: "alert" }, message);
}
