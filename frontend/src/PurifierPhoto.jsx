import React, { useState } from "react";
import { api, Field, useText } from "./shared";

export default function PurifierPhoto({ onConfirm }) {
  const t = useText();
  const [photo, setPhoto] = useState(null), [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false), [error, setError] = useState(false);
  const [consent, setConsent] = useState(false);
  async function analyze(event) {
    event.preventDefault();
    if (!photo || !consent) return;
    setBusy(true); setError(false); setResult(null);
    try {
      if (photo.size > 1024 * 1024 || !["image/jpeg", "image/png", "image/webp"].includes(photo.type)) throw new Error();
      const encoded = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(",")[1]);
        reader.onerror = reject;
        reader.readAsDataURL(photo);
      });
      setResult(await api("/purifier/analyze", {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({image_base64: encoded, mime_type: photo.type, language: t("en", "hi")})}));
    } catch { setError(true); } finally { setBusy(false); }
  }
  return <section className="panel">
    <h2>{t("Check a purifier photo", "प्यूरिफ़ायर की फ़ोटो जाँचें")}</h2>
    <p>{t("Choose a close-up of the purifier, filter or CADR label. Avoid faces and personal details. JPEG, PNG or WebP, up to 1 MiB and 8 megapixels.",
      "प्यूरिफ़ायर, फ़िल्टर या CADR लेबल की पास से फ़ोटो चुनें। चेहरे और निजी जानकारी न रखें। JPEG, PNG या WebP, 1 MiB और 8 मेगापिक्सेल तक।")}</p>
    <form onSubmit={analyze}><fieldset disabled={busy}>
      <legend>{t("Optional photo analysis", "वैकल्पिक फ़ोटो विश्लेषण")}</legend>
      <Field title={t("Purifier or filter photo", "प्यूरिफ़ायर या फ़िल्टर की फ़ोटो")}>
        <input type="file" accept="image/jpeg,image/png,image/webp" required onChange={e => {setPhoto(e.target.files[0] || null); setResult(null); setConsent(false); setError(false);}} />
      </Field>
      <label><input type="checkbox" checked={consent} required onChange={e => setConsent(e.target.checked)} />
        {t("Allow this photo to be sent to Google for Gemini analysis when enabled. It is not saved by this app.",
          "चालू होने पर Gemini विश्लेषण के लिए यह फ़ोटो Google को भेजने की अनुमति दें। ऐप इसे सहेजता नहीं है।")}</label>
      <button disabled={!photo || !consent}>{busy ? t("Checking…", "जाँच जारी…") : t("Analyze photo", "फ़ोटो जाँचें")}</button>
    </fieldset></form>
    {error && <p role="alert">{t("Photo unavailable. Try a smaller supported image or enter CADR manually.", "फ़ोटो उपलब्ध नहीं। छोटी फ़ोटो चुनें या CADR खुद भरें।")}</p>}
    {result && <div role="status">
      <p>{result.mode === "gemini" ? t("Gemini photo observations — verify against the device label and manual.", "Gemini की फ़ोटो जाँच — लेबल और गाइड से पुष्टि करें।") : t("Photo analysis is unavailable. Use the manual checks below.", "फ़ोटो विश्लेषण उपलब्ध नहीं। नीचे दिए तरीके से खुद जाँचें।")}</p>
      <ul>{result.guidance.map((text, i) => <li key={i}>{text}</li>)}</ul>
      {result.observation?.cadr_m3h != null && <p>
        {t("Possible label CADR", "लेबल पर संभावित CADR")}: {result.observation.cadr_m3h} m³/h. {t("Confirm this number on your device before using it.", "इस्तेमाल से पहले डिवाइस पर इस संख्या की पुष्टि करें।")}{" "}
        <button type="button" onClick={() => onConfirm(result.observation.cadr_m3h)}>{t("I checked the label — use this CADR", "मैंने लेबल जाँचा — यह CADR भरें")}</button>
      </p>}
      {result.citations.map(c => <a key={c.url} href={c.url}>{c.title}</a>)}
    </div>}
  </section>;
}
