async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}
function buildDimsQuery({ dimension, mode } = {}) {
  const q = {};

  if (Array.isArray(dimension)) {
    if (dimension.length > 0) q.dimensions = dimension.join(',');
  } else if (typeof dimension === 'string' && dimension.trim() && dimension !== 'All') {
    q.dimensions = dimension.trim();
  }
  if (mode && (mode === 'any' || mode === 'all')) q.mode = mode;

  return q;
}

// Public API
export const getKpis = ({ dimension, mode } = {}) => {
  const params = new URLSearchParams(buildDimsQuery({ dimension, mode }));
  const query = params.toString();
  return fetchJSON(`/api/kpis${query ? `?${query}` : ''}`);
};

export const getReviews = ({ sentiment = 'all', page = 1, size = 10, dimension, mode } = {}) => {
  const base = {
    sentiment: String(sentiment || 'all'),
    page: String(page || 1),
    size: String(size || 10),
  };
  const dimsPart = buildDimsQuery({ dimension, mode });

  const params = new URLSearchParams({ ...base, ...dimsPart }).toString();
  return fetchJSON(`/api/reviews?${params}`);
};
