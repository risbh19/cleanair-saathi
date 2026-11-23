import React from "react";

export const Language = React.createContext("en");
export function useText() {
  const hi = React.useContext(Language) === "hi";
  return (en, hindi) => (hi ? hindi : en);
}

export async function api(path, options = {}) {
  const response = await fetch("/api" + path, options);
  if (!response.ok)
    throw Object.assign(new Error("Request failed"), {
      status: response.status,
    });
  return response.status === 204 ? null : response.json();
}

export function Field({ title, children }) {
  return (
    <label className="field">
      <span>{title}</span>
      {children}
    </label>
  );
}

export function timeLabel(value, lang) {
  return new Intl.DateTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
  }).format(new Date(value));
}

export const member = () => ({
  age_band: "adult",
  sensitive: false,
  commutes: [],
});
export const initial = () => ({
  locality: "",
  lat: 28.61,
  lon: 77.21,
  home_type: "flat",
  room_area_m2: 12,
  ceiling_m: 2.7,
  windows_leaky: false,
  purifier_cadr_m3h: 0,
  cooking_fuel: "lpg",
  budget_band: "low",
  members: [member()],
});
