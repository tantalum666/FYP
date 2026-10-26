import { useEffect, useState } from "react";
import {
  Check,
  Link2,
  LockKeyhole,
  Plus,
  Scale,
  Utensils,
  X,
} from "lucide-react";
import { Banner, Brand } from "./components";
import { LanguagePicker, clock, number, useLabel, useLanguage } from "./i18n";
import { MealSummary } from "./MealSummary";
import type { Meal } from "./mealTypes";
import { useStationConsole } from "./useStationConsole";
import "./meals.css";

type ConsoleAPI = ReturnType<typeof useStationConsole>;
export default function StationConsole() {
  const api = useStationConsole(),
    { t } = useLanguage(),
    label = useLabel();
  const [key, setKey] = useState("");
  const meal = api.data?.meal;
  useEffect(() => {
    document.title = "Senplate · Station";
  }, []);
  return (
    <main className="station-console">
      <header className="console-header">
        <Brand />
        <div>
          <LanguagePicker />
          {api.data && (
            <button
              className="quiet"
              disabled={api.busy}
              onClick={() => void api.disconnect()}
            >
              {t("Disconnect", "断开")}
            </button>
          )}
        </div>
      </header>
      {api.error && (
        <Banner>
          {label(api.error)}{" "}
          <button onClick={() => void api.refresh()}>
            {t("Refresh", "刷新")}
          </button>
        </Banner>
      )}
      {api.pending && !api.busy && (
        <Banner>
          {t("The last action is unconfirmed.", "上一操作结果尚未确认。")}{" "}
          <button onClick={() => void api.retry()}>
            {t("Check and retry", "核查并重试")}
          </button>
        </Banner>
      )}
      {api.loading ? (
        <p>{t("Connecting…", "正在连接…")}</p>
      ) : api.needsSetup ? (
        <section className="panel console-setup">
          <LockKeyhole size={32} />
          <h1>{t("Connect this station", "连接此设备")}</h1>
          <p>
            {t(
              "Use the setup key assigned to this station. A staff account does not replace a station key.",
              "使用此设备的设置密钥，员工账号不能替代设备密钥。",
            )}
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void api.connect(key).then((ok) => {
                if (ok) setKey("");
              });
            }}
          >
            <label>
              {t("Station key", "设备密钥")}
              <input
                type="password"
                autoComplete="off"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                required
              />
            </label>
            <button className="primary" disabled={api.busy || !key}>
              {t("Connect", "连接")}
            </button>
          </form>
        </section>
      ) : (
        api.data && (
          <>
            <div className="console-title">
              <div>
                <p className="eyebrow">{t("STATION 01", "设备 01")}</p>
                <h1>{t("One plate at a time.", "每次，认真记录一餐。")}</h1>
              </div>
              <span className="status">{t("Demo data", "演示数据")}</span>
            </div>
            {meal ? (
              <MealControls key={meal.id} meal={meal} api={api} />
            ) : (
              <section className="panel console-start">
                <h2>{t("What are you recording?", "这次记录什么？")}</h2>
                <p className="muted">
                  {t(
                    "Use the same station for your own plate or an anonymous school sample. Finish any open kitchen work first.",
                    "同一设备可用于个人餐盘或学校匿名样本，开始前请处理未完成的厨房工作。",
                  )}
                </p>
                <div className="console-mode-choices">
                  {(
                    [
                      ["personal", "Your meal", "个人餐食", Link2],
                      ["school", "School sample", "学校样本", Utensils],
                    ] as const
                  ).map(([mode, en, zh, Icon]) => (
                    <button
                      key={mode}
                      disabled={api.busy || !!api.pending || !!api.readError}
                      onClick={() =>
                        void api.mutate("/v1/device-console/meals", {
                          expected_run_id: api.data?.run_id,
                          mode,
                        })
                      }
                    >
                      <Icon size={28} />
                      <strong>{t(en, zh)}</strong>
                      <span>
                        {mode === "personal"
                          ? t(
                              "Confirm a phone pairing before recording.",
                              "配对手机并在此确认后记录。",
                            )
                          : t(
                              "Use an automatic sample ID. No child profiles.",
                              "使用自动样本编号，不建立儿童档案。",
                            )}
                      </span>
                    </button>
                  ))}
                </div>
              </section>
            )}
          </>
        )
      )}
    </main>
  );
}

