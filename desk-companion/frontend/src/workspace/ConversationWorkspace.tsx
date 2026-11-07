import { DraftGuardProvider } from "../components/DraftGuard";
import type { Translate } from "../types";
import { AssistantPanel } from "./AssistantPanel";

// This panel stays mounted across workspace navigation. Its drafts are scoped
// separately from the page editor; suspension releases media, not conversation.
export function ConversationWorkspace({
  visible,
  immersive = false,
  expanded,
  onExpandedChange,
  ...props
}: {
  visible: boolean;
  immersive?: boolean;
  expanded?: boolean;
  onExpandedChange?: (value: boolean) => void;
  suspended: boolean;
  t: Translate;
  taskId?: string;
  taskTitle?: string;
  onClearTask: () => void;
  onStateChange: (state: { dirty: boolean; busy: boolean }) => void;
}) {
  return (
    <section
      className="conversation-workspace"
      hidden={!visible}
      aria-label={props.t("Alice conversation", "Alice 对话")}
    >
      <DraftGuardProvider>
        <AssistantPanel
          {...props}
          workspace={!immersive}
          immersive={immersive}
          expanded={expanded}
          onExpandedChange={onExpandedChange}
        />
      </DraftGuardProvider>
    </section>
  );
}
