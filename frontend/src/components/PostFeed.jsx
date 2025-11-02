// src/components/PostFeed.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import { getPosts, getPostDetail, getPostComments, buildCommentTree } from "../api";

// 悬浮翻页图标
import IconLeft from "../../assets/icons/MingcuteLeftFill.png";
import IconRight from "../../assets/icons/MingcuteRightFill.png";

const BG_ARTICLE = "rgba(241, 240, 227, 0.75)"; // Article 
const BG_FORUM   = "rgba(233, 216, 191, 0.75)"; // Forum 

export default function PostFeed({ className = "" }) {
  const pageSize = 4;
  const commentSize = 10000; // 父评论/页

  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(1);
  const [items, setItems] = useState([]);
  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total]);

  const [view, setView] = useState("list"); // 'list' | 'detail'
  const [post, setPost] = useState(null);

  const [cPage, setCPage] = useState(1);
  const [cTotal, setCTotal] = useState(0);     // 父评论总数
  const [commentsTree, setCommentsTree] = useState([]);

  const [_, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [listSlide, setListSlide] = useState(0);
  const [cSlide, setCSlide] = useState(0);
  const listStage = useRef(0);
  const cStage = useRef(0);

  const flipRef = useRef(null);

  const Heart = ({ className = "w-3.5 h-3.5" }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className={className}>
      <path
        d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 1 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
        strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"
      />
    </svg>
  );

  const Badge = ({ type, className = "" }) => {
    const isForum = String(type) === "forum";
    const bg = isForum ? BG_FORUM : BG_ARTICLE;
    const color = isForum ? "#1a3f7a" : "#245a2a";
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 text-[12px] rounded-full border border-white/60 ${className}`}
        style={{ background: bg, color }}
        title={isForum ? "Forum (Reddit)" : "Article"}
      >
        {isForum ? "Forum" : "Article"}
      </span>
    );
  };

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setErr("");
    getPosts({ page, size: pageSize })
      .then((res) => {
        if (!mounted) return;
        setItems(res.items || []);
        setTotal(res.total || 1);
        requestAnimationFrame(() => setListSlide(0));
      })
      .catch((e) => mounted && setErr(e.message || String(e)))
      .finally(() => mounted && setLoading(false));
    return () => (mounted = false);
  }, [page]);

  const gotoPageWithSlide = (next, dir) => {
    const p = Math.min(totalPages, Math.max(1, next));
    if (p === page) return;
    listStage.current += 1;
    const stage = listStage.current;
    setListSlide(dir);
    requestAnimationFrame(() => setPage(p));
    setTimeout(() => stage === listStage.current && setListSlide(0), 500);
  };

  // —— 关键：有 id 必用 id，不再回退 tag —— //
  const openDetail = async (it) => {
    setLoading(true);
    setErr("");
    try {
      const id = it.id || it.tag;           // 列表后端保证 id 存在；极端兜底 tag
      const d = await getPostDetail(id);
      setPost(d);
      setCPage(1);

      if (d.type === "forum") {
        const c = await getPostComments({ id, page: 1, size: commentSize });
        setCommentsTree(buildCommentTree(c.items || []));
        setCTotal(c.total || 0);
      } else {
        setCommentsTree([]); setCTotal(0);
      }

      setView("detail");
      flipTo("detail");
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

  const gotoCommentPage = async (next, dir) => {
    if (!post || post.type !== "forum") return;
    const p = Math.min(cTotalPages, Math.max(1, next));
    if (p === cPage) return;
    cStage.current += 1;
    const stage = cStage.current;
    setCSlide(dir);
    setLoading(true);
    setErr("");
    try {
      const c = await getPostComments({ id: post.id || post.tag, page: p, size: commentSize });
      setCommentsTree(buildCommentTree(c.items || []));
      setCPage(p);
      setCTotal(c.total || 0);
      requestAnimationFrame(() => setCSlide(0));
    } catch (e) {
      setErr(e.message || String(e));
    } finally {
      setLoading(false);
      setTimeout(() => stage === cStage.current && setCSlide(0), 500);
    }
  };

  const sanitize = (txt) => {
    const s = String(txt ?? "").trim();
    if (!s || s.toLowerCase() === "nan") return "";
    return s;
  };

  const flipTo = (target) => {
    if (!flipRef.current) return;
    flipRef.current.style.transform = target === "detail" ? "rotateY(180deg)" : "rotateY(0deg)";
  };

  const backToList = () => {
    setView("list");
    setPost(null);
    setCommentsTree([]);
    flipTo("list");
  };

  return (
    <section
      className={`group relative rounded-2xl border border-[rgb(200,190,170)] shadow-sm ${className}`}
      style={{
        backgroundColor: "#ede5d6ff",
        padding: "0.9rem 0.7rem 0.9rem",
        overflow: "visible",
        perspective: "1200px",
      }}
    >
      {/* 翻转体 */}
      <div
        ref={flipRef}
        className="h-full w-full relative transition-transform duration-500 z-10"
        style={{ transformStyle: "preserve-3d", willChange: "transform" }}
      >
        {/* 列表面 */}
        <div className="absolute inset-0 overflow-hidden" style={{ backfaceVisibility: "hidden" }}>
          {err && (
            <div className="mb-2 mx-1 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {err}
            </div>
          )}

          <div className="h-full overflow-y-auto px-1">
            <div
              className="grid grid-cols-1 md:grid-cols-2 gap-4 transition-transform duration-500"
              style={{ transform: `translateX(${listSlide * 22}%)` }}
            >
              {items.map((it, idx) => {
                const cardBg = it.type === "forum" ? BG_FORUM : BG_ARTICLE;
                return (
                  <button
                    key={`${it.id || it.tag}-${idx}`}
                    onClick={() => openDetail(it)}
                    className="cursor-pointer text-left border border-white/60 rounded-xl px-5 py-4 shadow-sm flex flex-col justify-between transition-all hover:-translate-y-[1px]"
                    style={{ backgroundColor: cardBg }}
                    title={it.source ? `Source: ${it.source}` : ""}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <Badge type={it.type} />
                      {it.source && (
                        <span className="text-[12px] text-neutral-600 truncate ml-3">
                          {it.source}
                        </span>
                      )}
                    </div>

                    <div className="text-[15px] md:text-[16px] font-semibold text-neutral-900 mb-2 line-clamp-2">
                      {it.title}
                    </div>

                    {Array.isArray(it.dimensions) && it.dimensions.length > 0 && (
                      <div className="mb-2 flex flex-wrap gap-1.5">
                        {it.dimensions.slice(0, 4).map((d) => (
                          <span
                            key={d}
                            className="text-[11px] px-2 py-0.5 rounded-full border border-white/60 bg-white/60"
                          >
                            {d}
                          </span>
                        ))}
                        {it.dimensions.length > 4 && (
                          <span className="text-[11px] text-neutral-600">
                            +{it.dimensions.length - 4}
                          </span>
                        )}
                      </div>
                    )}

                    <div className="flex justify-between text-sm text-neutral-600">
                      <span className="truncate">{it.author}</span>
                      <span className="flex items-center gap-3 shrink-0">
                        <span className="tabular-nums">{it.time}</span>
                        <span className="flex items-center gap-1">
                          <Heart className="w-3.5 h-3.5" />
                          <span className="tabular-nums">{it.likes ?? it.score ?? 0}</span>
                        </span>
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* 详情面 */}
        <div className="absolute inset-0 overflow-hidden" style={{ transform: "rotateY(180deg)", backfaceVisibility: "hidden" }}>
          <div className="h-full border border-[rgb(200,190,170)] rounded-2xl shadow-sm overflow-hidden" style={{ background: "#f6f3ef" }}>
            <div className="px-5 py-3 flex justify-between items-center">
              <div className="flex items-center gap-2 pr-4">
                <Badge type={post?.type} />
                <h3 className="text-[17px] md:text-[18px] font-semibold text-neutral-900 line-clamp-2">
                  {post?.title}
                </h3>
              </div>
              <button
                onClick={backToList}
                className="cursor-pointer text-sm text-neutral-600 hover:text-neutral-900 px-2 py-0.5 rounded-lg border border-white/60 bg-white/70"
              >
                Back
              </button>
            </div>

            <div className="px-5 pb-2 text-sm text-neutral-600 flex gap-4 flex-wrap">
              <span>Author: <b className="text-neutral-800">{post?.author}</b></span>
              <span className="tabular-nums">Date: {post?.time}</span>
              <span className="flex items-center gap-1">
                <Heart className="w-3.5 h-3.5" />
                <span className="tabular-nums">{post?.likes ?? post?.score ?? 0}</span>
              </span>
              {post?.source && <span className="truncate">Source: <b className="text-neutral-800">{post.source}</b></span>}
            </div>

            <div className="h-[calc(100%-94px)] overflow-y-auto px-5 pb-4">
              <div className="rounded-xl border border-white/70 bg-white/70 px-4 py-3 mb-3 text-[15px]" style={{ maxHeight: 160, overflowY: "auto" }}>
                {String(post?.content ?? "").trim() || "(No content)"}
              </div>

              {post?.dimensions?.length > 0 && (
                <div className="mb-3 flex flex-wrap gap-1.5">
                  {post.dimensions.map((d) => (
                    <span key={d} className="text-[11px] px-2 py-0.5 rounded-full border border-white/60 bg-white/80">{d}</span>
                  ))}
                </div>
              )}

              {/* 子维度情感（保留带表情一行） */}
              {post && post.subs_sentiment && Object.keys(post.subs_sentiment).length > 0 && (
                <div className="mb-3 flex flex-wrap gap-2">
                  {Object.entries(post.subs_sentiment).map(([k, v]) => {
                    const vv = String(v).toLowerCase();
                    const emo = vv === "positive" ? "😊" : vv === "negative" ? "😟" : "😐";
                    return (
                      <span key={k} className="text-[12px] px-2 py-1 rounded-lg border border-white/60 bg-white/60 flex items-center gap-1">
                        <span>{emo}</span>
                        <span className="text-neutral-800">{k}</span>
                      </span>
                    );
                  })}
                </div>
              )}

              {/* 评论（仅论坛） */}
              {post?.type === "forum" ? (
                <div className="space-y-2 transition-transform duration-500" style={{ transform: `translateX(${cSlide * 22}%)` }}>
                  {commentsTree.length === 0 && <div className="text-sm text-neutral-600">No comments.</div>}
                  {commentsTree.map((c) => (
                    <div key={`c-${c.comment_id}`} className="rounded-xl border border-white/60 bg-white/70 px-4 py-3">
                      <div className="text-[13px] text-neutral-700 mb-1">
                        <b className="text-neutral-900">{c.author}</b>{" "}
                        <span className="tabular-nums text-neutral-500">{c.time}</span>
                        <span className="inline-flex items-center gap-1 ml-3 text-neutral-700">
                          <Heart className="w-3 h-3" />
                          <span className="tabular-nums">{c.score}</span>
                        </span>
                      </div>
                      <div className="text-[14px] text-neutral-900 whitespace-pre-wrap">
                        {String(c.content || "").trim()}
                      </div>

                      {Array.isArray(c.replies) && c.replies.length > 0 && (
                        <div className="mt-2 pl-3 border-l border-neutral-200 space-y-2">
                          {c.replies.map((r) => (
                            <div key={`r-${r.comment_id}`} className="rounded-lg border border-white/60 bg-white/60 px-3 py-2">
                              <div className="text-[12px] text-neutral-700 mb-1">
                                <b className="text-neutral-900">{r.author}</b>{" "}
                                <span className="tabular-nums text-neutral-500">{r.time}</span>
                                <span className="inline-flex items-center gap-1 ml-2 text-neutral-700">
                                  <Heart className="w-3 h-3" />
                                  <span className="tabular-nums">{r.score}</span>
                                </span>
                                <span className="ml-2 text-[12px] text-neutral-500">(reply)</span>
                              </div>
                              <div className="text-[13px] text-neutral-900 whitespace-pre-wrap">
                                {String(r.content || "").trim()}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-[12px] text-neutral-500">This is an article (no comments).</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 左侧悬浮按钮 */}
      <div className="absolute inset-y-0 left-0 w-16 z-[999] pointer-events-none">
        <button
          onClick={() => (view === "list" ? gotoPageWithSlide(page - 1, +1) : gotoCommentPage(cPage - 1, +1))}
          disabled={view === "list" ? page <= 1 : post?.type !== "forum" || cPage <= 1}
          className="cursor-pointer pointer-events-auto absolute left-2 top-1/2 -translate-y-1/2 opacity-0 hover:opacity-100 transition-opacity duration-150 rounded-full p-2 bg-transparent disabled:opacity-0"
        >
          <img src={IconLeft} alt="prev" className="w-36 h-17 select-none drop-shadow" style={{ opacity: 0.6 }} />
        </button>
      </div>

      {/* 右侧悬浮按钮 */}
      <div className="absolute inset-y-0 right-0 w-16 z-[999] pointer-events-none">
        <button
          onClick={() => (view === "list" ? gotoPageWithSlide(page + 1, -1) : gotoCommentPage(cPage + 1, -1))}
          disabled={view === "list" ? page >= totalPages : post?.type !== "forum" || cPage >= cTotalPages}
          className="cursor-pointer pointer-events-auto absolute right-2 top-1/2 -translate-y-1/2 opacity-0 hover:opacity-100 transition-opacity duration-150 rounded-full p-2 bg-transparent disabled:opacity-0"
        >
          <img src={IconRight} alt="next" className="w-36 h-17 select-none drop-shadow" style={{ opacity: 0.6 }} />
        </button>
      </div>
    </section>
  );
}
