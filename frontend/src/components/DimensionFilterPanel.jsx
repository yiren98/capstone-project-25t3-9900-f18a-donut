
import React, { useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { getCAIndex, getCASubthemes } from "../api";


const DOT = {
  Collaboration:"#f4bf2a", Performance:"#63b6a5", Execution:"#6a7be6", Agility:"#b78de3",
  "Ethical Responsibility":"#f1a57b", Accountability:"#6db0ff", "Customer Orientation":"#68c06f",
  Respect:"#e5a08a", Integrity:"#f1c74a", Learning:"#79c7b6", Innovation:"#6f73d8", "Well-being":"#c99bdd",
};


function hashToHsl(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  const hue = h % 360;
  const sat = 58; 
  const light = 52; 
  return `hsl(${hue} ${sat}% ${light}%)`;
}

const Pill = ({ dot, text, number, onClick, titleText }) => (
  <button
    onClick={onClick}
    title={titleText || text} 
    className={clsx(
      "w-full px-4 py-2 rounded-full bg-white border border-[#e8e2d8]",
      "hover:bg-black/5 cursor-pointer transition",
      "flex items-center justify-between"
    )}
  >
    <div className="flex items-center gap-2 min-w-0 flex-1">
      <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ background: dot || "#bbb" }} />

      <span className="text-[15px] text-neutral-800 overflow-hidden text-ellipsis whitespace-nowrap">
        {text}
      </span>
    </div>
    {number !== undefined && (
      <span className="text-[15px] font-medium text-neutral-700 pl-2 shrink-0">{number}</span>
    )}
  </button>
);

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
    <div
      className={clsx(
        "rounded-2xl border border-[#d6d0c5] shadow-sm px-6 py-5",
        "bg-[rgb(246,243,239)] flex flex-col",
        className
      )}
    >
      <div className="flex justify-between mb-3">
        <h2 className="text-lg font-semibold">Dimension and Subtheme Filter</h2>
        {step === 1 && (
          <button
            className="text-sm underline text-neutral-600 hover:text-neutral-900"
            onClick={() => {
              setStep(0);
              setDimension("");
              setSubs([]);
              onSelect?.("", "", ""); 
            }}
          >
            Back
          </button>
        )}
      </div>

      <p className="text-neutral-600 text-sm mb-3">
        {step === 0
          ? "Choose a cultural dimension to drill into its subthemes."
          : `Select a subtheme under “${dimension}”.`}
      </p>


      <div className="grid grid-cols-1 gap-2 overflow-y-auto pr-1" style={{ maxHeight: "calc(100% - 84px)" }}>
        {(step === 0 ? dims : subthemes).map((item) => {
          const text = step === 0 ? item : item.name;
          const num  = step === 0 ? cntMap[item] : undefined;

          const dot  = step === 0 ? (DOT[text] || "#bbb") : hashToHsl(text);

          return (
            <Pill
              key={text}
              dot={dot}
              text={text}
              number={num}
              titleText={text} 
              onClick={() => {
                if (step === 0) {

                  setDimension(text);
                  setStep(1);
                  onSelect?.(text, "", "");
                } else {

                  onSelect?.(dimension, item.name, item.file || "");
                }
              }}
            />
          );
        })}
      </div>

      {loading && <div className="pt-3 text-xs text-neutral-500">Loading…</div>}

      {step === 0 && !loading && (
        <div className="pt-3 text-xs text-neutral-500">{dims.length} dimensions available</div>
      )}
    </div>
  );
}
