// src/api.js

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, { credentials: "include", ...options });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data && data.message) msg = data.message;
    } catch (_) {}
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
  const parts = String(s).split(/[ T]/)[0]?.split(/[\/.]/);
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

/* ==== Post APIs ==== */

export const getPosts = ({ page = 1, size = 6, q = "", tag = "" } = {}) => {
  const params = new URLSearchParams({ page: String(page), size: String(size) });
  if (q && String(q).trim()) params.set("q", String(q).trim());
  if (tag && String(tag).trim()) params.set("tag", String(tag).trim());

  return fetchJSON(`/api/posts?${params.toString()}`).then((data) => {
    const items = (data.items || []).map((it) => ({
      ...it,
      time: toYMD(it.time),

      likes: typeof it.score === "number" ? it.score : 0,
    }));
    return { ...data, items };
  });
};

export const getPostDetail = async (idOrTag) => {
  if (!idOrTag) throw new Error("post id is required");
  const detail = await fetchJSON(`/api/posts/${encodeURIComponent(idOrTag)}`);
  return { ...detail, time: toYMD(detail.time), likes: detail.score ?? 0 };
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
      }));
      return { ...data, items };
    }
  );
};

export function buildCommentTree(flatItems = []) {
  const lvl1 = [];
  const map = new Map();
  for (const c of flatItems) {
    if (Number(c.level) === 1 || Number(c.depth) <= 1) {
      const node = { ...c, replies: [] };
      lvl1.push(node);
      map.set(c.comment_id, node);
    }
  }
  for (const c of flatItems) {
    if (Number(c.level) === 2 || Number(c.depth) > 1) {
      const key = c.parent_comment_id_norm || stripRedditPrefix(c.parent_id || "");
      const parent = map.get(key);
      if (parent) parent.replies.push(c);
      else lvl1.push({ ...c, replies: [], _dangling: true });
    }
  }
  return lvl1;
}

export async function getPostWithComments(idOrTag, { page = 1, size = 100 } = {}) {
  const [post, commentsPage] = await Promise.all([
    getPostDetail(idOrTag),
    getPostComments({ id: idOrTag, page, size }),
  ]);
  const tree = buildCommentTree(commentsPage.items);
  return { post, comments: { ...commentsPage, tree } };
}
