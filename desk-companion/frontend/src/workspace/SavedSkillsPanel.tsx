import { useEffect, useState } from "react";
import { DateTime } from "luxon";
import { ApiError, request } from "../api";
import { useDraftGuard } from "../components/DraftGuard";
import type { Translate } from "../types";
import { useWorkspace } from "./WorkspaceContext";
import { personalContextVisible } from "./personal/types";
import { usePrivateMutation } from "./personal/usePrivateMutation";
import { SavedSkillRun, type SavedSkillRunData } from "./SavedSkillRun";
import {
  checkBody,
  decisionBody,
  fillReady,
  runBody,
  scheduleBody,
  scheduleSkipNotice,
  skillError,
  type SkillScheduleDraft,
} from "./savedSkillState";
import "./saved-skills.css";

interface Skill {
  id: string;
  version: number;
  title: string;
  steps: string[];
  input_names: string[];
}

interface CheckResult {
  skill: Skill | null;
  saved: boolean;
}

interface SkillSchedule {
  id: string;
  frequency: SkillScheduleDraft["frequency"];
  timezone: string;
  inputs: Record<string, string>;
  note: string | null;
  note_provided: boolean;
  version: number;
  status: string;
  next_run_at: string | null;
  last_outcome: string | null;
}

function frequencyLabel(value: string, t: Translate) {
  return (
    {
      once: t("Once", "单次"),
      daily: t("Daily", "每天"),
      weekly: t("Weekly", "每周"),
    }[value] ?? value
  );
}

function scheduleStatus(status: string, t: Translate) {
  return (
    {
      active: t("Active", "启用中"),
      paused: t("Paused", "已暂停"),
      completed: t("Finished", "已结束"),
      cancelled: t("Cancelled", "已取消"),
    }[status] ?? status
  );
}

function nextLabel(value: string | null, zone: string, t: Translate) {
  if (!value) return t("No next time", "没有下一次");
  const local = DateTime.fromISO(value).setZone(zone);
  return local.isValid ? local.toFormat("yyyy-MM-dd HH:mm") : value;
}

