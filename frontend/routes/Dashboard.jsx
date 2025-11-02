import React, { useEffect, useMemo, useState } from "react";
import rioSmall from "../assets/icons/unsw_logo.png";
import rioBig from "../assets/icons/unsw_logo_text.png";
import SidebarNav from "../src/components/SidebarNav";
import BottomUtilities from "../src/components/BottomUtilities";
import TopSearchBar from "../src/components/TopSearchBar";
import PostFeed from "../src/components/PostFeed";
import CalendarPanel from "../src/components/CalendarPanel";
import SentimentVenn from "../src/components/SentimentVenn";
import DimensionRadar from "../src/components/DimensionRadar";
import IncomeStatistics from "../src/components/Statistics";
import { getAllPosts } from "../src/api";


function computeSBI(posts) {
  let pos = 0, neg = 0, neu = 0;
  for (const p of posts) {
    if (!p?.subs_sentiment) continue;
    for (const v of Object.values(p.subs_sentiment)) {
      const s = String(v).toLowerCase();
      if (s === "positive") pos++;
      else if (s === "negative") neg++;
      else neu++;
    }
  }
  const d = pos + neg + neu;
  return d ? ((pos - neg) / d) * 100 : 0;
}

export default function Dashboard() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(null);
  const [allPosts, setAllPosts] = useState([]);
  const [flipToken, setFlipToken] = useState(0);

  useEffect(() => {
    let mounted = true;
    (async () => {
      const arr = await getAllPosts({ limit: 1000 });
      if (mounted) setAllPosts(arr);
    })();
    return () => (mounted = false);
  }, []);


  const monthsWithData = useMemo(() => {
    const set = new Set();
    for (const p of allPosts) {
      const t = String(p.time || "");
      if (!/^\d{4}-\d{2}-\d{2}$/.test(t)) continue;
      const [y, m] = t.split("-").map((x) => parseInt(x, 10));
      if (y === year && m >= 1 && m <= 12) set.add(m);
    }
    return Array.from(set).sort((a, b) => a - b);
  }, [allPosts, year]);


  const filteredItems = useMemo(() => {
    if (!month) return allPosts;
    const mm = String(month).padStart(2, "0");
    const prefix = `${year}-${mm}`;
    return (allPosts || []).filter((p) => (p.time || "").startsWith(prefix));
  }, [allPosts, year, month]);


  const sbi = useMemo(() => {
    if (!month) return 0;
    return computeSBI(filteredItems);
  }, [filteredItems, month]);

  const delta = useMemo(() => {
    if (!month) return 0;
    let y = year, m = month - 1;
    if (m < 1) { y -= 1; m = 12; }
    const prevPrefix = `${y}-${String(m).padStart(2, "0")}`;
    const prevItems = (allPosts || []).filter((p) => (p.time || "").startsWith(prevPrefix));
    return Math.round(computeSBI(filteredItems) - computeSBI(prevItems));
  }, [allPosts, filteredItems, year, month]);


  useEffect(() => { setFlipToken((t) => t + 1); }, [year, month]);

  return (
    <div className="min-h-screen font-display" style={{ background: "rgb(242,241,237)" }}>
      <div
        className="
          px-7 pt-7 grid gap-x-6 gap-y-6
          grid-cols-1
          sm:grid-cols-[72px_minmax(0,1fr)]
          lg:grid-cols-[72px_minmax(0,1fr)_minmax(300px,420px)]
          xl:grid-cols-[72px_minmax(0,1fr)_420px]
        "
      >
        <div className="hidden sm:flex row-start-1 col-start-1 flex-col items-center self-start">
          <img src={rioSmall} alt="RIO icon" className="h-10 w-auto filter mt-[5px] contrast-125" />
          <img src={rioBig} alt="Rio Tinto" className="h-3 w-auto mt-[3.5px] filter grayscale contrast-125" />
        </div>

        <div className="row-start-1 col-start-1 sm:col-start-2 flex items-center self-start">
          <div className="translate-y-[2px]">
            <h1 className="text-xl md:text-4xl font-semibold text-neutral-900">Hi, YoloFun!</h1>
            <p className="text-sm md:text-base text-neutral-500 hidden xl:block">
              Here's an overview of Rio Tinto's corporate culture insights.
            </p>
          </div>
        </div>

        <div className="row-start-2 sm:row-start-1 col-start-1 sm:col-start-2 lg:col-start-3 w-full self-start mt-1.5">
          <TopSearchBar />
        </div>

        <aside className="hidden sm:flex row-start-2 col-start-1 justify-center self-start">
          <SidebarNav />
        </aside>

        <main className="row-start-3 sm:row-start-2 col-start-1 sm:col-start-2">
   
          <PostFeed className="flex-1 h-[395px]" data={filteredItems} flipToken={flipToken} />
        </main>

        <section className="row-start-4 sm:row-start-3 lg:row-start-2 col-start-1 sm:col-start-2 lg:col-start-3">
          <CalendarPanel
            className="h-full"
            year={year}
            selectedMonth={month}          
            monthsWithData={monthsWithData}  
            onYearChange={setYear}
            onMonthSelect={(m, y) => { setYear(y); setMonth(m); }}
            sbi={isFinite(sbi) ? sbi : 0}
            delta={isFinite(delta) ? delta : 0}
          />
        </section>

        <div className="row-start-5 sm:row-start-4 lg:row-start-3 col-span-full pb-4 grid gap-6
                        grid-cols-1
                        sm:grid-cols-[72px_minmax(0,1fr)]
                        lg:grid-cols-[72px_minmax(0,1fr)_minmax(300px,420px)]
                        xl:grid-cols-[72px_minmax(0,1fr)_420px]">

          <div className="hidden sm:flex col-start-1 mt-auto justify-center self-start">
            <BottomUtilities />
          </div>

          <section className="col-start-1 sm:col-start-2 grid gap-6
                              grid-cols-1
                              md:grid-cols-[minmax(260px,0.9fr)_minmax(340px,1.1fr)]">
            <SentimentVenn
              positive={270}
              negative={210}
              intersectionRate={34.09}
              title="Sentiment Analysis Statistics"
            />
            <DimensionRadar title="Cultural Dimensions" widthPx={640} heightPx={247} />
          </section>

          <section className="col-start-1 sm:col-start-2 lg:col-start-3">
            <IncomeStatistics />
          </section>
        </div>
      </div>
    </div>
  );
}
