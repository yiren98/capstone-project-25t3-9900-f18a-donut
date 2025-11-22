import React, { useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { getCAIndex, getCASubthemes } from "../api";

// Tag colors for normal vs selected state
const TAG_BG = "#e8e8e842";
const TAG_TEXT = "#b6b4b1ff";
const SELECT_BG = "#F6C945";
const SELECT_TEXT = "#111111";
const SELECT_RING = "#D6B300";

// Small reusable pill component for both dimensions and subthemes
const Pill = ({ text, onClick, titleText, selected = false }) => {
  const bg = selected ? SELECT_BG : TAG_BG;
  const fg = selected ? SELECT_TEXT : TAG_TEXT;
  return (
    <button
      onClick={onClick}
      title={titleText || text}
      className={clsx(
        "w-full px-5 py-2 rounded-full",
        "border transition-all duration-150",
        selected ? "border-[var(--ring)] shadow-sm" : "border-[#e3d5wa]",
        "hover:brightness-[.98] active:brightness-95",
        "cursor-pointer flex items-center"
      )}
      style={{ "--ring": SELECT_RING, background: bg, color: fg }}
    >
      <span className="text-[13px] font-medium overflow-hidden text-ellipsis whitespace-nowrap">
        {text}
      </span>
    </button>
  );
};

export default function DimensionFilterPanel({
  className = "",
  onSelect, // (dimension, subtheme, file) => void
}) {
  // step 0: choose dimension; step 1: choose subtheme
  const [step, setStep] = useState(0);
  // List of dimensions fetched from the backend
  const [dims, setDims] = useState([]);
  const [loading, setLoading] = useState(false);

  // Current selected dimension name
  const [dimension, setDimension] = useState("");
  // Subthemes available under the selected dimension
  const [subs, setSubs] = useState([]);
  // Currently selected subtheme name (for highlight and back behavior)
  const [selectedSubtheme, setSelectedSubtheme] = useState("");

  // Used to force a re-mount of the scrollable list for a quick fade transition
  const [viewKey, setViewKey] = useState(0);

  // Initial load: fetch all dimensions once
  useEffect(() => {
    let alive = true;
    setLoading(true);
    getCAIndex()
      .then((idx) => {
        if (!alive) return;
        setDims(idx?.dimensions || []);
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  // When entering step 1 and a dimension is selected, fetch its subthemes
  useEffect(() => {
    if (step !== 1 || !dimension) return;
    let alive = true;
    setLoading(true);
    getCASubthemes(dimension)
      .then((res) => {
        if (!alive) return;
        const list = (res?.subthemes || []).map((x) => ({
          name: x.name,
          file: x.file || "",
        }));
        setSubs(list);
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [step, dimension]);

  // Only expose subthemes when we are in step 1
  const subthemes = useMemo(() => (step === 1 ? subs : []), [step, subs]);

  return (
    <>
      {/* Local styles for scroll hiding + fade-in animation */}
      <style>{`
        .ys-hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        .ys-hide-scrollbar::-webkit-scrollbar { display: none; width: 0; height: 0; }
        .ys-fade-swap { animation: ysFadeIn 200ms cubic-bezier(0.22,1,0.36,1); }
        @keyframes ysFadeIn { from {opacity:0; transform: translateY(6px);} to {opacity:1; transform: translateY(0);} }
        @media (prefers-reduced-motion: reduce) { .ys-fade-swap { animation: none; } }
      `}</style>

      <div
        className={clsx(
          "rounded-2xl border shadow-sm px-5 py-4",
          "bg-black text-white border-[#333] flex flex-col h-[400px]",
          className
        )}
      >
        {/* Header row: title + back button when in subtheme view */}
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-base font-semibold">
            Dimension and Subtheme Filter (2023-2025)
          </h2>

          {step === 1 && (
            <button
              className="text-xs underline text-neutral-300 hover:text-white"
              onClick={() => {
                // Reset back to dimension list
                setStep(0);
                setDimension("");
                setSubs([]);
                setSelectedSubtheme("");
                setViewKey((k) => k + 1);
                // Notify parent that filters are cleared
                onSelect?.("", "", "");
              }}
            >
              Back
            </button>
          )}
        </div>

        {/* Helper text under the title */}
        <p className="text-neutral-300 text-[13px] mb-2 leading-snug">
          {step === 0
            ? "Choose a cultural dimension to drill into its subthemes."
            : `Select a subtheme under “${dimension}”. (click again to show the dimension summary)`}
        </p>

        {/* Scrollable list of pills (dimensions or subthemes depending on step) */}
        <div
          key={viewKey}
          className={clsx(
            "flex-1 grid grid-cols-1 gap-1.5 overflow-y-auto pr-1 ys-fade-swap ys-hide-scrollbar",
            "content-start items-start auto-rows-max"
          )}
          style={{
            scrollbarWidth: "none",
            msOverflowStyle: "none",
            gridAutoRows: "max-content",
            alignContent: "start",
            alignItems: "start",
          }}
        >
          {(step === 0 ? dims : subthemes).map((item) => {
            const text = step === 0 ? item : item.name;
            const selected = step === 1 && selectedSubtheme === text;

            return (
              <Pill
                key={text}
                text={text}
                selected={selected}
                titleText={text}
                onClick={() => {
                  if (step === 0) {
                    // Dimension selected: move to subtheme view
                    setDimension(text);
                    setSelectedSubtheme("");
                    setStep(1);
                    setViewKey((k) => k + 1);
                    // Inform parent that a dimension was chosen, but no subtheme yet
                    onSelect?.(text, "", "");
                  } else {
                    // In subtheme view: toggle selection
                    if (selected) {
                      // Clicking again clears subtheme filter, keeps dimension
                      setSelectedSubtheme("");
                      onSelect?.(dimension, "", "");
                    } else {
                      // New subtheme selected
                      setSelectedSubtheme(text);
                      onSelect?.(dimension, text, item.file || "");
                    }
                  }
                }}
              />
            );
          })}
        </div>

        {/* Loading indicator at the bottom */}
        {loading && (
          <div className="pt-2 text=[11px] text-neutral-400">Loading…</div>
        )}

        {/* Simple footer summary when showing dimensions and not loading */}
        {step === 0 && !loading && (
          <div className="pt-2 text-[11px] text-neutral-400">
            {dims.length} dimensions available
          </div>
        )}
      </div>
    </>
  );
}
