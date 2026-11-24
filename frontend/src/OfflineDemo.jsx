import React, { useState } from "react";
import demo from "./offline-demo.json";
import { Field, timeLabel, useText } from "./shared";

export default function OfflineDemo({ lang }) {
  const t = useText();
  const [done, setDone] = useState({});
  const [windows, setWindows] = useState("closed");
  const [cadr, setCadr] = useState(0);
  const current = demo.simulations.find(s => s.windows === windows && s.cadr === cadr);
  return <section>
    <h1>{t("Offline demo", "ऑफ़लाइन डेमो")}</h1>
    <p>{t("Synthetic Delhi data and an example household. Changes last until you leave this screen.",
      "दिल्ली के कृत्रिम आँकड़े और उदाहरण परिवार। बदलाव इस स्क्रीन पर रहने तक दिखेंगे।")}</p>
    <p>PM2.5 · {demo.pm25} µg/m³ · {timeLabel(demo.as_of, lang)} IST</p>
    <details><summary>{t("48-hour example forecast", "48 घंटे का उदाहरण पूर्वानुमान")}</summary>
      <ol>{demo.forecast.map(row => <li key={row.timestamp}>{timeLabel(row.timestamp, lang)} IST · {row.pm25} µg/m³</li>)}</ol>
    </details>
    <h2>{t("Example plan", "उदाहरण योजना")}</h2>
    {demo.actions.map(a => <p key={a.id}><label><input type="checkbox" checked={!!done[a.id]}
      onChange={e => setDone({...done, [a.id]: e.target.checked})} />{a[lang].title}</label></p>)}
    <h2>{t("Eight-hour room comparison", "आठ घंटे की कमरे की तुलना")}</h2>
    <p>12 m² × 2.7 m</p>
    <Field title={t("Windows", "खिड़कियाँ")}><select value={windows} onChange={e => setWindows(e.target.value)}>
      <option value="closed">{t("Closed", "बंद")}</option><option value="open">{t("Open", "खुली")}</option>
    </select></Field>
    <Field title="CADR (m³/h)"><select value={cadr} onChange={e => setCadr(Number(e.target.value))}>
      {[0,100,200,300].map(n => <option key={n}>{n}</option>)}
    </select></Field>
    <p role="status">{t("Estimated inhaled PM2.5", "साँस में गया अनुमानित PM2.5")} · {Number(current.dose.toPrecision(2))} µg</p>
  </section>;
}
