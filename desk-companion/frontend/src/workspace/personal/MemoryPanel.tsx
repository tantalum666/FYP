import { Modal } from "../../components/Dialogs";
import { useDraftState } from "../../components/DraftGuard";
import type { Translate } from "../../types";
import { MemoryPanel as CanonicalMemoryPanel } from "../MemoryPanel";
import type { PersonalMemory } from "./types";
import type { PrivateMutation } from "./usePrivateMutation";

/** Saved chat and ordinary assistant edit the same fact service and UI. */
export function MemoryPanel({
  t,
  onClose,
}: {
  memories: PersonalMemory[];
  mutation: PrivateMutation;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
  t: Translate;
}) {
  const guard = useDraftState();
  return (
    <Modal
      title={t("Saved memories", "已保存记忆")}
      closeLabel={t("Close memories", "关闭记忆")}
      onClose={onClose}
      dirty={guard.dirty}
      busy={guard.busy}
      wide
    >
      <CanonicalMemoryPanel t={t} />
    </Modal>
  );
}
