import React, {
  useEffect,
  useMemo,
  useState,
  useCallback,
  useRef,
} from "react";
import { getDimensionCounts, getSubthemeCounts } from "../api";

const SCROLL_WIDTH = 4;
const SC_TRACK_COLOR = "rgb(237, 229, 213)";
const SC_THUMB_COLOR = "rgba(238, 227, 212, 0.88)";
const SC_THUMB_BORDER = "rgba(0,0,0,0.35)";
const SC_GUTTER = 6;

const EmptyState = ({ children, style }) => (
  <div
    className="flex items-center justify-center text-neutral-500 text-[16px] rounded-xl border"
    style={{ border: "1px solid #fefefeff", ...style }}
  >
    {children || "No results."}
  </div>
);

export default function DimensionRadar({
  className = "",
  title = "Cultural Dimensions",
  year,
  month,
  selectedDimension = "",
  selectedSubtheme = "",
  onFilterChange,
  leftMax = 300,
  rightMin = 220,
  gapPx = 12,
  heightPx = 260,
}) {
  const [level, setLevel] = useState(0);
  const [focusDim, setFocusDim] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeSub, setActiveSub] = useState("");

  const rootRef = useRef(null);
  const [leftSize, setLeftSize] = useState(leftMax);
  const [rightWidth, setRightWidth] = useState(0); 


  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const W = el.clientWidth || 0;
      const maxLeftAllowed = Math.max(
        200,
        Math.min(leftMax, W - rightMin - gapPx)
      );
      const nextLeft = Number.isFinite(maxLeftAllowed)
        ? Math.max(200, maxLeftAllowed)
        : leftMax;
      setLeftSize(nextLeft);

      setRightWidth(Math.max(0, W - nextLeft - gapPx));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [leftMax, rightMin, gapPx]);

  const colors = useMemo(
    () => [
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
    ],
    []
  );

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
            .filter((d) => d.value > 0)
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
            .filter((d) => d.value > 0)
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

  const PAD = 12;
  const W = leftSize,
    H = heightPxInner(heightPx);
  const boxShort = Math.min(W, H);
  const cx = Math.round(W * 0.48);
  const cy = Math.round(H * 0.52);
  const rMax = Math.max(0, Math.floor(boxShort / 2 - PAD));
  const rMin = Math.max(8, Math.floor(rMax * 0.25));
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
      const rOut = rMin + Math.max(0, rMax - rMin) * t;
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
    if (level !== 0) return;
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

  const scRef = useRef(null);
  const [hovering, setHovering] = useState(false);
  const [scrolling, setScrolling] = useState(false);
  const [thumb, setThumb] = useState({ top: 0, height: 0 });
  const hideTimer = useRef(null);

  const [isTouch, setIsTouch] = useState(false);
  useEffect(() => {
    const val =
      typeof window !== "undefined" &&
      ("ontouchstart" in window ||
        navigator.maxTouchPoints > 0 ||
        navigator.msMaxTouchPoints > 0);
    setIsTouch(Boolean(val));
  }, []);

  useEffect(() => {
    const el = scRef.current;
    if (!el) return;
    const update = () => {
      const { scrollHeight, scrollTop, clientHeight } = el;
      if (scrollHeight <= clientHeight) {
        setThumb({ top: 0, height: 0 });
        return;
      }
      const available = clientHeight - SC_GUTTER * 2;
      const height = Math.max(24, available * (clientHeight / scrollHeight));
      const top =
        SC_GUTTER +
        (scrollTop / (scrollHeight - clientHeight)) * (available - height);
      setThumb({ top, height });
    };
    const onScroll = () => {
      update();
      setScrolling(true);
      clearTimeout(hideTimer.current);
      hideTimer.current = setTimeout(() => setScrolling(false), 400);
    };
    update();
    el.addEventListener("scroll", onScroll, { passive: true });
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => {
      el.removeEventListener("scroll", onScroll);
      ro.disconnect();
    };
  }, [items.length, loading]);

  const useCompactLegend = rightWidth > 0 && rightWidth < 420;
  const legendGrid = (
    <div
      ref={scRef}
      className="h-full min-w-0 no-native-scrollbar"
      style={{
        overflowY: (isTouch || hovering) && !loading ? "auto" : "hidden",
        paddingRight: 8,
        WebkitOverflowScrolling: "touch",
        touchAction: "pan-y",
      }}
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      onTouchStart={() => setHovering(true)}
      onTouchEnd={() => setHovering(false)}
    >
      <div
        className="grid gap-x-1.5 gap-y-1.5 min-w-0"
        style={{
          gridTemplateColumns: useCompactLegend
            ? "repeat(auto-fill, minmax(140px, 1fr))"
            : "1fr", 
        }}
      >
        {items.map((d, i) => {
          const isActive = level === 1 && activeSub && d.name === activeSub;
          return (
            <button
              key={`${d.name}-${i}`}
              onClick={() =>
                level === 0 ? clickDimension(d.name) : clickSubtheme(d.name)
              }
              className={`flex items-center gap-1 rounded-lg border px-2 py-1.5 shadow-sm text-left hover:shadow transition w-full min-w-0
                          ${
                            isActive
                              ? "bg-yellow-50 border-yellow-300"
                              : "bg-white/92 border-[#e9e4da]"
                          }`}
              style={{ cursor: "pointer", maxWidth: "100%" }}
              title={d.name}
            >
              <span
                className="inline-block w-2 h-2 rounded-full shrink-0"
                style={{ background: d.color }}
              />
              <span className="text-[11px] text-neutral-700 truncate flex-1 min-w-0">
                {d.name}
              </span>
              <span className="ml-1 text-[11px] font-semibold tabular-nums text-neutral-800 shrink-0">
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
      ref={rootRef}
      className={`rounded-2xl border border-[#d6d0c5] shadow-sm px-4 py-3 overflow-hidden ${className}`}
      style={{
        width: "100%",
        background: "rgba(255,255,255,0.7)",
        height: heightPx,
        "--card-h": `${heightPx}px`,
      }}
    >
      <style>{`
        .no-native-scrollbar { scrollbar-width: none; -ms-overflow-style: none; }
        .no-native-scrollbar::-webkit-scrollbar { width: 0; height: 0; }
      `}</style>

      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[15px] font-semibold text-neutral-800">
          {title}
          {level === 1 ? ` · ${focusDim}` : ""}
        </h3>
        <div className="text-[12px] text-neutral-500">
          {year ? `Year: ${year}` : "all years"}
          {month ? `, month: ${month}` : ""}
        </div>
      </div>

      <div
        className="flex items-stretch"
        style={{ gap: gapPx, height: "calc(var(--card-h) - 72px)" }}
      >
        <div
          className="relative shrink-0"
          style={{ width: leftSize, height: "100%", overflow: "hidden" }}
        >
          {loading ? (
            <div className="w-full h-full flex items-center justify-center text-[12px] text-neutral-500">
              Loading…
            </div>
          ) : items.length === 0 ? (
            <EmptyState style={{ width: "100%", height: "100%" }}>
              {selectedSubtheme
                ? `No data for "${selectedSubtheme}".`
                : selectedDimension
                ? `No data under "${selectedDimension}".`
                : `No data${year ? ` · ${year}` : ""}${
                    month ? `-${month}` : ""
                  }.`}
            </EmptyState>
          ) : (
            <svg width={leftSize} height={"100%"}>
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
                  const x = cx + rMax * Math.cos(a),
                    y = cy + rMax * Math.sin(a);
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
                      fontSize="12"
                      fill="#333"
                      style={{ pointerEvents: "none" }}
                    >
                      {d.value}
                    </text>
                  );
                })}
              </g>

              {level === 1 && items.length > 0 && !loading && (
                <foreignObject x="8" y={H - 32} width="24" height="24">
                  <button
                    onClick={backToTop}
                    className="w-6 rounded-md border border-neutral-300/70 hover:bg-neutral-50 text-[14px]"
                    title="Back"
                    style={{ cursor: "pointer" }}
                  >
                    ⮌
                  </button>
                </foreignObject>
              )}
            </svg>
          )}
        </div>

        <div className="relative h-full min-w-0 flex-1">
          {loading ? (
            <div className="h-full flex items-center justify-center text-[12px] text-neutral-500">
              Loading…
            </div>
          ) : items.length === 0 ? (
            <EmptyState style={{ width: "100%", height: "100%" }}>
              Try another month/dimension.
            </EmptyState>
          ) : (
            legendGrid
          )}

          {!loading && items.length > 0 && thumb.height > 0 && !isTouch && (
            <div
              className="pointer-events-none absolute top-0 right-1 h-full transition-opacity duration-150"
              style={{
                width: SCROLL_WIDTH,
                opacity: hovering || scrolling ? 1 : 0,
              }}
            >
              <div
                className="absolute right-0 top-0 h-full rounded-full"
                style={{
                  width: SCROLL_WIDTH,
                  background: SC_TRACK_COLOR,
                  boxShadow: "inset 0 0 1px rgba(255,255,255,0.04)",
                }}
              />
              <div
                className="absolute right-0 rounded-full"
                style={{
                  width: SCROLL_WIDTH,
                  top: thumb.top,
                  height: thumb.height,
                  background: SC_THUMB_COLOR,
                  boxShadow: `inset 0 0 0 1px ${SC_THUMB_BORDER}`,
                }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function heightPxInner(total) {
  const headerAndPadding = 72;
  return Math.max(120, total - headerAndPadding);
}
