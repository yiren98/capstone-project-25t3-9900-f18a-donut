import React, { useEffect, useState } from "react";
import { getPostDetail, getPostComments, buildCommentTree } from "../api";

const BG_FORUM   = "rgba(233,216,191,0.75)";
const BG_ARTICLE = "rgba(241,240,227,0.75)";

const COMMENT_SIZE = 100;

// Re-usable heart icon (same look as in list)
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

// "Forum" / "Article" label
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

// Background colour for subtheme sentiment chips
const subBg = (emo) => {
  const v = String(emo || "").toLowerCase();
  if (v === "positive") return "#f9a7044e";
  if (v === "negative") return "#ff000024";
  if (v === "neutral")  return "#F0F0F0";
  return "rgba(255, 255, 255, 0.7)";
};

// Basic cleaning for text from the API
const sanitize = (txt) => {
  const s = String(txt ?? "").trim();
  if (!s || s.toLowerCase() === "nan") return "";
  return s;
};

// Normalize one comment node to a flat structure we can safely render
const normalizeCommentNode = (n = {}) => ({
  ...n,
  author: n.author || "Anon",
  time: n.time || n.created_time || "",
  score: n.score ?? n.likes ?? n.ups ?? 0,
  content: sanitize(n.body ?? n.text ?? n.content ?? ""),
  replies: Array.isArray(n.replies) ? n.replies.map(normalizeCommentNode) : [],
});

// Normalize an entire tree of comment nodes
const normalizeTree = (nodes = []) => nodes.map(normalizeCommentNode);

