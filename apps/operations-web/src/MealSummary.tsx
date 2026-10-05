import { useLabel, useLanguage, number, clock } from "./i18n";
import { Banner } from "./components";
import type { Meal } from "./mealTypes";
import "./meals.css";

const nutrients = [
  "energy_kcal",
  "protein_g",
  "carbohydrate_g",
  "fat_g",
  "fibre_g",
];
export function MealSummary({
  meal,
  compact = false,
}: {
  meal: Meal;
  compact?: boolean;
}) {
  const { t } = useLanguage(),
    label = useLabel();
  return (
    <div className="meal-summary">
      <div className="meal-total">
        <span>{t("Food provided", "已提供食物")}</span>
        <strong>
          {number(meal.provided_g)} <small>g</small>
        </strong>
      </div>
      {meal.state === "completed" && (
        <p>
          {t("Total remaining", "总剩余")}:{" "}
          <strong>{number(meal.remaining_g)} g</strong>
          {meal.remaining_g === null && (
            <span> · {t("Not recorded", "未取得有效记录")}</span>
          )}
        </p>
      )}
      <div className="portion-list">
        {meal.portions.map((p) => (
          <div key={p.id}>
            <span>
              <strong>{t(p.reference.name_en, p.reference.name_zh)}</strong>
              <small>
                {label("group_" + p.reference.food_group)} · {clock(p.at)}
                {p.entry_source === "manual_correction"
                  ? " · " + t("Corrected by a person", "人工纠正")
                  : ""}
              </small>
            </span>
            <b>{number(p.amount_g)} g</b>
          </div>
        ))}
      </div>
      <h3>{t("Reference nutrition", "参考营养")}</h3>
      {meal.nutrition.status !== "complete" && (
        <Banner>
          {t(
            "Some food has no matching reference. Unknown values stay blank; known-item subtotals are shown separately.",
            "部分食物没有匹配资料。未知值保留空缺，已知食物小计单独展示。",
          )}
        </Banner>
      )}
      <div className="nutrient-grid">
        {nutrients.map((key) => (
          <div key={key}>
            <span>{label("nutrient_" + key)}</span>
            <strong>
              {number(meal.nutrition.total[key])}{" "}
              <small>{key === "energy_kcal" ? "kcal" : "g"}</small>
            </strong>
            {meal.nutrition.total[key] === null &&
              meal.nutrition.known_subtotal[key] !== null && (
                <small>
                  {t("Known items", "已知项小计")}:{" "}
                  {number(meal.nutrition.known_subtotal[key])}
                </small>
              )}
          </div>
        ))}
      </div>
      <p className="caption">
        {t(
          "Estimates for the food provided, using matched references. Weight loss does not identify nutrients eaten.",
          "根据匹配资料估算已提供食物的营养。总重下降不能确定吃下了哪些营养。",
        )}
      </p>
      {!compact && (
        <>
          <h3>
            {t("Food groups by recorded weight", "按记录重量划分的食物组")}
          </h3>
          <div className="food-groups">
            {Object.entries(meal.food_groups_g).map(([group, g]) => (
              <div key={group}>
                <span>{label("group_" + group)}</span>
                <div className="group-track">
                  <span
                    style={{
                      width: `${meal.provided_g ? (g / meal.provided_g) * 100 : 0}%`,
                    }}
                  />
                </div>
                <b>{number(g)} g</b>
              </div>
            ))}
          </div>
          {meal.plan_comparison && (
            <section className="plan-comparison">
              <h3>
                {t(
                  meal.plan_comparison.plan.name_en,
                  meal.plan_comparison.plan.name_zh,
                )}
              </h3>
              <p className="caption">
                {t(
                  meal.plan_comparison.plan.scope_en,
                  meal.plan_comparison.plan.scope_zh,
                )}
              </p>
              <div className="sample-table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>{t("Group", "食物组")}</th>
                      <th>{t("Recorded", "记录值")}</th>
                      <th>{t("Demo plan", "示范计划")}</th>
                      <th>{t("Difference", "差值")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {meal.plan_comparison.groups.map((g) => (
                      <tr key={g.group}>
                        <td>{label("group_" + g.group)}</td>
                        <td>{number(g.recorded_g)} g</td>
                        <td>{number(g.target_g)} g</td>
                        <td>{number(g.difference_g)} g</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="caption">
                {t(
                  "This comparison is not an assessment of a child's diet or nutritional compliance.",
                  "此比较不评价儿童个人饮食，也不判定营养合规。",
                )}
              </p>
            </section>
          )}
          <details className="meal-sources">
            <summary>
              {t("Food references & recording history", "食物资料与记录过程")}
            </summary>
            {meal.portions.map((p) => (
              <div key={p.id}>
                <strong>{t(p.reference.name_en, p.reference.name_zh)}</strong>
                <p>{t(p.reference.notes_en, p.reference.notes_zh)}</p>
                <p>
                  {p.reference.source} · {p.reference.data_version}
                </p>
                {p.reference.source_url && (
                  <a
                    href={p.reference.source_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t("View source", "查看来源")} {p.reference.source_id}
                  </a>
                )}
              </div>
            ))}
            {meal.history.map((h) => (
              <p key={h.id}>
                {clock(h.at)} · {label("meal_action_" + h.action)} {h.note}
              </p>
            ))}
          </details>
        </>
      )}
    </div>
  );
}
