// src/components/IncomeStatistics.jsx
import React, { useEffect, useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { getSBI } from "../api";

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const YEAR_MIN = 2013;
const YEAR_MAX = 2025;

export default function IncomeStatistics({
  title = "Monthly Statistics",
  year = "all", // "all" | number
}) {
  const [series, setSeries] = useState([]);
  const [err, setErr] = useState("");
  const [phase, setPhase] = useState(1);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    setPhase(0);
    setErr("");
    setSeries([]);
    setLoading(true);

    (async () => {
      try {
        if (String(year).toLowerCase() === "all") {
          const rows = [];
          for (let y = YEAR_MIN; y <= YEAR_MAX; y++) {
            if (!alive) return;
            const base = await getSBI({ year: y });
            const monthsWithData = Array.isArray(base?.months_with_data)
              ? base.months_with_data : [];
            const monthVals = await Promise.all(
              monthsWithData.map((m) =>
                getSBI({ year: y, month: m })
                  .then((r) => Number(r?.sbi))
                  .catch(() => NaN)
              )
            );
            const valid = monthVals.filter(Number.isFinite);
            const avg = valid.length
              ? valid.reduce((a, b) => a + b, 0) / valid.length
              : null;
            rows.push({ label: String(y), sbi: avg === null ? null : Math.round(avg) });
          }
          if (!alive) return;
          setSeries(rows);
          requestAnimationFrame(() => setPhase(1));
        } else {
          const base = await getSBI({ year });
          const monthsWithData = Array.isArray(base?.months_with_data)
            ? base.months_with_data : [];
          const list = await Promise.all(
            monthsWithData.map((m) =>
              getSBI({ year, month: m })
                .then((r) => ({ m, sbi: Number(r?.sbi ?? 0) }))
                .catch(() => ({ m, sbi: null }))
            )
          );
          const map = new Map(list.map(({ m, sbi }) => [m, sbi]));
          const s = MONTHS.map((name, idx) => {
            const mon = idx + 1;
            return map.has(mon)
              ? { label: name, sbi: map.get(mon) }
              : { label: name, sbi: null };
          });
          if (!alive) return;
          setSeries(s);
          requestAnimationFrame(() => setPhase(1));
        }
      } catch (e) {
        if (!alive) return;
        setErr(e?.message || String(e));
        setSeries([]);
        requestAnimationFrame(() => setPhase(1));
      } finally {
        if (alive) setLoading(false);
      }
    })();

    return () => { alive = false; };
  }, [year]);

  const isAll = String(year).toLowerCase() === "all";
  const subtitle = useMemo(() => `Year: ${isAll ? "all" : year}`, [year, isAll]);

  const dataFiltered = useMemo(
    () => series.filter((d) => d.sbi !== null && Number.isFinite(d.sbi)),
    [series]
  );

  return (
    <div
      className="relative rounded-2xl border border-[#d6d0c5] shadow-sm px-4 py-3"
      style={{ background: "rgb(246,243,239)", height: 300, width: "100%" }}
    >
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-[14px] font-semibold text-neutral-800">
          {title.toUpperCase()}
        </h3>
        <span className="text-[12px] text-neutral-500">{subtitle}</span>
      </div>

      {err && (
        <div className="text-[12px] text-red-700 bg-red-50 border border-red-200 rounded-md px-2 py-1 mb-2">
          {err}
        </div>
      )}

      <div style={{ transition: "opacity 300ms ease", opacity: phase, height: "85%" }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={dataFiltered}
            margin={{ left: -30, right: 12, top: 10, bottom: 0 }}
          >
            <CartesianGrid stroke="#eae6e0" vertical={false} />
            <XAxis
              dataKey="label"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#8c887f", fontSize: 11 }}
              height={28}
              tickMargin={10}
              interval={0}
              padding={{ left: 6, right: 6 }}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#8c887f", fontSize: 11 }}
              domain={[-100, 100]}
              tickFormatter={(v) => `${v}`}
            />
            <Tooltip
              contentStyle={{
                background: "#fff",
                border: "1px solid #ddd",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              formatter={(v) => [`${v}`, "Sentiment Balance Index"]}
              labelFormatter={(label) =>
                isAll ? `Year: ${label}` : `Month: ${label}`
              }
            />
            <Line
              type="monotone"
              dataKey="sbi"
              stroke="#160c02ff"
              strokeWidth={2.5}
              dot={{ fill: "#f0dd09ff", stroke: "#252422ff", r: 4 }}
              activeDot={{ r: 6, fill: "#e1c568ff", stroke: "#a58325ff" }}
              isAnimationActive={true}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {loading && (
        <div
          className="absolute inset-0 flex items-center justify-center"
          aria-live="polite"
        >
          <div className="rounded-xl border border-white/60 bg-white/85 px-4 py-3 shadow-sm backdrop-blur-[2px]">
            <div className="flex items-center gap-3">
              <span
                className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-neutral-400 border-t-transparent"
                aria-hidden
              />
              <span className="text-sm text-neutral-700">
                {isAll ? "Loading yearly averages…" : "Loading monthly data…"}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
