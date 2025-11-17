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

// Static month labels so missing months still reserve a slot
const MONTHS = [
  "Jan","Feb","Mar","Apr","May","Jun",
  "Jul","Aug","Sep","Oct","Nov","Dec"
];

// Allowed year range when aggregating "all years"
const YEAR_MIN = 2013;
const YEAR_MAX = 2025;

export default function IncomeStatistics({
  className = "",
  title = "Monthly Statistics",
  year = "all",
  height = 260,
}) {
  // Series data passed into Recharts
  const [series, setSeries] = useState([]);
  // Optional error message (shown above the chart)
  const [err, setErr] = useState("");
  // Simple fade-in phase for the chart when data changes
  const [phase, setPhase] = useState(1);
  // Loading flag (also controls overlay spinner)
  const [loading, setLoading] = useState(false);

  // Fetch SBI time series whenever the selected year changes
  useEffect(() => {
    let alive = true;
    setPhase(0);
    setErr("");
    setSeries([]);
    setLoading(true);

    (async () => {
      try {
        // "all" mode: compute a yearly average SBI for each year
        if (String(year).toLowerCase() === "all") {
          const rows = [];
          for (let y = YEAR_MIN; y <= YEAR_MAX; y++) {
            if (!alive) return;

            const base = await getSBI({ year: y });
            const monthsWithData = Array.isArray(base?.months_with_data)
              ? base.months_with_data
              : [];

            // For each month with data, fetch its SBI and keep finite values
            const monthVals = await Promise.all(
              monthsWithData.map((m) =>
                getSBI({ year: y, month: m })
                  .then((r) => Number(r?.sbi))
                  .catch(() => NaN)
              )
            );
            const valid = monthVals.filter(Number.isFinite);

            // Yearly average of SBI (if we have any valid months)
            const avg = valid.length
              ? valid.reduce((a, b) => a + b, 0) / valid.length
              : null;

            rows.push({
              label: String(y),
              sbi: avg === null ? null : Math.round(avg),
            });
          }

          if (!alive) return;
          setSeries(rows);
          // Use RAF to avoid tiny flicker when the dataset changes
          requestAnimationFrame(() => setPhase(1));
        } else {
          // Specific year: show monthly SBI values from Jan–Dec
          const base = await getSBI({ year });
          const monthsWithData = Array.isArray(base?.months_with_data)
            ? base.months_with_data
            : [];

          // Only query SBI for months that actually have data
          const list = await Promise.all(
            monthsWithData.map((m) =>
              getSBI({ year, month: m })
                .then((r) => ({ m, sbi: Number(r?.sbi ?? 0) }))
                .catch(() => ({ m, sbi: null }))
            )
          );

          // Map month number -> SBI value
          const map = new Map(list.map(({ m, sbi }) => [m, sbi]));

          // Build a full 12-month series, filling gaps with nulls
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
        // Surface the error but still render the empty chart shell
        setErr(e?.message || String(e));
        setSeries([]);
        requestAnimationFrame(() => setPhase(1));
      } finally {
        if (alive) setLoading(false);
      }
    })();

    return () => {
      // Guard against late-arriving responses
      alive = false;
    };
  }, [year]);

  const isAll = String(year).toLowerCase() === "all";

  // Small helper for subtitle text
  const subtitle = useMemo(
    () => `Year: ${isAll ? "all" : year}`,
    [year, isAll]
  );

  // Filter out null / non-finite points so Recharts doesn't choke
  const dataFiltered = useMemo(
    () => series.filter((d) => d.sbi !== null && Number.isFinite(d.sbi)),
    [series]
  );

  return (
    <div
      className={`relative rounded-2xl border border-[#d6d0c5] shadow-sm px-4 py-3 ${className}`}
      style={{ background: "rgb(246,243,239)", height, width: "100%" }}
    >
      {/* Header bar: title + current year selection */}
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-[14px] font-semibold text-neutral-800">
          {title.toUpperCase()}
        </h3>
        <span className="text-[12px] text-neutral-500">{subtitle}</span>
      </div>

      {/* Error banner (if the fetch failed) */}
      {err && (
        <div className="text-[12px] text-red-700 bg-red-50 border border-red-200 rounded-md px-2 py-1 mb-2">
          {err}
        </div>
      )}

      {/* Main chart area with a small fade-in when data updates */}
      <div
        style={{
          transition: "opacity 300ms ease",
          opacity: phase,
          height: `calc(${height}px - 70px)`, // reserve space for header + error
        }}
      >
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
              domain={[-100, 100]} // SBI is normalized to [-100, 100]
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
              connectNulls={false} // we want gaps where there is no data
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Loading overlay – sits on top of the chart while fetching */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center" aria-live="polite">
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
