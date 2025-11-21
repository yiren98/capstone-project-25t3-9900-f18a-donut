import React, { useEffect, useRef, useState } from "react";

// Custom scrollbar constants for the legend panel
const SCROLL_WIDTH = 4;
const SC_TRACK_COLOR = "rgb(237, 229, 213)";
const SC_THUMB_COLOR = "rgba(238, 227, 212, 0.88)";
const SC_THUMB_BORDER = "rgba(0,0,0,0.35)";
const SC_GUTTER = 6;

export default function DimensionRadarLegend({
  items,
  loading,
  level,
  activeSub,
  useCompact,
  onClickDimension,
  onClickSubtheme,
}) {
  // Scroll container & scrollbar state
  const scRef = useRef(null);
  const [hovering, setHovering] = useState(false);
  const [scrolling, setScrolling] = useState(false);
  const [thumb, setThumb] = useState({ top: 0, height: 0 });
  const hideTimer = useRef(null);

  // Touch detection so we do not rely on hover on mobile devices
  const [isTouch, setIsTouch] = useState(false);
  useEffect(() => {
    const val =
      typeof window !== "undefined" &&
      ("ontouchstart" in window ||
        navigator.maxTouchPoints > 0 ||
        navigator.msMaxTouchPoints > 0);
    setIsTouch(Boolean(val));
  }, []);

  // Keep custom scrollbar thumb in sync with the legend scroll container
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

  return (
    <div className="relative h-full min-w-0">
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
            // In compact mode: wrap into multiple columns; otherwise simple 1-column list
            gridTemplateColumns: useCompact
              ? "repeat(auto-fill, minmax(115px, 1fr))"
              : "1fr",
          }}
        >
          {items.map((d, i) => {
            const isActive = level === 1 && activeSub && d.name === activeSub;
            const handleClick = () => {
              if (level === 0) onClickDimension?.(d.name);
              else onClickSubtheme?.(d.name);
            };

            return (
              <button
                key={`${d.name}-${i}`}
                onClick={handleClick}
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

      {/* Custom scrollbar overlay for the legend */}
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
  );
}
