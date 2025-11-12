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
  const [year, setYear] = useState("all");         
  const [month, setMonth] = useState(null);
  const [monthsWithData, setMonthsWithData] = useState([]);
  const [sbi, setSbi] = useState(0);
  const [delta, setDelta] = useState(0);
  const [flipToken, setFlipToken] = useState(0);

  const [dimension, setDimension] = useState("");
  const [subtheme, setSubtheme] = useState("");
  const [sentiment, setSentiment] = useState(""); // "positive" | "negative" | ""

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const info = await getSBI({ year });
        if (!mounted) return;
        const mlist = info.months_with_data || [];
        setMonthsWithData(mlist);
        if (month && !mlist.includes(month)) setMonth(null);
      } catch {
        setMonthsWithData([]);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [year]);

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
          setSbi(0);
          setDelta(0);
        }
      } catch {
        if (!mounted) return;
        setSbi(0);
        setDelta(0);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [year, month]);

  useEffect(() => {
    setFlipToken((t) => t + 1);
  }, [year, month]);

  const handleYearChange = (y) => {
    setYear(y);
    setMonth(null);
    setFlipToken((t) => t + 1);
  };
  const handleMonthSelect = (m, y) => {
    if (y && y !== year) setYear(y);
    setMonth(m);
    setFlipToken((t) => t + 1);
  };

  // DimensionRadar
  const handleDimRadarFilter = ({ dimension: d = "", subtheme: s = "" }) => {
    setDimension(d);
    setSubtheme(s);
    setFlipToken((t) => t + 1);
  };

  return (
    <div
      className="min-h-screen font-display"
      style={{ background: "rgb(242,241,237)" }}
    >
      <div
        className="
          px-6 pt-7 grid gap-x-6 gap-y-6
          grid-cols-1
          sm:grid-cols-[0px_minmax(0,1fr)]
          lg:grid-cols-[0px_minmax(0,1fr)_minmax(300px,420px)]
          xl:grid-cols-[0px_minmax(0,1fr)_420px]
        "
      >
        <div className="hidden sm:flex row-start-1 col-start-1 flex-col items-center self-start">
          <img
            src={rioSmall}
            alt="RIO icon"
            className="h-10 w-auto filter mt-[5px] contrast-125"
          />
          <img
            src={rioBig}
            alt="Rio Tinto"
            className="h-3 w-auto mt-[3.5px] filter grayscale contrast-125"
          />
        </div>

        <div className="row-start-1 col-start-1 sm:col-start-2 flex items-center self-start">
          <div className="translate-y-[2px]">
            <h1 className="text-xl md:text-4xl font-semibold text-neutral-900">
              Culture Insights Dashboard
            </h1>
            <p className="text-sm md:text-base text-neutral-500 hidden xl:block">
              Here's an overview of Rio Tinto's corporate culture insights.
            </p>
          </div>
        </div>

        <div className="row-start-2 sm:row-start-1 col-start-1 sm:col-start-2 lg:col-start-3 w-full self-start mt-1.5">
          <TopRouteTabs />
        </div>

        <aside className="hidden sm:flex row-start-2 col-start-1 justify-center self-start">
          <div className="w-[52px] sm:w-[50px] lg:w-[60px]" />
        </aside>

        <main className="row-start-3 sm:row-start-2 col-start-1 sm:col-start-2">
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

        <section className="row-start-4 sm:row-start-3 lg:row-start-2 col-start-1 sm:col-start-2 lg:col-start-3 z-[20]">
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

        <div
          className="
            row-start-5 sm:row-start-4 lg:row-start-3 col-span-full pb-4 grid gap-6
            grid-cols-1
            sm:grid-cols-[0px_minmax(0,1fr)]
            lg:grid-cols-[0px_minmax(0,1fr)_minmax(300px,420px)]
            xl:grid-cols-[0px_minmax(0,1fr)_420px]
          "
        >
          <div className="hidden sm:flex col-start-1 mt-auto justify-center self-start">
            <div className="w-[52px] sm:w-[56px] lg:w-[60px]" />
          </div>

          <section
            className="
              col-start-1 sm:col-start-2 grid gap-6
              grid-cols-1
              md:grid-cols-[minmax(200px,0.65fr)_minmax(400px,1.35fr)]
            "
          >
            <SentimentVenn
              title="Sentiment Analysis Statistics"
              year={year}
              month={month}
              dimension={dimension}
              subtheme={subtheme}
            />
            <DimensionRadar
              title="Cultural Dimensions"
              year={year}
              month={month}
              widthPx={770}
              heightPx={300}
              selectedDimension={dimension}
              selectedSubtheme={subtheme}
              onFilterChange={handleDimRadarFilter}
            />
          </section>

          <section className="col-start-1 sm:col-start-2 lg:col-start-3">
            <IncomeStatistics year={year} />
          </section>
        </div>
      </div>
    </div>
  );
}
