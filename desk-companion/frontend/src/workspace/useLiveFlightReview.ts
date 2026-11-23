import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type RefObject,
} from "react";
import {
  getFlightCheckout,
  selectFlightSource,
  type LiveCheckout,
} from "./LiveFlightCheckout";

type Review = { chat: string; task?: string; view: LiveCheckout };
const markerKey = "desk-owner-flight-review";

export function useLiveFlightReview(
  chat: RefObject<string | undefined>,
  task: string | undefined,
  owner: boolean | undefined,
  visible: boolean,
  available: boolean,
) {
  const [current, setCurrent] = useState<Review | null>(null);
  const epoch = useRef(0);
  const clear = useCallback(() => {
    epoch.current++;
    setCurrent(null);
    sessionStorage.removeItem(markerKey);
  }, []);
  const receive = useCallback(
    (conversation: string, view: LiveCheckout) => {
      setCurrent({ chat: conversation, task, view });
      if (view.id)
        sessionStorage.setItem(
          markerKey,
          JSON.stringify({ chat: conversation, task, id: view.id }),
        );
      else sessionStorage.removeItem(markerKey);
    },
    [task],
  );
  useEffect(() => {
    window.addEventListener("desk:session", clear);
    window.addEventListener("desk:auth-required", clear);
    if (owner !== undefined && (!owner || !visible)) clear();
    if (owner && visible && available) {
      const generation = epoch.current;
      try {
        const marker = JSON.parse(sessionStorage.getItem(markerKey) ?? "null");
        if (
          marker?.id &&
          marker?.chat &&
          marker.task === task &&
          (!chat.current || chat.current === marker.chat)
        ) {
          void getFlightCheckout(marker.chat, marker.id)
            .then((view) => {
              if (
                generation !== epoch.current ||
                (chat.current && chat.current !== marker.chat)
              )
                return;
              chat.current = marker.chat;
              receive(marker.chat, view);
            })
            .catch(() => {});
        }
      } catch {
        /* A damaged or expired marker has no authority to restore a review. */
      }
    }
    return () => {
      epoch.current++;
      window.removeEventListener("desk:session", clear);
      window.removeEventListener("desk:auth-required", clear);
    };
  }, [owner, visible, available, task, chat, receive, clear]);
  const select = useCallback(
    async (source: { proposal_id?: string; job_id?: string }) => {
      const generation = epoch.current;
      const reply = await selectFlightSource(chat.current, task, source);
      if (generation !== epoch.current) return false;
      chat.current = reply.conversation_id;
      receive(reply.conversation_id, reply.live_flight_checkout);
      return true;
    },
    [chat, task, receive],
  );
  const update = useCallback(
    (original: string, next: LiveCheckout) => {
      if (!original || original !== chat.current) return;
      setCurrent((prior) =>
        prior?.chat === original &&
        prior.task === task &&
        prior.view.id === next.id
          ? { ...prior, view: next }
          : prior,
      );
    },
    [chat, task],
  );
  return { current, clear, select, receive, update };
}
