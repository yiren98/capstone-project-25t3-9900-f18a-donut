import React, { useEffect, useRef, useState } from "react";
import { getPosts, getPostDetail } from "../api";

const BG_ARTICLE = "rgba(241,240,227,0.75)";
const BG_FORUM   = "rgba(233,216,191,0.75)";

const FETCH_PAGE_SIZE = 6;
const DETAIL_CONCURRENCY = 6;

// Custom scrollbar styling
const SCROLL_WIDTH    = 4;
const SC_TRACK_COLOR  = "rgb(237, 229, 213)";
const SC_THUMB_COLOR  = "rgba(226, 152, 56, 0.88)";
const SC_THUMB_BORDER = "rgba(0,0,0,0.35)";
const SC_GUTTER       = 6;

// Small heart icon for likes
const Heart = ({ className = "w-3.5 h-3.5" }) => (
  <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" className={className}>
    <path
      d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1a5.5 5.5 0 1 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.8z"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

// "Forum" / "Article" badge on each card
const Badge = ({ type }) => {
  const isForum = String(type) === "forum";
  return (
    <span
      className="inline-flex px-2 py-0.5 text-[12px] rounded-full border border-white/60"
      style={{
        background: isForum ? BG_FORUM : BG_ARTICLE,
        color: isForum ? "#1a3f7a" : "#245a2a",
      }}
    >
      {isForum ? "Forum" : "Article"}
    </span>
  );
};

// Background colour used for subtheme sentiment chips
const subBg = (emo) => {
  const v = String(emo || "").toLowerCase();
  if (v === "positive") return "#f9a7044e";
  if (v === "negative") return "#ff000024";
  if (v === "neutral")  return "#F0F0F0";
  return "rgba(255, 255, 255, 0.7)";
};

// Fetch subs_sentiment for a batch of post keys with limited concurrency
const fetchAllSubsForKeys = async (keys, signal) => {
  const local = new Map();
  let active = 0;
  let idx = 0;

  const isAborted = () => signal?.aborted;

  return new Promise((resolve, reject) => {
    const pump = () => {
      if (isAborted()) return reject(new DOMException("Aborted", "AbortError"));
      if (idx >= keys.length && active === 0) return resolve(local);

      while (active < DETAIL_CONCURRENCY && idx < keys.length) {
        const k = keys[idx++];
        active += 1;
        getPostDetail(k)
          .then((d) => {
            local.set(k, d?.subs_sentiment ?? {});
          })
          .catch(() => {
            local.set(k, {});
          })
          .finally(() => {
            active -= 1;
            pump();
          });
      }
    };
    pump();
  });
};

// Merge old and new lists by unique key, preserving order
const mergeUnique = (oldList, newList) => {
  const seen = new Set();
  const res  = [];
  for (const it of [...oldList, ...newList]) {
    const key = it.tag || it.id || it.key || it._id;
    if (!key) continue;
    if (seen.has(key)) continue;
    seen.add(key);
    res.push(it);
  }
  return res;
};

export default function PostFeedList({
  year,
  month,
  filterFlipKey,
  sentiment = null,
  subtheme = "",
  dimension = "",
  onOpenPost,
}) {
  const [items, setItems]       = useState([]);
  const [err, setErr]           = useState("");

  const [page, setPage]         = useState(1);
  const [hasMore, setHasMore]   = useState(true);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  // Cache for subsentiment: Map<postKey, subs_sentiment object>
  const [subsCache, setSubsCache] = useState(() => new Map());

  const scRef       = useRef(null);
  const sentinelRef = useRef(null);

  const [hovering, setHovering]   = useState(false);
  const [scrolling, setScrolling] = useState(false);
  const [thumb, setThumb]         = useState({ top: 0, height: 0 });
  const hideTimer = useRef(null);

  const postsAbortRef = useRef(null);

  const [isTouch, setIsTouch] = useState(false);

  // Detect touch devices for better scroll behaviour
  useEffect(() => {
    const val =
      typeof window !== "undefined" &&
      ("ontouchstart" in window ||
        navigator.maxTouchPoints > 0 ||
        navigator.msMaxTouchPoints > 0);
    setIsTouch(Boolean(val));
  }, []);

  // Initial load and refetch whenever filters or flipKey change
  useEffect(() => {
    postsAbortRef.current?.abort();
    const ctrl = new AbortController();
    postsAbortRef.current = ctrl;

    setErr("");
    setItems([]);
    setSubsCache(new Map());
    setPage(1);
    setHasMore(true);
    setLoadingMore(false);
    setLoadingList(true);
    if (scRef.current) scRef.current.scrollTop = 0;

    (async () => {
      try {
        const res = await getPosts({
          page: 1,
          size: FETCH_PAGE_SIZE,
          year,
          month,
          sentiment,
          subtheme,
          dimension,
          signal: ctrl.signal,
        });

        const arr = Array.isArray(res?.items) ? res.items : [];
        const keys = arr.map((it) => it.tag || it.id).filter(Boolean);

        const subsMap = await fetchAllSubsForKeys(keys, ctrl.signal);

        if (ctrl.signal.aborted) return;
        setItems(arr);
        setSubsCache(subsMap);
        setHasMore(Boolean(res?.hasMore ?? (arr.length === FETCH_PAGE_SIZE)));
      } catch (e) {
        if (e.name !== "AbortError") setErr(e?.message || String(e));
      } finally {
        if (!ctrl.signal.aborted) setLoadingList(false);
      }
    })();

    return () => ctrl.abort();
  }, [year, month, sentiment, subtheme, dimension, filterFlipKey]);

  // Custom scroll thumb: keep it in sync with content height and scrollTop
  useEffect(() => {
    const el = scRef.current;
    if (!el) return;

    const update = () => {
      const { scrollHeight, scrollTop, clientHeight } = el;
      if (scrollHeight <= clientHeight) {
        setThumb({ top: 0, height: 0 });
        return;
      }
      const available = clientHeight - SC_GUTTER * 2;
      const height = Math.max(24, available * (clientHeight / scrollHeight));
      const top =
        SC_GUTTER +
        (scrollTop / (scrollHeight - clientHeight)) * (available - height);
      setThumb({ top, height });
    };

    const onScroll = () => {
      update();
      setScrolling(true);
      clearTimeout(hideTimer.current);
      hideTimer.current = setTimeout(() => setScrolling(false), 400);
    };

    update();
    el.addEventListener("scroll", onScroll, { passive: true });

    const ro = new ResizeObserver(update);
    ro.observe(el);

    return () => {
      el.removeEventListener("scroll", onScroll);
      ro.disconnect();
    };
  }, [items.length, loadingList]);

  // IntersectionObserver used to trigger loading the next page
  useEffect(() => {
    const root = scRef.current;
    const sentinel = sentinelRef.current;
    if (!root || !sentinel) return;

    const loadNextPage = async () => {
      if (!hasMore || loadingMore || loadingList) return;

      const ctrl = new AbortController();
      postsAbortRef.current = ctrl;
      setLoadingMore(true);

      try {
        const res = await getPosts({
          page: page + 1,
          size: FETCH_PAGE_SIZE,
          year,
          month,
          sentiment,
          subtheme,
          dimension,
          signal: ctrl.signal,
        });

        const arr = Array.isArray(res?.items) ? res.items : [];
        const keys = arr.map((it) => it.tag || it.id).filter(Boolean);

        const subsMap = await fetchAllSubsForKeys(keys, ctrl.signal);
        if (ctrl.signal.aborted) return;

        setItems((prev) => mergeUnique(prev, arr));
        setSubsCache((prev) => {
          const next = new Map(prev);
          for (const [k, v] of subsMap.entries()) next.set(k, v);
          return next;
        });

        setHasMore(Boolean(res?.hasMore ?? (arr.length === FETCH_PAGE_SIZE)));
        setPage((p) => p + 1);
      } catch (e) {
        if (e.name !== "AbortError") setErr(e?.message || String(e));
      } finally {
        if (!ctrl.signal.aborted) setLoadingMore(false);
      }
    };

    const io = new IntersectionObserver(
      (entries) => {
        const ent = entries[0];
        if (ent.isIntersecting) loadNextPage();
      },
      { root, threshold: 0.1 }
    );

    io.observe(sentinel);
    return () => io.disconnect();
  }, [hasMore, loadingMore, loadingList, page, year, month, sentiment, subtheme, dimension]);

  return (
    <>
      {err && (
        <div className="mx-1 mb-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {err}
        </div>
      )}

      <div className="relative h-full px-1 overflow-hidden">
        <div
          ref={scRef}
          className="h-full no-native-scrollbar"
          style={{
            // Only show scrollbars when hovering (or on touch) and not during initial loading
            overflowY: (isTouch || hovering) && !loadingList ? "auto" : "hidden",
            position: "relative",
            WebkitOverflowScrolling: "touch",
            touchAction: "pan-y",
          }}
          onMouseEnter={() => setHovering(true)}
          onMouseLeave={() => setHovering(false)}
          onTouchStart={() => setHovering(true)}
          onTouchEnd={() => setHovering(false)}
        >
          {/* Empty state */}
          {!loadingList && items.length === 0 && (
            <div className="flex h-full items-center justify-center text-[17px] text-neutral-500">
              No results.
            </div>
          )}

          {/* Grid of post cards */}
          {!loadingList && items.length > 0 && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {items.map((it, i) => {
                const like = it.likes ?? it.score ?? 0;
                const key  = it.tag || it.id;
                const dict = subsCache.get(key) || {};

                return (
                  <button
                    key={key + "-" + i}
                    onClick={() => onOpenPost?.(key)}
                    className="relative flex flex-col gap-2 rounded-xl border border-white/60 px-5 py-4 text-left shadow-sm transition-all hover:-translate-y-[1px]"
                    style={{ background: it.type === "forum" ? BG_FORUM : BG_ARTICLE }}
                  >
                    <div className="flex items-start justify-between">
                      <Badge type={it.type} />
                      <div className="flex items-center gap-3 text-neutral-800">
                        <span className="text-[12px] tabular-nums">{it.time}</span>
                        <span className="flex items-center gap-1">
                          <Heart className="w-3.5 h-3.5" />
                          <span className="text-[12px] tabular-nums">{like}</span>
                        </span>
                      </div>
                    </div>

                    <div className="text-[15px] font-semibold text-neutral-900 md:text-[16px]">
                      {it.title}
                    </div>

                    {it.dimensions && it.dimensions.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {it.dimensions.map((d) => (
                          <span
                            key={d}
                            className="rounded-full border border-white/60 bg-white/70 px-2 py-0.5 text-[11px] whitespace-nowrap"
                          >
                            {d}
                          </span>
                        ))}
                      </div>
                    )}

                    {dict && Object.keys(dict).length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {Object.entries(dict).map(([k, v]) => (
                          <span
                            key={k}
                            className="rounded-full border border-white/60 px-2 py-0.5 text-[12px] whitespace-nowrap"
                            style={{ background: subBg(v) }}
                            title={k + " — " + v}
                          >
                            {k}
                          </span>
                        ))}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          )}

          {/* Sentinel for infinite scroll */}
          {!loadingList && hasMore && <div ref={sentinelRef} className="h-8 w-full" />}

          {/* "Loading more..." indicator */}
          {loadingMore && (
            <div className="my-3 flex items-center justify-center">
              <div className="rounded-md border border-white/60 bg-white/85 px-3 py-1.5 shadow-sm">
                <div className="flex items-center gap-2">
                  <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-neutral-400 border-t-transparent" />
                  <span className="text-[13px] text-neutral-700">
                    Loading more…
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Custom vertical scrollbar overlay */}
        {!loadingList && thumb.height > 0 && !isTouch && (
          <div
            className="pointer-events-none absolute top-0 right-0 h-full transition-opacity duration-150"
            style={{ width: SCROLL_WIDTH, opacity: hovering || scrolling ? 1 : 0 }}
          >
            <div
              className="absolute right-0 top-0 h-full rounded-full"
              style={{
                width: SCROLL_WIDTH,
                background: SC_TRACK_COLOR,
                boxShadow: "inset 0 0 1px rgba(255,255,255,0.04)",
              }}
            />
            <div
              className="absolute right-0 rounded-full"
              style={{
                width: SCROLL_WIDTH,
                top: thumb.top,
                height: thumb.height,
                background: SC_THUMB_COLOR,
                boxShadow: "inset 0 0 0 1px " + SC_THUMB_BORDER,
              }}
            />
          </div>
        )}

        {/* Full-screen loading overlay for initial fetch / filter change */}
        {loadingList && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="rounded-xl border border-white/60 bg-white/85 px-4 py-3 shadow-sm backdrop-blur-[2px]">
              <div className="flex items-center gap-3">
                <span
                  className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-neutral-400 border-t-transparent"
                  aria-hidden
                />
                <span className="text-sm text-neutral-700">
                  Loading filtered results…
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
