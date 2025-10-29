// src/components/DimensionRadialBars.jsx
import React from "react";
import {
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
  PolarGrid,
  ResponsiveContainer,
} from "recharts";

const DEFAULT = [
  { key: "Collaboration", value: 26, color: "#F6C945" },
  { key: "Diversity",     value: 18, color: "#8BC5BF" },
  { key: "Inclusion",     value: 22, color: "#7F86C6" },
  { key: "Belonging",     value: 14, color: "#C993C7" },
  { key: "Innovation",    value: 27, color: "#F39B7F" }, 
  { key: "Leadership",    value: 21, color: "#6DB1FF" },
  { key: "Recognition",   value: 19, color: "#9DD67A" },
  { key: "Respect",       value: 23, color: "#E6B8A2" },
];

export default function DimensionRadialBars({
  title = "Cultural Dimensions",
  data = DEFAULT,
  widthPx = 520,
  heightPx = 230,
}) {
  const dims = data.filter(d => typeof d.value === "number" && d.value >= 0);
  const maxVal = Math.max(...dims.map(d => d.value), 1);  

  const record = dims.reduce((acc, d, i) => {
    acc[`d${i}`] = d.value;
    return acc;
  }, {});
  const chartData = [record];

  const rings = dims.length;
  const usableBand = 64;    
  const startRadius = 18;
  const gap = 2;
  const thickness = Math.max(5, Math.floor(usableBand / rings) - gap);

  const bars = dims.map((d, i) => {
    const inner = startRadius + i * (usableBand / rings);
    return {
      dataKey: `d${i}`,
      color: d.color,
      innerRadius: `${inner}%`,
      outerRadius: `${inner + thickness}%`,
      label: d.key,
    };
  });

  const chartHeight = Math.max(140, heightPx - 56);

  return (
    <div
      className="rounded-2xl border border-[#d6d0c5] bg-white/70 shadow-sm px-4 py-3 overflow-hidden"
      style={{ width: "100%", maxWidth: widthPx, height: heightPx }}
    >
      <h3 className="text-[14px] font-semibold text-neutral-800 mb-2">
        {title}
      </h3>

      <div className="grid grid-cols-[220px_1fr] gap-4 items-center h-[calc(100%-28px)]">
        <div style={{ width: "100%", height: chartHeight }}>
          <ResponsiveContainer width="100%" height="100%">
            <RadialBarChart
              data={chartData}
              startAngle={90}
              endAngle={-270}
              innerRadius="0%"
              outerRadius="100%"
            >
              <PolarGrid stroke="#eee8de" />
              <PolarAngleAxis type="number" domain={[0, maxVal]} tick={false} />
              {bars.map(b => (
                <RadialBar
                  key={b.dataKey}
                  dataKey={b.dataKey}
                  clockWise
                  background={{ fill: "#f5f3ee" }}
                  cornerRadius={999}
                  fill={b.color}
                  innerRadius={b.innerRadius}
                  outerRadius={b.outerRadius}
                  isAnimationActive={false}
                />
              ))}
            </RadialBarChart>
          </ResponsiveContainer>
        </div>

        <div className="h-full flex items-center">
          <div className="w-full">
            {(() => {
              const rows = [];
              for (let i = 0; i < dims.length; i += 2) rows.push(dims.slice(i, i + 2));
              return (
                <div
                  className="w-full"
                  style={{
                    display: "grid",
                    gridTemplateRows: `repeat(${rows.length}, auto)`,
                    rowGap: "10px",
                  }}
                >
                  {rows.map((pair, ri) => (
                    <div key={`row-${ri}`} className="grid grid-cols-2 gap-x-1">
                      {pair.map((d) => (
                        <div
                          key={d.key}
                          className="flex items-center gap-1 rounded-lg border border-[#e9e4da] bg-white/90 px-1 py-1.5 shadow-sm min-h-[34px]"
                          style={{ maxWidth: "900px" }}
                          title={d.key}
                        >
                          <span
                            className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
                            style={{ background: d.color }}
                          />
                          <span className="text-[12px] text-neutral-700 leading-none truncate">
                            {d.key}
                          </span>
                        </div>
                      ))}
                      {pair.length === 1 && <div />} 
                    </div>
                  ))}
                </div>
              );
            })()}
          </div>
        </div>
      </div>
    </div>
  );
}
