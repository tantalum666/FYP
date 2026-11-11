import { useEffect, useRef, useState } from "react";
import { CloudSun, MapPin } from "lucide-react";
import type { DateTime } from "luxon";
import type { Language, Translate } from "../types";
import { useWorkspace } from "../workspace/WorkspaceContext";
import { weatherLocation, type CoarseLocation } from "./weatherLocation";
import { request } from "../api";

type Weather = {
  available: boolean;
  area: "nearby" | "hong_kong";
  temperature?: number;
  observed_at?: string;
  source?: string;
};
export function HomeConditions({
  now,
  zone,
  language,
  t,
  visible = true,
}: {
  now: DateTime;
  zone: string;
  language: Language;
  t: Translate;
  visible?: boolean;
}) {
  const [weather, setWeather] = useState<Weather>();
  const locationRequest = useRef<Promise<CoarseLocation | null> | undefined>(
    undefined,
  );
  const [locationRevision, setLocationRevision] = useState(0);
  const { data } = useWorkspace();
  const weatherMode =
    data?.calendar_extras.preferences.weather_location ?? "none";
  useEffect(() => {
    if (!visible || weatherMode === "none") return;
    let live = true;
    async function load() {
      try {
        const requested = locationRequest.current;
        locationRequest.current = undefined;
        const location =
          weatherMode === "automatic"
            ? await (requested ?? weatherLocation())
            : null;
        if (!live) return;
        let value: Weather | undefined;
        if (location) {
          try {
            value = await request<Weather>("/weather", {
              method: "POST",
              body: JSON.stringify(location),
            });
          } catch {
            /* The same public Hong Kong fallback also covers a failed location provider. */
          }
        }
        if (!live) return;
        if (!value?.available) value = await request<Weather>("/weather");
        if (live) setWeather(value);
      } catch {
        if (live) setWeather({ available: false, area: "hong_kong" });
      }
    }
    void load();
    const timer = setInterval(() => {
      if (!document.hidden) void load();
    }, 600000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [visible, weatherMode, locationRevision]);
  const local = now
    .setZone(zone)
    .setLocale(language === "zh" ? "zh-CN" : "en-GB");
  return (
    <div className="alice-conditions" hidden={!visible}>
      <time dateTime={local.toISO() ?? undefined}>
        <strong>{local.toFormat("HH:mm")}</strong>
        <span>
          {local.toFormat(language === "zh" ? "M月d日 EEEE" : "EEEE, d MMM")}
        </span>
      </time>
      <div
        hidden={weatherMode === "none"}
        className="alice-weather"
        title={weather?.source && `${weather.source} · ${weather.observed_at}`}
      >
        <CloudSun size={17} />
        <span>
          {weather?.available && typeof weather.temperature === "number"
            ? `${Math.round(weather.temperature)}°C`
            : weather
              ? t("Weather unavailable", "天气暂不可用")
              : t("Weather…", "正在读取天气…")}
        </span>
        <small>
          <button
            type="button"
            className="weather-location"
            disabled={weatherMode !== "automatic"}
            aria-label={t("Use current location", "重新获取当前位置")}
            onClick={() => {
              locationRequest.current = weatherLocation(true);
              setLocationRevision((value) => value + 1);
            }}
          >
            <MapPin size={11} />
            {weather?.area === "nearby"
              ? t("Nearby", "当前位置")
              : t("Hong Kong", "香港")}
          </button>
          {weather?.available && weather.source && (
            <a
              href={
                weather.source === "Hong Kong Observatory"
                  ? "https://www.hko.gov.hk/en/wxinfo/currwx/current.htm"
                  : "https://open-meteo.com/"
              }
              target="_blank"
              rel="noreferrer"
              aria-label={t("Weather data source", "天气资料来源")}
            >
              {weather.source === "Hong Kong Observatory"
                ? t("HKO", "天文台")
                : "Open-Meteo"}
            </a>
          )}
        </small>
      </div>
    </div>
  );
}
