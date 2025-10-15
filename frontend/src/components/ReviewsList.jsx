function escapeHTML(s = "") {
  return s.replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}
function stripe(sent) {
  const s = (sent || "").toLowerCase();
  if (s === "positive") return "strip-pos";
  if (s === "negative") return "strip-neg";
  return "strip-neu";
}

function formatYearMonth(dateStr) {
  if (!dateStr) return "Unknown date";
  if (/^\d{4}-\d{2}$/.test(dateStr)) {
    const [y, m] = dateStr.split("-").map(Number);
    const dt = new Date(y, m - 1, 1);
    return dt.toLocaleString("en-AU", { year: "numeric", month: "short" }); // "Sep 2025"
  }
  const dt = new Date(dateStr);
  return isNaN(dt) ? "Unknown date" : dt.toLocaleString("en-AU", { year: "numeric", month: "short" });
}

function Badge({ sent }) {
  const s = (sent || "").toLowerCase();
  if (s === "positive")
    return <span className="text-xs px-2 py-0.5 rounded-full ring-1 text-green-700 ring-green-600/20 bg-green-50">Positive</span>;
  if (s === "negative")
    return <span className="text-xs px-2 py-0.5 rounded-full ring-1 text-red-700 ring-red-600/20 bg-red-50">Negative</span>;
  return <span className="text-xs px-2 py-0.5 rounded-full ring-1 text-gray-600 ring-gray-500/20 bg-gray-50">Neutral</span>;
}

export default function ReviewsList({ items, loading }) {
  if (loading) return <div className="text-center text-stone py-16">Loading…</div>;
  if (!items?.length) return <div className="text-center text-stone py-16">No data</div>;

  return (
    <div className="grid grid-cols-1 gap-5">
      {items.map((r, i) => (
          <article
            key={r.id ?? i}
            className={`p-5 rounded-2xl bg-white shadow-sm ring-1 ring-black/5
                        hover:shadow-md focus-visible:shadow-md
                        transition-transform transition-shadow duration-300
                        hover:-translate-y-1 focus-visible:-translate-y-1
                        ${stripe(r?.sentiment)}`}
            tabIndex={0}
          >


          <div className="flex items-center gap-3 mb-2">
            <Badge sent={r?.sentiment} />
            <span className="text-xs text-stone">#{r?.id ?? ""}</span>
            {r?.dimension && <span className="text-xs text-stone/80">• {r.dimension}</span>}
            {(r?.region || r?.year) && (
              <span className="ml-auto text-xs text-stone/70">
                {r?.region ? `${r.region} - ` : ""}
                {formatYearMonth(r?.year)}
              </span>
            )}
          </div>
          <div
            className="text-[15px] leading-relaxed text-ink"
            dangerouslySetInnerHTML={{ __html: escapeHTML(r?.text || "") }}
          />
        </article>
      ))}
    </div>
  );
}