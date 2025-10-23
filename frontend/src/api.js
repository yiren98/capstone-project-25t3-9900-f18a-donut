// src/api.js

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, {
    credentials: "include",
    ...options,
  });
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

/* ==== Post APIs ==== */

export const getPosts = ({ page = 1, size = 10, q = "", tag = "" } = {}) => {
  const params = new URLSearchParams({
    page: String(page),
    size: String(size),
  });
  if (q && String(q).trim()) params.set("q", String(q).trim());
  if (tag && String(tag).trim()) params.set("tag", String(tag).trim());
  return fetchJSON(`/api/posts?${params.toString()}`);
};

export const getPostDetail = async (id) => {
  if (!id) throw new Error("post id is required");
  return fetchJSON(`/api/posts/${encodeURIComponent(id)}`);
};

export const getPostComments = ({ id, page = 1, size = 50 } = {}) => {
  if (!id) throw new Error("post id is required");
  const params = new URLSearchParams({
    page: String(page),
    size: String(size),
  });
  return fetchJSON(`/api/posts/${encodeURIComponent(id)}/comments?${params.toString()}`);
};
