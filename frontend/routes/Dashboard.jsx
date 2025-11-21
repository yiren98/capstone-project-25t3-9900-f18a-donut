// routes/Dashboard.jsx
import React, { useEffect, useState } from "react";
import rioSmall from "../assets/icons/unsw_logo.png";
import rioBig from "../assets/icons/unsw_logo_text.png";

import TopRouteTabs from "../src/components/TopRouteTabs";
import PostFeed from "../src/components/PostFeed";
import CalendarPanel from "../src/components/CalendarPanel";
import SentimentVenn from "../src/components/SentimentVenn";
import DimensionRadar from "../src/components/DimensionRadar";
import IncomeStatistics from "../src/components/Statistics";
import { getSBI } from "../src/api";

export default function Dashboard() {
  // Global time filter: "all" or a specific year
  const [year, setYear] = useState(2025);
  // Currently selected month (null = no month filter)
  const [month, setMonth] = useState(null);
  // Months that actually have data for the selected year
  const [monthsWithData, setMonthsWithData] = useState([]);
  // Sentiment Balance Index value for the current (year, month)
  const [sbi, setSbi] = useState(0);
  // Change in SBI compared with the previous period
  const [delta, setDelta] = useState(0);
  // Flip token to force child components (PostFeed etc.) to refresh when filters change
  const [flipToken, setFlipToken] = useState(0);

  // Filters from DimensionRadar
  const [dimension, setDimension] = useState("");
  const [subtheme, setSubtheme] = useState("");
  // Placeholder for sentiment filter (reserved for future use)
  const [sentiment] = useState("");

  // Shared card height for the bottom statistics section
  const CARD_H = 300;

  // ---------- data effects ----------

  // Fetch which months have data whenever the year changes
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const info = await getSBI({ year });
        if (!mounted) return;
        const mlist = info.months_with_data || [];
        setMonthsWithData(mlist);
      } catch {
        // On error, just clear the list and keep the UI consistent
        setMonthsWithData([]);
      }
    })();
    return () => { mounted = false; };
  }, [year]);

  // If the currently selected month is no longer valid for this year, reset it
  useEffect(() => {
    if (month && !monthsWithData.includes(month)) {
      setMonth(null);
    }
  }, [month, monthsWithData]);

  // Fetch SBI and delta when year/month changes
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        if (month) {
          const info = await getSBI({ year, month });
          if (!mounted) return;
          setSbi(Number(info.sbi || 0));
          setDelta(Number(info.delta || 0));
        } else {
          // No month selected -> neutral values
          setSbi(0);
          setDelta(0);
        }
      } catch {
        if (!mounted) return;
        setSbi(0);
        setDelta(0);
      }
    })();
    return () => { mounted = false; };
  }, [year, month]);

  // Any time year/month changes, bump the flip token to trigger PostFeed refresh
  useEffect(() => { setFlipToken((t) => t + 1); }, [year, month]);

  // ---------- handlers ----------

  // Year selector from the calendar
  const handleYearChange = (y) => {
    setYear(y);
    setMonth(null); // reset month when year changes
    setFlipToken((t) => t + 1);
  };

  // Month click from the calendar (may also adjust year)
  const handleMonthSelect = (m, y) => {
    if (y && y !== year) setYear(y);
    setMonth(m);
    setFlipToken((t) => t + 1);
  };

  // DimensionRadar callback: update selected dimension and subtheme
  const handleDimRadarFilter = ({ dimension: d = "", subtheme: s = "" }) => {
    setDimension(d);
    setSubtheme(s);
    setFlipToken((t) => t + 1);
  };

  return (
    <div className="min-h-screen font-display" style={{ background: "rgb(242,241,237)" }}>
      <div
        className="
          px-6 pt-7 grid gap-x-6 gap-y-6
          grid-cols-1
          sm:grid-cols-[0px_minmax(0,1fr)]
          lg:grid-cols-[0px_minmax(0,1fr)_minmax(300px,420px)]
          xl:grid-cols-[0px_minmax(0,1fr)_420px]
        "
      >
        {/* Left logo column: only visible on small screens and above */}
        <div className="hidden sm:flex row-start-1 col-start-1 flex-col items-center self-start">
          <img src={rioSmall} alt="RIO icon" className="h-10 w-auto filter mt-[5px] contrast-125" />
          <img src={rioBig} alt="Rio Tinto" className="h-3 w-auto mt-[3.5px] filter grayscale contrast-125" />
        </div>

        {/* Page title + description */}
        <div className="row-start-1 col-start-1 sm:col-start-2 flex items-center self-start">
          <div className="translate-y-[2px]">
            <h1 className="text-xl md:text-4xl font-semibold text-neutral-900">
              AI Culture Intelligence Dashboard
            </h1>
            <p className="text-sm md:text-base text-neutral-500 hidden xl:block">
              Here’s an AI-generated overview of Rio Tinto’s corporate culture insights.
            </p>
          </div>
        </div>

        {/* Top navigation tabs (Dashboard / Culture Analysis / Statistics) */}
        <div className="row-start-2 sm:row-start-2 lg:row-start-1 col-start-1 sm:col-start-2 lg:col-start-3 w-full self-start mt-2 lg:mt-1.5 mb-2">
          <TopRouteTabs className="ml-auto max-w-[480px]" />
        </div>

        {/* Spacer column under the logo to keep grid alignment consistent */}
        <aside className="hidden sm:flex row-start-2 col-start-1 justify-center self-start">
          <div className="w-[52px] sm:w-[50px] lg:w-[60px]" />
        </aside>

        {/* Main content feed: posts list filtered by year/month/dimension/subtheme */}
        <main className="row-start-3 sm:row-start-3 lg:row-start-2 col-start-1 sm:col-start-2">
          <PostFeed
            className="flex-1 h-[395px]"
            year={year}
            month={month}
            filterFlipKey={flipToken}
            sentiment={sentiment}
            subtheme={subtheme}
            dimension={dimension}
          />
        </main>

        {/* Right-hand side calendar + SBI panel */}
        <section className="row-start-4 sm:row-start-4 lg:row-start-2 col-start-1 sm:col-start-2 lg:col-start-3 z-[20]">
          <CalendarPanel
            className="h-full"
            year={year}
            selectedMonth={month}
            monthsWithData={monthsWithData}
            onYearChange={handleYearChange}
            onMonthSelect={handleMonthSelect}
            sbi={Number.isFinite(sbi) ? sbi : 0}
            delta={Number.isFinite(delta) ? delta : 0}
          />
        </section>

        {/* Bottom section: sentiment and dimension visualizations + statistics */}
        <div
          className="
            row-start-5 sm:row-start-5 lg:row-start-3 col-span-full
            grid gap-6
            grid-cols-1
            sm:grid-cols-[0px_minmax(0,1fr)]
            lg:grid-cols-[0px_minmax(0,1fr)_minmax(300px,420px)]
            xl:grid-cols-[0px_minmax(0,1fr)_420px]
          "
        >
          {/* Spacer to align with logo column on larger screens */}
          <div className="hidden sm:flex col-start-1 justify-center">
            <div className="w-[52px] sm:w-[50px] lg:w-[60px]" />
          </div>

          {/* Left stats: Venn + radar charts */}
          <section
            className="
              col-start-1 sm:col-start-2
            "
          >
            <div
              className="
                grid gap-6
                md:grid-cols-[4fr_7fr]
                items-stretch
              "
            >
              <SentimentVenn
                className="h-full"
                height={CARD_H}
                title="Sentiment Analysis Statistics"
                year={year}
                month={month}
                dimension={dimension}
                subtheme={subtheme}
              />
              <DimensionRadar
                className="h-full"
                title="Cultural Dimensions"
                year={year}
                month={month}
                heightPx={CARD_H}
                selectedDimension={dimension}
                selectedSubtheme={subtheme}
                onFilterChange={handleDimRadarFilter}
              />
            </div>
          </section>

          {/* Right stats: time series / income-style statistics for cultural indicators */}
          <section className="col-start-1 sm:col-start-2 lg:col-start-3">
            <IncomeStatistics className="h-full" year={year} height={CARD_H} />
          </section>
        </div>
      </div>
    </div>
  );
}
