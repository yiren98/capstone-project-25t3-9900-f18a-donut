// src/api.js
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

// ✅ 新增：地区 / 年份 查询片段
function buildRegionYearQuery({ region, year } = {}) {
  const q = {};
  if (region && String(region).trim() && String(region).trim() !== 'All') {
    q.region = String(region).trim();
  }
  if (year && String(year).trim() && String(year).trim() !== 'All') {
    q.year = String(year).trim(); // 支持 '2024' 或 '2024-06'
  }
  return q;
}

// Public API
export const getKpis = ({ dimension, mode, region, year } = {}) => {
  const params = new URLSearchParams({
    ...buildDimsQuery({ dimension, mode }),
    ...buildRegionYearQuery({ region, year }),
  });
  const query = params.toString();
  return fetchJSON(`/api/kpis${query ? `?${query}` : ''}`);
};

export const getYears = async () => {
  const res = await fetch('/api/years');
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json(); // { years: [...] }
};

export const getReviews = ({
  sentiment = 'all',
  page = 1,
  size = 10,
  dimension,
  mode,
  region,
  year,
} = {}) => {
  const base = {
    sentiment: String(sentiment || 'all'),
    page: String(page || 1),
    size: String(size || 10),
  };
  const params = new URLSearchParams({
    ...base,
    ...buildDimsQuery({ dimension, mode }),
    ...buildRegionYearQuery({ region, year }),
  }).toString();

  return fetchJSON(`/api/reviews?${params}`);
};
