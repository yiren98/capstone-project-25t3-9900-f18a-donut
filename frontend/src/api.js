const BASE = "https://capstone-project-25t3-9900-f18a-donut.onrender.com";

// async function fetchJSON(url, options = {}) {
//   const res = await fetch(url, { credentials: "include", ...options });
//   if (!res.ok) {
//     let msg = `${res.status} ${res.statusText}`;
//     try {
//       const data = await res.json();
//       if (data && data.message) msg = data.message;
//     } catch {
//       /* noop: fall back to status text */
//     }
//     throw new Error(msg);
//   }
//   return res.json();
// }

async function fetchJSON(url, options = {}) {
  const fullUrl = url.startsWith("http") ? url : `${BASE}${url}`;

  const res = await fetch(fullUrl, { credentials: "include", ...options });

  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data?.message) msg = data.message;
    } catch {}
    throw new Error(msg);
  }

  return res.json();
}


// Try to normalise various date formats into YYYY-MM-DD.
// Falls back to original input if it cannot parse.
function toYMD(s) {
  if (!s) return "";
  // Already in YYYY-MM-DD → just return it.
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;

  // Try native Date parsing first.
  const d = new Date(s);
  if (!isNaN(d)) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }

  // As a fallback, split the string and guess whether it's Y-M-D or D-M-Y.
  const parts = String(s).split(/[ T]/)[0]?.split(/[/.]/);
  if (parts && parts.length >= 3) {
    const [y, m, d2] =
      parts[0].length === 4
        ? [parts[0], parts[1], parts[2]] // 2025-11-03 style
        : [parts[2], parts[0], parts[1]]; // 03/11/2025 style
    return `${String(y).padStart(4, "0")}-${String(m).padStart(2, "0")}-${String(
      d2
    ).padStart(2, "0")}`;
  }
  // If we still cannot figure it out, keep the original string.
  return s;
}

// Reddit-style IDs sometimes carry a prefix ("t1_", "t3_", etc.).
// This helper strips that prefix for easier key comparison.
function stripRedditPrefix(pid = "") {
  if (!pid) return "";
  const idx = pid.indexOf("_");
  return idx >= 0 ? pid.slice(idx + 1) : pid;
}

// Safe "maybe integer" helper used for query params.
const toInt = (v) => {
  if (v === null || v === undefined || v === "") return undefined;
  const n = Number(v);
  return Number.isFinite(n) ? Math.trunc(n) : undefined;
};

/* ==== SBI (Sentiment Balance Index) ==== */

// Fetch SBI for a given year and optional month.
// Throws if year is missing / not an integer.
export const getSBI = async ({ year, month } = {}) => {
  const y = toInt(year);
  if (!Number.isInteger(y)) throw new Error("year is required");

  const params = new URLSearchParams({ year: String(y) });
  const m = toInt(month);
  if (Number.isInteger(m)) params.set("month", String(m));

  return fetchJSON(`/api/sbi?${params.toString()}`);
};

/* ==== Posts list + details + comments ==== */

// Fetch a paginated list of posts with optional filters.
// Also normalises some fields to keep the UI code simpler.
export const getPosts = ({
  page = 1,
  size = 6,
  q = "",
  tag = "",
  year,
  month,
  dimension = "",
  subtheme = "",
  sentiment = "",
} = {}) => {
  const params = new URLSearchParams({ page: String(page), size: String(size) });

  // Optional text search / tag filters.
  if (q && String(q).trim()) params.set("q", String(q).trim());
  if (tag && String(tag).trim()) params.set("tag", String(tag).trim());

  // Optional year/month filters.
  const y = toInt(year);
  const m = toInt(month);
  if (Number.isInteger(y)) params.set("year", String(y));
  if (Number.isInteger(m)) params.set("month", String(m));

  // Optional culture filters.
  if (dimension) params.set("dimension", String(dimension));
  if (subtheme) params.set("subtheme", String(subtheme));
  if (sentiment) params.set("sentiment", String(sentiment).toLowerCase());

  return fetchJSON(`/api/posts?${params}`)
    .then((data) => {
      const items = (data.items || []).map((it) => ({
        ...it,
        time: toYMD(it.time),
        likes: typeof it.score === "number" ? it.score : 0,
        type: it.type || "article",
        is_post: (it.type || "article") === "forum",
        dimensions: Array.isArray(it.dimensions) ? it.dimensions : [],
        source: it.source || "",
      }));
      return { ...data, items };
    });
};

// Single post detail + some normalisation for UI use.
export const getPostDetail = async (id) => {
  if (!id) throw new Error("post id is required");
  const detail = await fetchJSON(`/api/posts/${encodeURIComponent(id)}`);
  return {
    ...detail,
    time: toYMD(detail.time),
    likes: detail.score ?? 0,
    type: detail.type || "article",
    is_post: (detail.type || "article") === "forum",
    dimensions: Array.isArray(detail.dimensions) ? detail.dimensions : [],
    subthemes: Array.isArray(detail.subthemes) ? detail.subthemes : [],
    subs_sentiment:
      typeof detail.subs_sentiment === "object" ? detail.subs_sentiment : {},
    source: detail.source || "",
  };
};

