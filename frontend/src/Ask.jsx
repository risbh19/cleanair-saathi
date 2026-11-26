import React, { useEffect, useRef, useState } from "react";
import { api, Field, useText } from "./shared";

export default function Ask({ lang, headers }) {
  const t = useText();
  const [question, edit] = useState("");
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const recognition = useRef(null);
  const [listening, setListening] = useState(false);
  const [voiceError, setVoiceError] = useState(false);
  const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
  useEffect(() => () => {
    if (recognition.current) {
      recognition.current.onend = null;
      recognition.current.onresult = null;
      recognition.current.onerror = null;
      recognition.current.abort();
    }
  }, []);
  function dictate() {
    if (listening) { recognition.current?.stop(); return; }
    const speech = new Speech();
    recognition.current = speech;
    speech.lang = lang === "hi" ? "hi-IN" : "en-IN";
    speech.onresult = e => edit(e.results[0][0].transcript.slice(0, 500));
    speech.onend = () => setListening(false);
    speech.onerror = () => { setVoiceError(true); setListening(false); };
    setVoiceError(false);
    try { speech.start(); setListening(true); } catch { setVoiceError(true); }
  }
  async function ask(event) {
    event.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError(false);
    try {
      const reply = await api("/chat", { method: "POST", headers: { ...headers, "Content-Type": "application/json" },
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
    <p>{t("Ask about your room, filters, air forecasts, AQI or commute emissions.", "फ़िल्टर, हवा के पूर्वानुमान, AQI या सफ़र के उत्सर्जन के बारे में पूछें।")}</p>
    <small>{t("In live mode your question is sent to Google. Leave out personal details.", "लाइव मोड में आपका सवाल Google को भेजा जाता है। व्यक्तिगत जानकारी न लिखें।")}</small>
    <div aria-live="polite">{messages.map((m, i) => <article className="panel" key={i}>
      <strong>{m.question}</strong><p>{m.answer}</p>
      {m.citations.map(c => <a key={c.url} href={c.url}>{c.title}</a>)}
    </article>)}</div>
    <form onSubmit={ask}><Field title={t("Question", "सवाल")}><input required maxLength={500} disabled={busy}
      value={question} onChange={e => edit(e.target.value)} /></Field>
      {Speech && <><button type="button" disabled={busy} onClick={dictate}>
        {listening ? t("Stop dictation", "बोलना बंद करें") : t("Dictate a question", "बोलकर सवाल लिखें")}
      </button><small>{t("Your browser’s speech service processes the audio. Review the text before sending.",
        "आपके ब्राउज़र की वाणी सेवा ऑडियो संसाधित करती है। भेजने से पहले सवाल पढ़ लें।")}</small></>}
      {voiceError && <p role="status">{t("Dictation unavailable. Type your question.", "बोलकर लिखना उपलब्ध नहीं है। अपना सवाल टाइप करें।")}</p>}
      <button className="primary" disabled={busy || listening || !question.trim()}>{t("Ask", "पूछें")}</button>
    </form>
    {error && <p role="alert">{t("Could not load an answer. Try again.", "उत्तर नहीं मिला। फिर कोशिश करें।")}</p>}
  </section>;
}
