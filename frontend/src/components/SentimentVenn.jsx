import React, { useEffect, useMemo, useState } from "react";
import { getSentimentStats } from "../api";

const TITLE_CLS = "text-[15px] font-semibold text-neutral-800";
const VALUE_CLS = "text-[18px] font-semibold tabular-nums";
const SUBLABEL_CLS = "text-[12px] -mt-0.5";

// Simple reusable empty state container
const EmptyState = ({ children, style }) => (
  <div
    className="flex items-center justify-center text-neutral-500 text-[16px] rounded-xl border"
    style={{ border: "1px solid #fefefeff", ...style }}
  >
    {children || "No results."}
  </div>
);

export default function SentimentVenn({
  className = "",
  title = "Sentiment Analysis Statistics",
  year,
  month,
  dimension = "",
  subtheme = "",
  height = 260, // outer card height
}) {
  // Positive / negative counts returned from the backend
  const [pos, setPos] = useState(0);
  const [neg, setNeg] = useState(0);
  // Simple "fade in" phase flag for the main visual
  const [phase, setPhase] = useState(1);

  // Load sentiment stats whenever filters change
  useEffect(() => {
    let alive = true;
    setPhase(0); // briefly hide chart before animating in

    (async () => {
      try {
        const data = await getSentimentStats({ year, month, dimension, subtheme });
        if (!alive) return;
        setPos(Number(data.positive || 0));
        setNeg(Number(data.negative || 0));
      } catch {
        if (!alive) return;
        setPos(0);
        setNeg(0);
      } finally {
        // Use RAF to avoid layout flicker when the numbers update
        requestAnimationFrame(() => setPhase(1));
      }
    })();

    return () => {
      alive = false;
    };
  }, [year, month, dimension, subtheme]);

  // Compute bubble sizes based on positive / negative ratio
  const sizes = useMemo(() => {
    const p = Math.max(0, pos);
    const n = Math.max(0, neg);
    const total = Math.max(1, p + n);
    const pr = p / total;
    const nr = n / total;

    const minD = 70;
    const maxD = 200;

    // Non-linear scaling so extreme ratios don't completely explode/shrink
    const easing = (r) => minD + (maxD - minD) * Math.pow(r, 0.65);

    return { dPos: easing(pr), dNeg: easing(nr) };
  }, [pos, neg]);

  // Visual tweaks to move circles closer together / squash slightly
  const GAP_PUSH = 1;
  const SQUEEZE = 1;
  const empty = pos <= 0 && neg <= 0;

  // Build a context-aware "no data" message based on current filters
  const buildMsg = () => {
    const ym = [year, month].filter(Boolean).join("-");
    if (subtheme) return `No sentiment data for "${subtheme}"${ym ? ` · ${ym}` : ""}.`;
    if (dimension) return `No sentiment data under "${dimension}"${ym ? ` · ${ym}` : ""}.`;
    return `No sentiment data${ym ? ` · ${ym}` : ""}.`;
  };

  return (
    <div
      className={`rounded-2xl border border-[#d6d0c5] shadow-sm px-4 py-3 ${className}`}
      style={{
        width: "100%",
        height,
        background: "rgba(255,255,255,0.7)",
        backdropFilter: "blur(6px)",
        WebkitBackdropFilter: "blur(6px)",
      }}
    >
      {/* Header */}
      <div className="flex justify-between items-center mb-2">
        <h3 className={TITLE_CLS}>{title}</h3>
      </div>

      {/* Main bubble / venn visual */}
      <div
        className="relative w-full"
        style={{
          height: height - 92, // leave room for header + legend
          transition: "opacity 260ms ease",
          opacity: phase,
        }}
      >
        {empty ? (
          // No data => show friendly empty state
          <EmptyState style={{ width: "100%", height: "100%" }}>
            {buildMsg()}
          </EmptyState>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="relative flex items-center">
              {/* Soft glow strip between the two circles when both exist */}
              {pos > 0 && neg > 0 && (
                <div
                  aria-hidden
                  className="absolute left-1/2 -translate-x-1/2"
                  style={{
                    width: 28,
                    height: Math.max(sizes.dPos, sizes.dNeg) * 0.9,
                    borderRadius: 999,
                    background:
                      "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.28) 48%, rgba(255,255,255,0) 100%)",
                    filter: "blur(6px)",
                  }}
                />
              )}

              {/* Positive bubble */}
              {pos > 0 && (
                <div
                  className="relative rounded-full will-change-transform"
                  style={{
                    width: sizes.dPos,
                    height: sizes.dPos,
                    marginRight: -GAP_PUSH,
                    background:
                      "radial-gradient(closest-side, #F6C543 70%, rgba(246,197,67,0.75) 85%, rgba(246,197,67,0.06) 100%)",
                    filter: "blur(0.25px)",
                    boxShadow:
                      "0 0 0px rgba(246,197,67,0.32), 0 0 60px rgba(246,197,67,0.18)",
                    transform: `scaleX(${SQUEEZE})`,
                  }}
                >
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-neutral-900">
                    <div className={VALUE_CLS}>{pos}</div>
                    <div className={SUBLABEL_CLS}>positive</div>
                  </div>
                </div>
              )}

              {/* Negative bubble */}
              {neg > 0 && (
                <div
                  className="relative rounded-full will-change-transform"
                  style={{
                    width: sizes.dNeg,
                    height: sizes.dNeg,
                    marginLeft: -GAP_PUSH,
                    background:
                      "radial-gradient(closest-side, #ef4444 68%, rgba(234, 91, 91, 0.72) 85%, rgba(239,68,68,0.06) 100%)",
                    filter: "blur(0.25px)",
                    boxShadow:
                      "0 0 0px rgba(239,68,68,0.32), 0 0 60px rgba(239,68,68,0.18)",
                    transform: `scaleX(${SQUEEZE})`,
                  }}
                >
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-neutral-900">
                    <div className={VALUE_CLS}>{neg}</div>
                    <div className={SUBLABEL_CLS}>negative</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Small legend pills at the bottom */}
      <div className="mt-1 flex items-center justify-center gap-7 text-[13px]">
        {!empty && pos > 0 && (
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-neutral-200">
            <span
              className="h-2.5 w-2.5 rounded-full inline-block"
              style={{ background: "#F6C543" }}
            />
            <span className="font-semibold tabular-nums">{pos}</span>
            <span className="text-neutral-600">Positive</span>
          </span>
        )}
        {!empty && neg > 0 && (
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-neutral-200">
            <span
              className="h-2.5 w-2.5 rounded-full inline-block"
              style={{ background: "#ef4444" }}
            />
            <span className="font-semibold tabular-nums">{neg}</span>
            <span className="text-neutral-600">Negative</span>
          </span>
        )}
      </div>
    </div>
  );
}
