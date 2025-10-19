import { useEffect, useState } from "react";
import Header from "./components/Header.jsx";
// import KpiCards from "./components/KpiCards.jsx";
// import SentimentTabs from "./components/SentimentTabs.jsx";
// import DimensionFilter from "./components/DimensionFilter.jsx";
// import ReviewsList from "./components/ReviewsList.jsx";
import Pager from "./components/Pager.jsx";
// import RegionFilter from "./components/RegionFilter.jsx";
// import DateFilter from "./components/DateFilter.jsx";

import { getPosts, getPostComments } from "./api.js";

export default function App() {
  // const [sentiment, setSentiment] = useState("all");
  // const [dimension, setDimension] = useState("All");
  // const [region, setRegion] = useState("All");
  // const [year, setYear] = useState("All");
  // const [kpis, setKpis] = useState({ total: 0, positive_count: 0, negative_count: 0 });

  const [page, setPage] = useState(1);
  const [size] = useState(10);
  const [posts, setPosts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState("");

  const [selectedPost, setSelectedPost] = useState(null);  // { reddit_id, title_content, ... }
  const [comments, setComments] = useState([]);
  const [cTotal, setCTotal] = useState(0);
  const [cPage, setCPage] = useState(1);
  const [cSize] = useState(50);
  const [cLoading, setCLoading] = useState(false);


  useEffect(() => {
    setLoading(true);
    getPosts({ page, size, q, hasComments: true })   // 
      .then((data) => {
        setPosts(data.items || []);
        setTotal(data.total || 0);
      })
      .finally(() => setLoading(false));
  }, [page, size, q]);


  useEffect(() => {
    if (!selectedPost) return;
    setCLoading(true);
    getPostComments({ reddit_id: selectedPost.reddit_id, page: cPage, size: cSize })
      .then((data) => {
        setComments(data.items || []);
        setCTotal(data.total || 0);
      })
      .finally(() => setCLoading(false));
  }, [selectedPost, cPage, cSize]);

  return (
    <>
      <Header title="Corporate Culture Monitor" subtitle="Reddit Edition (Posts & Comments)" />

      <div className="mx-auto max-w-6xl px-5 md:px-8">
        {}
        <section className="mt-4 mb-6 p-4 md:p-5 rounded-2xl bg-white shadow-sm ring-1 ring-black/5
                            flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <input
              placeholder="Search post title/content/location/source"
              value={q}
              onChange={(e)=>{ setQ(e.target.value); setPage(1); }}
              className="w-72 rounded-xl border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black/10"
            />
          </div>

          <Pager
            page={page}
            size={size}
            total={total}
            onPrev={()=> setPage((p) => Math.max(1, p - 1))}
            onNext={()=> setPage((p) => p + 1)}
          />
        </section>

        {/* =====  ===== */}
        <main className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <section className="space-y-3">
            <h2 className="text-lg font-semibold">Posts</h2>
            <div className="rounded-2xl bg-white shadow-sm ring-1 ring-black/5 divide-y">
              {loading ? (
                <div className="p-6 text-sm text-gray-500">Loading posts…</div>
              ) : posts.length === 0 ? (
                <div className="p-6 text-sm text-gray-500">No posts.</div>
              ) : (
                posts.map((p) => (
                  <button
                    key={p.reddit_id}
                    onClick={() => { setSelectedPost(p); setCPage(1); }}
                    className="w-full text-left p-4 hover:bg-gray-50 transition"
                  >
                    <div className="text-xs text-gray-500 flex items-center gap-2">
                      <span className="rounded-full px-2 py-0.5 bg-gray-100">{p.location || "Global"}</span>
                      <span>{p.time}</span>
                      <span className="ml-auto text-[11px] uppercase tracking-wider">{p.source}</span>
                    </div>
                    <div className="mt-2 text-base font-medium leading-snug">
                      {p.title_content}
                    </div>
                  </button>
                ))
              )}
            </div>
          </section>

          {/* ===== data ===== */}
          <section className="space-y-3">
            <h2 className="text-lg font-semibold">
              {selectedPost ? "Comments" : "Comments (select a post)"}
            </h2>

            {selectedPost && (
              <div className="rounded-2xl bg-white shadow-sm ring-1 ring-black/5">
                <div className="p-4 border-b">
                  <div className="text-xs text-gray-500">#{selectedPost.reddit_id}</div>
                  <div className="mt-1 text-sm">{selectedPost.title_content}</div>
                </div>

                <div className="p-2">
                  <div className="flex items-center justify-between px-2 py-2">
                    <div className="text-xs text-gray-500">
                      Total: {cTotal}
                    </div>
                    <div>
                      <button
                        className="mr-2 rounded-lg border px-3 py-1 text-xs"
                        onClick={() => setCPage((x) => Math.max(1, x - 1))}
                      >
                        Prev
                      </button>
                      <button
                        className="rounded-lg border px-3 py-1 text-xs"
                        onClick={() => setCPage((x) => x + 1)}
                      >
                        Next
                      </button>
                    </div>
                  </div>

                  {cLoading ? (
                    <div className="p-4 text-sm text-gray-500">Loading comments…</div>
                  ) : comments.length === 0 ? (
                    <div className="p-4 text-sm text-gray-500">No comments.</div>
                  ) : (
                    <ul className="space-y-2">
                      {comments.map((c) => (
                        <li
                          key={c.comment_id}
                          className="mx-2 rounded-xl p-3 bg-gray-50 border border-gray-100"
                          style={{ marginLeft: `${Math.min(c.depth || 0, 6) * 12}px` }}
                        >
                          <div className="text-[11px] text-gray-500 flex items-center gap-2">
                            <span>@{c.author || "unknown"}</span>
                            <span>•</span>
                            <span>score {c.score}</span>
                            <span className="ml-auto">{c.created_time}</span>
                          </div>
                          <div className="mt-1 text-sm leading-relaxed">{c.body}</div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </section>
        </main>

        {/* KPI*/}
        {/* <section className="mt-4 mb-8 p-4 ...">
            <SentimentTabs ... />
            <DimensionFilter ... />
            <RegionFilter ... />
            <DateFilter ... />
           <Pager ... />
          </section>
          <KpiCards total={kpis.total} ... />
          <ReviewsList items={items} loading={loading} /> */}
      </div>
    </>
  );
}
