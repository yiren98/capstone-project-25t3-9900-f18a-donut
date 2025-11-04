// routes/Dashboard.jsx
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
import { getSBI } from "../src/api";

export default function Dashboard() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(null); // null=整年
  const [monthsWithData, setMonthsWithData] = useState([]);
  const [sbi, setSbi] = useState(0);
  const [delta, setDelta] = useState(0);
  const [flipToken, setFlipToken] = useState(0);

  // 取该年的可用月份
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const info = await getSBI({ year });
        if (!mounted) return;
        setMonthsWithData(info.months_with_data || []);
        // 如果当前月在新年无数据 -> 置空
        if (month && !(info.months_with_data || []).includes(month)) setMonth(null);
      } catch {
        setMonthsWithData([]);
      }
    })();
    return () => { mounted = false; };
  }, [year]);

  // 选中月份 -> sbi/delta；未选月=0
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
          setSbi(0); setDelta(0);
        }
      } catch {
        if (!mounted) return;
        setSbi(0); setDelta(0);
      }
    })();
    return () => { mounted = false; };
  }, [year, month]);

  // 提示 PostFeed 做筛选刷新动画
  useEffect(() => { setFlipToken((t) => t + 1); }, [year, month]);

  // —— 新增：更健壮的回调 —— //
  const handleYearChange = (y) => {
    setYear(y);
    setMonth(null);          // 换年时清空月份
    setFlipToken(t => t + 1); // 立即触发一次刷新（不用等副作用）
  };

  const handleMonthSelect = (m, y) => {
    // CalendarPanel 会把当前 year 也带过来
    if (y && y !== year) setYear(y);
    setMonth(m);
    setFlipToken(t => t + 1); // 立即触发刷新，PostFeed 第一时间按月筛
  };

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
          <PostFeed
            className="flex-1 h-[395px]"
            year={year}
            month={month}
            filterFlipKey={flipToken}
          />
        </main>

        <section className="row-start-4 sm:row-start-3 lg:row-start-2 col-start-1 sm:col-start-2 lg:col-start-3 z-[20]">
          <CalendarPanel
            className="h-full"
            year={year}
            selectedMonth={month}
            monthsWithData={monthsWithData}
            onYearChange={handleYearChange}          // <—— 改用加固回调
            onMonthSelect={handleMonthSelect}        // <—— 改用加固回调
            sbi={Number.isFinite(sbi) ? sbi : 0}
            delta={Number.isFinite(delta) ? delta : 0}
          />
        </section>

        {/* 下面保持不变 */}
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
            <IncomeStatistics year={year} />
          </section>
        </div>
      </div>
    </div>
  );
}
