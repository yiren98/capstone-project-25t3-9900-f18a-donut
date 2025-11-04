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

export default function IncomeStatistics({
  title = "Monthly Statistics",
  year = new Date().getFullYear(),
}) {
  const [series, setSeries] = useState(MONTHS.map(m => ({ month: m, sbi: null })));
  const [err, setErr] = useState("");
  const [phase, setPhase] = useState(1);

  useEffect(() => {
    let alive = true;

    setPhase(0);

    (async () => {
      setErr("");
      try {

        const base = await getSBI({ year });
        const monthsWithData = Array.isArray(base.months_with_data) ? base.months_with_data : [];


        const tasks = monthsWithData.map((m) =>
          getSBI({ year, month: m }).then((r) => ({ m, sbi: Number(r.sbi ?? 0) }))
        );
        const list = await Promise.all(tasks);

        const map = new Map(list.map(({ m, sbi }) => [m, sbi]));
        const s = MONTHS.map((name, idx) => {
          const mon = idx + 1;
          return map.has(mon) ? { month: name, sbi: map.get(mon) } : { month: name, sbi: null };
        });

        if (!alive) return;
        setSeries(s);

        requestAnimationFrame(() => setPhase(1));
      } catch (e) {
        if (!alive) return;
        setErr(e.message || String(e));
        setSeries(MONTHS.map(m => ({ month: m, sbi: null })));
        requestAnimationFrame(() => setPhase(1));
      }
    })();

    return () => { alive = false; };
  }, [year]);

  const subtitle = useMemo(() => `year: ${year}`, [year]);

  const dataFiltered = useMemo(
    () => series.filter(d => d.sbi !== null),
    [series]
  );

  return (
    <div
      className="rounded-2xl border border-[#d6d0c5] shadow-sm px-4 py-3"
      style={{
        background: "rgb(246,243,239)",
        height: 270,
        width: "100%",
      }}
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

      <div
        style={{
          transition: "opacity 300ms ease",
          opacity: phase,
          height: "85%",
        }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={dataFiltered}
            margin={{ left: -10, right: 10, top: 5, bottom: 0 }}
          >
            <CartesianGrid stroke="#eae6e0" vertical={false} />
            <XAxis
              dataKey="month"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#8c887f", fontSize: 12 }}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#8c887f", fontSize: 12 }}
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
              labelFormatter={(label) => `Month: ${label}`}
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
    </div>
  );
}
