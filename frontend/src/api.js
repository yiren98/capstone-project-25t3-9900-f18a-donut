// src/api.js

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, { credentials: "include", ...options });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data && data.message) msg = data.message;
    } catch { /* noop */ }
    throw new Error(msg);
  }
  return res.json();
}

function toYMD(s) {
  if (!s) return "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
  const d = new Date(s);
  if (!isNaN(d)) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }
  const parts = String(s).split(/[ T]/)[0]?.split(/[/.]/);

  if (parts && parts.length >= 3) {
    const [y, m, d2] =
      parts[0].length === 4 ? [parts[0], parts[1], parts[2]] : [parts[2], parts[0], parts[1]];
    return `${String(y).padStart(4, "0")}-${String(m).padStart(2, "0")}-${String(d2).padStart(2, "0")}`;
  }
  return s;
}

function stripRedditPrefix(pid = "") {
  if (!pid) return "";
  const idx = pid.indexOf("_");
  return idx >= 0 ? pid.slice(idx + 1) : pid;
}

const toInt = (v) => {
  if (v === null || v === undefined || v === "") return undefined;
  const n = Number(v);
  return Number.isFinite(n) ? Math.trunc(n) : undefined;
};

/* ==== SBI ==== */
export const getSBI = async ({ year, month } = {}) => {
  const y = toInt(year);
  if (!Number.isInteger(y)) throw new Error("year is required");
  const params = new URLSearchParams({ year: String(y) });
  const m = toInt(month);
  if (Number.isInteger(m)) params.set("month", String(m));
  return fetchJSON(`/api/sbi?${params.toString()}`);
};

/* ==== Posts ==== */

export const getPosts = ({ page = 1, size = 6, q = "", tag = "", year, month, dimension = "", subtheme = "", sentiment = "" } = {}) => {
  const params = new URLSearchParams({ page: String(page), size: String(size) });
  if (q && String(q).trim()) params.set("q", String(q).trim());
  if (tag && String(tag).trim()) params.set("tag", String(tag).trim());

  const y = toInt(year);
  const m = toInt(month);
  if (Number.isInteger(y)) params.set("year", String(y));
  if (Number.isInteger(m)) params.set("month", String(m));

  if (dimension) params.set("dimension", String(dimension));
  if (subtheme)  params.set("subtheme", String(subtheme));
  if (sentiment) params.set("sentiment", String(sentiment).toLowerCase());

  return fetchJSON(`/api/posts?${params.toString()}`).then((data) => {
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
    subs_sentiment: typeof detail.subs_sentiment === "object" ? detail.subs_sentiment : {},
    source: detail.source || "",
  };
};

export const getPostComments = ({ id, page = 1, size = 100 } = {}) => {
  if (!id) throw new Error("post id is required");
  const params = new URLSearchParams({ page: String(page), size: String(size) });
  return fetchJSON(`/api/posts/${encodeURIComponent(id)}/comments?${params.toString()}`).then(
    (data) => {
      const items = (data.items || []).map((c) => ({
        ...c,
        time: toYMD(c.time),
        parent_comment_id_norm:
          c.parent_comment_id_norm || stripRedditPrefix(c.parent_id || ""),
        comment_id_norm:
          c.comment_id_norm || stripRedditPrefix(c.comment_id || ""),
      }));
      return { ...data, items };
    }
  );
};

export function buildCommentTree(flatItems = []) {
  const lvl1 = [];
  const map = new Map();
  for (const c of flatItems) {
    if (Number(c.level) === 1 || Number(c.depth) === 0) {
      const key = c.comment_id_norm || stripRedditPrefix(c.comment_id || "");
      const node = { ...c, comment_id_norm: key, replies: [] };
      lvl1.push(node);
      map.set(key, node);
    }
  }
  for (const c of flatItems) {
    if (Number(c.level) === 2 || Number(c.depth) === 1) {
      const key = c.parent_comment_id_norm || stripRedditPrefix(c.parent_id || "");
      const parent = map.get(key);
      if (parent) parent.replies.push(c);
      else lvl1.push({ ...c, replies: [], _dangling: true });
    }
  }
  return lvl1;
}

export async function getPostWithComments(id, { page = 1, size = 100 } = {}) {
  const [post, commentsPage] = await Promise.all([
    getPostDetail(id),
    getPostComments({ id, page, size }),
  ]);
  const tree = buildCommentTree(commentsPage.items);
  return { post, comments: { ...commentsPage, tree } };
}

// ==== Sentiment aggregate ====
export const getSentimentStats = async ({
  year,
  month,
  dimension = "",
  subtheme = "",
} = {}) => {
  const toInt = (v) => {
    if (v === null || v === undefined || v === "") return undefined;
    const n = Number(v);
    return Number.isFinite(n) ? Math.trunc(n) : undefined;
  };
  const params = new URLSearchParams();
  const y = toInt(year);
  const m = toInt(month);
  if (Number.isInteger(y)) params.set("year", String(y));
  if (Number.isInteger(m)) params.set("month", String(m));
  if (dimension) params.set("dimension", String(dimension));
  if (subtheme) params.set("subtheme", String(subtheme));
  return fetch(`/api/sentiment_stats?${params.toString()}`, { credentials: "include" })
    .then(async (r) => {
      if (!r.ok) {
        let msg = `${r.status} ${r.statusText}`;
        try { const j = await r.json(); if (j.message) msg = j.message; } catch { /* noop */ }
        throw new Error(msg);
      }
      return r.json();
    });
};

export async function getDimensionCounts({ year, month } = {}) {
  const qs = new URLSearchParams();
  if (year) qs.set("year", year);
  if (month) qs.set("month", month);
  const res = await fetch(`/api/dimension_counts?${qs.toString()}`);
  if (!res.ok) throw new Error("dimension_counts failed");
  return res.json(); // [{ name, count, color? }]
}

export async function getSubthemeCounts({ year, month, dimension }) {
  const qs = new URLSearchParams();
  if (dimension) qs.set("dimension", dimension);
  if (year) qs.set("year", year);
  if (month) qs.set("month", month);
  const res = await fetch(`/api/subtheme_counts?${qs.toString()}`);
  if (!res.ok) throw new Error("subtheme_counts failed");
  return res.json(); // [{ name, count, color? }]
}

const BASE =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

console.log("🔗 Backend API Base URL:", BASE);

// 通用 GET 请求函数
const jget = async (url) => {
  try {
    const r = await fetch(url, { credentials: "include" });
    if (!r.ok) {
      const text = await r.text();
      throw new Error(`Request failed (${r.status}): ${text}`);
    }
    return r.json();
  } catch (err) {
    console.error("❌ API fetch error:", err);
    throw err;
  }
};

// ===============================
// Culture Analysis APIs
// ===============================

export const getCAOverall = () => jget(`${BASE}/ca/overall`);

export const getCADimension = (name) =>
  jget(`${BASE}/ca/dimension/${encodeURIComponent(name)}`);

export const getCASubthemes = (dimension) =>
  jget(`${BASE}/ca/subthemes?dimension=${encodeURIComponent(dimension)}`);

export const getCASubthemeByFile = (file) =>
  jget(`${BASE}/ca/subtheme/by-file/${encodeURIComponent(file)}`);

export const getCAIndex = () => jget(`${BASE}/ca/index`);