import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useWorkspace } from "../WorkspaceContext";
import { apiOrigin } from "../../native";
import {
  BrowserPostureCapture,
  type CameraState,
} from "./BrowserPostureCapture";

const KEY = "desk.posture.local-camera.v1";
const Context = createContext<{
  state: CameraState;
  allowed: boolean;
  enable: () => void;
  disable: () => void;
}>({ state: { phase: "idle" }, allowed: false, enable() {}, disable() {} });

function saved(origin: string) {
  try {
    return localStorage.getItem(`${KEY}:${origin}`) === "enabled";
  } catch {
    return false;
  }
}
function clientId() {
  try {
    const value = localStorage.getItem(KEY + ".client");
    if (value && /^[a-f0-9-]{36}$/.test(value)) return value;
    const next = crypto.randomUUID();
    localStorage.setItem(KEY + ".client", next);
    return next;
  } catch {
    return crypto.randomUUID();
  }
}

/** Mounted above navigation, so opening a panel does not restart the camera. */
export function PostureCaptureProvider({ children }: { children: ReactNode }) {
  const { data, offline, stale } = useWorkspace();
  const origin = apiOrigin();
  const [consent, setConsent] = useState(() => ({
    origin,
    allowed: saved(origin),
  }));
  const allowed = consent.origin === origin && consent.allowed;
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState<CameraState>({ phase: "idle" });
  const prompt = useRef(false);
  const [client] = useState(clientId);
  const capture = useRef<BrowserPostureCapture | null>(null);
  const configured = !!(
    allowed &&
    data?.principal.kind === "owner" &&
    data.personal_context_visible &&
    data.posture.preferences.enabled &&
    !data.posture.paused &&
    data.posture.preferences.camera_source === "browser"
  );
  const active = configured && !offline && !stale;
  useEffect(() => {
    // Desktop tabs may continue while open. Mobile OS suspension can expire a
    // lease; returning starts a fresh stream automatically, without a new grant.
    const changed = () => {
      if (!document.hidden && configured) setRevision((value) => value + 1);
    };
    document.addEventListener("visibilitychange", changed);
    return () => document.removeEventListener("visibilitychange", changed);
  }, [configured]);
  useEffect(() => {
    if (!active) {
      setState({ phase: "idle" });
      return;
    }
    let current = true;
    const session = new BrowserPostureCapture((next) => {
      if (current) setState(next);
    });
    capture.current = session;
    const mayPrompt = prompt.current;
    prompt.current = false;
    void session.start(client, mayPrompt).catch(() => {
      if (current)
        setState({ phase: "error", code: "POSTURE_CAMERA_UNAVAILABLE" });
    });
    return () => {
      current = false;
      session.stop();
      if (capture.current === session) capture.current = null;
    };
  }, [active, revision, client]);
  return (
    <Context.Provider
      value={{
        state,
        allowed,
        enable: () => {
          prompt.current = true;
          try {
            localStorage.setItem(`${KEY}:${origin}`, "enabled");
          } catch {
            /* Current visit still works. */
          }
          setConsent({ origin, allowed: true });
          setRevision((value) => value + 1);
        },
        disable: () => {
          capture.current?.stop();
          setState({ phase: "idle" });
          try {
            localStorage.removeItem(`${KEY}:${origin}`);
          } catch {
            /* Stop remains immediate. */
          }
          setConsent({ origin, allowed: false });
        },
      }}
    >
      {children}
    </Context.Provider>
  );
}
export const usePostureCapture = () => useContext(Context);
