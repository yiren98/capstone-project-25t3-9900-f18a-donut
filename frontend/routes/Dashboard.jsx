// src/routes/Dashboard.jsx
import { useEffect, useState } from "react";
import Header from "../src/components/Header.jsx";
import Pager from "../src/components/Pager.jsx";
import PostCard from "../src/components/PostCard.jsx";
import { getPosts } from "../src/api.js";

function useDebounced(value, delay = 300) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}

export default function Dashboard() {
  const [page, setPage] = useState(1);
  const [size] = useState(10);
  const [posts, setPosts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [q, setQ] = useState("");
  const qDebounced = useDebounced(q, 300);
  const [onlyHasComments, setOnlyHasComments] = useState(true);

  const [loggingOut, setLoggingOut] = useState(false);

  const onLogout = async () => {
    try {
      setLoggingOut(true);
      await fetch("/api/logout", { method: "POST", credentials: "include" });
    } finally {
      setLoggingOut(false);
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
  };

  useEffect(() => {
    setLoading(true);
    setErrorMsg("");
    getPosts({ page, size, q: qDebounced })
      .then((data) => {
        setPosts(data.items || []);
        setTotal(data.total || 0);
      })
      .catch((e) => setErrorMsg(e?.message || "Failed to load posts"))
      .finally(() => setLoading(false));
  }, [page, size, qDebounced]);

  useEffect(() => {
    setPage(1);
  }, [qDebounced, onlyHasComments]);

  const canPrev = page > 1;
  const canNext = page * size < (total || 0);

  const visiblePosts = onlyHasComments
    ? (posts || []).filter((p) => (p.comment_count ?? 0) > 0)
    : posts;

  return (
    <>
      <Header title="Corporate Culture Monitor" subtitle="Reddit Edition (Posts)" />

      <div className="mx-auto max-w-6xl px-5 md:px-8 mt-2">
        <div className="flex justify-end">
          <button
            onClick={onLogout}
            disabled={loggingOut}
            className="rounded-xl border border-gray-300 bg-white px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-60"
          >
            {loggingOut ? "Logging out…" : "Logout"}
          </button>
        </div>

        <section
          className="mt-4 mb-6 p-4 md:p-5 rounded-2xl bg-white shadow-sm ring-1 ring-black/5
                     flex flex-col gap-4 md:flex-row md:items-center md:justify-between"
        >
          <div className="flex items-center gap-3">
            <input
              placeholder="Search title/content/author/location/source"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="w-80 rounded-xl border border-gray-200 px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-black/10"
            />
            <label className="inline-flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={onlyHasComments}
                onChange={(e) => setOnlyHasComments(e.target.checked)}
                className="rounded border-gray-300"
              />
              Only with comments
            </label>
          </div>
          <Pager
            page={page}
            size={size}
            total={total}
            onPrev={() => canPrev && setPage((p) => Math.max(1, p - 1))}
            onNext={() => canNext && setPage((p) => p + 1)}
          />
        </section>

        {errorMsg && <div className="mb-4 text-sm text-red-600">{errorMsg}</div>}

        <main className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {loading ? (
            <div className="p-6 text-sm text-gray-500 col-span-2">Loading posts…</div>
          ) : (visiblePosts || []).length === 0 ? (
            <div className="p-6 text-sm text-gray-500 col-span-2">No posts found.</div>
          ) : (
            visiblePosts.map((p) => <PostCard key={p.id} data={p} />)
          )}
        </main>
      </div>
    </>
  );
}
