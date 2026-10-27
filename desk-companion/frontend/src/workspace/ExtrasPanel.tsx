import { useEffect, useRef, useState } from "react";
import { useDraftGuard } from "../components/DraftGuard";
import { errorText, write } from "../api";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import { CheckIns } from "./CheckIns";
import type { WorkspacePreferences } from "./types";

export function ExtrasPanel({ t }: { t: Translate }) {
  const { data, refresh } = useWorkspace();
  const saved = data?.calendar_extras.preferences;
  const [form, setForm] = useState<WorkspacePreferences | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null),
    [notice, setNotice] = useState("");
  const baseline = useRef<WorkspacePreferences | null>(null);
  useDraftGuard(
    !!form &&
      !!baseline.current &&
      JSON.stringify(form) !== JSON.stringify(baseline.current),
    busy,
  );
  useEffect(() => {
    if (saved && !form) {
      setForm(saved);
      baseline.current = saved;
    }
  }, [saved, form]);
  if (!form || !saved)
    return <p>{t("Loading preferences…", "正在读取偏好…")}</p>;
  const change = <K extends keyof WorkspacePreferences>(
    key: K,
    value: WorkspacePreferences[K],
  ) => { setForm({ ...form, [key]: value }); setNotice(""); };
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { version, ...preferences } = form!;
      const next = await write<WorkspacePreferences>("/workspace/preferences", {
        expected_version: version,
        preferences,
      });
      setForm({ ...preferences, version: next.version });
      baseline.current = { ...preferences, version: next.version };
      await refresh();
      setNotice(t("Preferences saved.", "偏好已保存。"));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="workspace-panel" onSubmit={save}>
      <h3>{t("Make this desk yours", "适合你的桌面")}</h3>
      <div className="workspace-form-grid">
        <label className="field">
          {t("Weather location", "天气地区")}
          <select
            value={form.weather_location}
            onChange={(e) =>
              change("weather_location", e.target.value as "none" | "hong_kong")
            }
          >
            <option value="none">{t("Not selected", "未选择")}</option>
            <option value="hong_kong">
              {t("Hong Kong Observatory", "香港天文台")}
            </option>
          </select>
        </label>
        <label className="field">
          {t("Public holidays", "公众假期")}
          <select
            value={form.holiday_region}
            onChange={(e) =>
              change("holiday_region", e.target.value as "none" | "hong_kong")
            }
          >
            <option value="none">{t("Not selected", "未选择")}</option>
            <option value="hong_kong">
              {t("Hong Kong · 2025–2027", "香港 · 2025–2027")}
            </option>
          </select>
        </label>
      </div>
      <p className="workspace-hint">
        {t(
          "Weather is fetched only after a location is selected. Holiday dates are public holidays, not a calculation of leave entitlement.",
          "选择地区后才读取天气。此处为公众假期，不计算个人休假资格。",
        )}
      </p>
      <label className="check-field">
        <input
          type="checkbox"
          checked={form.show_lunar}
          onChange={(e) => change("show_lunar", e.target.checked)}
        />
        {t("Show the Chinese lunar date", "显示农历日期")}
      </label>
      <section className="workspace-section">
        <h3>{t("Reminders & quiet hours", "提醒与安静时段")}</h3>
        <label className="field">
          {t("Reminder strength", "提醒方式")}
          <select
            value={form.reminder_strength}
            onChange={(e) =>
              change("reminder_strength", e.target.value as "silent" | "chime")
            }
          >
            <option value="silent">{t("On-screen only", "仅屏幕显示")}</option>
            <option value="chime">
              {t("On-screen + desk chime", "屏幕与桌面提示音")}
            </option>
          </select>
        </label>
        <p className="workspace-hint">
          {t(
            "The desk screen must also enable sound once. Quiet hours suppress sound, not calendar reminders.",
            "桌面屏幕还需首次启用声音。安静时段只暂停声音，不隐藏日历提醒。",
          )}
        </p>
        <label className="check-field">
          <input
            type="checkbox"
            checked={form.quiet_enabled}
            onChange={(e) => change("quiet_enabled", e.target.checked)}
          />
          {t("Use quiet hours", "启用安静时段")}
        </label>
        <div className="workspace-form-grid">
          <label className="field">
            {t("From", "开始")}
            <input
              type="time"
              required
              value={form.quiet_start}
              onInput={(e) => change("quiet_start", e.currentTarget.value)}
            />
          </label>
          <label className="field">
            {t("Until", "结束")}
            <input
              type="time"
              required
              value={form.quiet_end}
              onInput={(e) => change("quiet_end", e.currentTarget.value)}
            />
          </label>
        </div>
        <label className="check-field">
          <input
            type="checkbox"
            checked={form.daily_brief_enabled}
            onChange={(e) => change("daily_brief_enabled", e.target.checked)}
          />
          {t("Morning calendar briefing", "早晨行程简报")}
        </label>
        <label className="field">
          {t("Briefing time", "简报时间")}
          <input
            type="time"
            required
            value={form.daily_brief_time}
            onInput={(e) => change("daily_brief_time", e.currentTarget.value)}
          />
        </label>
        <label className="check-field">
          <input
            type="checkbox"
            checked={form.evening_check_enabled}
            onChange={(e) => change("evening_check_enabled", e.target.checked)}
          />
          {t("Evening check-in", "晚间检查")}
        </label>
        <label className="field">
          {t("Check-in time", "检查时间")}
          <input
            type="time"
            required
            value={form.evening_check_time}
            onInput={(e) => change("evening_check_time", e.currentTarget.value)}
          />
        </label>
        <p className="workspace-hint">
          {t(
            "Morning and evening check-ins use these times and the quiet hours above. Each one explains why it fired. They do not create a second reminder schedule.",
            "早晨简报和晚间检查使用这里的时间和上方的安静时段。每一条都会说明触发原因，不会另建一套提醒。",
          )}
        </p>
        <CheckIns t={t} />
      </section>
      <section className="workspace-section">
        <h3>{t("Companion", "桌面助理")}</h3>
        <label className="check-field">
          <input
            type="checkbox"
            checked={form.voice_enabled}
            onChange={(e) => change("voice_enabled", e.target.checked)}
          />
          {t("Allow the local wake-word worker", "允许本地唤醒词工作进程")}
        </label>
        <p className="workspace-hint">
          {t(
            "The local worker listens for its configured phrase before opening a voice session. It requires a microphone and an installed wake model.",
            "本地进程检测配置的唤醒词后才打开语音会话，需要麦克风和已安装的唤醒模型。",
          )}
        </p>
        <label className="field">
          {t("Always-on display scene", "常亮画面")}
          <select
            value={form.avatar_display}
            onChange={(e) =>
              change(
                "avatar_display",
                e.target.value as "calendar" | "companion",
              )
            }
          >
            <option value="calendar">{t("Calendar", "日历")}</option>
            <option value="companion">
              {t("Companion & next event", "角色与下一项日程")}
            </option>
          </select>
        </label>
      </section>
      <button className="primary" disabled={busy}>
        {t("Save preferences", "保存偏好")}
      </button>
      {notice && <p role="status">{notice}</p>}
      {!!error && (
        <p className="error-message" role="alert">
          {errorText(error, t)}
        </p>
      )}
    </form>
  );
}
