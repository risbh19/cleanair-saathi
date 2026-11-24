import React, { useState } from "react";
import { api, Field, useText } from "./shared";

export default function SchoolRun({ headers }) {
  const t = useText();
  const [code, setCode] = useState("");
  const [departure, setDeparture] = useState("08:00");
  const [result, setResult] = useState(null);
  const [working, setWorking] = useState(false);
  async function submit(leave) {
    setWorking(true); setResult(null);
    try {
      if (leave) {
        await api("/community/school-run", { method: "DELETE", headers });
        setResult("left");
      } else {
        const response = await api("/community/school-run", { method: "POST",
          headers: { ...headers, "Content-Type": "application/json" },
          body: JSON.stringify({ group_code: code.trim(), departure }) });
        setResult(response.matched ? "match" : "waiting");
      }
    } catch { setResult("error"); }
    finally { setWorking(false); }
  }
  const messages = {
    match: t("Another household in your group chose the same locality and time. Arrange details privately with the group.",
      "आपके समूह में एक और परिवार ने यही इलाका और समय चुना। आगे की बात समूह में निजी तौर पर करें।"),
    waiting: t("No overlap yet. Check again after another household joins.", "अभी मिलान नहीं है। दूसरा परिवार जुड़े तो फिर जाँचें।"),
    left: t("Your offer was removed.", "आपका प्रस्ताव हटा दिया गया।"),
    error: t("Check the group code and try again.", "समूह कोड जाँचें और फिर कोशिश करें।"),
  };
  return <details><summary>{t("School-run carpool group", "स्कूल कारपूल समूह")}</summary>
    <p>{t("Adults can share a private code with households they know. Joining lists your locality and chosen departure slot for seven days. Keep the code private.",
      "वयस्क परिचित परिवारों को निजी कोड दे सकते हैं। जुड़ने पर सात दिनों के लिए आपके इलाके और चुने हुए समय से मिलान होगा। कोड निजी रखें।")}</p>
    <form onSubmit={e => { e.preventDefault(); submit(false); }}>
      <fieldset disabled={working}><legend>{t("Private group", "निजी समूह")}</legend>
        <button type="button" onClick={() => { setCode(crypto.randomUUID()); setResult(null); }}>{t("Create group code", "समूह कोड बनाएँ")}</button>
        <Field title={t("Group code", "समूह कोड")}><input required value={code} onChange={e => { setCode(e.target.value); setResult(null); }} /></Field>
        <Field title={t("Departure (IST)", "प्रस्थान (IST)")}><select value={departure} onChange={e => { setDeparture(e.target.value); setResult(null); }}>
          {Array.from({length: 96}, (_, i) => {
            const time = String(Math.floor(i / 4)).padStart(2, "0") + ":" + String(15 * (i % 4)).padStart(2, "0");
            return <option key={time}>{time}</option>;
          })}
        </select></Field>
        <button>{t("Join and check", "जुड़ें और जाँचें")}</button>
        <button type="button" onClick={() => submit(true)}>{t("Withdraw offer", "प्रस्ताव हटाएँ")}</button>
      </fieldset>
    </form>
    {result && <p role="status">{messages[result]}</p>}
  </details>;
}
