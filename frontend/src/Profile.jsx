import React, { useState } from "react";
import { api, Field, initial, member, useText } from "./shared";
import { householdExamples } from "./householdExamples";

const options = {
  home_type: [
    ["flat", "Flat", "फ़्लैट"],
    ["independent_house", "Independent house", "स्वतंत्र मकान"],
    ["other", "Other", "अन्य"],
  ],
  cooking_fuel: [
    ["lpg", "LPG", "एलपीजी"],
    ["png", "Piped gas", "पाइप गैस"],
    ["electric", "Electric", "बिजली"],
    ["biomass", "Biomass", "जैव ईंधन"],
    ["other", "Other", "अन्य"],
  ],
  budget_band: [
    ["low", "Low", "कम"],
    ["medium", "Medium", "मध्यम"],
    ["high", "High", "अधिक"],
  ],
  age_band: [
    ["child", "Child", "बच्चा"],
    ["teen", "Teen", "किशोर"],
    ["adult", "Adult", "वयस्क"],
    ["older_adult", "Older adult", "बुज़ुर्ग"],
  ],
  mode: [
    ["walk", "Walk", "पैदल"],
    ["cycle", "Cycle", "साइकिल"],
    ["bus", "Bus", "बस"],
    ["metro", "Metro", "मेट्रो"],
    ["car", "Car", "कार"],
    ["two_wheeler", "Two-wheeler", "दोपहिया"],
    ["auto", "Auto", "ऑटो"],
  ],
};

