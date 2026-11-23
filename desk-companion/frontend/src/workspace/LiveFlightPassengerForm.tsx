import type { FormEvent } from "react";
import type { Translate } from "../types";

const fields = [
  ["given_name", "Given names as on passport", "护照名字"],
  ["family_name", "Family name", "护照姓氏"],
  ["born_on", "Date of birth", "出生日期", "date"],
  ["nationality", "Nationality (two-letter code)", "国籍（两位字母）"],
] as const;
const leadFields = [
  ["phone_number", "Phone including country code", "手机（含国际区号）", "tel"],
  [
    "phone_country",
    "Phone country (two letters)",
    "电话所属国家或地区（两位字母）",
  ],
  ["address_line1", "Street address", "街道地址"],
  ["address_city", "City", "城市"],
  ["address_postal", "Postal code", "邮政编码"],
  [
    "address_country",
    "Address country (two letters)",
    "地址国家或地区（两位字母）",
  ],
] as const;
const passportFields = [
  ["passport_number", "Passport number", "护照号码"],
  [
    "passport_country",
    "Issuing country (two letters)",
    "签发国家或地区（两位字母）",
  ],
  ["passport_issue", "Issue date", "签发日期", "date"],
  ["passport_expiry", "Expiry date", "有效期至", "date"],
] as const;
type Field = readonly [string, string, string, string?];
function field(item: Field, index: number, t: Translate) {
  const [key, en, zh, type] = item;
  const country = key === "nationality" || key.endsWith("_country");
  return (
    <label key={key}>
      {t(en, zh)}
      <input
        name={`${index}.${key}`}
        type={type ?? "text"}
        required
        autoComplete="off"
        maxLength={country ? 2 : 140}
        pattern={country ? "[A-Za-z]{2}" : undefined}
      />
    </label>
  );
}
export function LiveFlightPassengerForm({
  adults,
  passport,
  busy,
  t,
  total,
  onConfirm,
}: {
  adults: number;
  passport: boolean;
  busy: boolean;
  t: Translate;
  total: string;
  onConfirm: (
    passengers: Record<string, string>[],
    email: string,
  ) => Promise<boolean>;
}) {
  // Keep traveller fields only in this private form, never in a chat, app write queue or web storage.
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy || !window.isSecureContext) return;
    const form = e.currentTarget,
      data = new FormData(form);
    const people = Array.from({ length: adults }, (_, i) => {
      const person: Record<string, string> = {};
      for (const [key] of [
        ...fields,
        ...(i === 0 ? leadFields : []),
        ...(passport ? passportFields : []),
        ["gender"],
      ]) {
        const value = String(data.get(`${i}.${key}`) ?? "").trim();
        person[key] =
          key === "nationality" || key.endsWith("_country")
            ? value.toUpperCase()
            : value;
      }
      return person;
    });
    if (await onConfirm(people, String(data.get("email") ?? ""))) form.reset();
  }
  return (
    <form onSubmit={submit}>
      <label>
        {t("Contact email", "联系电邮")}
        <input type="email" name="email" autoComplete="off" required />
      </label>
      {Array.from({ length: adults }, (_, i) => (
        <fieldset key={i}>
          <legend>{t(`Passenger ${i + 1}`, `乘客 ${i + 1}`)}</legend>
          {fields.map((f) => field(f, i, t))}
          <label>
            {t("Passport gender", "护照性别")}
            <select name={`${i}.gender`} required defaultValue="">
              <option value="" disabled>
                {t("Select", "请选择")}
              </option>
              <option value="m">{t("Male", "男")}</option>
              <option value="f">{t("Female", "女")}</option>
            </select>
          </label>
          {i === 0 && leadFields.map((f) => field(f, i, t))}
          {passport && passportFields.map((f) => field(f, i, t))}
        </fieldset>
      ))}
      <button type="submit" className="primary" disabled={busy}>
        {t("Confirm booking and pay", "确认预订并支付")} {total}
      </button>
    </form>
  );
}
