// src/components/DimensionFilterPanel.jsx
import React, { useMemo, useState } from "react";
import clsx from "clsx";

const DIM_ORDER = [
  "Collaboration","Performance","Execution","Agility","Ethical Responsibility",
  "Accountability","Customer Orientation","Respect","Integrity","Learning",
  "Innovation","Well-being",
];

const DEFAULT_COUNTS = {
  Collaboration:27, Performance:27, Execution:23, Agility:21,
  "Ethical Responsibility":21, Accountability:19, "Customer Orientation":12,
  Respect:12, Integrity:10, Learning:6, Innovation:3, "Well-being":3,
};

const DOT = {
  Collaboration:"#f4bf2a",
  Performance:"#63b6a5",
  Execution:"#6a7be6",
  Agility:"#b78de3",
  "Ethical Responsibility":"#f1a57b",
  Accountability:"#6db0ff",
  "Customer Orientation":"#68c06f",
  Respect:"#e5a08a",
  Integrity:"#f1c74a",
  Learning:"#79c7b6",
  Innovation:"#6f73d8",
  "Well-being":"#c99bdd",
};

const SUBTHEMES = {
  Collaboration:["Cross-Team Sync","Knowledge Sharing","Decision Velocity"],
  Performance:["OKR Quality","Outcome Metrics","Efficiency"],
  Execution:["Goal Tracking","Roadmap Hygiene","Incident Response"],
  Agility:["Change Readiness","Delivery Flow","Time-to-Value"],
  "Ethical Responsibility":["ESG Reporting","Community Impact","Sourcing & Compliance"],
  Accountability:["Ownership Clarity","Escalation Path","Retros Outcome"],
  "Customer Orientation":["Feedback Loop","Service Quality","NPS Drivers"],
  Respect:["Inclusion","Workplace Civility","Policy Adherence"],
  Integrity:["Transparency","Data Privacy","Audit Readiness"],
  Learning:["L&D Hours","Mentorship","Postmortem Quality"],
  Innovation:["R&D Funding","Pilot Programs","Experimentation Rate"],
  "Well-being":["Workload Balance","Recognition","Flexibility"],
};

const Pill = ({ dot, text, number, onClick }) => (
  <button
    onClick={onClick}
    className="w-full flex items-center justify-between px-4 py-2 rounded-full bg-white border border-[#e8e2d8] hover:bg-black/[0.05] cursor-pointer transition"
  >
    <div className="flex items-center gap-2">
      <span className="h-2.5 w-2.5 rounded-full" style={{ background: dot }} />
      <span className="text-[15px] text-neutral-800">{text}</span>
    </div>
    {number !== undefined && (
      <span className="text-[15px] font-medium text-neutral-700">{number}</span>
    )}
  </button>
);

export default function DimensionFilterPanel({
  className = "",
  counts = DEFAULT_COUNTS,
  onSelect,                // (dimension, subtheme) => void
}) {
  const [step, setStep] = useState(0); 
  const [dimension, setDimension] = useState("");

  const subthemes = useMemo(() => (step === 1 ? SUBTHEMES[dimension] || [] : []), [step, dimension]);

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
            onClick={() => { setStep(0); setDimension(""); }}
          >
            Back
          </button>
        )}
      </div>

      <p className="text-neutral-600 text-sm mb-4">
        {step === 0 ? "Choose a cultural dimension to drill into its subthemes."
                    : `Select a subtheme under “${dimension}”.`}
      </p>

      <div className="grid grid-cols-1 gap-2">
        {(step === 0 ? DIM_ORDER : subthemes).map((item) => (
          <Pill
            key={item}
            dot={DOT[item] || "#bbb"}
            text={item}
            number={step === 0 ? counts[item] : undefined}
            onClick={() => {
              if (step === 0) { setDimension(item); setStep(1); }
              else onSelect?.(dimension, item);
            }}
          />
        ))}
      </div>

      {step === 0 && (
        <div className="pt-3 text-xs text-neutral-500">
          {DIM_ORDER.length} dimensions available
        </div>
      )}
    </div>
  );
}
