// src/components/IncomeStatistics.jsx
import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

export default function IncomeStatistics({
  title = "Monthly Statistics",
  data = [
    { month: "Jan", income: 77 },
    { month: "Feb", income: 71 },
    { month: "Apr", income: 62 },
    { month: "May", income: 67 },
    { month: "Jul", income: 57 },
    { month: "Aug", income: 44 },
    { month: "Sep", income: 52 },
    { month: "Oct", income: 62 },
  ],
}) {
  return (
    <div
      className="rounded-2xl border border-[#d6d0c5] shadow-sm px-4 py-3"
      style={{
        background: "rgb(246,243,239)",
        height: 247,
        width: "100%",
      }}
    >
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-[14px] font-semibold text-neutral-800">
          {title.toUpperCase()}
        </h3>
        <span className="text-[12px] text-neutral-500"></span>
      </div>

      <ResponsiveContainer width="100%" height="85%">
        <LineChart data={data}
        margin={{ left: -20, right: 20, top: 5, bottom: 0 }}
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
            domain={[0, 100]}
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
          />
          <Line
            type="monotone"
            dataKey="income"
            stroke="#111"
            strokeWidth={2}
            dot={{ fill: "#111", strokeWidth: 2, r: 3 }}
            activeDot={{ r: 5, fill: "#e44", stroke: "#111" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
