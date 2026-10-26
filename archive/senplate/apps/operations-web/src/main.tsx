import React from "react";
import { createRoot } from "react-dom/client";
import { LanguageProvider } from "./i18n";
import App from "./App";
import StationConsole from "./StationConsole";
import "./styles.css";
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <LanguageProvider>
      {location.pathname.replace(/\/+$/, "") === "/device" ? <StationConsole /> : <App />}
    </LanguageProvider>
  </React.StrictMode>,
);
