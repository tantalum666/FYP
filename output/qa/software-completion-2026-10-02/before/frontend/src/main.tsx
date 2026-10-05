import React from "react";
import ReactDOM from "react-dom/client";
import "@fontsource-variable/inter";
import "./styles.css";
import { App } from "./App";

const DeviceApp = React.lazy(() =>
  import("./device/DeviceApp").then((module) => ({
    default: module.DeviceApp,
  })),
);
const isDevice =
  new URLSearchParams(location.search).get("surface") === "device";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
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
    ) : (
      <App />
    )}
  </React.StrictMode>,
);
