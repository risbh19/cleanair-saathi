import React, { useContext, useEffect, useState } from "react";
import { api, Language, Source, timeLabel, useText } from "./shared";

const bands = {
  Good: "अच्छा",
  Satisfactory: "संतोषजनक",
  "Moderately polluted": "मध्यम प्रदूषित",
  Poor: "खराब",
  "Very poor": "बहुत खराब",
  Severe: "गंभीर",
};

function useAir(path, headers) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [attempt, retry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setError(false);
    api(path, { headers, signal: controller.signal })
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(true);
      });
    return () => controller.abort();
  }, [path, attempt, headers]);
  return { data, setData, error, retry: () => retry((n) => n + 1) };
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

export default function Today({ profile, openProfile, headers }) {
  const t = useText(),
    lang = useContext(Language);
  const now = useAir(
      profile ? `/air/now?lat=${profile.lat}&lon=${profile.lon}` : "/air/now",
    ),
    forecast = useAir("/air/forecast?hours=48"),
    grap = useAir("/grap/status"),
    weather = useAir("/weather/forecast?hours=48");
  const band = (b) => (b ? t(b, bands[b] || b) : "—");
  const n = now.data,
    f = forecast.data;
  const format = (value) =>
    value == null
      ? "—"
      : Number(value.toFixed(1)).toLocaleString(
          lang === "hi" ? "hi-IN" : "en-IN",
        );
  function indexLabel(index) {
    if (index?.value_range) {
      const [low, high] = index.value_range;
      return (
        t("band range", "श्रेणी सीमा") + " " + format(low) + "–" + format(high)
      );
    }
    return format(index?.value);
  }
  return (
    <>
      <div className="heading">
        <div>
          <small>{t("DELHI · REGIONAL AIR", "दिल्ली · क्षेत्रीय हवा")}</small>
          <h1>
            {n?.data_mode === "replay"
              ? t("Delhi winter replay", "दिल्ली की सर्दियों का रीप्ले")
              : t("Today’s air", "आज की हवा")}
          </h1>
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
              {n.stations?.length
                ? t(
                    "Station PM2.5 sub-index estimate",
                    "स्टेशन PM2.5 उप-सूचकांक का अनुमान",
                  )
                : t("Hourly PM2.5 sub-index", "घंटे का PM2.5 उप-सूचकांक")}{" "}
              · {indexLabel(n.hourly_subindex_estimate)}
            </p>
            {(n.hourly_subindex_estimate?.value_range ||
              n.pm25_subindex_24h?.value_range) && (
              <a style={{ color: "inherit" }} href={n.methodology_url}>
                {t("CPCB breakpoint table", "CPCB की श्रेणी तालिका")}
              </a>
            )}
            <Source data={n} />
            {n.stations?.length > 0 && (
              <details>
                <summary>
                  {t("Contributing stations", "शामिल स्टेशन")} (
                  {n.stations.length})
                </summary>
                <ul>
                  {n.stations.map((s) => (
                    <li key={s.location_id}>
                      <a style={{ color: "inherit" }} href={s.url}>
                        {s.name}
                      </a>{" "}
                      · {s.provider} · {format(s.distance_km)} km ·{" "}
                      {format(s.pm25_ug_m3)} µg/m³ · {timeLabel(s.as_of, lang)}{" "}
                      IST
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </>
        )}
      </section>
      <section className="panel">
        <h2>
          {n?.data_mode === "replay"
            ? t(
                "Latest recorded GRAP order (outside replay)",
                "नवीनतम दर्ज GRAP आदेश (रीप्ले से अलग)",
              )
            : t("Delhi-NCR GRAP status", "दिल्ली-एनसीआर GRAP स्थिति")}
        </h2>
        {!grap.data ? (
          <Status request={grap} />
        ) : grap.data.order ? (
          <>
            <strong>
              {grap.data.order.stage === 0
                ? t(
                    "No active stage in the recorded order",
                    "दर्ज आदेश में कोई चरण लागू नहीं",
                  )
                : t("Recorded stage", "दर्ज चरण") +
                  " " +
                  ["", "I", "II", "III", "IV"][grap.data.order.stage]}
            </strong>
            <p>
              {t("Effective from", "लागू होने का समय")} ·{" "}
              {new Intl.DateTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", {
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
                timeZone: "Asia/Kolkata",
              }).format(new Date(grap.data.order.effective_from))}{" "}
              IST
            </p>
            <a href={grap.data.order.source_url}>
              {t("Read the CAQM order", "CAQM का आदेश पढ़ें")}
            </a>
          </>
        ) : (
          <p>
            {t(
              "No effective CAQM order has been recorded.",
              "लागू CAQM आदेश अभी दर्ज नहीं है।",
            )}
          </p>
        )}
      </section>
      {profile && <DailyPlan headers={headers} />}
      {n && (
        <section className="panel">
          <h2>{t("24-hour average", "24 घंटे का औसत")}</h2>
          <p>
            {format(n.mean_24h_pm25_ug_m3)} µg/m³ ·{" "}
            {band(n.pm25_subindex_24h?.band)} ·{" "}
            {t("PM2.5 sub-index", "PM2.5 उप-सूचकांक")}{" "}
            {indexLabel(n.pm25_subindex_24h)}
          </p>
          {n.average_as_of && n.data_mode === "live" && (
            <p className="source">
              CAMS · Open-Meteo · {timeLabel(n.average_as_of, lang)} IST
              {n.average_stale && " · " + t("Older data", "पुराना डेटा")}
            </p>
          )}
          <small>
            {n.valid_hours}/24 {t("hours available", "घंटों का डेटा उपलब्ध")}
          </small>
        </section>
      )}
      <section className="panel">
        <h2>
          {f?.data_mode === "replay"
            ? t("Next 48 archived hours", "अगले 48 संग्रहित घंटे")
            : t("48-hour forecast", "48 घंटे का पूर्वानुमान")}
        </h2>
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
      <section className="panel">
        <h2>{t("Delhi weather forecast", "दिल्ली का मौसम पूर्वानुमान")}</h2>
        {!weather.data ? (
          <Status request={weather} />
        ) : (
          <>
            <p className="source">
              {weather.data.data_mode === "fixture" ? (
                t("Demo · Synthetic weather", "डेमो · कृत्रिम मौसम डेटा")
              ) : (
                <a href={weather.data.source_url}>
                  {weather.data.data_mode === "replay"
                    ? t(
                        "January 2025 replay · Open-Meteo weather archive",
                        "जनवरी 2025 रीप्ले · Open-Meteo मौसम संग्रह",
                      )
                    : t("Weather data by Open-Meteo", "मौसम डेटा · Open-Meteo")}
                </a>
              )}
              {" · "}
              {timeLabel(
                weather.data.fetched_at ?? weather.data.as_of,
                lang,
              )}{" "}
              IST
              {weather.data.stale && " · " + t("Older data", "पुराना डेटा")}
            </p>
            <WeatherHour
              rows={weather.data.hours}
              format={format}
              lang={lang}
            />
          </>
        )}
      </section>
    </>
  );
}

function WeatherHour({ rows, format, lang }) {
  const t = useText();
  const [index, setIndex] = useState(0);
  const row = rows[index];
  return (
    <>
      <label className="field">
        <span>{t("Forecast hour", "पूर्वानुमान का समय")} (IST)</span>
        <select
          value={index}
          onChange={(event) => setIndex(Number(event.target.value))}
        >
          {rows.map((item, i) => (
            <option key={item.timestamp} value={i}>
              {timeLabel(item.timestamp, lang)}
            </option>
          ))}
        </select>
      </label>
      <dl className="grid">
        {[
          [t("Temperature", "तापमान"), "temperature_2m", "°C"],
          [
            t("Relative humidity", "सापेक्ष आर्द्रता"),
            "relative_humidity_2m",
            "%",
          ],
          [t("Wind speed", "हवा की गति"), "wind_speed_10m", "m/s"],
          [
            t("Boundary-layer height", "वायुमंडलीय सीमा परत की ऊँचाई"),
            "boundary_layer_height",
            "m",
          ],
        ].map(([label, key, unit]) => (
          <div className="stat" key={key}>
            <dt>{label}</dt>
            <dd>
              {row[key] == null
                ? t("Unavailable", "अनुपलब्ध")
                : format(row[key]) + " " + unit}
            </dd>
          </div>
        ))}
      </dl>
    </>
  );
}

function DailyPlan({ headers }) {
  const plan = useAir("/plan/today", headers);
  const lang = useContext(Language),
    t = useText();
  const [saving, setSaving] = useState(null);
  const [failed, setFailed] = useState(false);
  async function update(item, status) {
    setSaving(item.item_id);
    setFailed(false);
    try {
      const result = await api("/plan/items/" + item.item_id + "/status", {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      plan.setData((old) => ({
        ...old,
        actions: old.actions.map((action) =>
          action.item_id === result.item_id
            ? { ...action, status: result.status }
            : action,
        ),
      }));
    } catch {
      setFailed(true);
    } finally {
      setSaving(null);
    }
  }
  return (
    <section className="panel">
      <h2>{t("Household action plan", "परिवार की कार्ययोजना")}</h2>
      {!plan.data ? (
        <Status request={plan} />
      ) : (
        <>
          <p>
            {plan.data.band_used
              ? t("PM2.5 band used", "चयन में उपयोग की गई PM2.5 श्रेणी") +
                " · " +
                t(plan.data.band_used, bands[plan.data.band_used])
              : t(
                  "Based on your household profile. A fresh air reading is unavailable.",
                  "यह योजना आपके परिवार की जानकारी पर आधारित है। ताज़ा रीडिंग उपलब्ध नहीं है।",
                )}
            {plan.data.data_mode === "fixture" &&
              " · " + t("Synthetic demo", "कृत्रिम डेमो")}
            {plan.data.data_mode === "replay" &&
              " · " + t("Winter replay", "सर्दियों का रीप्ले")}
          </p>
          <p>
            {plan.data.plan_date} · {t("Completed", "पूरे हुए")}{" "}
            {plan.data.actions.filter((a) => a.status === "done").length}/
            {plan.data.actions.length}
          </p>
          {failed && (
            <p role="alert">
              {t(
                "Could not save this change. Please try again.",
                "बदलाव सहेजा नहीं जा सका। फिर कोशिश करें।",
              )}
            </p>
          )}
          <ol>
            {plan.data.actions.map((action) => (
              <li key={action.id}>
                <strong>{action[lang].title}</strong>
                {action.time_of_day && <small> · {({morning: t("Morning", "सुबह"), afternoon: t("Afternoon", "दोपहर"), evening: t("Evening", "शाम"), anytime: t("Any time", "कभी भी")})[action.time_of_day]}</small>}
                <p>{action[lang].step}</p>
                {action.indoor_example && <details><summary>
                  {t("Modeled overnight dose difference", "रात की अनुमानित मात्रा का अंतर")} · {Number(action.indoor_example.avoided_inhaled_pm25_ug.toPrecision(2))} µg
                </summary><p>{t("Eight hours at the plan’s outdoor PM2.5 level, closed windows, purifier on versus off.", "योजना के बाहरी PM2.5 स्तर पर आठ घंटे, बंद खिड़कियाँ, प्यूरिफ़ायर चालू और बंद होने की तुलना।")}</p>
                <p>{action.indoor_example.assumptions.outdoor_pm25_ug_m3[0]} µg/m³ · {action.indoor_example.room_volume_m3.toFixed(1)} m³ · CADR {action.indoor_example.assumptions.purifier_cadr_m3_h} m³/h</p>
                <a href={action.indoor_example.method_url}>{t("Model reference", "मॉडल संदर्भ")}</a></details>}
                {!action.commute_example && !action.indoor_example && <small>{t("Impact has not been quantified for this action.", "इस काम के असर की मात्रा का अनुमान उपलब्ध नहीं है।")}</small>}
                {action.commute_example && (
                  <CommuteImpact example={action.commute_example} />
                )}
                <label>
                  {t("Progress", "प्रगति")}{" "}
                  <select
                    aria-label={
                      t("Progress", "प्रगति") + " · " + action[lang].title
                    }
                    value={action.status}
                    disabled={saving !== null}
                    onChange={(event) => update(action, event.target.value)}
                  >
                    <option value="planned">{t("Planned", "करना है")}</option>
                    <option value="done">{t("Done", "पूरा हुआ")}</option>
                    <option value="skipped">{t("Skipped", "छोड़ा गया")}</option>
                  </select>
                </label>
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  );
}

function CommuteImpact({ example }) {
  const t = useText();
  const { baseline, alternative, distance_km, co2_difference_g } = example;
  const number = (value) =>
    value.toLocaleString(t("en-IN", "hi-IN"), { maximumSignificantDigits: 3 });
  const vehicle =
    baseline.mode === "petrol_hatchback_lt1000cc"
      ? t(
          "Petrol hatchback under 1,000 cc",
          "1,000 सीसी से छोटी पेट्रोल हैचबैक",
        )
      : t("Scooter under 110 cc", "110 सीसी से छोटा स्कूटर");
  return (
    <details>
      <summary>
        {t("Example CO₂ difference", "उदाहरण में CO₂ का अंतर")} ·{" "}
        {number(co2_difference_g)} g
      </summary>
      <p>
        {t(
          "One traveller, one way, at the first saved car or two-wheeler trip distance.",
          "एक यात्री का एकतरफ़ा सफ़र, कार या दोपहिया के पहले दर्ज सफ़र की दूरी पर।",
        )}
      </p>
      {[
        [vehicle, baseline],
        [t("City bus", "शहरी बस"), alternative],
      ].map(([label, leg]) => (
        <p key={leg.mode}>
          {label} · {number(distance_km)} km × {leg.g_co2_per_passenger_km} g
          CO₂/{t("passenger-km", "यात्री-किमी")} ≈ {number(leg.trip_co2_g)} g
          CO₂.{" "}
          <a href={leg.source_url}>
            {t("Source", "स्रोत")} ({leg.vintage})
          </a>
        </p>
      ))}
      <p>
        {t(
          "The difference assumes replacing this trip with the bus. Marking the card done records progress only.",
          "अंतर की गणना इस सफ़र की जगह बस लेने की मान्यता पर है। कार्ड पूरा करने पर केवल प्रगति दर्ज होती है।",
        )}
      </p>
    </details>
  );
}
