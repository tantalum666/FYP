import { useEffect, useRef, useState } from "react";
import { errorText, request, write } from "../api";
import type { Translate } from "../types";
import type { Proposal } from "./assistantTypes";
import { ProposalActionCard } from "./ProposalActionCard";
import { proposalDecisionNotice } from "./proposalDecision";
import { useDraftGuard } from "../components/DraftGuard";

type ConnectedApp = {
  id: "gmail" | "calendar" | "microsoft365" | "teams" | "sharepoint";
  provider: "google" | "microsoft";
  organization_only?: boolean;
  name: string;
  configured: boolean;
  connected: boolean;
  email?: string | null;
  version: string;
};
type Catalog = {
  apps: ConnectedApp[];
  mcp: Array<{ id: string; name: string; tools: number }>;
};
type Authorization = {
  app: string;
  providerName: string;
  flow: string;
  initialVersion: string;
  popup: Window | null;
  url: string;
  expires: number;
};

export function AppConnectionsPanel({ t }: { t: Translate }) {
  const [catalog, setCatalog] = useState<Catalog>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const [notice, setNotice] = useState("");
  const [proposal, setProposal] = useState<Proposal>();
  const [authorization, setAuthorization] = useState<Authorization>();
  const alive = useRef(true);
  const translate = useRef(t);
  translate.current = t;
  const readEpoch = useRef(0);
  useDraftGuard(false, busy || !!authorization);
  async function reload() {
    const epoch = ++readEpoch.current;
    const result = await request<Catalog>("/apps");
    if (alive.current && epoch === readEpoch.current) setCatalog(result);
    return result;
  }
  useEffect(() => {
    alive.current = true;
    void reload().catch((reason) => {
      if (alive.current) setError(reason);
    });
    return () => {
      alive.current = false;
      readEpoch.current++;
    };
  }, []);
  useEffect(() => {
    if (!authorization) return;
    let closed = false,
      reading = false;
    const poll = async () => {
      if (closed || reading) return;
      reading = true;
      try {
        const [fresh, flow] = await Promise.all([
          request<Catalog>("/apps"),
          request<{ status: string }>(
            `/apps/${authorization.app}/authorization/${authorization.flow}`,
          ),
        ]);
        if (closed || !alive.current) return;
        const app = fresh.apps.find((item) => item.id === authorization.app);
        if (app?.connected && app.version !== authorization.initialVersion) {
          setCatalog(fresh);
          setAuthorization(undefined);
          setError(undefined);
          setNotice(
            translate.current(`${app.name} connected.`, `${app.name} 已连接。`),
          );
          return;
        }
        if (
          !["pending", "exchanging"].includes(flow.status) ||
          performance.now() > authorization.expires
        ) {
          await request(`/apps/${authorization.app}/cancel`, {
            method: "POST",
            body: JSON.stringify({ flow_id: authorization.flow }),
          });
          if (!closed && alive.current) {
            setAuthorization(undefined);
            setNotice(
              translate.current(
                "Connection was not completed.",
                "尚未完成连接。",
              ),
            );
          }
        }
      } catch (reason) {
        if (!closed && alive.current) setError(reason);
      } finally {
        reading = false;
      }
    };
    const interval = setInterval(() => void poll(), 1500);
    window.addEventListener("focus", poll);
    return () => {
      closed = true;
      clearInterval(interval);
      window.removeEventListener("focus", poll);
      authorization.popup?.close();
    };
  }, [authorization]);
  async function perform(action: () => Promise<void>) {
    setBusy(true);
    setError(undefined);
    setNotice("");
    try {
      await action();
    } catch (reason) {
      if (alive.current) setError(reason);
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  function connect(app: ConnectedApp) {
    // Open within the click gesture; no username/password is collected by FYP.
    const popup = window.open(
      "about:blank",
      "alice-connect-app",
      "width=620,height=760",
    );
    void perform(async () => {
      try {
        const result = await request<{ url: string; flow_id: string }>(
          `/apps/${app.id}/connect`,
          { method: "POST", body: "{}" },
        );
        const target = new URL(result.url);
        const valid =
          app.provider === "google"
            ? target.origin === "https://accounts.google.com" &&
              target.pathname === "/o/oauth2/v2/auth"
            : target.origin === "https://login.microsoftonline.com" &&
              /^\/(common|organizations)\/oauth2\/v2\.0\/authorize$/.test(
                target.pathname,
              );
        if (!valid) throw new Error("Invalid authorization destination");
        if (!alive.current) {
          popup?.close();
          return;
        }
        if (popup) popup.location.href = result.url;
        setAuthorization({
          app: app.id,
          providerName: app.provider === "google" ? "Google" : "Microsoft",
          flow: result.flow_id,
          initialVersion: app.version,
          popup,
          url: result.url,
          expires: performance.now() + 600000,
        });
      } catch (reason) {
        popup?.close();
        throw reason;
      }
    });
  }
  return (
    <section className="app-connections" aria-label={t("Apps", "应用")}>
      <h3>{t("Apps", "应用")}</h3>
      {catalog?.apps.map((app) => (
        <article className="app-connection-row" key={app.id}>
          <div>
            <h4>{app.name}</h4>
            <p>
              {app.connected
                ? app.email || t("Connected", "已连接")
                : {
                    gmail: t(
                      "Prepare and send email after review.",
                      "准备邮件，确认后发送。",
                    ),
                    calendar: t(
                      "Preview your Google calendar.",
                      "查看并导入 Google 日历。",
                    ),
                    microsoft365: t(
                      "Outlook, calendar, OneDrive, To Do and OneNote.",
                      "Outlook、日历、OneDrive、To Do 与 OneNote。",
                    ),
                    teams: t(
                      "Read chats with your work or school account.",
                      "通过工作或学校账号查看聊天。",
                    ),
                    sharepoint: t(
                      "Read sites and document libraries.",
                      "查看站点与文档库。",
                    ),
                  }[app.id]}
            </p>
          </div>
          <div className="workspace-inline-actions">
            <button
              className="secondary"
              disabled={busy || !!authorization || !app.configured}
              onClick={() => connect(app)}
            >
              {app.connected
                ? t("Reconnect", "重新连接")
                : t("Connect", "连接")}
            </button>
            {app.connected && (
              <button
                className="text-button"
                disabled={busy || !!authorization}
                onClick={() =>
                  void perform(async () => {
                    await request(`/apps/${app.id}/disconnect`, {
                      method: "POST",
                      body: JSON.stringify({ expected_version: app.version }),
                    });
                    await reload();
                    setProposal(undefined);
                    window.dispatchEvent(new Event("desk:jobs"));
                  })
                }
              >
                {t("Disconnect", "断开")}
              </button>
            )}
            {["gmail", "microsoft365"].includes(app.id) && app.connected && (
              <button
                className="text-button"
                disabled={busy || !!authorization}
                onClick={() =>
                  void perform(async () => {
                    const result = await write<{ proposal?: Proposal }>(
                      "/email/drafts",
                      {
                        provider: app.id === "gmail" ? "gmail" : "outlook",
                        to: "me",
                        subject: "FYP email test",
                        body: "Test",
                      },
                    );
                    if (alive.current) setProposal(result.proposal);
                  })
                }
              >
                {t("Prepare a test email", "准备测试邮件")}
              </button>
            )}
          </div>
          {!app.configured && (
            <small>
              {t(
                "Connection setup is not finished yet.",
                "此应用的连接设置尚未完成。",
              )}
            </small>
          )}
          <details>
            <summary>{t("Access", "访问范围")}</summary>
            <p>
              {app.id === "gmail"
                ? t(
                    "Read email previews and send reviewed email.",
                    "读取邮件摘要及发送已确认的邮件。",
                  )
                : app.id === "calendar"
                  ? t(
                      "Read-only calendar events; preview before local import.",
                      "只读访问日历；导入本地前先预览。",
                    )
                  : app.id === "microsoft365"
                    ? t(
                        "Read email previews, calendar events, tasks and notebook lists; send reviewed emails. Browse Word, Excel and PowerPoint file names through OneDrive.",
                        "读取邮件摘要、日程、任务和笔记本目录；发送已确认的邮件。在 OneDrive 中查看 Word、Excel、PowerPoint 文件目录。",
                      )
                    : t(
                        "Work or school account required. Your organization's administrator may need to approve access.",
                        "需要工作或学校账号，组织管理员可能需要批准访问。",
                      )}
            </p>
          </details>
        </article>
      ))}
      {authorization && (
        <div role="status">
          <p>
            {t(
              `Complete sign-in in the ${authorization.providerName} window.`,
              `请在 ${authorization.providerName} 窗口中完成登录与授权。`,
            )}
          </p>
          {!authorization.popup && (
            <a href={authorization.url} target="_blank" rel="noreferrer">
              {t(
                `Continue to ${authorization.providerName}`,
                `前往 ${authorization.providerName} 授权`,
              )}
            </a>
          )}
          <button
            className="text-button"
            onClick={() =>
              void perform(async () => {
                await request(`/apps/${authorization.app}/cancel`, {
                  method: "POST",
                  body: JSON.stringify({ flow_id: authorization.flow }),
                });
                setAuthorization(undefined);
                await reload();
              })
            }
          >
            {t("Cancel", "取消")}
          </button>
        </div>
      )}
      {!!catalog?.mcp.length && (
        <details>
          <summary>{t("MCP connections", "MCP 连接")}</summary>
          {catalog.mcp.map((item) => (
            <p key={item.id}>
              {item.name} ·{" "}
              {t(
                `${item.tools} configured tools`,
                `${item.tools} 项已配置工具`,
              )}
            </p>
          ))}
        </details>
      )}
      {proposal && (
        <ProposalActionCard
          proposal={proposal}
          t={t}
          busy={busy}
          onDecision={(action) =>
            void perform(async () => {
              const result = await write<{ kind?: string }>(
                `/assistant/proposals/${proposal.id}/decisions`,
                { action },
              );
              if (alive.current) {
                setProposal(undefined);
                setNotice(
                  proposalDecisionNotice(result, action, proposal.kind, t),
                );
              }
              window.dispatchEvent(new Event("desk:jobs"));
            })
          }
        />
      )}
      {!!notice && <p role="status">{notice}</p>}
      {!!error && (
        <p role="alert" className="error-message">
          {errorText(error, t)}
        </p>
      )}
    </section>
  );
}
