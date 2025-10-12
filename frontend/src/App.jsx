import { useEffect, useMemo, useState } from "react";
import Header from "./components/Header.jsx";
import KpiCards from "./components/KpiCards.jsx";
import SentimentTabs from "./components/SentimentTabs.jsx";
import DimensionFilter from "./components/DimensionFilter.jsx";
import ReviewsList from "./components/ReviewsList.jsx";
import Pager from "./components/Pager.jsx";
import { getKpis, getReviews } from "./api.js";

export default function App() {
  const [sentiment, setSentiment] = useState("all");
  const [dimension, setDimension] = useState("All");
  const [page, setPage] = useState(1);
  const [size] = useState(10);

  const [kpis, setKpis] = useState({ total: 0, positive_count: 0, negative_count: 0 });
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getKpis({ dimension }).then(setKpis).catch(() => {});
  }, [dimension]);

  // eNPS 
  const enpsValue = useMemo(() => {
    const t = Number(kpis.total) || 0;
    const p = Number(kpis.positive_count) || 0;
    const n = Number(kpis.negative_count) || 0;
    if (!t) return 0;
    return Number((((p - n) / t) * 100).toFixed(2));
  }, [kpis]);

  // sentiment + dimension + slect page
  useEffect(() => {
    setLoading(true);
    getReviews({ sentiment, page, size, dimension })
      .then((data) => {
        setItems(data.items || []);
        setTotal(data.total || 0);
      })
      .finally(() => setLoading(false));
  }, [sentiment, page, size, dimension]);

  return (
    
    <>
      <Header title="Corporate Culture Monitor" subtitle="Sprint 1" />

      <div className="mx-auto max-w-6xl px-5 md:px-8">
        {/* Toolbar */}
        <section className="mt-4 mb-8 p-4 md:p-5 rounded-2xl bg-white shadow-sm ring-1 ring-black/5
                            flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-col sm:flex-row gap-4 sm:items-center">
            <SentimentTabs value={sentiment} onChange={(v)=>{ setSentiment(v); setPage(1); }} />
            <DimensionFilter value={dimension} onChange={(v)=>{ setDimension(v); setPage(1); }} />
          </div>
          <Pager
            page={page}
            size={size}
            total={total}
            onPrev={()=> setPage(p=> Math.max(1, p-1))}
            onNext={()=> setPage(p=> p + 1)}
          />
        </section>

        {/* KPI (base dimension) */}
        <KpiCards
          total={kpis.total}
          pos={kpis.positive_count}
          neg={kpis.negative_count}
          enps={enpsValue}
        />

        {/* Reviews */}
        <main className="mt-6">
          <ReviewsList items={items} loading={loading} />
        </main>
      </div>
    </>
  );
}
