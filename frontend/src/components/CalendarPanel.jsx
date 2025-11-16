const YEAR_MIN = 2013;
const YEAR_MAX = 2025;
const YEAR_OPTS = Array.from(
  { length: YEAR_MAX - YEAR_MIN + 1 },
  (_, i) => YEAR_MIN + i
).concat("all");
// YEAR_OPTS = [2013, 2014, ... , 2025, "all"]

export default function CalendarPanel({
  className = "",
  year = "all",
  selectedMonth = null,
  monthsWithData = [],
  onMonthSelect,
  onYearChange,
  sbi = 0,
  delta = 0,
}) {
  const months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];

  const isAll = String(year).toLowerCase() === "all";
  const idx = YEAR_OPTS.findIndex((v) => String(v) === String(year));

  const atFirst = idx <= 0;
  const atLast = idx >= YEAR_OPTS.length - 1; // All

  const goPrevYear = () => {
    if (atFirst) return;
    onYearChange?.(YEAR_OPTS[idx - 1]);
  };
  const goNextYear = () => {
    if (atLast) return;
    onYearChange?.(YEAR_OPTS[idx + 1]);
  };

  const canClick = (n) => (!isAll && monthsWithData.includes(n));

  const handleMonthClick = (n) => {
    if (!canClick(n)) return; 
    const next = selectedMonth === n ? null : n;
    onMonthSelect?.(next, isAll ? "all" : year);
  };

  const sbiVal = Math.max(
    -100,
    Math.min(100, Number.isFinite(sbi) ? sbi : 0)
  );
  const pct = (Math.abs(sbiVal) / 100) * 50;
  const isPos = sbiVal >= 0;
  const deltaStr = `${delta > 0 ? "↑" : delta < 0 ? "↓" : "±"} ${Math.abs(
    Math.round(delta)
  )} pts vs last month`;

  return (
    <div
      className={`rounded-2xl border border-[#d6d0c5] shadow-sm px-5 py-5 text-white ${className}`}
      style={{ background: "#141416", minHeight: 395 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold">View Data by Month</h3>

        <div className="flex items-center gap-4 text-sm text-white/85">
          <button
            className={`px-2 py-1 rounded ${
              atFirst ? "opacity-40 cursor-not-allowed" : "hover:bg-white/10"
            }`}
            onClick={goPrevYear}
            disabled={atFirst}
          >
            {"<"}
          </button>

          <span className="tabular-nums px-2 py-1">
            {isAll ? "All" : year}
          </span>

          <button
            className={`px-2 py-1 rounded ${
              atLast ? "opacity-40 cursor-not-allowed" : "hover:bg-white/10"
            }`}
            onClick={goNextYear}
            disabled={atLast}
          >
            {">"}
          </button>
        </div>
      </div>

      {/* Months */}
      <div className="grid grid-cols-6 gap-x-5 gap-y-6 mb-10">
        {months.map((m, idx) => {
          const n = idx + 1;
          const active = selectedMonth === n;
          const clickable = canClick(n);

  
          if (!clickable) {
            return (
              <div
                key={n}
                className="h-12 rounded-full flex items-center justify-center bg-transparent text-white/35 border border-white/10"
                title={
                  isAll ? `${m} (disabled in All mode)` : `${m} (no data)`
                }
              >
                {m}
              </div>
            );
          }


          const base =
            "h-12 rounded-full flex items-center justify-center transition-all ring-1 ring-white/15";
          const tone = active
            ? "bg-yellow-500/90 text-black font-semibold shadow-[0_10px_34px_rgba(255,190,0,.35)]"
            : "bg-white/12 text-white/90 hover:bg-white/18";

          return (
            <button
              key={n}
              onClick={() => handleMonthClick(n)}
              className={`${base} ${tone}`}
            >
              {m}
            </button>
          );
        })}
      </div>

      {/* SBI */}
      <div className="mb-2 text-[15px]">Sentiment Balance Index</div>
      <div className="w-full h-3 rounded-full bg-white/15 relative overflow-hidden">
        <div className="absolute left-1/2 top-0 bottom-0 w-[1px] bg-white/35" />
        <div
          className="absolute top-0 bottom-0"
          style={{
            left: isPos ? "50%" : `${50 - pct}%`,
            right: isPos ? `${50 - pct}%` : "50%",
            background: isPos
              ? "linear-gradient(90deg, #fde047, #facc15)"
              : "linear-gradient(270deg, #f35b5bff, #ef1717ff)",
          }}
        />
      </div>
      <div className="mt-3 flex items-center justify-between text-sm">
        <span className="text-white/85">
          Current: <b className="text-white">{Math.round(sbiVal)}</b>
        </span>
        <span className={isPos ? "text-yellow-300" : "text-red-400"}>
          {deltaStr}
        </span>
      </div>

      {/* Legend */}
      <div className="mt-8 flex items-center justify-center gap-10 text-[12px] text-white/75">
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-white/40" />
          Months with data
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-[#F6C543]" />
          Selected month
        </span>
      </div>
    </div>
  );
}
