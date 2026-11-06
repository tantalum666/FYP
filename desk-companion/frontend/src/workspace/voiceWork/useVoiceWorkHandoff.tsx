import { lazy, Suspense, useEffect, useRef, useState } from "react";
import type { Translate } from "../../types";
import { useWorkspace } from "../WorkspaceContext";
import { ResponseFence } from "../personal/responseFence";
import { emptyVoiceInputs, reduceVoiceInputs } from "./types";
import type { WorkGoalRequest } from "../agent/types";

const VoiceWorkPanel = lazy(() =>
  import("./VoiceWorkPanel").then((m) => ({ default: m.VoiceWorkPanel })),
);
const WorkTools = lazy(() => import("../WorkTools"));

export function useVoiceWorkHandoff(
  t: Translate,
  taskId: string | undefined,
  suspended: boolean,
  endVoice: () => void,
  onSteered?: (reply: { text: string; message: string }) => void,
) {
  const { data, offline, stale } = useWorkspace();
  const [inputs, setInputs] = useState(emptyVoiceInputs);
  const [workVisible, setWorkVisible] = useState(false);
  const [goal, setGoal] = useState<WorkGoalRequest | null>(null);
  const [session, setSession] = useState(0);
  const fence = useRef(new ResponseFence());
  const visible =
    data?.principal.kind === "owner" &&
    !!data.personal_context_visible &&
    !offline &&
    !stale &&
    !suspended;
  fence.current.update(
    `${data?.principal.id}:${taskId}:${data?.voice.config_revision}:${session}`,
    visible,
  );
  const epoch = fence.current.capture();
  useEffect(() => {
    setInputs(emptyVoiceInputs());
    setGoal(null);
    setWorkVisible(false);
  }, [epoch]);
  useEffect(() => {
    const clear = () => {
      fence.current.update("invalidated", false);
      setInputs(emptyVoiceInputs());
      setGoal(null);
      setWorkVisible(false);
      setSession((n) => n + 1);
    };
    window.addEventListener("desk:session", clear);
    window.addEventListener("desk:personal-context", clear);
    return () => {
      window.removeEventListener("desk:session", clear);
      window.removeEventListener("desk:personal-context", clear);
    };
  }, []);
  function observe(event: { type: string }) {
    if (!fence.current.accepts(epoch)) return;
    if (event.type === "ready") setInputs(emptyVoiceInputs());
    if (event.type === "voice_input")
      setInputs((previous) => reduceVoiceInputs(previous, event));
  }
  return {
    observe,
    panel:
      visible && (inputs.inputs.length > 0 || workVisible) ? (
        <Suspense fallback={null}>
          <VoiceWorkPanel
            key={epoch}
            t={t}
            state={inputs}
            fence={fence.current}
            owner={visible}
            taskId={taskId}
            onHandoff={(next) => {
              endVoice();
              setInputs(emptyVoiceInputs());
              setGoal(next);
              setWorkVisible(true);
            }}
            onSteered={(reply) => {
              endVoice();
              setInputs(emptyVoiceInputs());
              window.dispatchEvent(new Event("desk:agent-runs"));
              onSteered?.(reply);
            }}
            onInvalidated={() => {
              setInputs(emptyVoiceInputs());
              setGoal(null);
            }}
          />
          {workVisible && (
            <WorkTools
              t={t}
              initialGoal={goal ?? undefined}
              onInitialGoalHandled={() => setGoal(null)}
            />
          )}
        </Suspense>
      ) : null,
  };
}