export default function Profile({ saved, onSave, onDelete, headers }) {
  const t = useText();
  const [draft, setDraft] = useState(() => {
    if (!saved) return initial();
    const { id, ...fields } = saved;
    return fields;
  });
  const [example, setExample] = useState(null);
  const [step, move] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const title = [
    t("Location", "स्थान"),
    t("Home", "घर"),
    t("Members & commutes", "सदस्य और सफ़र"),
  ];
  function edit(key, value) {
    setDraft((old) => ({ ...old, [key]: value }));
  }
  function updateMember(i, patch) {
    edit(
      "members",
      draft.members.map((m, j) => (j === i ? { ...m, ...patch } : m)),
    );
  }
  function choice(key, label, value, change) {
    return (
      <Field title={label}>
        <select value={value} onChange={(e) => change(e.target.value)}>
          {options[key].map(([id, en, hi]) => (
            <option key={id} value={id}>
              {t(en, hi)}
            </option>
          ))}
        </select>
      </Field>
    );
  }
  function number(key, label, min, max) {
    return (
      <Field title={label}>
        <input
          type="number"
          step="any"
          min={min}
          max={max}
          required
          value={draft[key]}
          onChange={(e) =>
            edit(key, e.target.value === "" ? "" : Number(e.target.value))
          }
        />
      </Field>
    );
  }
  async function submit(e) {
    e.preventDefault();
    if (step < 2) {
      move(step + 1);
      return;
    }
    setBusy(true);
    setError(false);
    try {
      onSave(
        await api("/households", {
          method: "POST",
          headers: { ...headers, "Content-Type": "application/json" },
          body: JSON.stringify(draft),
        }),
      );
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }
  async function remove() {
    setBusy(true);
    setError(false);
    try {
      await api("/households/" + saved.id, { method: "DELETE", headers });
      onDelete();
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <h1>{t("Your household", "आपका परिवार")}</h1>
      <form onSubmit={submit}>
        <fieldset disabled={busy}>
          <legend>
            {step + 1}/3 · {title[step]}
          </legend>
          {step === 0 && (
            <>
              <p>
                {t(
                  "Enter your neighbourhood in Delhi. Coordinates are saved to two decimal places.",
                  "दिल्ली में अपना इलाका लिखें। निर्देशांक दो दशमलव स्थानों तक सहेजे जाते हैं।",
                )}
              </p>
              <Field title={t("Locality", "इलाका")}>
                <input
                  required
                  maxLength={80}
                  pattern=".*\S.*"
                  value={draft.locality}
                  onChange={(e) => edit("locality", e.target.value)}
                />
              </Field>
              <div className="grid">
                {number("lat", t("Latitude", "अक्षांश"), 28.5, 28.8)}
                {number("lon", t("Longitude", "देशांतर"), 77, 77.4)}
              </div>
            </>
          )}
          {step === 0 && !saved && (
            <details>
              <summary>{t("Start with an example household", "उदाहरण परिवार चुनें")}</summary>
              <p>{t(
                "Choose an example to fill in the home, members and trips. Review the details before saving.",
                "घर, सदस्य और सफ़र की जानकारी भरने के लिए एक उदाहरण चुनें। सहेजने से पहले विवरण जाँचें।",
              )}</p>
              <div className="grid">
                {householdExamples.map(({ en, hi, fields }) => (
                  <button key={en} type="button" aria-pressed={example === en} onClick={() => {
                    setDraft((old) => ({
                      ...old, ...fields, locality: old.locality.trim() || "Central Delhi",
                    }));
                    setExample(en);
                  }}>
                    {t(en, hi)}
                  </button>
                ))}
              </div>
            </details>
          )}
          {step === 1 && (
            <div className="grid">
              {choice(
                "home_type",
                t("Home type", "घर का प्रकार"),
                draft.home_type,
                (v) => edit("home_type", v),
              )}
              {choice(
                "cooking_fuel",
                t("Cooking fuel", "रसोई का ईंधन"),
                draft.cooking_fuel,
                (v) => edit("cooking_fuel", v),
              )}
              {number(
                "room_area_m2",
                t("Room area (m²)", "कमरे का क्षेत्रफल (m²)"),
                0.01,
                1000,
              )}
              {number(
                "ceiling_m",
                t("Ceiling height (m)", "छत की ऊँचाई (m)"),
                0.01,
                20,
              )}
              {number(
                "purifier_cadr_m3h",
                t("Purifier CADR (m³/h)", "प्यूरिफ़ायर CADR (m³/h)"),
                0,
                5000,
              )}
              {choice(
                "budget_band",
                t("Budget", "बजट"),
                draft.budget_band,
                (v) => edit("budget_band", v),
              )}
              <label>
                <input
                  type="checkbox"
                  checked={draft.windows_leaky}
                  onChange={(e) => edit("windows_leaky", e.target.checked)}
                />
                {t(
                  "Windows let air through when closed",
                  "बंद खिड़कियों से हवा आती है",
                )}
              </label>
            </div>
          )}
          {step === 2 && (
            <>
              {draft.members.map((m, i) => (
                <div className="person" key={i}>
                  <h3>
                    {t("Member", "सदस्य")} {i + 1}
                  </h3>
                  {choice(
                    "age_band",
                    t("Age group", "आयु वर्ग"),
                    m.age_band,
                    (v) => updateMember(i, { age_band: v }),
                  )}
                  <label>
                    <input
                      type="checkbox"
                      checked={m.sensitive}
                      onChange={(e) =>
                        updateMember(i, { sensitive: e.target.checked })
                      }
                    />
                    {t(
                      "Sensitive to air pollution",
                      "वायु प्रदूषण के प्रति संवेदनशील",
                    )}
                  </label>
                  {m.commutes.map((trip, j) => {
                    function update(key, value) {
                      updateMember(i, {
                        commutes: m.commutes.map((c, k) =>
                          k === j ? { ...c, [key]: value } : c,
                        ),
                      });
                    }
                    return (
                      <fieldset key={j}>
                        <legend>
                          {t("Commute", "सफ़र")} {j + 1}
                        </legend>
                        <div className="grid">
                          {choice(
                            "mode",
                            t("Travel mode", "आवागमन का साधन"),
                            trip.mode,
                            (v) => update("mode", v),
                          )}
                          <Field title={t("Distance (km)", "दूरी (किमी)")}>
                            <input
                              type="number"
                              min="0.01"
                              max="500"
                              step="any"
                              required
                              value={trip.distance_km}
                              onChange={(e) =>
                                update(
                                  "distance_km",
                                  e.target.value === ""
                                    ? ""
                                    : Number(e.target.value),
                                )
                              }
                            />
                          </Field>
                          {[
                            ["depart_time", t("Departure", "प्रस्थान")],
                            ["return_time", t("Return", "वापसी")],
                          ].map(([key, label]) => (
                            <Field key={key} title={label}>
                              <input
                                type="time"
                                required
                                value={trip[key]}
                                onChange={(e) => update(key, e.target.value)}
                              />
                            </Field>
                          ))}
                        </div>
                        <button
                          type="button"
                          onClick={() =>
                            updateMember(i, {
                              commutes: m.commutes.filter((_, k) => k !== j),
                            })
                          }
                        >
                          {t("Remove commute", "सफ़र हटाएँ")}
                        </button>
                      </fieldset>
                    );
                  })}
                  <div className="actions">
                    <button
                      type="button"
                      disabled={m.commutes.length >= 10}
                      onClick={() =>
                        updateMember(i, {
                          commutes: [
                            ...m.commutes,
                            {
                              mode: "metro",
                              distance_km: 5,
                              depart_time: "09:00",
                              return_time: "18:00",
                            },
                          ],
                        })
                      }
                    >
                      {t("Add commute", "सफ़र जोड़ें")}
                    </button>
                    {draft.members.length > 1 && (
                      <button
                        type="button"
                        onClick={() =>
                          edit(
                            "members",
                            draft.members.filter((_, j) => i !== j),
                          )
                        }
                      >
                        {t("Remove member", "सदस्य हटाएँ")}
                      </button>
                    )}
                  </div>
                </div>
              ))}
              <button
                type="button"
                disabled={draft.members.length >= 30}
                onClick={() => edit("members", [...draft.members, member()])}
              >
                {t("Add member", "सदस्य जोड़ें")}
              </button>
            </>
          )}
          <div className="actions">
            {step > 0 && (
              <button type="button" onClick={() => move(step - 1)}>
                {t("Back", "पीछे")}
              </button>
            )}
            <button className="primary">
              {step === 2
                ? t("Save household", "परिवार सहेजें")
                : t("Continue", "आगे बढ़ें")}
            </button>
          </div>
        </fieldset>
      </form>
      {saved && (
        <div className="actions">
          {confirm && (
            <p>
              {t(
                "Delete this household and all its commutes?",
                "यह परिवार और इसके सभी सफ़र मिटाएँ?",
              )}
            </p>
          )}
          <button
            disabled={busy}
            onClick={() => (confirm ? remove() : setConfirm(true))}
          >
            {confirm
              ? t("Confirm deletion", "मिटाने की पुष्टि करें")
              : t("Delete household", "परिवार मिटाएँ")}
          </button>
          {confirm && (
            <button onClick={() => setConfirm(false)}>
              {t("Cancel", "रद्द करें")}
            </button>
          )}
        </div>
      )}
      {error && (
        <p role="alert">
          {t(
            "Could not complete the request. Your form is still here. Try again.",
            "अनुरोध पूरा नहीं हुआ। फ़ॉर्म में जानकारी सुरक्षित है। फिर कोशिश करें।",
          )}
        </p>
      )}
    </section>
  );
}
