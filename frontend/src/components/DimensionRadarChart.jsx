import React, { useMemo } from "react";

// Internal helper to reserve space for header/padding and keep a minimum chart height
function heightPxInner(total) {
  const headerAndPadding = 72;
  return Math.max(120, total - headerAndPadding);
}

// Utility to create SVG path for a ring-shaped sector (donut slice)
const arcPath = (cx, cy, r0, r1, a0, a1) => {
  const c = Math.cos;
  const s = Math.sin;
  const x0 = cx + r1 * c(a0);
  const y0 = cy + r1 * s(a0);
  const x1 = cx + r1 * c(a1);
  const y1 = cy + r1 * s(a1);
  const x2 = cx + r0 * c(a1);
  const y2 = cy + r0 * s(a1);
  const x3 = cx + r0 * c(a0);
  const y3 = cy + r0 * s(a0);
  const large = a1 - a0 > Math.PI ? 1 : 0;
  return `M ${x0} ${y0} A ${r1} ${r1} 0 ${large} 1 ${x1} ${y1} L ${x2} ${y2} A ${r0} ${r0} 0 ${large} 0 ${x3} ${y3} Z`;
};

export default function DimensionRadarChart({
  width,
  heightPx,
  items,
  level,
  onDimensionClick,
  onSubthemeClick,
  onBackToTop,
}) {
  // Geometry setup for the radar
  const PAD = 12;
  const W = width;
  const H = heightPxInner(heightPx);
  const boxShort = Math.min(W, H);
  const cx = Math.round(W * 0.48); // slightly left of center
  const cy = Math.round(H * 0.52); // slightly lower than center
  const rMax = Math.max(0, Math.floor(boxShort / 2 - PAD));
  const rMin = Math.max(8, Math.floor(rMax * 0.25));
  const gapRatio = 0.14; // angular gap between sectors
  const maxVal = Math.max(1, ...items.map((d) => d.value));

  // Convert items into polar sectors (start/end angle + inner/outer radius)
  const sectors = useMemo(() => {
    const n = Math.max(1, items.length);
    const full = Math.PI * 2;
    const step = full / n;
    const pad = step * gapRatio;
    return items.map((d, i) => {
      const a0 = -Math.PI / 2 + i * step + pad / 2;
      const a1 = -Math.PI / 2 + (i + 1) * step - pad / 2;
      // Non-linear scaling so small categories are still visible
      const t = Math.pow(d.value / maxVal, 0.78);
      const rOut = rMin + Math.max(0, rMax - rMin) * t;
      return { ...d, start: a0, end: a1, rIn: 8, rOut };
    });
  }, [items, rMin, rMax, maxVal]);

  return (
    <svg width={width} height={"100%"}>
      {/* Background grid: rings + radial lines */}
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

      {/* Coloured sectors */}
      <g>
        {sectors.map((d, i) => (
          <path
            key={i}
            d={arcPath(cx, cy, d.rIn, d.rOut, d.start, d.end)}
            fill={d.color}
            fillOpacity="0.92"
            stroke="rgba(0,0,0,0.06)"
            onClick={() =>
              level === 0 ? onDimensionClick?.(d.name) : onSubthemeClick?.(d.name)
            }
            style={{ cursor: "pointer" }}
          />
        ))}
      </g>

      {/* Value labels around the arc (near the outer radius) */}
      <g>
        {sectors.map((d, i) => {
          const a = (d.start + d.end) / 2;
          const rr = d.rOut + 12;
          const tx = cx + rr * Math.cos(a);
          const ty = cy + rr * Math.sin(a);
          return (
            <text
              key={i}
              x={tx}
              y={ty}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize="12"
              fill="#333"
              style={{ pointerEvents: "none" }}
            >
              {d.value}
            </text>
          );
        })}
      </g>

      {/* Back button rendered inside the SVG when in subtheme view */}
      {level === 1 && items.length > 0 && (
        <foreignObject x="8" y={H - 32} width="24" height="24">
          <button
            onClick={onBackToTop}
            className="w-6 rounded-md border border-neutral-300/70 hover:bg-neutral-50 text-[14px]"
            title="Back"
            style={{ cursor: "pointer" }}
          >
            ⮌
          </button>
        </foreignObject>
      )}
    </svg>
  );
}
