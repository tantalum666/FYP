import { lazy, Suspense, useState } from "react";
import type { Translate } from "../types";
import { useDraftState } from "../components/DraftGuard";

const WorkTools = lazy(() => import("./WorkTools"));

export function WorkToolsEntry({ t }: { t: Translate }) {
  const [open, setOpen] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const guard = useDraftState();
  return (
    <section className="task-work-tools">
      <button
        className="text-button"
        aria-expanded={open}
        onClick={() => {
          if (open && (guard.dirty || guard.busy)) {
            setBlocked(true);
            return;
          }
          setBlocked(false);
          setOpen((value) => !value);
        }}
      >
        {t("Research and follow-up tools", "资料工作与持续跟进工具")}
      </button>
      {blocked && (
        <p role="status">
          {t(
            "Save or cancel your current changes before closing.",
            "关闭前请先保存或取消当前修改。",
          )}
        </p>
      )}
      {open && (
        <Suspense fallback={<p>{t("Loading tools…", "正在载入工具…")}</p>}>
          <WorkTools t={t} />
        </Suspense>
      )}
    </section>
  );
}
