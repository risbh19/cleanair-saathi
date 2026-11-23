import React, { useState } from "react";
import { api, Field, useText } from "./shared";

const modes = {
  petrol_hatchback_lt1000cc: [
    "Petrol hatchback under 1,000 cc",
    "1,000 सीसी से छोटी पेट्रोल हैचबैक",
    5,
  ],
  scooter_lt110cc: ["Scooter under 110 cc", "110 सीसी से छोटा स्कूटर", 2],
  cng_auto: ["CNG auto-rickshaw", "सीएनजी ऑटो", 3],
  intracity_bus: ["City bus", "शहरी बस", 1],
};

export default function Commute() {
  const t = useText();
  const [km, distance] = useState(10),
    [legs, setLegs] = useState({
      baseline: { mode: "petrol_hatchback_lt1000cc", travellers: 1 },
      alternative: { mode: "intracity_bus", travellers: 1 },
    });
  const [result, setResult] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(false);
  function edit(key, patch) {
    setResult(null);
    setError(false);
    setLegs({ ...legs, [key]: { ...legs[key], ...patch } });
  }
  async function run(e) {
    e.preventDefault();
    setBusy(true);
    setError(false);
    try {
      setResult(
        await api("/simulate/commute", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ distance_km: Number(km), ...legs }),
        }),
      );
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }
  const labels = {
    baseline: t("Current trip", "मौजूदा सफ़र"),
    alternative: t("Alternative trip", "वैकल्पिक सफ़र"),
  };
  const fmt = (n) =>
    Number(n.toPrecision(3)).toLocaleString(t("en-IN", "hi-IN"), {
      maximumSignificantDigits: 3,
    });
  return (
    <section>
      <h1>{t("Compare commute emissions", "सफ़र के उत्सर्जन की तुलना")}</h1>
      <p>
        {t(
          "Compare one traveller making the same one-way trip by two modes.",
          "एक यात्री के लिए एक ही दूरी के एकतरफ़ा सफ़र की दो साधनों से तुलना करें।",
        )}
      </p>
      <form onSubmit={run}>
        <fieldset disabled={busy}>
          <legend>{t("Trip assumptions", "सफ़र की मान्यताएँ")}</legend>
          <Field title={t("One-way distance (km)", "एकतरफ़ा दूरी (किमी)")}>
            <input
              required
              min="0.001"
              max="500"
              step="any"
              type="number"
              value={km}
              onChange={(e) => {
                distance(e.target.value);
                setResult(null);
              }}
            />
          </Field>
          <div className="grid">
            {Object.entries(legs).map(([key, leg]) => (
              <div key={key}>
                <Field title={labels[key]}>
                  <select
                    value={leg.mode}
                    onChange={(e) =>
                      edit(key, { mode: e.target.value, travellers: 1 })
                    }
                  >
                    {Object.entries(modes).map(([id, [en, hi]]) => (
                      <option key={id} value={id}>
                        {t(en, hi)}
                      </option>
                    ))}
                  </select>
                </Field>
                {leg.mode !== "intracity_bus" && (
                  <Field
                    title={t(
                      "Travellers sharing emissions",
                      "उत्सर्जन साझा करने वाले यात्री",
                    )}
                  >
                    <select
                      value={leg.travellers}
                      onChange={(e) =>
                        edit(key, { travellers: Number(e.target.value) })
                      }
                    >
                      {Array.from({ length: modes[leg.mode][2] }, (_, i) => (
                        <option key={i}>{i + 1}</option>
                      ))}
                    </select>
                  </Field>
                )}
              </div>
            ))}
          </div>
          <button className="primary">
            {t("Compare trips", "सफ़र की तुलना करें")}
          </button>
        </fieldset>
      </form>
      {error && (
        <p role="alert">
          {t(
            "Could not load emission factors. Try again.",
            "उत्सर्जन गुणांक उपलब्ध नहीं हैं। फिर कोशिश करें।",
          )}
        </p>
      )}
      {result && (
        <section className="panel" role="status">
          <h2>
            {t("Estimated CO₂ per traveller", "प्रति यात्री अनुमानित CO₂")}
          </h2>
          {Object.keys(legs).map((key) => (
            <p key={key}>
              {labels[key]} · {fmt(result[key].trip_co2_g)} g CO₂
            </p>
          ))}
          <strong>
            {t(
              "Difference (current − alternative)",
              "अंतर (मौजूदा − वैकल्पिक)",
            )}{" "}
            · {fmt(result.co2_difference_g)} g CO₂
          </strong>
          <details>
            <summary>{t("Calculation and source", "गणना और स्रोत")}</summary>
            {Object.keys(legs).map((key) => {
              const v = result[key];
              return (
                <p key={key}>
                  {labels[key]} · {result.distance_km} km ×{" "}
                  {v.factor_g_co2_per_km}{" "}
                  {v.factor_basis === "vehicle"
                    ? t("g CO₂/vehicle-km", "g CO₂/वाहन-किमी")
                    : t("g CO₂/passenger-km", "g CO₂/यात्री-किमी")}
                  {v.factor_basis === "vehicle" && " ÷ " + v.travellers} ={" "}
                  {fmt(v.trip_co2_g)} g CO₂.{" "}
                  <a href={v.source_url}>
                    {t("India GHG Program", "भारत GHG कार्यक्रम")} ({v.vintage})
                  </a>
                </p>
              );
            })}
            <p>
              {t(
                "Historical Indian operating averages. The city bus factor excludes BRT and intercity trips.",
                "भारत के ऐतिहासिक परिचालन औसत। शहरी बस का गुणांक बीआरटी और अंतरशहरी सफ़र पर लागू नहीं होता।",
              )}
            </p>
          </details>
        </section>
      )}
    </section>
  );
}
