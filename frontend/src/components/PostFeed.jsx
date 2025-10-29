// src/components/PostFeed.jsx
import React, { useEffect, useMemo, useState } from "react";
import { getPosts, getPostDetail, getPostComments } from "../api";

export default function PostFeed({ className = "" }) {
  const pageSize = 6;
  const commentSize = 2;

  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(1);
  const [items, setItems] = useState([]);
  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total]);

  const [view, setView] = useState("list"); // 'list' | 'detail'
  const [post, setPost] = useState(null);

  const [cPage, setCPage] = useState(1);
  const [cTotal, setCTotal] = useState(0);
  const [comments, setComments] = useState([]);

  const [_, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const Heart = ({ className = "w-3.5 h-3.5" }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className={className}>
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 1 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
        strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );

  const Arrow = ({ left, disabled, onClick, small }) => (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`px-1 ${small ? "text-[12px]" : "text-[15px]"} leading-none select-none ${
        disabled ? "text-neutral-400 cursor-not-allowed" : "text-neutral-700 hover:text-neutral-900"
      }`}
      aria-label={left ? "Prev page" : "Next page"}
      title={left ? "Prev page" : "Next page"}
    >
      {left ? "‹" : "›"}
    </button>
  );

  const MiniPager = ({ page, totalPages, onPrev, onNext }) => (
    <div className="inline-flex items-center gap-1 bg-white/60 px-2 py-0.5 rounded-full border border-white/70 shadow-sm">
      <Arrow left small disabled={page <= 1} onClick={onPrev} />
      <span className="text-[12px] text-neutral-800 select-none tabular-nums">
        {page}/{totalPages}
      </span>
      <Arrow small disabled={page >= totalPages} onClick={onNext} />
    </div>
  );

  // 列表
  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setErr("");
    getPosts({ page, size: pageSize })
      .then((res) => {
        if (!mounted) return;
        setItems(res.items || []);
        setTotal(res.total || 1);
      })
      .catch((e) => mounted && setErr(e.message || String(e)))
      .finally(() => mounted && setLoading(false));
    return () => (mounted = false);
  }, [page]);

  const goto = (p) => {
    const next = Math.min(totalPages, Math.max(1, p));
    setPage(next);
    setView("list");
    setPost(null);
  };


  const openDetail = async (it) => {
    setLoading(true);
    setErr("");
    try {
      const idOrTag = it.tag || it.id;
      const d = await getPostDetail(idOrTag);
      setPost(d);
      setCPage(1);
      const c = await getPostComments({ id: idOrTag, page: 1, size: commentSize });
      setComments(c.items || []);
      setCTotal(c.total || 0);
      setView("detail");
    } catch (e) {
      setErr(e.message || String(e));
    } finally {
      setLoading(false);
    }
  };


  const cTotalPages = useMemo(
    () => Math.max(1, Math.ceil((cTotal || 0) / commentSize)),
    [cTotal, commentSize]
  );

  const gotoCommentPage = async (nextPage) => {
    if (!post) return;
    const p = Math.min(cTotalPages, Math.max(1, nextPage));
    if (p === cPage) return;
    setLoading(true);
    setErr("");
    try {
      const c = await getPostComments({ id: post.tag || post.id, page: p, size: commentSize });
      setComments(c.items || []);
      setCPage(p);
      setCTotal(c.total || 0);
    } catch (e) {
      setErr(e.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  const sanitize = (txt) => {
    const s = String(txt ?? "").trim();
    if (!s || s.toLowerCase() === "nan") return "";
    return s;
  };

  return (
    <section
      className={`rounded-2xl border border-[rgb(200,190,170)] shadow-sm ${className}`}
      style={{ backgroundColor: "#ede5d6ff", padding: "1.2rem 0.7rem 1.0rem" }}
    >

      {view === "list" && (
        <>
          {err && (
            <div className="mb-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {err}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {items.map((it, idx) => (
              <button
                key={`${it.id || it.tag}-${idx}`}
                onClick={() => openDetail(it)}
                className="text-left border border-white/60 rounded-xl px-5 py-4 shadow-sm flex flex-col justify-between transition-all hover:translate-y-[-1px] focus:outline-none"
                style={{ backgroundColor: idx % 2 === 0 ? "#EAE6DE" : "#e5dfbecc" }}
              >
                <div className="text-[15px] md:text-[16px] font-semibold text-neutral-900 leading-snug mb-2 line-clamp-2">
                  {it.title}
                </div>
                <div className="flex items-center justify-between text-sm text-neutral-600">
                  <span className="truncate">{it.author}</span>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="tabular-nums">{it.time}</span>
                    <span className="flex items-center gap-1">
                      <Heart className="w-3.5 h-3.5" />
                      <span className="tabular-nums">{it.likes}</span>
                    </span>
                  </div>
                </div>
              </button>
            ))}
          </div>


          <div className="mt-3 flex items-center justify-center">
            <MiniPager
              page={page}
              totalPages={totalPages}
              onPrev={() => goto(page - 1)}
              onNext={() => goto(page + 1)}
            />
          </div>
        </>
      )}


      {view === "detail" && post && (
        <div
          className="border border-[rgb(200,190,170)] rounded-2xl shadow-sm overflow-hidden"
          style={{ background: "#f6f3ef" }}
        >
          <div className="px-5 py-3 flex items-center justify-between">
            <h3 className="text-[17px] md:text-[18px] font-semibold text-neutral-900 leading-snug pr-4">
              {post.title}
            </h3>
            <button
              onClick={() => setView("list")}
              className="text-sm text-neutral-600 hover:text-neutral-900 px-2 py-0.5 rounded-lg border border-white/60 bg-white/70"
            >
              Back
            </button>
          </div>

          <div className="px-5 pb-2 text-sm text-neutral-600 flex flex-wrap items-center gap-x-4 gap-y-1">
            <span className="truncate">
              Author: <b className="text-neutral-800">{post.author}</b>
            </span>
            <span className="tabular-nums">Date: {post.time}</span>
            <span className="flex items-center gap-1">
              <Heart className="w-3.5 h-3.5" />
              <span className="tabular-nums">{post.likes ?? post.score ?? 0}</span>
            </span>
          </div>

          <div className="px-5 pb-3">

            <div
              className="rounded-xl border border-white/70 bg-white/70 px-4 py-3 leading-relaxed text-[15px] text-neutral-800 mb-3"
              style={{ maxHeight: 120, overflowY: "auto" }}
            >
              {sanitize(post.content) || "(No content)"}
            </div>


            <div className="space-y-2" style={{ maxHeight: 320, overflowY: "auto" }}>
              {comments.length === 0 && (
                <div className="text-sm text-neutral-600">No comments.</div>
              )}

              {comments.map((c) => (
                <div
                  key={`c-${c.comment_id}`}
                  className="rounded-xl border border-white/60 bg-white/70 px-4 py-3"
                >
                  <div className="text-[13px] text-neutral-700 mb-1">
                    <b className="text-neutral-900">{c.author}</b>{" "}
                    <span className="tabular-nums text-neutral-500">{c.time}</span>
                    <span className="inline-flex items-center gap-1 ml-3 text-neutral-700">
                      <Heart className="w-3 h-3" />
                      <span className="tabular-nums">{c.score}</span>
                    </span>
                    {Number(c.level) === 2 && (
                      <span className="ml-2 text-[12px] text-neutral-500">(reply)</span>
                    )}
                  </div>
                  <div className="text-[14px] text-neutral-900 leading-relaxed whitespace-pre-wrap">
                    {sanitize(c.content)}
                  </div>
                </div>
              ))}
            </div>


            <div className="mt-2 flex items-center justify-center">
              <MiniPager
                page={cPage}
                totalPages={Math.max(1, Math.ceil((cTotal || 0) / commentSize))}
                onPrev={() => gotoCommentPage(cPage - 1)}
                onNext={() => gotoCommentPage(cPage + 1)}
              />
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
