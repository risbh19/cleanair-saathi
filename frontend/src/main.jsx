import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, Language, useText } from "./shared";
import Profile from "./Profile";
import Today from "./Today";
import Commute from "./Commute";
import Ask from "./Ask";
import Lab from "./Lab";
import "./style.css";

function Dashboard({ lang, setLang }) {
  const t = useText();
  const [page, go] = useState("today"),
    [profile, setProfile] = useState(null),
    [state, setState] = useState("loading");
  const [headers, setHeaders] = useState(null),
    [attempt, retry] = useState(0);
  useEffect(() => {
    let current = true;
    async function load() {
      setState("loading");
      try {
        let token = localStorage.getItem("saathi.session");
        if (!token) {
          token = crypto.randomUUID();
          localStorage.setItem("saathi.session", token);
        }
        const auth = { Authorization: "Bearer " + token };
        setHeaders(auth);
        const saved = await api("/households/me", { headers: auth });
        if (current) {
          setProfile(saved);
          setState("ready");
        }
      } catch (e) {
        if (current) {
          setState(e.status === 404 ? "ready" : "error");
        }
      }
    }
    load();
    return () => {
      current = false;
    };
  }, [attempt]);
  const pages = [
    ["today", t("Today", "आज")],
    ["profile", t("Household", "परिवार")],
    ["lab", t("Indoor Lab", "घर की हवा")],
    ["ask", t("Ask Saathi", "साथी से पूछें")],
    ["commute", t("Commute", "सफ़र")],
  ];
  return (
    <>
      <header>
        <div className="bar">
          <span className="brand">
            CleanAir <b>Saathi</b>
          </span>
          <button
            lang={lang === "en" ? "hi" : "en"}
            onClick={() => setLang(lang === "en" ? "hi" : "en")}
          >
            {lang === "en" ? "हिन्दी" : "English"}
          </button>
        </div>
      </header>
      <nav aria-label={t("Main navigation", "मुख्य नेविगेशन")}>
        {pages.map(([id, label]) => (
          <button
            key={id}
            aria-current={page === id ? "page" : undefined}
            onClick={() => go(id)}
          >
            {label}
          </button>
        ))}
      </nav>
      <main>
        {page === "today" && (
          <Today
            headers={headers}
            profile={profile}
            openProfile={() => go("profile")}
          />
        )}
        {page === "ask" && <Ask key={lang} lang={lang} />}
        {page === "commute" && <Commute />}
        {page === "lab" && (
          <Lab key={profile?.id ?? "anonymous"} profile={profile} />
        )}
        {page === "profile" &&
          (state === "ready" ? (
            <Profile
              saved={profile}
              headers={headers}
              onSave={(p) => {
                setProfile(p);
                go("today");
              }}
              onDelete={() => {
                setProfile(null);
                go("today");
              }}
            />
          ) : state === "loading" ? (
            <p role="status">
              {t("Loading household…", "परिवार लोड हो रहा है…")}
            </p>
          ) : (
            <p role="alert">
              {t(
                "Could not open your household. Check browser storage and the API connection.",
                "परिवार नहीं खुला। ब्राउज़र स्टोरेज और API कनेक्शन जाँचें।",
              )}{" "}
              <button onClick={() => retry((n) => n + 1)}>
                {t("Retry", "फिर कोशिश करें")}
              </button>
            </p>
          ))}
      </main>
    </>
  );
}

function App() {
  const [lang, change] = useState(() => {
    try {
      return localStorage.getItem("saathi.lang") === "hi" ? "hi" : "en";
    } catch {
      return "en";
    }
  });
  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem("saathi.lang", lang);
    } catch {}
  }, [lang]);
  return (
    <Language.Provider value={lang}>
      <Dashboard lang={lang} setLang={change} />
    </Language.Provider>
  );
}
createRoot(document.getElementById("root")).render(<App />);
