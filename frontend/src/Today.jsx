import React, { useContext, useEffect, useState } from "react";
import { api, Language, timeLabel, useText } from "./shared";

const bands = {
  Good: "अच्छा",
  Satisfactory: "संतोषजनक",
  "Moderately polluted": "मध्यम प्रदूषित",
  Poor: "खराब",
  "Very poor": "बहुत खराब",
  Severe: "गंभीर",
};

function useAir(path) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [attempt, retry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setError(false);
    api(path, { signal: controller.signal })
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(true);
      });
    return () => controller.abort();
  }, [path, attempt]);
  return { data, error, retry: () => retry((n) => n + 1) };
}

function Status({ request }) {
  const t = useText();
  return request.error ? (
    <div role="alert">
      {t("Data unavailable.", "डेटा उपलब्ध नहीं है।")}{" "}
      <button onClick={request.retry}>{t("Retry", "फिर कोशिश करें")}</button>
    </div>
  ) : (
    <p role="status">{t("Loading…", "लोड हो रहा है…")}</p>
  );
}

function Source({ data }) {
  const t = useText(),
    lang = useContext(Language);
  return (
    <p className="source">
      {data.data_mode === "fixture"
        ? t("Demo · Synthetic Delhi data", "डेमो · दिल्ली का कृत्रिम डेटा")
        : t("Live mode · CAMS via Open-Meteo", "लाइव मोड · Open-Meteo से CAMS")}
      {" · "}
      {timeLabel(data.as_of, lang)} IST
      {data.stale && " · " + t("Older data", "पुराना डेटा")}
      {data.age_hours != null &&
        data.data_mode === "live" &&
        " · " +
          Math.round(data.age_hours) +
          " " +
          t("hours old", "घंटे पुराना")}
    </p>
  );
}

export default function Today({ profile, openProfile }) {
  const t = useText(),
    lang = useContext(Language);
  const now = useAir("/air/now"),
    forecast = useAir("/air/forecast?hours=48");
  const band = (b) => (b ? t(b, bands[b] || b) : "—");
  const n = now.data,
    f = forecast.data;
  const format = (value) =>
    value == null
      ? "—"
      : Number(value.toFixed(1)).toLocaleString(
          lang === "hi" ? "hi-IN" : "en-IN",
        );
  return (
    <>
      <div className="heading">
        <div>
          <small>{t("DELHI · REGIONAL AIR", "दिल्ली · क्षेत्रीय हवा")}</small>
          <h1>{t("Today’s air", "आज की हवा")}</h1>
        </div>
        <button onClick={openProfile}>
          {profile ? profile.locality : t("Set up household", "परिवार जोड़ें")}{" "}
          ↗
        </button>
      </div>
      <section className="brief">
        <h2>{t("Current PM2.5", "वर्तमान PM2.5")}</h2>
        {!n ? (
          <Status request={now} />
        ) : (
          <>
            <div className="reading">
              {format(n.hourly_pm25_ug_m3)} <span>µg/m³</span>
            </div>
            <strong>{band(n.hourly_subindex_estimate?.band)}</strong>
            <p>
              {t("Hourly PM2.5 sub-index", "घंटे का PM2.5 उप-सूचकांक")} ·{" "}
              {format(n.hourly_subindex_estimate?.value)}
            </p>
            <Source data={n} />
          </>
        )}
      </section>
      {n && (
        <section className="panel">
          <h2>{t("24-hour average", "24 घंटे का औसत")}</h2>
          <p>
            {format(n.mean_24h_pm25_ug_m3)} µg/m³ ·{" "}
            {band(n.pm25_subindex_24h?.band)} ·{" "}
            {t("PM2.5 sub-index", "PM2.5 उप-सूचकांक")}{" "}
            {format(n.pm25_subindex_24h?.value)}
          </p>
          <small>
            {n.valid_hours}/24 {t("hours available", "घंटों का डेटा उपलब्ध")}
          </small>
        </section>
      )}
      <section className="panel">
        <h2>{t("48-hour forecast", "48 घंटे का पूर्वानुमान")}</h2>
        {!f ? (
          <Status request={forecast} />
        ) : (
          <>
            <Source data={f} />
            <div className="grid">
              {[
                ["lowest_hour", t("Lowest hour", "सबसे कम वाला घंटा")],
                ["highest_hour", t("Highest hour", "सबसे अधिक वाला घंटा")],
              ].map(
                ([key, label]) =>
                  f[key] && (
                    <div key={key} className="stat">
                      <small>{label}</small>
                      <strong>{format(f[key].pm25_ug_m3)} µg/m³</strong>
                      {timeLabel(f[key].timestamp, lang)} IST
                    </div>
                  ),
              )}
            </div>
            <details>
              <summary>
                {t("View all 48 hours", "सभी 48 घंटे देखें")} (
                {f.available_hours}/48)
              </summary>
              <table>
                <thead>
                  <tr>
                    <th>{t("Time", "समय")} (IST)</th>
                    <th>PM2.5 (µg/m³)</th>
                    <th>{t("Band", "श्रेणी")}</th>
                  </tr>
                </thead>
                <tbody>
                  {f.hours.map((row) => (
                    <tr key={row.timestamp}>
                      <td>{timeLabel(row.timestamp, lang)}</td>
                      <td>{format(row.pm25_ug_m3)}</td>
                      <td>{band(row.subindex_estimate?.band)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          </>
        )}
      </section>
    </>
  );
}
