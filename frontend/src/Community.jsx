import React, { useEffect, useState } from "react";
import SchoolRun from "./SchoolRun";
import { api, Field, useText } from "./shared";

export default function Community({ profile, headers }) {
  const t = useText();
  const [locality, edit] = useState(profile?.locality || "");
  const [digest, show] = useState(null);
  const [week, setWeek] = useState(null);
  const [busy, wait] = useState(false);
  const [error, setError] = useState(false);
  const [share, setShare] = useState(false);
  useEffect(() => {
    let current = true;
    if (profile) api("/plan/week", { headers }).then(data => current && setWeek(data))
      .catch(() => current && setWeek({ error: true }));
    return () => { current = false; };
  }, [profile, headers]);
  async function load(e, example = false) {
    e.preventDefault();
    wait(true); show(null); setError(false); setShare(false);
    try { show(await api(example ? "/community/example" : "/community/digest?locality=" + encodeURIComponent(locality.trim()))); }
    catch { setError(true); }
    finally { wait(false); }
  }
  function summary(d) {
    const s = d.summary;
    const numbers = [
      t("Completed actions", "पूरे किए काम") + " " + s.actions,
      t("Participating households", "भाग लेने वाले परिवार") + " " + s.households,
    ];
    if (s.modeled_co2_g != null) numbers.push(t("Modeled CO₂ difference", "अनुमानित CO₂ अंतर") + " " + Math.round(s.modeled_co2_g) + " g");
    if (s.modeled_pm25_ug != null) numbers.push(t("Modeled inhaled PM2.5 difference", "साँस में गए PM2.5 का अनुमानित अंतर") + " " + Math.round(s.modeled_pm25_ug) + " µg");
    const mode = {demo: t("Fictional households", "काल्पनिक परिवार"), fixture: t("Synthetic air data", "कृत्रिम वायु डेटा"), replay: t("Archived air data", "संग्रहित वायु डेटा"), live: t("Live air data", "लाइव वायु डेटा")};
    return [d.locality, d.start + " – " + d.end, mode[d.data_mode], ...numbers].filter(Boolean).join(" · ");
  }
  return <section>
    <h1>{t("Community digest", "इलाके का साप्ताहिक सार")}</h1>
    {week && <section className="panel"><h2>{t("Your last seven days", "आपके पिछले सात दिन")}</h2>
      <p>{week.error ? t("Could not load your week.", "साप्ताहिक जानकारी नहीं मिली।") :
        week.summary ? summary(week) : t("No completed actions this week.", "इस सप्ताह कोई पूरा किया काम नहीं है।")}</p></section>}
    <form onSubmit={load}><Field title={t("Locality", "इलाका")}><input required maxLength={80} value={locality}
      disabled={busy} onChange={e => { edit(e.target.value); show(null); setShare(false); }} /></Field>
      <button disabled={busy || !locality.trim()}>{t("Show digest", "सार देखें")}</button> <button type="button" disabled={busy} onClick={e => load(e, true)}>{t("View fictional example", "काल्पनिक उदाहरण देखें")}</button></form>
    {error && <p role="alert">{t("Could not load the digest. Try again.", "सार नहीं मिला। फिर कोशिश करें।")}</p>}
    {digest && <section className="panel" role="status">
      {digest.summary ? <><p>{summary(digest)}</p>
        <button onClick={async () => {
          if (navigator.share) {
            try { await navigator.share({ title: "CleanAir Saathi", text: summary(digest) }); return; }
            catch (err) { if (err.name === "AbortError") return; }
          }
          setShare(true);
        }}>{t("Share summary", "सार साझा करें")}</button>
        {share && <Field title={t("Copy this summary", "यह सार कॉपी करें")}><textarea readOnly value={summary(digest)} onFocus={e => e.target.select()} /></Field>}
      </> : <p>{t("A digest appears once five households complete actions in this locality during the last seven days.",
        "पिछले सात दिनों में इस इलाके के पाँच परिवारों के काम पूरे करने पर सार दिखाई देगा।")}</p>}
    </section>}
    {profile && <SchoolRun headers={headers} />}
    <small>{t("Impact figures compare modeled scenarios on completed cards. Completion records participation; actual savings are unmeasured.",
      "असर के आँकड़े पूरे किए गए कार्ड के मॉडल की तुलना हैं। काम पूरा करने से भागीदारी दर्ज होती है। वास्तविक बचत मापी नहीं गई है।")}</small>
  </section>;
}