function MealControls({ meal: m, api }: { meal: Meal; api: ConsoleAPI }) {
  const { t } = useLanguage(),
    label = useLabel();
  const [food, setFood] = useState(""),
    [note, setNote] = useState(""),
    [missing, setMissing] = useState("not_measured"),
    [qr, setQr] = useState("");
  const [now, setNow] = useState(Date.now()),
    [correction, setCorrection] = useState("");
  const disabled = api.busy || !!api.pending || !!api.readError;
  const reading = m.current,
    ref = api.foods.find((f) => f.id === food),
    canMeasure = !!reading?.observation_id;
  async function act(action: string, extra: Record<string, unknown> = {}) {
    const ok = await api.mutate(`/v1/device-console/meals/${m.id}/actions`, {
      expected_version: m.version,
      action,
      ...extra,
    });
    if (ok) {
      setFood("");
      setNote("");
      setCorrection("");
    }
    return ok;
  }
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const validCode =
    m.pairing?.code && new Date(m.pairing.expires_at ?? 0).getTime() > now;
  useEffect(() => {
    setQr("");
    if (!validCode) return;
    let disposed = false,
      url = "";
    fetch("/v1/device-console/pairing-qr.svg")
      .then((r) => {
        if (!r.ok) throw Error();
        return r.blob();
      })
      .then((b) => {
        url = URL.createObjectURL(b);
        if (disposed) URL.revokeObjectURL(url);
        else setQr(url);
      })
      .catch(() => {});
    return () => {
      disposed = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [m.pairing?.code, !!validCode]);
  const primary = (
    name: string,
    action: string,
    extra: Record<string, unknown> = {},
    off = false,
  ) => (
    <button
      className="primary"
      disabled={disabled || off}
      onClick={() => void act(action, extra)}
    >
      {name}
    </button>
  );
  const chooseFood = (
    <label>
      {t("Food reference", "食物参考")}
      <select
        value={food}
        onChange={(e) => setFood(e.target.value)}
        disabled={disabled}
      >
        <option value="">
          {t("Choose the food you are adding", "选择本次加入的食物")}
        </option>
        {api.foods.map((f) => (
          <option key={f.id} value={f.id}>
            {t(f.name_en, f.name_zh)}
          </option>
        ))}
      </select>
      {ref && <span className="caption">{t(ref.notes_en, ref.notes_zh)}</span>}
    </label>
  );
  return (
    <div className="console-meal-layout">
      <section className="panel console-measurement">
        <div className="console-state">
          <Scale size={24} />
          <span className="status">{label("meal_" + m.state)}</span>
        </div>
        {m.sample_code && (
          <p>
            {t("Anonymous sample", "匿名样本")} <b>{m.sample_code}</b>
          </p>
        )}
        <div className="console-weight">
          <strong>{number(reading?.net_g ?? null)}</strong>
          <span>g</span>
        </div>
        <p className="muted">
          {t("Current net weight", "当前净重")} ·{" "}
          {clock(reading?.observed_at ?? null)}
        </p>
        {!canMeasure && (
          <Banner>
            {t(
              "Wait for a fresh, stable reading with the plate on the station.",
              "请将餐盘放稳，等待新的有效读数。",
            )}
          </Banner>
        )}
        {m.state === "setup" && (
          <>
            <h2>{t("Start with an empty plate", "从空餐盘开始")}</h2>
            <p>
              {t(
                "Place the tared empty plate on the station. Confirm only when the reading is stable at zero.",
                "放好已去皮的空餐盘，读数稳定在零点后再确认。",
              )}
            </p>
            {primary(
              t("Confirm empty plate", "确认空餐盘"),
              "confirm_empty",
              { observation_id: reading?.observation_id },
              !canMeasure || reading?.net_g !== 0,
            )}
          </>
        )}
        {m.state === "pairing" && (
          <div className="pairing-panel">
            {validCode ? (
              <>
                <h2>{t("Connect your iPhone", "连接你的 iPhone")}</h2>
                <p>
                  {t(
                    "Open Dining → Record a meal in Senplate, then scan or enter this code.",
                    "在 Senplate 用餐页选择记录餐食，再扫描或输入此代码。",
                  )}
                </p>
                {qr && (
                  <img
                    src={qr}
                    alt={t("Meal pairing QR code", "餐食配对二维码")}
                  />
                )}
                <code>{m.pairing?.code}</code>
                <span className="caption">
                  {t("Expires in", "有效期剩余")}{" "}
                  {Math.max(
                    0,
                    Math.ceil(
                      (new Date(m.pairing?.expires_at ?? 0).getTime() - now) /
                        1000,
                    ),
                  )}{" "}
                  s
                </span>
              </>
            ) : (
              <Banner>
                {t(
                  "Get a new pairing code to connect a phone.",
                  "请获取新配对码后连接手机。",
                )}
              </Banner>
            )}
            {m.pair_request?.state === "pending" && validCode && (
              <div className="pair-request">
                <h3>{m.pair_request.applicant_name}</h3>
                <p>
                  {t(
                    "Match this number on the phone before confirming.",
                    "确认前，请核对手机是否显示同一号码。",
                  )}
                </p>
                <strong className="pair-check">
                  {m.pair_request.check_code}
                </strong>
                {primary(
                  t("Confirm this person", "确认此人配对"),
                  "approve_pairing",
                  { request_id: m.pair_request.id },
                  !canMeasure || reading?.net_g !== 0,
                )}
                <button
                  disabled={disabled}
                  onClick={() =>
                    void act("reject_pairing", {
                      request_id: m.pair_request?.id,
                    })
                  }
                >
                  {t("Reject request", "拒绝申请")}
                </button>
              </div>
            )}
            <button
              disabled={disabled || !canMeasure || reading?.net_g !== 0}
              onClick={() => void act("rotate_code")}
            >
              {t("Get a new code", "获取新代码")}
            </button>
          </div>
        )}
        {m.state === "recording" && (
          <div className="console-actions">
            {m.prepared ? (
              <>
                <h2>
                  {t(
                    m.prepared.reference.name_en,
                    m.prepared.reference.name_zh,
                  )}
                </h2>
                <p>
                  {t(
                    m.prepared.reference.notes_en,
                    m.prepared.reference.notes_zh,
                  )}
                </p>
                <div className="portion-delta">
                  <span>{t("Added in this item", "本项新增")}</span>
                  <strong>{number(m.prepared.candidate_g)} g</strong>
                </div>
                {m.prepared.validation_error &&
                  m.prepared.validation_error !== "NO_POSITIVE_PORTION" && (
                    <Banner>{label(m.prepared.validation_error)}</Banner>
                  )}
                {primary(
                  t("Record this portion", "记录本项份量"),
                  "confirm_portion",
                  { observation_id: reading?.observation_id },
                  !canMeasure || !!m.prepared.validation_error,
                )}
                <details>
                  <summary>{t("Cancel this item", "取消本项")}</summary>
                  <p className="caption">
                    {t(
                      `Remove unrecorded food until the plate returns to ${m.prepared.baseline_g} g.`,
                      `请移走未记录食物，使餐盘恢复到 ${m.prepared.baseline_g} 克。`,
                    )}
                  </p>
                  <label>
                    {t("Reason", "原因")}
                    <input
                      value={note}
                      maxLength={500}
                      onChange={(e) => setNote(e.target.value)}
                    />
                  </label>
                  <button
                    disabled={
                      disabled ||
                      !note.trim() ||
                      !canMeasure ||
                      reading?.net_g !== m.prepared.baseline_g
                    }
                    onClick={() =>
                      void act("cancel_portion", {
                        note,
                        observation_id: reading?.observation_id,
                      })
                    }
                  >
                    {t("Cancel item at starting weight", "按起点重量取消本项")}
                  </button>
                </details>
              </>
            ) : (
              <>
                <h2>{t("Add one food at a time", "每次加入一种食物")}</h2>
                {chooseFood}
                {primary(
                  t("Begin this item", "开始记录本项"),
                  "prepare_portion",
                  {
                    reference_id: food,
                    observation_id: reading?.observation_id,
                  },
                  !food || !canMeasure,
                )}
                {m.portions.length > 0 &&
                  primary(
                    t("Finish plating", "完成装盘"),
                    "finish_plating",
                    { observation_id: reading?.observation_id },
                    !canMeasure,
                  )}
                {m.portions.length > 0 && (
                  <details>
                    <summary>
                      {t("Correct a food reference", "纠正食物参考")}
                    </summary>
                    <label>
                      {t("Recorded item", "已记录项目")}
                      <select
                        value={correction}
                        onChange={(e) => setCorrection(e.target.value)}
                      >
                        <option value="">
                          {t("Choose an item", "选择项目")}
                        </option>
                        {m.portions.map((p) => (
                          <option key={p.id} value={p.id}>
                            {t(p.reference.name_en, p.reference.name_zh)} ·{" "}
                            {p.amount_g} g
                          </option>
                        ))}
                      </select>
                    </label>
                    <p className="caption">
                      {t(
                        "Select the corrected reference above. The measured grams stay unchanged.",
                        "在上方选择正确资料，原称重克数保持不变。",
                      )}
                    </p>
                    <label>
                      {t("Correction reason", "纠正原因")}
                      <input
                        value={note}
                        maxLength={500}
                        onChange={(e) => setNote(e.target.value)}
                      />
                    </label>
                    <button
                      disabled={
                        disabled || !correction || !food || !note.trim()
                      }
                      onClick={() =>
                        void act("correct_food", {
                          portion_id: correction,
                          reference_id: food,
                          note,
                        })
                      }
                    >
                      {t("Save correction", "保存纠正")}
                    </button>
                  </details>
                )}
              </>
            )}
          </div>
        )}
        {m.state === "observing" && (
          <div className="console-actions">
            <h2>{t("Keep the whole plate in view", "保留整盘的余量记录")}</h2>
            <p>
              {t(
                "The total remaining weight is recorded separately. It cannot reveal how much of each food was eaten.",
                "总剩余量单独记录，不能由此确定每种食物吃了多少。",
              )}
            </p>
            {canMeasure && !m.remaining_comparable && (
              <Banner>{label("REMAINING_NOT_COMPARABLE")}</Banner>
            )}
            {primary(
              t("Complete with this remaining weight", "按当前总剩余量完成"),
              "complete",
              { observation_id: reading?.observation_id },
              !canMeasure || !m.remaining_comparable,
            )}
            <details>
              <summary>
                {t("Complete without remaining weight", "不记录总剩余量并完成")}
              </summary>
              <label>
                {t("Reason", "原因")}
                <select
                  value={missing}
                  onChange={(e) => setMissing(e.target.value)}
                >
                  <option value="not_measured">
                    {t("Not measured", "未测量")}
                  </option>
                  <option value="pan_removed">
                    {t("Plate removed", "餐盘已离位")}
                  </option>
                  <option value="unreliable">
                    {t("Reading unreliable", "读数不可靠")}
                  </option>
                  <option value="contents_changed">
                    {t("Contents changed after plating", "装盘后内容已改变")}
                  </option>
                </select>
              </label>
              <button
                disabled={disabled}
                onClick={() =>
                  void act("complete", { remaining_reason: missing })
                }
              >
                {t("Save without remaining weight", "保存并注明余量未知")}
              </button>
            </details>
          </div>
        )}
        {api.data?.development && <DemoInputs key={m.id} meal={m} api={api} />}
        <details className="end-recording">
          <summary>{t("Cancel this recording", "取消此次记录")}</summary>
          <label>
            {t("Reason", "原因")}
            <input
              value={note}
              maxLength={500}
              onChange={(e) => setNote(e.target.value)}
            />
          </label>
          <button
            disabled={disabled || !note.trim()}
            onClick={() => void act("cancel", { note })}
          >
            <X size={16} />
            {t("Cancel and preserve history", "取消并保留记录")}
          </button>
        </details>
      </section>
      <section className="panel console-recorded">
        <h2>{t("Recorded on this plate", "此餐盘的记录")}</h2>
        {m.portions.length ? (
          <MealSummary meal={m} />
        ) : (
          <div className="meal-empty">
            <Plus size={32} />
            <p>
              {t(
                "Recorded portions will appear here. Choose a food before adding it.",
                "选择食物后再加料，确认的份量会显示在这里。",
              )}
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

function DemoInputs({ meal, api }: { meal: Meal; api: ConsoleAPI }) {
  const { t } = useLanguage();
  const [weight, setWeight] = useState("0");
  const valid =
    weight.trim() !== "" &&
    Number.isInteger(Number(weight)) &&
    Number(weight) >= 0 &&
    Number(weight) <= 5000;
  const disabled = api.busy || !!api.pending || !!api.readError;
  const simulate = (action: string, seconds = 1) =>
    api.mutate("/v1/device-console/simulate", {
      run_id: meal.run_id,
      action,
      weight_g: Number(weight),
      seconds,
    });
  return (
    <details className="demo-inputs">
      <summary>{t("Demo input controls", "演示输入控制")}</summary>
      <p className="caption">
        {t(
          "Software simulation only. These buttons do not read a physical scale.",
          "仅用于软件模拟，这些按钮不会读取真实电子秤。",
        )}
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (valid) void simulate("set");
        }}
      >
        <label>
          {t("Simulated net weight (g)", "模拟净重（克）")}
          <input
            type="number"
            min={0}
            max={5000}
            step={1}
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            required
          />
        </label>
        <button disabled={disabled || !valid}>
          <Check size={16} />
          {t("Send stable reading", "发送稳定读数")}
        </button>
      </form>
      <div className="button-row">
        <button
          disabled={disabled || !valid}
          onClick={() => void simulate("unstable")}
        >
          {t("Unstable", "不稳定")}
        </button>
        <button
          disabled={disabled || !valid}
          onClick={() => void simulate("remove")}
        >
          {t("Plate removed", "餐盘离位")}
        </button>
        <button
          disabled={disabled || !valid}
          onClick={() => void simulate("advance", 6)}
        >
          {t("Age reading 6 s", "读数过时 6 秒")}
        </button>
      </div>
    </details>
  );
}