// Recursive comment renderer for threaded comment trees
function CommentNode({ node, depth = 0 }) {
  const score = node.score ?? node.likes ?? node.ups ?? 0;
  const content = node.content ?? node.body ?? node.text ?? "";

  return (
    <div className="rounded-lg border border-white/60 bg-white/70 px-3 py-2">
      <div className="mb-1 flex items-center justify-between text-[12px] text-neutral-600">
        <span className="truncate">
          {node.author || "Anon"} •{" "}
          <span className="tabular-nums">{node.time || ""}</span>
        </span>
        <span className="inline-flex items-center gap-1 text-neutral-700">
          <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" className="w-3 h-3">
            <path
              d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1a5.5 5.5 0 1 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.8z"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="tabular-nums">{score}</span>
        </span>
      </div>

      <div className="text-[14px] text-neutral-900 whitespace-pre-wrap">
        {content || "(empty)"}
      </div>

      {Array.isArray(node.replies) && node.replies.length > 0 && (
        <div className="mt-2 space-y-2 pl-3 border-l border-neutral-300/50">
          {node.replies.map((r) => (
            <CommentNode
              key={r.comment_id_norm || r.comment_id || Math.random()}
              node={r}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Detail view: fetch and display a single post and its comments (if any)
export default function PostFeedDetail({ postKey, onBack }) {
  const [post, setPost]       = useState(null);
  const [err, setErr]         = useState("");

  const [cmtLoading, setCmtLoading] = useState(false);
  const [cmtErr, setCmtErr]         = useState("");
  const [cmtTree, setCmtTree]       = useState([]);
  const [cmtOpen, setCmtOpen]       = useState(true);

  // Fetch post detail + comments when postKey changes
  useEffect(() => {
    if (!postKey) return;

    let cancelled = false;
    setErr("");
    setPost(null);
    setCmtTree([]);
    setCmtErr("");
    setCmtLoading(false);

    (async () => {
      try {
        const d = await getPostDetail(postKey);
        if (cancelled) return;
        setPost(d);

        // For forum posts, we also fetch the comment tree
        if (String(d.type) === "forum") {
          setCmtLoading(true);
          try {
            const cpage = await getPostComments({
              id: postKey,
              page: 1,
              size: COMMENT_SIZE,
            });
            const raw = Array.isArray(cpage?.tree)
              ? cpage.tree
              : buildCommentTree(cpage?.items || []);
            if (cancelled) return;
            setCmtTree(normalizeTree(raw));
          } catch (e) {
            if (cancelled) return;
            setCmtErr(e?.message || String(e));
            setCmtTree([]);
          } finally {
            if (!cancelled) setCmtLoading(false);
          }
        }
      } catch (e) {
        if (!cancelled) setErr(e?.message || String(e));
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [postKey]);

  // Loading state while we wait for the detail to come back
  if (!post && !err) {
    return (
      <div className="relative h-full rounded-2xl border border-[rgb(200,190,170)] bg-[#f6f3ef] shadow-sm">
        <div className="flex h-full items-center justify-center text-sm text-neutral-600">
          Loading post…
        </div>
      </div>
    );
  }

  // Error state with a simple "back to list" button
  if (err) {
    return (
      <div className="relative h-full rounded-2xl border border-[rgb(200,190,170)] bg-[#f6f3ef] shadow-sm">
        <div className="flex h-full flex-col items-center justify-center gap-3 text-sm text-red-700">
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2">
            {err}
          </div>
          <button
            onClick={onBack}
            className="rounded-lg border border-white/60 bg-white/70 px-3 py-1 text-sm text-neutral-700 hover:text-neutral-900"
          >
            Back to list
          </button>
        </div>
      </div>
    );
  }

  if (!post) return null;

  return (
    <div className="relative h-full rounded-2xl border border-[rgb(200,190,170)] bg-[#f6f3ef] shadow-sm">
      <div className="flex items-center justify-between px-5 py-3">
        <div className="flex items-center gap-2 pr-4">
          <Badge type={post.type} />
          <h3 className="line-clamp-2 text-[17px] font-semibold text-neutral-900 md:text-[18px]">
            {post.title}
          </h3>
        </div>
        <button
          onClick={onBack}
          className="rounded-lg border border-white/60 bg-white/70 px-2 py-0.5 text-sm text-neutral-600 hover:text-neutral-900"
        >
          Back
        </button>
      </div>

      <div className="flex flex-wrap gap-4 px-5 pb-2 text-sm text-neutral-600">
        {post.author && (
          <span>
            Author: <b className="text-neutral-800">{post.author}</b>
          </span>
        )}
        <span className="tabular-nums">Date: {post.time}</span>
        <span className="flex items-center gap-1">
          <Heart className="w-3.5 h-3.5" />
          <span className="tabular-nums">
            {post.likes ?? post.score ?? 0}
          </span>
        </span>
        {post.source && (
          <span className="truncate">
            Source: <b className="text-neutral-800">{post.source}</b>
          </span>
        )}
      </div>

      <div className="h-[calc(100%-94px)] overflow-y-auto px-5 pb-4">
        {/* Main content text */}
        <div className="max-h-[160px] overflow-y-auto rounded-xl border border-white/70 bg-white/70 px-4 py-3 text-[15px]">
          {(post.content || "").trim() || "(No content)"}
        </div>

        {/* Dimension chips */}
        {post.dimensions && post.dimensions.length > 0 && (
          <div className="mb-3 mt-3 flex flex-wrap gap-1.5">
            {post.dimensions.map((d) => (
              <span
                key={d}
                className="rounded-full border border-white/60 bg-white/80 px-2 py-0.5 text-[11px]"
              >
                {d}
              </span>
            ))}
          </div>
        )}

        {/* Subtheme sentiment chips */}
        {post.subs_sentiment && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {Object.entries(post.subs_sentiment).map(([k, v]) => (
              <span
                key={k}
                className="rounded-full border border-white/60 px-2 py-0.5 text-[12px]"
                style={{ background: subBg(v) }}
              >
                {k}
              </span>
            ))}
          </div>
        )}

        {/* Comments section for forum posts */}
        {String(post.type) === "forum" && (
          <div className="mt-3">
            <div className="flex items-center justify-between">
              <h4 className="text-[14px] font-semibold text-neutral-800">
                Comments
              </h4>
              <button
                onClick={() => setCmtOpen((v) => !v)}
                className="text-[12px] text-neutral-600 hover:text-neutral-900"
              >
                {cmtOpen ? "Hide" : "Show"}
              </button>
            </div>

            {cmtErr && (
              <div className="mt-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
                {cmtErr}
              </div>
            )}

            {cmtOpen && (
              <div className="mt-2">
                {cmtLoading ? (
                  <div className="text-[12px] text-neutral-600">Loading comments…</div>
                ) : cmtTree.length === 0 ? (
                  <div className="text-[12px] text-neutral-600">No comments</div>
                ) : (
                  <div className="space-y-3">
                    {cmtTree.map((c) => (
                      <CommentNode
                        key={c.comment_id_norm || c.comment_id || Math.random()}
                        node={c}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Simple note for non-forum posts */}
        {String(post.type) !== "forum" && (
          <div className="mt-3 text-[12px] text-neutral-500">
            This is an article (no comments).
          </div>
        )}
      </div>
    </div>
  );
}
