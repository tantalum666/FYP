import React from "react";
import { isNative } from "./native";
if (isNative) document.documentElement.classList.add("native-app");
import ReactDOM from "react-dom/client";
import "@fontsource-variable/inter";
import "./styles.css";
import { DraftGuardProvider } from "./components/DraftGuard";
import { App } from "./App";
import { WorkspaceProvider } from "./workspace/WorkspaceContext";
import "./workspace/workspace.css";
import "./web-workspace.css";
import "./conversation-workspace.css";
import { SharedCalendar } from "./workspace/SharedCalendar";
import { NativeSetup } from "./workspace/NativeSetup";
import { PhoneSync } from "./workspace/PhoneFeatures";

const PhoneApp = React.lazy(() =>
  import("./phone/PhoneApp").then((module) => ({ default: module.PhoneApp })),
);
const isPhone =
  isNative || new URLSearchParams(location.search).get("surface") === "phone";

const DeviceApp = React.lazy(() =>
  import("./device/DeviceApp").then((module) => ({
    default: module.DeviceApp,
  })),
);
const isDevice =
  new URLSearchParams(location.search).get("surface") === "device";
const isHeadStudy =
  new URLSearchParams(location.search).get("surface") === "head-history";
const HeadStudy = React.lazy(() =>
  import("./workspace/HeadStudy").then((module) => ({
    default: module.HeadStudy,
  })),
);
const modelParams = new URLSearchParams(location.search);
const isA1NativeReview = modelParams.get("surface") === "a1-history";
const A1NativeReview = React.lazy(() =>
  import("./workspace/A1NativeReview").then((module) => ({
    default: module.A1NativeReview,
  })),
);
const isExistingAvatar =
  ["head", "models", "a1"].includes(modelParams.get("surface") ?? "") ||
  (modelParams.get("surface") === "avatar" && modelParams.get("clean") !== "1");
const ExistingAvatar = React.lazy(() =>
  import("./workspace/ExistingAvatar").then((module) => ({
    default: module.ExistingAvatar,
  })),
);
const isCleanAvatar =
  modelParams.get("surface") === "avatar" && modelParams.get("clean") === "1";
const CleanAvatar = React.lazy(() =>
  import("./workspace/CleanAvatar").then((module) => ({
    default: module.CleanAvatar,
  })),
);

const root = ReactDOM.createRoot(document.getElementById("root")!);
root.render(
  <React.StrictMode>
    <NativeSetup>
      {isA1NativeReview ? (
        <React.Suspense
          fallback={<div className="app-loading">Opening archived draft…</div>}
        >
          <A1NativeReview />
        </React.Suspense>
      ) : isCleanAvatar ? (
        <React.Suspense
          fallback={
            <div className="app-loading">Opening character output…</div>
          }
        >
          <CleanAvatar />
        </React.Suspense>
      ) : isExistingAvatar ? (
        <React.Suspense
          fallback={<div className="app-loading">Opening complete model…</div>}
        >
          <ExistingAvatar />
        </React.Suspense>
      ) : isHeadStudy ? (
        <React.Suspense
          fallback={<div className="app-loading">Opening A1 head study…</div>}
        >
          <HeadStudy />
        </React.Suspense>
      ) : new URLSearchParams(location.search).get("surface") === "share" ? (
        <SharedCalendar />
      ) : (
        <DraftGuardProvider>
          <WorkspaceProvider>
            <PhoneSync />
            {isDevice ? (
              <React.Suspense
                fallback={
                  <div
                    className="app-loading"
                    style={{
                      minHeight: "100dvh",
                      background: "#171C1F",
                      color: "#F1EDE5",
                    }}
                  >
                    Opening display…
                  </div>
                }
              >
                <DeviceApp />
              </React.Suspense>
            ) : isPhone ? (
              <React.Suspense
                fallback={
                  <div className="app-loading">Opening your companion…</div>
                }
              >
                <PhoneApp />
              </React.Suspense>
            ) : (
              <App />
            )}
          </WorkspaceProvider>
        </DraftGuardProvider>
      )}
    </NativeSetup>
  </React.StrictMode>,
);
if (import.meta.hot) import.meta.hot.dispose(() => root.unmount());
