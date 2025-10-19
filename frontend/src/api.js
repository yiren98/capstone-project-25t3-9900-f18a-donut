// src/api.js
async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

/* ==== ==== */
// function buildDimsQuery({ dimension, mode } = {}) {
//   const q = {};
//   if (Array.isArray(dimension)) {
//     if (dimension.length > 0) q.dimensions = dimension.join(',');
//   } else if (typeof dimension === 'string' && dimension.trim() && dimension !== 'All') {
//     q.dimensions = dimension.trim();
//   }
//   if (mode && (mode === 'any' || mode === 'all')) q.mode = mode;
//   return q;
// }
// function buildRegionYearQuery({ region, year } = {}) {
//   const q = {};
//   if (region && String(region).trim() && String(region).trim() !== 'All') {
//     q.region = String(region).trim();
//   }
//   if (year && String(year).trim() && String(year).trim() !== 'All') {
//     q.year = String(year).trim();
//   }
//   return q;
// }
// export const getKpis = ({ dimension, mode, region, year } = {}) => {
//   const params = new URLSearchParams({
//     ...buildDimsQuery({ dimension, mode }),
//     ...buildRegionYearQuery({ region, year }),
//   });
//   const query = params.toString();
//   return fetchJSON(`/api/kpis${query ? `?${query}` : ''}`);
// };
// export const getYears = async () => {
//   const res = await fetch('/api/years');
//   if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
//   return res.json();
// };
// export const getReviews = ({ sentiment = 'all', page = 1, size = 10, dimension, mode, region, year } = {}) => {
//   const base = { sentiment: String(sentiment || 'all'), page: String(page || 1), size: String(size || 10) };
//   const params = new URLSearchParams({
//     ...base,
//     ...buildDimsQuery({ dimension, mode }),
//     ...buildRegionYearQuery({ region, year }),
//   }).toString();
//   return fetchJSON(`/api/reviews?${params}`);
// };

export const getPosts = ({ page = 1, size = 10, q = "", hasComments = true } = {}) => {
  const params = new URLSearchParams({
    page: String(page),
    size: String(size),
  });
  if (q && String(q).trim()) params.set("q", String(q).trim());
  if (hasComments) params.set("has_comments", "true"); // 
  return fetchJSON(`/api/posts?${params.toString()}`);
};

export const getPostComments = ({ reddit_id, page = 1, size = 50 } = {}) => {
  if (!reddit_id) throw new Error("reddit_id is required");
  const params = new URLSearchParams({
    page: String(page),
    size: String(size),
  });
  return fetchJSON(`/api/posts/${encodeURIComponent(reddit_id)}/comments?${params.toString()}`);
};

