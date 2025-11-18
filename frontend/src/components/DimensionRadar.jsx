import React, {
  useEffect,
  useMemo,
  useState,
  useCallback,
  useRef,
} from "react";
import { getDimensionCounts, getSubthemeCounts } from "../api";
import DimensionRadarChart from "./DimensionRadarChart";
import DimensionRadarLegend from "./DimensionRadarLegend";

// Simple reusable empty state container for the chart / legend
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
  leftMax = 300, // upper bound for the left (radar) width
  rightMin = 220, // minimum width reserved for the legend on the right
  gapPx = 12, // gap between radar and legend columns
  heightPx = 260, // overall card height
}) {
  // level 0: dimension-level view, level 1: subtheme-level view
  const [level, setLevel] = useState(0);
  // Name of the currently focused dimension (when level === 1)
  const [focusDim, setFocusDim] = useState("");
  // Data items to be rendered as sectors (dimensions or subthemes)
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  // Currently selected subtheme name (for highlighting in legend)
  const [activeSub, setActiveSub] = useState("");

  // Root container reference for layout calculations
  const rootRef = useRef(null);
  // Calculated left column width (radar) based on available space
  const [leftSize, setLeftSize] = useState(leftMax);
  // Calculated legend width on the right (for responsive legend layout)
  const [rightWidth, setRightWidth] = useState(0);

  // Resize observer to keep left/right split responsive
  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;

    const ro = new ResizeObserver(() => {
      const W = el.clientWidth || 0;
      // Limit left side so the right legend always has at least rightMin
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

  // Fixed palette – each item cycles through these colours
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

  // Fetch dimension or subtheme counts depending on current level
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      if (level === 0) {
        // Level 0: fetch all dimension counts for the given year/month
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
        // Level 1: fetch subtheme counts under the currently focused dimension
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

  // Refetch when the level/dimension/year/month change
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Sync internal view state with external selectedDimension / selectedSubtheme
  useEffect(() => {
    if (!selectedDimension) {
      // Reset to top-level view if nothing is selected
      setLevel(0);
      setFocusDim("");
      setActiveSub("");
      return;
    }
    // When a dimension is selected externally, move to subtheme view
    setLevel(1);
    setFocusDim(selectedDimension);
    setActiveSub(selectedSubtheme || "");
  }, [selectedDimension, selectedSubtheme]);

  // Click handler when a dimension arc / legend item is clicked (level 0 only)
  const handleDimensionClick = (dimName) => {
    if (level !== 0 && dimName !== focusDim) return;
    if (selectedDimension === dimName) {
      // Clicking the currently active dimension clears the filter
      onFilterChange?.({ dimension: "", subtheme: "" });
      setLevel(0);
      setFocusDim("");
      setActiveSub("");
    } else {
      // Focus on the chosen dimension and move into level 1
      onFilterChange?.({ dimension: dimName, subtheme: "" });
      setLevel(1);
      setFocusDim(dimName);
      setActiveSub("");
    }
  };

  // Click handler for subtheme arcs / legend items (toggle behaviour)
  const handleSubthemeClick = (subName) => {
    const next = activeSub === subName ? "" : subName;
    setActiveSub(next);
    onFilterChange?.({ dimension: focusDim, subtheme: next });
  };

  // Reset back to top-level dimension view
  const handleBackToTop = () => {
    setLevel(0);
    setFocusDim("");
    setActiveSub("");
    onFilterChange?.({ dimension: "", subtheme: "" });
  };

  // Use a more compact legend layout when the right side is narrow
  const useCompactLegend = rightWidth > 0 && rightWidth < 420;

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
      {/* Local style to hide native scrollbars for legend */}
      <style>{`
        .no-native-scrollbar { scrollbar-width: none; -ms-overflow-style: none; }
        .no-native-scrollbar::-webkit-scrollbar { width: 0; height: 0; }
      `}</style>

      {/* Header row: title + active dimension + date filters */}
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

      {/* Main layout: left radar + right legend */}
      <div
        className="flex items-stretch"
        style={{ gap: gapPx, height: "calc(var(--card-h) - 72px)" }}
      >
        {/* Radar panel (left) */}
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
            <DimensionRadarChart
              width={leftSize}
              heightPx={heightPx}
              items={items}
              level={level}
              onDimensionClick={handleDimensionClick}
              onSubthemeClick={handleSubthemeClick}
              onBackToTop={handleBackToTop}
            />
          )}
        </div>

        {/* Legend panel (right) */}
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
            <DimensionRadarLegend
              items={items}
              loading={loading}
              level={level}
              activeSub={activeSub}
              useCompact={useCompactLegend}
              onClickDimension={handleDimensionClick}
              onClickSubtheme={handleSubthemeClick}
            />
          )}
        </div>
      </div>
    </div>
  );
}
