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
import { SharedCalendar } from "./workspace/SharedCalendar";
import { Avatar } from "./workspace/Avatar";
import { NativeSetup } from "./workspace/NativeSetup";
import { PhoneSync } from "./workspace/PhoneFeatures";

const DeviceApp = React.lazy(() =>
  import("./device/DeviceApp").then((module) => ({
    default: module.DeviceApp,
  })),
);
const isDevice =
  new URLSearchParams(location.search).get("surface") === "device";

const root = ReactDOM.createRoot(document.getElementById("root")!);
root.render(
  <React.StrictMode>
    <NativeSetup>
      {new URLSearchParams(location.search).get("surface") === "share" ? (
        <SharedCalendar />
      ) : (
        <DraftGuardProvider>
          <WorkspaceProvider>
            <PhoneSync />
            {new URLSearchParams(location.search).get("surface") ===
            "avatar" ? (
              <Avatar standalone />
            ) : isDevice ? (
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
