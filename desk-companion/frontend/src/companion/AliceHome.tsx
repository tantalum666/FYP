import { useState } from "react";
import type { DateTime } from "luxon";
import type { Language, Occurrence, Translate } from "../types";
import { ConversationWorkspace } from "../workspace/ConversationWorkspace";
import { useWorkspace } from "../workspace/WorkspaceContext";
import { useSceneActivity } from "./useSceneActivity";
import { AliceScene } from "./AliceScene";
import { HomeConditions } from "./HomeConditions";
import { AliceAgenda } from "./AliceAgenda";

export function AliceHome({
  visible = true,
  surface,
  t,
  language,
  now,
  zone,
  events,
  connection,
  obscured,
  onPlan,
  onMore,
  onReconnect,
  onTasks,
  onEvent,
  onConversationState,
  task,
  onClearTask,
}: {
  visible?: boolean;
  surface: "web" | "device";
  t: Translate;
  language: Language;
  now: DateTime;
  zone: string;
  events: Occurrence[] | null;
  connection: "online" | "offline" | "connecting";
  obscured: boolean;
  onPlan: () => void;
  onMore: () => void;
  onReconnect?: () => void;
  onTasks: () => void;
  onEvent: (event: Occurrence) => void;
  onConversationState: (value: { dirty: boolean; busy: boolean }) => void;
  task?: { id: string; title: string };
  onClearTask: () => void;
}) {
  const scene = useSceneActivity();
  const { data } = useWorkspace();
  const [expanded, setExpanded] = useState(false);
  return (
    <section
      className={`alice-home alice-home-${surface} ${expanded ? "conversation-expanded" : ""}`}
      hidden={!visible}
      aria-label={t("Alice home", "Alice 首页")}
    >
      <AliceScene
        t={t}
        active={visible && scene.visible && !scene.blocked && !obscured}
        motion={scene.motion}
        voiceState={data?.voice.state ?? "idle"}
        listening={!!data?.voice.wake_word?.active}
        obscured={obscured}
        connection={connection}
        onPlan={onPlan}
        onMore={onMore}
        onReconnect={onReconnect}
      />
      <HomeConditions
        now={now}
        zone={zone}
        language={language}
        t={t}
        visible={visible && !obscured && scene.visible}
      />
      <AliceAgenda
        t={t}
        language={language}
        now={now}
        zone={zone}
        events={events}
        obscured={obscured || expanded}
        onCalendar={onPlan}
        onEvent={onEvent}
        onTasks={onTasks}
      />
      <div className="alice-home-conversation" inert={obscured}>
        <ConversationWorkspace
          visible
          t={t}
          immersive
          expanded={expanded}
          onExpandedChange={setExpanded}
          suspended={!visible || obscured || !scene.visible}
          taskId={task?.id}
          taskTitle={task?.title}
          onClearTask={onClearTask}
          onStateChange={onConversationState}
        />
      </div>
    </section>
  );
}
