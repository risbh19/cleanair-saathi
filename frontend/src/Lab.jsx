import React, { useState } from "react";
import { api, Field, useText } from "./shared";

export default function Lab({ profile }) {
  const t = useText();
  const [room, setRoom] = useState({
    floor_area_m2: profile?.room_area_m2 ?? 12,
    ceiling_height_m: profile?.ceiling_m ?? 2.7,
    purifier_cadr_m3_h: profile?.purifier_cadr_m3h ?? 0,
    windows: "closed",
    outside: 100,
    hours: 8,
  });
  const [result, setResult] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(false);
  function edit(key, v) {
    setRoom({ ...room, [key]: v });
    setResult(null);
    setError(false);
  }
  async function run(e) {
    e.preventDefault();
    setBusy(true);
    setError(false);
    const { outside, hours, ...settings } = room;
    try {
      setResult(
        await api("/simulate/indoor", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...settings,
            outdoor_pm25_ug_m3: Array(hours).fill(outside),
          }),
        }),
      );
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <h1>{t("Indoor Air Lab", "घर की हवा की लैब")}</h1>
      <p>
        {t(
          "Compare your settings with the same room closed and unfiltered. Enter one outdoor concentration for the entire scenario.",
          "अपनी सेटिंग की तुलना उसी बंद कमरे से करें जिसमें फ़िल्टर नहीं है। पूरी अवधि के लिए बाहर का एक सांद्रता मान भरें।",
        )}
      </p>
      <form onSubmit={run}>
        <fieldset disabled={busy}>
          <legend>{t("Room scenario", "कमरे की स्थिति")}</legend>
          <div className="grid">
            {[
              [
                "floor_area_m2",
                t("Room area (m²)", "कमरे का क्षेत्रफल (m²)"),
                1,
                1000,
              ],
              [
                "ceiling_height_m",
                t("Ceiling height (m)", "छत की ऊँचाई (m)"),
                1,
                15,
              ],
              [
                "purifier_cadr_m3_h",
                t("Purifier CADR (m³/h)", "प्यूरिफ़ायर CADR (m³/h)"),
                0,
                10000,
              ],
              [
                "outside",
                t("Outdoor PM2.5 (µg/m³)", "बाहर का PM2.5 (µg/m³)"),
                0,
                10000,
              ],
              ["hours", t("Duration (hours)", "अवधि (घंटे)"), 1, 48],
            ].map(([key, label, min, max]) => (
              <Field key={key} title={label}>
                <input
                  required
                  type="number"
                  min={min}
                  max={max}
                  step={key === "hours" ? 1 : "any"}
                  value={room[key]}
                  onChange={(e) =>
                    edit(
                      key,
                      e.target.value === "" ? "" : Number(e.target.value),
                    )
                  }
                />
              </Field>
            ))}
            <Field title={t("Windows", "खिड़कियाँ")}>
              <select
                value={room.windows}
                onChange={(e) => edit("windows", e.target.value)}
              >
                <option value="closed">{t("Closed", "बंद")}</option>
                <option value="open">{t("Open", "खुली")}</option>
              </select>
            </Field>
          </div>
          <button className="primary">
            {t("Compare settings", "तुलना करें")}
          </button>
        </fieldset>
      </form>
      {error && (
        <p role="alert">
          {t(
            "Simulation unavailable. Try again.",
            "सिमुलेशन उपलब्ध नहीं है। फिर कोशिश करें।",
          )}
        </p>
      )}
      {result && (
        <section className="panel" role="status">
          <h2>{t("Estimated inhaled PM2.5", "साँस में गया अनुमानित PM2.5")}</h2>
          <p>
            {t("Selected settings", "चुनी गई सेटिंग")} ·{" "}
            {result.selected.inhaled_pm25_ug.toPrecision(2)} µg
          </p>
          <p>
            {t("Closed, unfiltered room", "बंद कमरा, बिना फ़िल्टर")} ·{" "}
            {result.baseline_closed_no_purifier.inhaled_pm25_ug.toPrecision(2)}{" "}
            µg
          </p>
          <small>
            {t(
              "Illustrative model of one well-mixed room. Cooking and other indoor sources are excluded.",
              "यह एक कमरे का उदाहरण मॉडल है जिसमें हवा पूरी तरह मिली हुई है। खाना पकाने और अन्य अंदरूनी स्रोतों को छोड़ दिया गया है।",
            )}
          </small>
          <ModelAssumptions result={result} />
        </section>
      )}
    </section>
  );
}

function ModelAssumptions({ result }) {
  const t = useText();
  const room = result.assumptions;
  const rows = [
    [t("Room dimensions", "कमरे का आकार"), `${room.floor_area_m2} m² × ${room.ceiling_height_m} m`],
    [t("Windows", "खिड़कियाँ"), room.windows === "open" ? t("Open", "खुली") : t("Closed", "बंद")],
    [t("Purifier CADR", "प्यूरिफ़ायर CADR"), `${room.purifier_cadr_m3_h} m³/h`],
    [t("Outdoor PM2.5", "बाहर का PM2.5"), `${room.outdoor_pm25_ug_m3[0]} µg/m³ × ${room.outdoor_pm25_ug_m3.length} h`],
    [t("Particle penetration fraction", "अंदर आने वाले कणों का अंश"), room.penetration_fraction],
    [t("Air changes per hour (closed / open)", "प्रति घंटे हवा का बदलाव (बंद / खुली खिड़कियाँ)"), `${room.closed_air_changes_h} / ${room.open_air_changes_h}`],
    [t("Particle deposition rate", "कणों के जमने की दर"), `${room.deposition_rate_h} /h`],
    [t("Breathing rate", "साँस लेने की दर"), `${room.breathing_rate_m3_h} m³/h`],
  ];
  return (
    <details>
      <summary>{t("Model assumptions", "मॉडल की मान्यताएँ")}</summary>
      <p>{t(
        "The model assumes the room reaches equilibrium each hour. Air exchange, particle deposition and breathing rates are illustrative.",
        "मॉडल मानता है कि हर घंटे कमरे में कणों की सांद्रता संतुलन पर पहुँचती है। हवा के बदलाव, कणों के जमने और साँस लेने की दरें उदाहरण के लिए हैं।",
      )}</p>
      <dl>
        {rows.map(([label, value]) => (
          <React.Fragment key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </React.Fragment>
        ))}
      </dl>
      <a href={result.method_url}>{t("EPA model reference", "EPA मॉडल संदर्भ")}</a>
    </details>
  );
}
