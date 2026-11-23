"""Small, source-grounded text and speech readback of a public weather lookup."""

from datetime import datetime
import re


def _day_line(row, zh, *, timed, supplement=False):
    parts = []
    if (conditions := row.get("conditions")) and not supplement:
        parts.append(conditions.rstrip("。."))
    if "minimum_c" in row and "maximum_c" in row:
        low, high = row["minimum_c"], row["maximum_c"]
        parts.append(f"{low:g} 至 {high:g}°C" if zh else f"{low:g} to {high:g}°C")
    if (chance := row.get("peak_precipitation_probability_pct")) is not None:
        parts.append(
            f"逐小时降水概率最高 {chance:g}%"
            if zh
            else f"peak hourly precipitation chance {chance:g}%"
        )
    elif category := row.get("significant_rain_category"):
        parts.append(
            f"显著降雨概率{category}" if zh else f"{category.lower()} chance of significant rain"
        )
    if timed:
        if (amount := row.get("precipitation_mm")) is not None:
            parts.append(
                f"预计全天降水 {amount:g} 毫米" if zh else f"{amount:g} mm forecast for the day"
            )
        if windows := row.get("precipitation_windows"):
            times = ("、" if zh else " and ").join(f"{w['from']}–{w['until']}" for w in windows[:2])
            parts.append(
                f"预计降水时段包括 {times}" if zh else f"precipitation expected around {times}"
            )
    return ("，" if zh else ", ").join(parts)


def weather_summary(result, language):
    zh = language == "zh"
    name = result["place"]
    if not result["available"]:
        reason = result.get("status")
        if reason == "ambiguous":
            options = ("、" if zh else " or ").join(result["choices"])
            return (
                f"有多个地点叫{name}。你想查哪一个？{options}。"
                if zh
                else f"Which {name} do you mean? The matches include {options}."
            )
        if reason == "missing_city":
            return "想查哪个城市的天气？" if zh else "Which city should I check?"
        if reason == "specify_city":
            return (
                f"想查{name}的哪个城市或城镇？"
                if zh
                else f"Which city or town in {name} should I check?"
            )
        if reason == "not_found":
            return (
                f"没有找到“{name}”。可以补充所在国家或地区吗？"
                if zh
                else f"I couldn't locate {name}. Which country or region is it in?"
            )
        if reason == "invalid_coordinates":
            return (
                "请提供有效的纬度和经度。" if zh else "Please give a valid latitude and longitude."
            )
        if reason == "out_of_range":
            return (
                f"{name}的预报未覆盖所选日期。"
                if zh
                else f"The available forecast for {name} does not cover that date."
            )
        if stamp := result.get("last_report_at"):
            return (
                f"{name}最新可读资料日期为 {stamp}，暂时无法确认所问天气。"
                if zh
                else f"The latest report I could read for {name} is dated {stamp}. I couldn't verify the requested weather."
            )
        return (
            f"暂时没有读到{name}所问日期的天气资料。"
            if zh
            else f"I couldn't retrieve weather for {name} on the requested date."
        )

    source = result["source"]
    if zh and source == "Hong Kong Observatory":
        source = "香港天文台"
    sentences = []
    if current := result.get("current"):
        stamp = datetime.fromisoformat(current["time"]).strftime("%Y-%m-%d %H:%M")
        temperature = current["temperature_c"]
        if zh:
            basis = "实测" if current["basis"] == "station" else "估算"
            condition = f"，{current['conditions']}" if current.get("conditions") else ""
            sentences.append(f"{name}当地 {stamp}，{source}{basis} {temperature:g}°C{condition}。")
        else:
            verb = "measured" if current["basis"] == "station" else "estimated"
            condition = f", {current['conditions']}" if current.get("conditions") else ""
            sentences.append(
                f"In {name} at {stamp} local time, {source} {verb} {temperature:g}°C{condition}."
            )
    if outlook := result.get("local_forecast"):
        desc = outlook["conditions"].strip()
        if zh:
            desc = re.split(r"(?<=[。！？])(?:吹|风势|风力)", desc, maxsplit=1)[0]
        else:
            desc = re.split(
                r"(?<=\.)\s+(?=(?:Moderate|Fresh|Light|Strong) (?:to |[a-z-]+ winds))",
                desc,
                maxsplit=1,
            )[0]
        # Preserve the official period, which may cross midnight, as issued.
        sentences.append(f"{outlook['period']}，{desc}" if zh else f"{outlook['period']} — {desc}")
    days = result["days"]
    if days:
        lines = []
        for row in days:
            prefix = row.get("source", "")
            if not sentences and not lines:
                prefix = (
                    source
                    if result["area"] == "hong_kong" and not prefix
                    else f"{name} ({prefix or source})"
                )
            same_day = (
                result.get("current") and row["date"] == result.get("local_date") and len(days) == 1
            )
            date_label = ("今天预计" if zh else "Today, expect") if same_day else row["date"]
            label = f"{prefix} {date_label}".strip()
            supplement = bool(result.get("local_forecast")) and bool(prefix)
            lines.append(
                label
                + ("" if zh and same_day else " ")
                + _day_line(row, zh, timed=len(days) == 1 and not supplement, supplement=supplement)
            )
        sentences.append(("。" if zh else ". ").join(lines) + ("。" if zh else "."))
    if missing := result.get("uncovered_days"):
        sentences.append(
            f"另外 {missing} 天还没有可用预报。"
            if zh
            else f"A forecast is unavailable for {missing} of the requested days."
        )
    return ("" if zh else " ").join(sentences)
