import React, { useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { getCAIndex, getCASubthemes } from "../api";

const DOT = {
  Collaboration:"#f4bf2a", Performance:"#63b6a5", Execution:"#6a7be6", Agility:"#b78de3",
  "Ethical Responsibility":"#f1a57b", Accountability:"#6db0ff", "Customer Orientation":"#68c06f",
  Respect:"#e5a08a", Integrity:"#f1c74a", Learning:"#79c7b6", Innovation:"#6f73d8", "Well-being":"#c99bdd",
};

const TAG_BG = "#e8e8e842";   
const TAG_TEXT = "#b6b4b1ff";  
const SELECT_BG = "#F6C945";    
const SELECT_TEXT = "#111111";  
const SELECT_RING = "#D6B300"; 

function hashToHsl(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  const hue = h % 360;
  const sat = 58;
  const light = 52;
  return `hsl(${hue} ${sat}% ${light}%)`;
}

const Pill = ({ dot, text, number, onClick, titleText, selected = false }) => {
  const bg = selected ? SELECT_BG : TAG_BG;
  const fg = selected ? SELECT_TEXT : TAG_TEXT;
  return (
    <button
      onClick={onClick}
      title={titleText || text}
      className={clsx(
        "w-full px-3 py-1.5 rounded-full",
        "border transition-all duration-150",
        selected ? "border-[var(--ring)] shadow-sm" : "border-[#e3d5wa]",
        "hover:brightness-[.98] active:brightness-95",
        "cursor-pointer flex items-center justify-between"
      )}
      style={{ "--ring": SELECT_RING, background: bg, color: fg }}
    >
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <span
          className="h-2 w-2 rounded-full shrink-0"
          style={{ background: selected ? "#111" : (dot || "#222") }}
        />
        <span className="text-[13px] font-medium overflow-hidden text-ellipsis whitespace-nowrap">
          {text}
        </span>
      </div>
      {number !== undefined && (
        <span className="text-[13px] font-semibold pl-2 shrink-0" style={{ color: fg }}>
          {number}
        </span>
      )}
    </button>
  );
};

export default function DimensionFilterPanel({
  className = "",
  onSelect, // (dimension, subtheme, file) => void
}) {
  const [step, setStep] = useState(0); 
  const [dims, setDims] = useState([]);
  const [cntMap, setCntMap] = useState({});
  const [loading, setLoading] = useState(false);

  const [dimension, setDimension] = useState("");
  const [subs, setSubs] = useState([]);
  const [selectedSubtheme, setSelectedSubtheme] = useState(""); 


  const [viewKey, setViewKey] = useState(0);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    getCAIndex()
      .then((idx) => {
        if (!alive) return;
        setDims(idx?.dimensions || []);
        setCntMap(idx?.subtheme_count_by_dim || {});
      })
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (step !== 1 || !dimension) return;
    let alive = true;
    setLoading(true);
    getCASubthemes(dimension)
      .then((res) => {
        if (!alive) return;
        const list = (res?.subthemes || []).map(x => ({
          name: x.name,
          file: x.file || "",
        }));
        setSubs(list);
      })
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [step, dimension]);

  const subthemes = useMemo(() => (step === 1 ? subs : []), [step, subs]);

  return (
    <>

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
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-base font-semibold">Dimension and Subtheme Filter</h2>

   
          {step === 1 && (
            <button
              className="text-xs underline text-neutral-300 hover:text-white"
              onClick={() => {
                setStep(0);
                setDimension("");
                setSubs([]);
                setSelectedSubtheme("");
                setViewKey(k => k + 1);
                onSelect?.("", "", "");
              }}
            >
              Back
            </button>
          )}
        </div>

        <p className="text-neutral-300 text-[13px] mb-2 leading-snug">
          {step === 0
            ? "Choose a cultural dimension to drill into its subthemes."
            : `Select a subtheme under “${dimension}”. (click again to show the dimension summary)`}
        </p>


        <div
          key={viewKey}
          className={clsx(
            "flex-1 grid grid-cols-1 gap-2 overflow-y-auto pr-1 ys-fade-swap",
            "ys-hide-scrollbar",
            "[-webkit-overflow-scrolling:touch]"
          )}
          style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
        >
          {(step === 0 ? dims : subthemes).map((item) => {
            const text = step === 0 ? item : item.name;
            const num  = step === 0 ? cntMap[item] : undefined;
            const dot  = step === 0 ? (DOT[text] || "#bbb") : hashToHsl(text);
            const selected = step === 1 && selectedSubtheme === text;

            return (
              <Pill
                key={text}
                dot={dot}
                text={text}
                number={num}
                selected={selected}
                titleText={text}
                onClick={() => {
                  if (step === 0) {
           
                    setDimension(text);
                    setSelectedSubtheme("");  
                    setStep(1);
                    setViewKey(k => k + 1);
                    onSelect?.(text, "", "");  
                  } else {
           
                    if (selected) {
           
                      setSelectedSubtheme("");
                      onSelect?.(dimension, "", ""); 
                    } else {
                  
                      setSelectedSubtheme(text);
                      onSelect?.(dimension, text, (item.file || ""));
                    }
                  }
                }}
              />
            );
          })}
        </div>

        {loading && <div className="pt-2 text=[11px] text-neutral-400">Loading…</div>}

        {step === 0 && !loading && (
          <div className="pt-2 text-[11px] text-neutral-400">{dims.length} dimensions available</div>
        )}
      </div>
    </>
  );
}
