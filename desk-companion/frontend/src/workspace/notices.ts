/** Browser notification payload. The desk does not contact a push service. */

export interface DeskNotice {
  id: string;
  kind?: string;
  state: string;
  title_en: string;
  title_zh: string;
  body_en: string;
  body_zh: string;
  reason_en: string;
  reason_zh: string;
  push: { title: string; body: string; tag: string };
}

export function browserPayload(notice: DeskNotice, language: "en" | "zh") {
  const title = language === "zh" ? notice.title_zh : notice.title_en;
  const body =
    notice.kind === "memory_morning"
      ? language === "zh"
        ? "请打开记忆页查看早晨核对。"
        : "Open Memory to read the morning check-in."
      : language === "zh"
        ? notice.body_zh
        : notice.body_en;
  return { title, options: { body, tag: notice.push.tag } };
}

export function showBrowserNotice(
  notice: DeskNotice,
  language: "en" | "zh",
  notifier:
    | {
        permission: string;
        show: (title: string, options: { body: string; tag: string }) => void;
      }
    | undefined,
): boolean {
  if (
    !notifier ||
    notifier.permission !== "granted" ||
    notice.state === "dismissed"
  )
    return false;
  const payload = browserPayload(notice, language);
  notifier.show(payload.title, payload.options);
  return true;
}

export function openNotices(notices: DeskNotice[]): DeskNotice[] {
  const seen = new Set<string>();
  return notices.filter((notice) => {
    if (notice.state !== "open" || seen.has(notice.id)) return false;
    seen.add(notice.id);
    return true;
  });
}