export function SavedSkillsPanel({ t }: { t: Translate }) {
  const { data, offline, stale } = useWorkspace();
  const visible = personalContextVisible(
    data?.principal.kind === "owner",
    data?.personal_context_visible,
    offline,
    stale,
  );
  const [skills, setSkills] = useState<Skill[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [skill, setSkill] = useState<Skill | null>(null);
  const [runs, setRuns] = useState<SavedSkillRunData[]>([]);
  const [title, setTitle] = useState("");
  const [steps, setSteps] = useState("");
  const [names, setNames] = useState("");
  const [passed, setPassed] = useState(false);
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [note, setNote] = useState("");
  const [schedules, setSchedules] = useState<SkillSchedule[]>([]);
  const [frequency, setFrequency] = useState<SkillScheduleDraft["frequency"]>("daily");
  const [startLocal, setStartLocal] = useState("");
  const [zone, setZone] = useState("Asia/Hong_Kong");
  const [localError, setLocalError] = useState<string | null>(null);
  const [readError, setReadError] = useState<unknown>(null);
  const [revision, setRevision] = useState(0);
  const mutation = usePrivateMutation();
  const dirty =
    passed ||
    zone.trim() !== "Asia/Hong_Kong" ||
    [title, steps, names, note, startLocal, ...Object.values(inputs)].some((value) =>
      value.trim(),
    );
  useDraftGuard(dirty, mutation.busy);

  useEffect(() => {
    if (!visible) {
      setSkills([]);
      setSkill(null);
      setRuns([]);
      setSchedules([]);
      setInputs({});
      return;
    }
    let live = true;
    void request<{ skills: Skill[] }>("/saved-skills").then(
      (list) => {
        if (!live) return;
        setSkills(list.skills);
        setReadError(null);
      },
      (error) => {
        if (live) setReadError(error);
      },
    );
    return () => {
      live = false;
    };
  }, [visible, revision]);

  useEffect(() => {
    if (!visible || !selected) return;
    let live = true;
    void request<{ skill: Skill; runs: SavedSkillRunData[]; schedules?: SkillSchedule[] }>(
      `/saved-skills/${selected}`,
    ).then(
      (detail) => {
        if (!live) return;
        setSkill(detail.skill);
        setRuns(detail.runs);
        setSchedules(detail.schedules ?? []);
        setInputs((current) => {
          const next: Record<string, string> = {};
          for (const name of detail.skill.input_names) next[name] = current[name] ?? "";
          return next;
        });
      },
      (error) => {
        if (live) setReadError(error);
      },
    );
    return () => {
      live = false;
    };
  }, [visible, selected, revision]);

  useEffect(() => {
    const clear = () => {
      setTitle("");
      setSteps("");
      setNames("");
      setPassed(false);
      setNote("");
      setInputs({});
      setSchedules([]);
      setFrequency("daily");
      setStartLocal("");
      setZone("Asia/Hong_Kong");
      setSelected(null);
      setLocalError(null);
      mutation.clear();
    };
    window.addEventListener("desk:session", clear);
    window.addEventListener("desk:personal-context", clear);
    return () => {
      window.removeEventListener("desk:session", clear);
      window.removeEventListener("desk:personal-context", clear);
    };
  }, [mutation]);

  const errorCode =
    localError ?? (readError instanceof ApiError ? readError.code : null) ??
    (mutation.error instanceof ApiError ? mutation.error.code : null);

  return (
    <details className="saved-skills" id="saved-skills">
      <summary>{t("Saved skills", "已保存的做法")}</summary>
      {!visible ? (
        <p>
          {t(
            "Open this desk as the owner to save a skill.",
            "请以主人身份打开这台桌面，再保存做法。",
          )}
        </p>
      ) : (
        <>
          <p>
            {t(
              "Save a checklist you already checked. Running it again waits for your approval.",
              "保存你已经核对过的清单。再次运行时，会等你批准。",
            )}
          </p>
          <form
            className="saved-skill-form"
            onSubmit={(event) => {
              event.preventDefault();
              const parsed = checkBody({ title, stepsText: steps, namesText: names, passed });
              if (!parsed.ok) {
                setLocalError(parsed.reason);
                return;
              }
              setLocalError(null);
              void mutation.run("/saved-skills/checks", parsed.body, async (result) => {
                const saved = result as CheckResult;
                setTitle("");
                setSteps("");
                setNames("");
                setPassed(false);
                if (saved.skill) setSelected(saved.skill.id);
                setRevision((value) => value + 1);
              });
            }}
          >
            <label>
              {t("Title", "标题")}
              <input
                id="saved-skill-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
            </label>
            <label>
              {t("Steps", "步骤")}
              <textarea
                id="saved-skill-steps"
                value={steps}
                onChange={(event) => setSteps(event.target.value)}
                rows={3}
              />
            </label>
            <label>
              {t("Inputs to fill next time", "下次要填写的输入")}
              <input
                id="saved-skill-names"
                value={names}
                onChange={(event) => setNames(event.target.value)}
                placeholder={t("quantity", "数量")}
              />
            </label>
            <label className="saved-skill-check">
              <input
                id="saved-skill-passed"
                type="checkbox"
                checked={passed}
                onChange={(event) => setPassed(event.target.checked)}
              />
              {t("I checked this by hand", "我已亲手核对")}
            </label>
            <button type="submit" className="primary" disabled={mutation.busy}>
              {t("Save skill", "保存做法")}
            </button>
          </form>
          {skills.length > 0 && (
            <ul className="saved-skill-list">
              {skills.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => setSelected(item.id)}
                    aria-pressed={item.id === selected}
                  >
                    {item.title}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {skill && selected === skill.id && (
            <section className="saved-skill-card">
              <h3>{skill.title}</h3>
              <ol className="saved-skill-steps">
                {skill.steps.map((step, index) => (
                  <li key={`${index}:${step}`}>{step}</li>
                ))}
              </ol>
              {skill.input_names.map((name) => (
                <label key={name}>
                  {name}
                  <input
                    aria-label={name}
                    value={inputs[name] ?? ""}
                    onChange={(event) =>
                      setInputs((current) => ({ ...current, [name]: event.target.value }))
                    }
                  />
                </label>
              ))}
              <label>
                {t("Note", "备注")}
                <input
                  id="saved-skill-note"
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                />
              </label>
              <button
                type="button"
                className="secondary"
                disabled={mutation.busy || !fillReady(skill.input_names, inputs)}
                onClick={() => {
                  setLocalError(null);
                  void mutation.run(
                    `/saved-skills/${skill.id}/runs`,
                    runBody(
                      Object.fromEntries(skill.input_names.map((name) => [name, inputs[name] ?? ""])),
                      note,
                    ),
                    async () => {
                      setNote("");
                      setRevision((value) => value + 1);
                    },
                  );
                }}
              >
                {t("Prepare", "准备")}
              </button>
              <div className="saved-skill-schedule-form">
                <p>
                  {t(
                    "Schedule this fill. Each time waits for your approval. Quiet hours, proactive off, and a missed time skip it.",
                    "为这次填写定时。每次都会等你批准。安静时段、关闭主动建议，或错过的时间，都不会补做。",
                  )}
                </p>
                <label>
                  {t("How often", "频率")}
                  <select
                    id="saved-skill-frequency"
                    value={frequency}
                    onChange={(event) =>
                      setFrequency(event.target.value as SkillScheduleDraft["frequency"])
                    }
                  >
                    <option value="once">{t("Once", "单次")}</option>
                    <option value="daily">{t("Daily", "每天")}</option>
                    <option value="weekly">{t("Weekly", "每周")}</option>
                  </select>
                </label>
                <label>
                  {t("First time", "第一次")}
                  <input
                    id="saved-skill-start"
                    type="datetime-local"
                    value={startLocal}
                    onChange={(event) => setStartLocal(event.target.value)}
                  />
                </label>
                <label>
                  {t("Timezone", "时区")}
                  <input
                    id="saved-skill-zone"
                    value={zone}
                    onChange={(event) => setZone(event.target.value)}
                  />
                </label>
                <button
                  type="button"
                  id="saved-skill-schedule"
                  className="secondary"
                  disabled={mutation.busy || !fillReady(skill.input_names, inputs)}
                  onClick={() => {
                    if (!startLocal.trim() || !zone.trim()) {
                      setLocalError("choose_time");
                      return;
                    }
                    setLocalError(null);
                    void mutation.run(
                      `/saved-skills/${skill.id}/schedules`,
                      scheduleBody(
                        Object.fromEntries(
                          skill.input_names.map((name) => [name, inputs[name] ?? ""]),
                        ),
                        note,
                        { frequency, startLocal, timezone: zone },
                      ),
                      async () => {
                        setStartLocal("");
                        setNote("");
                        setRevision((value) => value + 1);
                      },
                    );
                  }}
                >
                  {t("Schedule", "定时")}
                </button>
              </div>
              {schedules.map((item) => {
                const skipped = scheduleSkipNotice(item.last_outcome, t);
                return (
                  <article key={item.id} className="saved-skill-schedule">
                    <p>
                      {frequencyLabel(item.frequency, t)} · {scheduleStatus(item.status, t)} ·{" "}
                      {nextLabel(item.next_run_at, item.timezone, t)}
                    </p>
                    <ul>
                      {Object.entries(item.inputs).map(([name, value]) => (
                        <li key={name}>
                          <span>{name}</span> {value}
                        </li>
                      ))}
                    </ul>
                    {item.note_provided && item.note ? <p>{item.note}</p> : null}
                    {skipped ? <p>{skipped}</p> : null}
                    <div className="saved-skill-actions">
                      {item.status === "active" && (
                        <button
                          type="button"
                          className="secondary"
                          disabled={mutation.busy}
                          onClick={() => {
                            setLocalError(null);
                            void mutation.run(
                              `/saved-skills/schedules/${item.id}/actions`,
                              { action: "pause", expected_version: item.version },
                              async () => setRevision((value) => value + 1),
                            );
                          }}
                        >
                          {t("Pause", "暂停")}
                        </button>
                      )}
                      {item.status === "paused" && (
                        <button
                          type="button"
                          className="secondary"
                          disabled={mutation.busy}
                          onClick={() => {
                            setLocalError(null);
                            void mutation.run(
                              `/saved-skills/schedules/${item.id}/actions`,
                              { action: "resume", expected_version: item.version },
                              async () => setRevision((value) => value + 1),
                            );
                          }}
                        >
                          {t("Resume", "恢复")}
                        </button>
                      )}
                      {(item.status === "active" || item.status === "paused") && (
                        <button
                          type="button"
                          className="secondary"
                          disabled={mutation.busy}
                          onClick={() => {
                            setLocalError(null);
                            void mutation.run(
                              `/saved-skills/schedules/${item.id}/actions`,
                              { action: "cancel", expected_version: item.version },
                              async () => setRevision((value) => value + 1),
                            );
                          }}
                        >
                          {t("Cancel schedule", "取消定时")}
                        </button>
                      )}
                    </div>
                  </article>
                );
              })}
              {runs.map((run) => (
                <SavedSkillRun
                  key={run.id}
                  run={run}
                  t={t}
                  disabled={mutation.busy}
                  onDecide={(action) => {
                    setLocalError(null);
                    void mutation.run(
                      `/saved-skills/runs/${run.id}/decision`,
                      decisionBody(run, action),
                      async () => setRevision((value) => value + 1),
                    );
                  }}
                />
              ))}
            </section>
          )}
          {errorCode && (
            <p role="alert">{skillError(errorCode, t)}</p>
          )}
          {mutation.pending && (
            <p role="status">
              {t(
                "The result is unknown. Retry uses the same attempt while this page stays open.",
                "结果还不确定。页面保持打开时，重试会沿用同一次尝试。",
              )}
              <button type="button" className="secondary" disabled={mutation.busy} onClick={() => void mutation.retry()}>
                {t("Retry the same request", "重试同一请求")}
              </button>
            </p>
          )}
        </>
      )}
    </details>
  );
}
