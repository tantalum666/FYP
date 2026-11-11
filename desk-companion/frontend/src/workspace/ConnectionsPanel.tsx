import { useEffect, useState } from "react";
import { Link2, Monitor, ShieldCheck, Smartphone } from "lucide-react";
import { errorText, request, write } from "../api";
import type { Session, Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import { OwnerAccess } from "./OwnerAccess";
import { AppConnectionsPanel } from "./AppConnectionsPanel";

export function PairDeviceForm({
  t,
  onPaired,
}: {
  t: Translate;
  onPaired: (session: Session) => void;
}) {
  const [code, setCode] = useState(""),
    [name, setName] = useState("My phone"),
    [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<{
      request_id: string;
      secret: string;
      check_code: string;
    } | null>(null),
    [error, setError] = useState<unknown>(null);
  const [state, setState] = useState("idle");
  useEffect(() => {
    if (!pending) return;
    let alive = true,
      working = false;
    const poll = async () => {
      if (working) return;
      working = true;
      try {
        const r = await request<{ state: string }>("/pairing/claim", {
          method: "POST",
          body: JSON.stringify({
            request_id: pending.request_id,
            secret: pending.secret,
          }),
        });
        if (!alive) return;
        setState(r.state);
        if (r.state === "approved") {
          onPaired(await request<Session>("/session"));
          setPending(null);
          window.dispatchEvent(new Event("desk:session"));
        } else if (r.state !== "pending") setPending(null);
      } catch (e) {
        if (alive) {
          setError(e);
          setPending(null);
        }
      } finally {
        working = false;
      }
    };
    void poll();
    const timer = setInterval(() => void poll(), 2000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [pending, onPaired]);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setPending(
        await request("/pairing/requests", {
          method: "POST",
          body: JSON.stringify({ code, name }),
        }),
      );
      setState("pending");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="pair-device-form">
      {pending ? (
        <div className="pair-code">
          <ShieldCheck />
          <h3>{t("Approve on your desk", "请在桌面端批准")}</h3>
          <p>
            {t(
              "Check that both screens show this number.",
              "请核对两边显示的号码一致。",
            )}
          </p>
          <strong>{pending.check_code}</strong>
          <button
            className="secondary"
            onClick={() => {
              setPending(null);
              setState("idle");
            }}
          >
            {t("Back", "返回")}
          </button>
        </div>
      ) : (
        <form onSubmit={submit}>
          <p>
            {t(
              "Create a pairing code in Device → Connections on your desk, then enter it here.",
              "在桌面端的“设备 → 连接”生成配对码，再填到这里。",
            )}
          </p>
          <label className="field">
            {t("Pairing code", "配对码")}
            <input
              required
              inputMode="numeric"
              pattern="[0-9]{8}"
              maxLength={8}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            />
          </label>
          <label className="field">
            {t("Screen name", "终端名称")}
            <input
              required
              maxLength={60}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <button className="primary" disabled={busy}>
            {t("Request pairing", "申请配对")}
          </button>
        </form>
      )}
      {state === "rejected" && (
        <p>
          {t(
            "Pairing was declined. Create a new code to try again.",
            "配对已拒绝，可生成新码后重试。",
          )}
        </p>
      )}
      {!!error && (
        <p role="alert" className="error-message">
          {errorText(error, t)}
        </p>
      )}
    </div>
  );
}

export function ConnectionsPanel({
  t,
  isDisplay = false,
}: {
  t: Translate;
  isDisplay?: boolean;
}) {
  const { data, refresh, offline } = useWorkspace();
  const [code, setCode] = useState<{ code: string; expires_at: string } | null>(
      null,
    ),
    [error, setError] = useState<unknown>(null),
    [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  async function act(path: string, body: unknown) {
    setBusy(true);
    setError(null);
    try {
      const r = await write(path, body);
      await refresh();
      return r;
    } catch (e) {
      setError(e);
      return null;
    } finally {
      setBusy(false);
    }
  }
  if (!data) return <p>{t("Connecting…", "正在连接…")}</p>;
  return (
    <div className="workspace-panel">
      {data.principal.kind === "owner" && <AppConnectionsPanel t={t} />}
      <div className="workspace-state">
        <Link2 />
        <div>
          <h3>{t("Connected screens", "已连接终端")}</h3>
          <p>
            {t(
              "Approved screens use the same calendar. You can revoke access here.",
              "获准终端共用同一份日历，可以在此撤销访问。",
            )}
          </p>
        </div>
      </div>
      {data.principal.kind !== "owner" ? (
        <>
          <p className="workspace-hint">
            {t(
              "Manage connected screens from your main desk.",
              "请在主桌面管理已连接的终端。",
            )}
          </p>
          <OwnerAccess t={t} />
        </>
      ) : (
        <>
          {isDisplay && (
            <button
              className="secondary"
              disabled={busy || offline}
              onClick={async () => {
                if (
                  await act("/devices/enrol-display", { name: "Desk display" })
                )
                  setNotice(
                    t(
                      "This display is paired and can reconnect after the owner session ends.",
                      "本屏幕已配对，拥有者会话结束后仍可重新连接。",
                    ),
                  );
              }}
            >
              <Monitor size={18} />
              {t("Keep this display paired", "保持本屏幕配对")}
            </button>
          )}
          <div className="workspace-inline-actions">
            <button
              className="primary"
              disabled={busy || offline}
              onClick={async () => {
                const result = await act("/pairing/codes", {
                  kind: "controller",
                });
                if (result)
                  setCode(result as { code: string; expires_at: string });
              }}
            >
              <Smartphone size={18} />
              {t("Pair another screen", "配对其他终端")}
            </button>
          </div>
          {code && Date.now() < new Date(code.expires_at).getTime() && (
            <div className="pair-code">
              <span>
                {t(
                  "Single-use code · valid for two minutes",
                  "单次配对码 · 两分钟有效",
                )}
              </span>
              <strong>
                {code.code.slice(0, 4)} {code.code.slice(4)}
              </strong>
              <small>
                {t(
                  "Approve the matching check number when the request appears below.",
                  "收到下方申请后，请核对号码再批准。",
                )}
              </small>
            </div>
          )}
          {data.pairing?.requests.map((r) => (
            <div className="pair-request" key={r.id}>
              <div>
                <strong>{r.name}</strong>
                <p>
                  {t("Check number", "核对号码")} <b>{r.check_code}</b>
                </p>
              </div>
              <div className="workspace-inline-actions">
                <button
                  className="primary"
                  disabled={busy}
                  onClick={async () => {
                    if (
                      await act("/pairing/decisions", {
                        request_id: r.id,
                        action: "approve",
                      })
                    )
                      setCode(null);
                  }}
                >
                  {t("Approve", "批准")}
                </button>
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={async () => {
                    if (
                      await act("/pairing/decisions", {
                        request_id: r.id,
                        action: "reject",
                      })
                    )
                      setCode(null);
                  }}
                >
                  {t("Decline", "拒绝")}
                </button>
              </div>
            </div>
          ))}
          <div className="workspace-list">
            {data.pairing?.clients.map((client) => (
              <div className="workspace-list-row" key={client.id}>
                <div>
                  <strong>{client.name}</strong>
                  <small>
                    {client.kind === "display"
                      ? t("Desk display", "桌面屏幕")
                      : t("Control screen", "控制终端")}
                  </small>
                </div>
                <button
                  className="text-button danger"
                  disabled={busy}
                  onClick={() => void act(`/devices/${client.id}/revoke`, {})}
                >
                  {t("Revoke", "撤销")}
                </button>
              </div>
            ))}
            {!data.pairing?.clients.length && (
              <p>{t("No paired screens yet.", "还没有配对终端。")}</p>
            )}
          </div>
        </>
      )}
      <section className="workspace-section">
        <h3>{t("Physical outputs", "实体反馈")}</h3>
        <p>
          {data.outputs.connected
            ? t("Output controller connected", "反馈控制器已连接")
            : t("Output controller not connected", "反馈控制器未连接")}
        </p>
        {data.outputs.source === "replay" && (
          <p className="source-badge">
            {t(
              "Replay controller · no physical action",
              "回放控制器 · 无实际动作",
            )}
          </p>
        )}
        <div className="workspace-inline-actions">
          <button
            className="danger-button"
            onClick={async () => {
              try {
                await request("/outputs/stop", {
                  method: "POST",
                  body: "{}",
                  headers: { "X-Operation-Id": crypto.randomUUID() },
                });
                await refresh();
              } catch (error) {
                setError(error);
              }
            }}
          >
            {t("Stop physical outputs", "停止实体反馈")}
          </button>
          {data.principal.kind === "owner" && (
            <button
              className="secondary"
              disabled={
                busy ||
                !data.outputs.connected ||
                !data.outputs.hardware_verified
              }
              onClick={() => void act("/outputs/enable", {})}
            >
              {t("Enable verified outputs", "启用已验证反馈设备")}
            </button>
          )}
        </div>
        {data.outputs.connected &&
          data.outputs.hardware_verified &&
          !data.outputs.stopped && (
            <div className="workspace-inline-actions">
              {data.outputs.capabilities.includes("arm") &&
                ["rest", "attention", "point_calendar"].map((preset, i) => (
                  <button
                    type="button"
                    key={preset}
                    className="secondary"
                    disabled={busy}
                    onClick={() =>
                      void act("/outputs/commands", { kind: "arm", preset })
                    }
                  >
                    {t(
                      ["Rest pose", "Attention gesture", "Point to calendar"][
                        i
                      ],
                      ["回到原位", "提示动作", "指向日历"][i],
                    )}
                  </button>
                ))}
              {data.outputs.capabilities.includes("light") &&
                ["off", "calm", "attention"].map((preset, i) => (
                  <button
                    type="button"
                    key={preset}
                    className="secondary"
                    disabled={busy}
                    onClick={() =>
                      void act("/outputs/commands", { kind: "light", preset })
                    }
                  >
                    {t(
                      ["Light off", "Steady light", "Attention light"][i],
                      ["关闭灯光", "常亮灯光", "提示灯光"][i],
                    )}
                  </button>
                ))}
            </div>
          )}
        <p className="workspace-hint">
          {data.outputs.stopped
            ? t(
                "Software stop is active. The physical stop switch remains independent.",
                "软件停止已启用，实物停机开关独立生效。",
              )
            : t(
                "Only named, verified actions are enabled.",
                "只允许已验证的预设动作。",
              )}
        </p>
      </section>
      {!!data.output_history?.length && (
        <section className="workspace-section">
          <h3>{t("Recent output receipts", "最近设备回执")}</h3>
          {data.output_history.slice(0, 5).map((item) => (
            <div className="workspace-list-row" key={item.id}>
              <span>
                {item.kind} · {item.preset}
              </span>
              <small>
                {item.state === "executed"
                  ? t("Driver reported completion", "驱动报告完成")
                  : item.state === "simulated"
                    ? t("Simulated", "已模拟")
                    : item.state === "failed"
                      ? t("Failed", "失败")
                      : item.state === "expired"
                        ? t("Expired", "已过期")
                        : item.state === "cancelled"
                          ? t("Cancelled", "已取消")
                          : t("Awaiting receipt", "等待回执")}
              </small>
            </div>
          ))}
        </section>
      )}
      {notice && <p role="status">{notice}</p>}
      {!!error && (
        <p role="alert" className="error-message">
          {errorText(error, t)}
        </p>
      )}
    </div>
  );
}