// Fetch flat comments for a post, then normalise IDs and dates
// so that we can build a proper tree structure later.
export const getPostComments = ({ id, page = 1, size = 100 } = {}) => {
  if (!id) throw new Error("post id is required");
  const params = new URLSearchParams({ page: String(page), size: String(size) });

  return fetchJSON(
    `/api/posts/${encodeURIComponent(id)}/comments?${params.toString()}`
  ).then((data) => {
    const items = (data.items || []).map((c) => ({
      ...c,
      time: toYMD(c.time),
      parent_comment_id_norm:
        c.parent_comment_id_norm || stripRedditPrefix(c.parent_id || ""),
      comment_id_norm:
        c.comment_id_norm || stripRedditPrefix(c.comment_id || ""),
    }));
    return { ...data, items };
  });
};

// Build a shallow comment tree from "flat" rows.
// Only supports two levels: top-level + direct replies.
export function buildCommentTree(flatItems = []) {
  const lvl1 = [];
  const map = new Map();

  // First pass: collect level-1 comments (or depth 0).
  for (const c of flatItems) {
    if (Number(c.level) === 1 || Number(c.depth) === 0) {
      const key =
        c.comment_id_norm || stripRedditPrefix(c.comment_id || "");
      const node = { ...c, comment_id_norm: key, replies: [] };
      lvl1.push(node);
      map.set(key, node);
    }
  }

  // Second pass: attach level-2 comments as replies where possible.
  for (const c of flatItems) {
    if (Number(c.level) === 2 || Number(c.depth) === 1) {
      const key =
        c.parent_comment_id_norm || stripRedditPrefix(c.parent_id || "");
      const parent = map.get(key);
      if (parent) parent.replies.push(c);
      else lvl1.push({ ...c, replies: [], _dangling: true });
    }
  }

  return lvl1;
}

// Convenience helper: fetch both post and its comments tree together.
export async function getPostWithComments(
  id,
  { page = 1, size = 100 } = {}
) {
  const [post, commentsPage] = await Promise.all([
    getPostDetail(id),
    getPostComments({ id, page, size }),
  ]);
  const tree = buildCommentTree(commentsPage.items);
  return { post, comments: { ...commentsPage, tree } };
}

// ==== Sentiment aggregate ====

// Aggregate positive/negative counts at different levels (overall, by dimension, subtheme).
export const getSentimentStats = async ({
  year,
  month,
  dimension = "",
  subtheme = "",
} = {}) => {
  // Local copy of toInt to keep this function self-contained.
  const toIntLocal = (v) => {
    if (v === null || v === undefined || v === "") return undefined;
    const n = Number(v);
    return Number.isFinite(n) ? Math.trunc(n) : undefined;
  };

  const params = new URLSearchParams();
  const y = toIntLocal(year);
  const m = toIntLocal(month);

  if (Number.isInteger(y)) params.set("year", String(y));
  if (Number.isInteger(m)) params.set("month", String(m));
  if (dimension) params.set("dimension", String(dimension));
  if (subtheme) params.set("subtheme", String(subtheme));

  // This uses plain fetch instead of fetchJSON only because it was
  // written earlier; behaviour is kept consistent with manual error handling.
  return fetch(`/api/sentiment_stats?${params.toString()}`, {
    credentials: "include",
  }).then(async (r) => {
    if (!r.ok) {
      let msg = `${r.status} ${r.statusText}`;
      try {
        const j = await r.json();
        if (j.message) msg = j.message;
      } catch {
        /* noop */
      }
      throw new Error(msg);
    }
    return r.json();
  });
};

// ==== Dimension / Subtheme counts for radar ====

// Aggregated counts for each dimension (optionally filtered by year/month).
export async function getDimensionCounts({ year, month } = {}) {
  const qs = new URLSearchParams();
  if (year) qs.set("year", year);
  if (month) qs.set("month", month);

  return fetchJSON(`/api/dimension_counts?${qs.toString()}`);
}

export async function getSubthemeCounts({ year, month, dimension }) {
  const qs = new URLSearchParams();
  if (dimension) qs.set("dimension", dimension);
  if (year) qs.set("year", year);
  if (month) qs.set("month", month);

  return fetchJSON(`/api/subtheme_counts?${qs.toString()}`);
}

// ==== Culture Analysis (summary JSON endpoints) ====

// const BASE = "/api";
// const BASE = "https://capstone-project-25t3-9900-f18a-donut.onrender.com/api";

// Small helper for "simple GET + JSON" endpoints used by CA.
const jget = async (url) => {
  const r = await fetch(url, { credentials: "include" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
};

// Overall culture summary payload.
export const getCAOverall = () => jget(`${BASE}/ca/overall`);

// Dimension-level summary payload (one dimension at a time).
export const getCADimension = (name) =>
  jget(`${BASE}/ca/dimension/${encodeURIComponent(name)}`);

// List of subthemes and their files under a given dimension.
export const getCASubthemes = (dimension) =>
  jget(`${BASE}/ca/subthemes?dimension=${encodeURIComponent(dimension)}`);

// Subtheme summary payload, looked up by underlying file name.
export const getCASubthemeByFile = (file) =>
  jget(`${BASE}/ca/subtheme/by-file/${encodeURIComponent(file)}`);

// Index of dimensions / subthemes used to build the CA filter panel.
export const getCAIndex = () => jget(`${BASE}/ca/index`);
