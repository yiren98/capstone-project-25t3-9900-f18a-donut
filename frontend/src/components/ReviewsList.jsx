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
    <div className="grid grid-cols-1 gap-3">
      {items.map((r, i) => (
        <article key={r.id ?? i} className={`p-4 rounded-2xl bg-white shadow-sm ring-1 ring-black/5 ${stripe(r?.sentiment)}`}>
          <div className="flex items-center gap-3 mb-2">
            <Badge sent={r?.sentiment} />
            <span className="text-xs text-stone">#{r?.id ?? ""}</span>
            {r?.dimension && <span className="text-xs text-stone/80">• {r.dimension}</span>}
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
