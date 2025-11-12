// src/components/DimensionRadar.jsx
import React, { useEffect, useMemo, useState, useCallback } from "react";
import { getDimensionCounts, getSubthemeCounts } from "../api";

export default function DimensionRadar({
  title = "Cultural Dimensions",
  year,
  month,

  selectedDimension = "",
  selectedSubtheme = "",

  onFilterChange,
  widthPx = 640,
  heightPx = 247,
}) {
  const [level, setLevel] = useState(0);
  const [focusDim, setFocusDim] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeSub, setActiveSub] = useState("");

  const colors = useMemo(() => [
    "#F6C945",
    "#8BC5BF",
    "#7F86C6",
    "#C993C7",
    "#F39B7F",
    "#6DB1FF",
    "#9DD67A",
    "#E6B8A2",
    "#B9A1FF",
    "#FFC4A1",
    "#8FD3FF",
    "#F2B2CE",
  ],[])

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      if (level === 0) {
        const data = await getDimensionCounts({ year, month });
        setItems(
          (data || [])
            .map((d, i) => ({
              name: d.name,
              value: Number(d.count || 0),
              color: colors[i % colors.length],
            }))
            .filter((d) => d.value > 0),
        );
      } else {
        const data = await getSubthemeCounts({
          year,
          month,
          dimension: focusDim,
        });
        setItems(
          (data || [])
            .map((d, i) => ({
              name: d.name,
              value: Number(d.count || 0),
              color: colors[i % colors.length],
            }))
            .filter((d) => d.value > 0),
        );
      }
    } finally {
      setLoading(false);
    }
  }, [level, focusDim, year, month, colors]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!selectedDimension) {
      setLevel(0);
      setFocusDim("");
      setActiveSub("");
      return;
    }
    setLevel(1);
    setFocusDim(selectedDimension);
    setActiveSub(selectedSubtheme || "");
  }, [selectedDimension, selectedSubtheme]);

  const W = widthPx,
    H = heightPx;
  const cx = Math.round(W * 0.4);
  const cy = Math.round(H * 0.7);
  const rMin = Math.max(12, Math.min(W, H) * 0.1);
  const rMax = Math.min(cx, Math.round(H * 2));
  const gapRatio = 0.14;
  const maxVal = Math.max(1, ...items.map((d) => d.value));

  const sectors = useMemo(() => {
    const n = Math.max(1, items.length);
    const full = Math.PI * 2;
    const step = full / n;
    const pad = step * gapRatio;
    return items.map((d, i) => {
      const a0 = -Math.PI / 2 + i * step + pad / 2;
      const a1 = -Math.PI / 2 + (i + 1) * step - pad / 2;
      const t = Math.pow(d.value / maxVal, 0.78);
      const rOut = rMin + (rMax - rMin) * t;
      return { ...d, start: a0, end: a1, rIn: 8, rOut };
    });
  }, [items, rMin, rMax, maxVal]);

  const arcPath = (cx, cy, r0, r1, a0, a1) => {
    const c = Math.cos,
      s = Math.sin;
    const x0 = cx + r1 * c(a0),
      y0 = cy + r1 * s(a0);
    const x1 = cx + r1 * c(a1),
      y1 = cy + r1 * s(a1);
    const x2 = cx + r0 * c(a1),
      y2 = cy + r0 * s(a1);
    const x3 = cx + r0 * c(a0),
      y3 = cy + r0 * s(a0);
    const large = a1 - a0 > Math.PI ? 1 : 0;
    return `M ${x0} ${y0} A ${r1} ${r1} 0 ${large} 1 ${x1} ${y1} L ${x2} ${y2} A ${r0} ${r0} 0 ${large} 0 ${x3} ${y3} Z`;
  };

  const clickDimension = (dimName) => {
    if (level === 0) {
      if (selectedDimension === dimName) {
        onFilterChange?.({ dimension: "", subtheme: "" });
        setLevel(0);
        setFocusDim("");
        setActiveSub("");
      } else {
        onFilterChange?.({ dimension: dimName, subtheme: "" });
        setLevel(1);
        setFocusDim(dimName);
        setActiveSub("");
      }
    }
  };

  const clickSubtheme = (subName) => {
    const next = activeSub === subName ? "" : subName;
    setActiveSub(next);
    onFilterChange?.({ dimension: focusDim, subtheme: next });
  };

  const backToTop = () => {
    setLevel(0);
    setFocusDim("");
    setActiveSub("");
    onFilterChange?.({ dimension: "", subtheme: "" });
  };

  const legend = (
    <div className="w-full">
      <div
        className="grid gap-x-1.5 gap-y-1.5"
        style={{ gridTemplateColumns: "repeat(2,minmax(0,1fr))" }}
      >
        {items.map((d, i) => {
          const isActive = level === 1 && activeSub && d.name === activeSub;
          return (
            <button
              key={`${d.name}-${i}`}
              onClick={() =>
                level === 0 ? clickDimension(d.name) : clickSubtheme(d.name)
              }
              className={`flex items-center gap-1 rounded-lg border px-2 py-1.5 shadow-sm text-left
                          hover:shadow transition
                          ${isActive ? "bg-yellow-50 border-yellow-300" : "bg-white/92 border-[#e9e4da]"}`}
              style={{ cursor: "pointer" }}
              title={d.name}
            >
              <span
                className="inline-block w-2 h-2 rounded-full"
                style={{ background: d.color }}
              />
              <span className="text-[11px] text-neutral-700 truncate">
                {d.name}
              </span>
              <span className="ml-auto text-[11px] font-semibold tabular-nums text-neutral-800">
                {d.value}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );

  return (
    <div
      className="rounded-2xl border border-[#d6d0c5] shadow-sm px-4 py-3 overflow-hidden"
      style={{
        width: "100%",
        maxWidth: widthPx,
        height: heightPx,
        background: "rgba(255,255,255,0.7)",
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[15px] font-semibold text-neutral-800">
          {title}
          {level === 1 ? ` · ${focusDim}` : ""}
        </h3>
        <div className="text-[12px] text-neutral-500">
          {year ? `year: ${year}` : "all years"}
          {month ? `, month: ${month}` : ""}
        </div>
      </div>

      <div
        className="grid"
        style={{
          gridTemplateColumns: "minmax(240px,1fr) 1.4fr",
          gap: "10px",
          height: "calc(100% - 28px)",
        }}
      >
        <div className="relative">
          {level === 1 && (
            <button
              onClick={backToTop}
              className="absolute left-0 bottom-0 text-[14px] w-6 h-6 rounded-md border border-neutral-300/70 hover:bg-neutral-50 flex items-center justify-center"
              title="Back"
              style={{ cursor: "pointer" }}
            >
              &lt;
            </button>
          )}

          <svg
            width="100%"
            height="100%"
            viewBox={`0 0 ${W} ${H}`}
            preserveAspectRatio="xMidYMid meet"
          >
            <g opacity="0.28" stroke="#eee7dc">
              {[0.25, 0.5, 0.75, 1].map((t, i) => (
                <circle
                  key={i}
                  cx={cx}
                  cy={cy}
                  r={rMin + (rMax - rMin) * t}
                  fill="none"
                />
              ))}
              {Array.from({ length: 12 }).map((_, i) => {
                const a = (i / 12) * Math.PI * 2;
                const x = cx + rMax * Math.cos(a);
                const y = cy + rMax * Math.sin(a);
                return <line key={i} x1={cx} y1={cy} x2={x} y2={y} />;
              })}
            </g>

            <g>
              {sectors.map((d, i) => (
                <path
                  key={i}
                  d={arcPath(cx, cy, d.rIn, d.rOut, d.start, d.end)}
                  fill={d.color}
                  fillOpacity="0.92"
                  stroke="rgba(0,0,0,0.06)"
                  onClick={() =>
                    level === 0 ? clickDimension(d.name) : clickSubtheme(d.name)
                  }
                  style={{ cursor: "pointer" }}
                />
              ))}
            </g>

            <g>
              {sectors.map((d, i) => {
                const a = (d.start + d.end) / 2,
                  rr = d.rOut + 12;
                const tx = cx + rr * Math.cos(a),
                  ty = cy + rr * Math.sin(a);
                return (
                  <text
                    key={i}
                    x={tx}
                    y={ty}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize="027"
                    fill="#333"
                    style={{ pointerEvents: "none" }}
                  >
                    {d.value}
                  </text>
                );
              })}
            </g>
          </svg>
        </div>

        <div className="h-full flex items-center">
          {loading ? (
            <div className="text-[12px] text-neutral-500">Loading…</div>
          ) : (
            legend
          )}
        </div>
      </div>
    </div>
  );
}
