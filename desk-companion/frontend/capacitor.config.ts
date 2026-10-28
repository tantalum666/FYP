import type { CapacitorConfig } from "@capacitor/cli";
const config: CapacitorConfig = {
  appId: "dev.group2.deskcompanion",
  appName: "Desk Companion",
  webDir: "dist",
  loggingBehavior: "none",
  ios: { contentInset: "never", preferredContentMode: "mobile" },
};
export default config;
