import React from "react";
import { timeLabel, useText } from "./shared";

export default function HourlyComparison({ result }) {
  const t = useText();
  const selected = result.selected.hourly_pm25_ug_m3;
  const baseline = result.baseline_closed_no_purifier.hourly_pm25_ug_m3;
  const hours = selected.length;
  const peak = Math.max(...selected, ...baseline);
  const lang = t("en", "hi");
  const format = (value) => value.toLocaleString(lang, { maximumSignificantDigits: 3 });
  const x = (i) => hours === 1 ? 180 : 42 + (i * 296) / (hours - 1);
  const y = (value) => 102 - (value / (peak || 1)) * 84;
  const points = (values) => values.map((value, i) => `${x(i)},${y(value)}`).join(" ");
  const selectedLabel = t("Selected settings", "चुनी गई सेटिंग");
  const baselineLabel = t("Closed, unfiltered room", "बंद कमरा, बिना फ़िल्टर");

  return (
    <section>
      <h3>{t("Hourly indoor PM2.5", "कमरे का घंटेवार PM2.5")} (µg/m³)</h3>
      <p>{selectedLabel} ({t("solid", "ठोस रेखा")}) · {baselineLabel} ({t("dashed", "टूटी रेखा")})</p>
      <svg viewBox="0 0 360 128" width="100%" aria-hidden="true">
        <path d="M42 16 V102 H338" fill="none" stroke="currentColor" />
        <g fontSize="11" fill="currentColor">
          {peak > 0 && <text x="38" y="21" textAnchor="end">{format(peak)}</text>}
          <text x="38" y="106" textAnchor="end">0</text>
          <text x={x(0)} y="121" textAnchor="middle">{t("Hour 1", "घंटा 1")}</text>
          {hours > 1 && <text x={x(hours - 1)} y="121" textAnchor="middle">{hours}</text>}
        </g>
        <polyline points={points(selected)} fill="none" stroke="#17675d" strokeWidth="3" />
        <polyline points={points(baseline)} fill="none" stroke="#9a4d16" strokeWidth="2" strokeDasharray="5 3" />
        {hours === 1 && <>
          <circle cx={x(0)} cy={y(selected[0])} r="5" fill="#17675d" />
          <circle cx={x(0)} cy={y(baseline[0])} r="3" fill="#9a4d16" />
        </>}
      </svg>
      <details>
        <summary>{t("Hourly values", "घंटेवार मान")}</summary>
        <table>
          <caption>{t("Estimated indoor PM2.5", "कमरे का अनुमानित PM2.5")} (µg/m³)</caption>
          <thead><tr>
            <th scope="col">{result.forecast ? t("Time (IST)", "समय (IST)") : t("Hour", "घंटा")}</th>
            <th scope="col">{selectedLabel}</th><th scope="col">{baselineLabel}</th>
          </tr></thead>
          <tbody>{selected.map((value, i) => (
            <tr key={i}>
              <th scope="row">{result.forecast ? timeLabel(result.forecast.hours[i].timestamp, lang) : i + 1}</th>
              <td>{format(value)}</td><td>{format(baseline[i])}</td>
            </tr>
          ))}</tbody>
        </table>
      </details>
    </section>
  );
}
