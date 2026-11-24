import React, { useState } from "react";
import { api, Field, useText } from "./shared";

export default function Ask({ lang }) {
  const t = useText();
  const [question, edit] = useState("");
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  async function ask(event) {
    event.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError(false);
    try {
      const reply = await api("/chat", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, language: lang }) });
      setMessages((old) => [...old, { question, ...reply }]);
      edit("");
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }
  return <section>
    <h1>{t("Ask Saathi", "साथी से पूछें")}</h1>
    <p>{t("Ask about purifier sizing, filter replacement or the air forecast.", "प्यूरिफ़ायर की क्षमता, फ़िल्टर बदलने या हवा के पूर्वानुमान के बारे में पूछें।")}</p>
    <small>{t("In live mode your question is sent to Google. Leave out personal details.", "लाइव मोड में आपका सवाल Google को भेजा जाता है। व्यक्तिगत जानकारी न लिखें।")}</small>
    <div aria-live="polite">{messages.map((m, i) => <article className="panel" key={i}>
      <strong>{m.question}</strong><p>{m.answer}</p>
      {m.citations.map(c => <a key={c.url} href={c.url}>{c.title}</a>)}
    </article>)}</div>
    <form onSubmit={ask}><Field title={t("Question", "सवाल")}><input required maxLength={500} disabled={busy}
      value={question} onChange={e => edit(e.target.value)} /></Field>
      <button className="primary" disabled={busy || !question.trim()}>{t("Ask", "पूछें")}</button>
    </form>
    {error && <p role="alert">{t("Could not load an answer. Try again.", "उत्तर नहीं मिला। फिर कोशिश करें।")}</p>}
  </section>;
}
