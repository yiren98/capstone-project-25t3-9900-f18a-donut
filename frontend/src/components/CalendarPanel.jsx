import React from "react";

export default function CalendarPanel({
  className = "",
  year,
  selectedMonth = null,
  monthsWithData = [],
  onMonthSelect,
  onYearChange,
  sbi = 0,
  delta = 0,
}) {
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const canClick = (n) => monthsWithData.includes(n);

  const goPrevYear = () => onYearChange?.(year - 1);
  const goNextYear = () => onYearChange?.(year + 1);

  const sbiClamped = Math.max(0, Math.min(100, Number.isFinite(sbi) ? sbi : 0));
  const deltaStr =
    `${delta > 0 ? "↑" : delta < 0 ? "↓" : "±"} ${Math.abs(Math.round(delta))} pts vs last month`;

  return (
    <div
      className={`rounded-2xl border border-[#d6d0c5] shadow-sm px-5 py-5 text-white ${className}`}
      style={{ background: "#141416", minHeight: 395 }}
    >

      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold">View Data by Month</h3>
        <div className="flex items-center gap-4 text-sm text-white/85">
          <button className="px-2 py-1 rounded hover:bg-white/10" onClick={goPrevYear}>{"<"}</button>
          <span className="tabular-nums">{year}</span>
          <button className="px-2 py-1 rounded hover:bg-white/10" onClick={goNextYear}>{">"}</button>
        </div>
      </div>


      <div className="grid grid-cols-6 gap-x-5 gap-y-6 mb-10">
        {months.map((m, idx) => {
          const n = idx + 1;
          const active = selectedMonth === n;
          const clickable = canClick(n);


          if (!clickable) {
            return (
              <div
                key={n}
                className="h-12 rounded-full flex items-center justify-center select-none bg-transparent text-white/35 border border-white/10"
                title={`${m} (no data)`}
              >
                {m}
              </div>
            );
          }

          const base = "h-12 rounded-full flex items-center justify-center select-none transition-all";
          const tone = active
            ? "bg-yellow-500/90 text-black font-semibold shadow-[0_10px_34px_rgba(255,190,0,.35)]"
            : "bg-white/12 text-white/90 hover:bg-white/18";

          return (
            <button
              key={n}
              onClick={() => onMonthSelect?.(n, year)}
              className={`${base} ${tone} ring-1 ring-white/15`}
              title={`Select ${m}`}
            >
              {m}
            </button>
          );
        })}
      </div>


      <div className="mb-3 text-[15px]">Sentiment Balance Index</div>
      <div className="w-full h-3 rounded-full bg-white/15 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-yellow-400 to-yellow-300"
          style={{ width: `${sbiClamped}%` }}
        />
      </div>
      <div className="mt-3 flex items-center justify-between text-sm">
        <span className="text-white/85">
          Current: <b className="text-white tabular-nums">{Math.round(sbiClamped)}</b>
        </span>
        <span className="text-yellow-300">{deltaStr}</span>
      </div>


      <div className="mt-8 flex items-center gap-6 text-[12px] text-white/75">
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-yellow-400 inline-block" /> Current month
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-white/40 inline-block" /> Months with data
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-full border border-white/40 inline-block" /> Selected month
        </span>
      </div>
    </div>
  );
}
