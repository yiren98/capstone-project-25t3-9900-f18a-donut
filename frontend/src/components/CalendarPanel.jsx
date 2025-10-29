// src/components/CalendarPanel.jsx
import React, { useMemo, useState } from "react";

export default function CalendarPanel({
  className = "",
  year: yearProp,
  monthsWithData = [1, 2, 4, 5, 7, 8, 9, 10],
  defaultSelectedMonth,
  onYearChange,
  onMonthSelect,
  sentimentScore = 62,
  sentimentDelta = +7,
}) {
  const now = new Date();
  const [year, setYear] = useState(yearProp ?? now.getFullYear());
  const [selected, setSelected] = useState(defaultSelectedMonth ?? now.getMonth() + 1);

  const months = useMemo(
    () => ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
    []
  );

  const goPrevYear = () => {
    const y = year - 1;
    setYear(y);
    onYearChange?.(y);
  };

  const goNextYear = () => {
    const y = year + 1;
    setYear(y);
    onYearChange?.(y);
  };

  const MonthChip = ({ mIndex }) => {
    const monthNum = mIndex + 1;
    const isThisYear = year === now.getFullYear();
    const isToday = isThisYear && monthNum === now.getMonth() + 1;
    const hasData = monthsWithData.includes(monthNum);
    const isSelected = monthNum === selected;

    let base =
      "h-12 w-16 md:h-13 md:w-13 rounded-full flex items-center justify-center text-[13px] md:text-[16px] select-none transition-all";
    let tone = "text-white/80 hover:bg-white/10";

    if (isToday) {
      tone =
        "bg-[#F6C543] text-black font-semibold shadow-[0_4px_16px_rgba(246,197,67,0.35)]";
    } else if (hasData) {
      tone = "bg-white/10 text-white/90 shadow-[0_6px_16px_rgba(0,0,0,0.25)]";
    } else if (isSelected) {
      tone = "ring-2 ring-[#F6C543] text-white/90";
    }

    return (
      <button
        type="button"
        className={`${base} ${tone}`}
        onClick={() => {
          setSelected(monthNum);
          onMonthSelect?.(year, monthNum);
        }}
      >
        {months[mIndex]}
      </button>
    );
  };

  // === Sentiment Bar ===
  const clamp = (v, min, max) => Math.max(min, Math.min(max, v));
  const score = clamp(sentimentScore, 0, 100);
  const isUp = sentimentDelta >= 0;

  return (
    <section className={`h-full rounded-2xl bg-[#1f1f22] text-white p-6 flex flex-col shadow-sm ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[15px] md:text-[16px] font-semibold">View Data by Month</h3>
        <div className="flex items-center gap-2 text-white/80">
          <button aria-label="Previous year" onClick={goPrevYear} className="p-1 rounded hover:bg-white/10">
            <svg width="18" height="18" viewBox="0 0 24 24" className="opacity-80">
              <path d="M15 18l-6-6 6-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
          <span className="min-w-[64px] text-center text-sm md:text-base">{year}</span>
          <button aria-label="Next year" onClick={goNextYear} className="p-1 rounded hover:bg-white/10">
            <svg width="18" height="18" viewBox="0 0 24 24" className="opacity-80">
              <path d="M9 6l6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      </div>

      {/* Months grid */}
      <div className="grid grid-cols-6 gap-x-4 gap-y-6 mt-2 mb-6 place-items-center">
        {months.map((_, idx) => <MonthChip key={idx} mIndex={idx} />)}
      </div>

      {/* Sentiment Balance Index */}
      <div className="mt-1 mb-5">
        <div className="flex items-end justify-between mb-2">
          <div className="text-white/90 text-sm md:text-[15px] font-medium">Sentiment Balance Index</div>
        </div>

        <div className="relative h-3 rounded-full bg-white/10 overflow-hidden">
          <div
            className="absolute inset-y-0 left-0 bg-gradient-to-r from-yellow-300 via-yellow-400 to-yellow-600"
            style={{ width: `${score}%` }}
          />
          <div className="absolute inset-y-0 left-1/2 w-[2px] bg-white/25" />
        </div>

        <div className="mt-2 flex items-center justify-between text-xs md:text-sm">
          <div className="text-white/80">
            Current: <span className="font-semibold text-white">{score}</span>
          </div>
          <div className="flex items-center gap-1 text-[#F6C543]">
            <svg viewBox="0 0 24 24" width="14" height="14" className={isUp ? "" : "rotate-180"} fill="currentColor">
              <path d="M12 4l6 8h-4v8H10v-8H6l6-8z" />
            </svg>
            <span className="font-medium">
              {isUp ? "Up" : "Down"} {Math.abs(sentimentDelta)} pts vs last month
            </span>
          </div>
        </div>
      </div>

      <div className="mt-auto pt-2 flex flex-wrap items-center gap-x-5 gap-y-2 text-[12px] md:text-[13px] text-white/70">
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-[#F6C543]" />
          Current month
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-white/25" />
          Months with data
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full ring-1 ring-[#F6C543]" />
          Selected month
        </span>
      </div>
    </section>
  );
}
