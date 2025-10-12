export default function Pager({ page, size, total, onPrev, onNext }) {
  const totalPages = Math.max(1, Math.ceil((total || 0) / size));
  return (
    <div className="flex items-center gap-3 text-sm">
      <button className="px-3 py-1.5 rounded-lg ring-1 ring-black/10 bg-white hover:bg-gray-50 transition disabled:opacity-40"
              onClick={onPrev} disabled={page<=1}>👈 Prev</button>
      <span className="text-stone">Page {page} / {totalPages}</span>
      <button className="px-3 py-1.5 rounded-lg ring-1 ring-black/10 bg-white hover:bg-gray-50 transition disabled:opacity-40"
              onClick={onNext} disabled={page>=totalPages}>Next 👉</button>
    </div>
  );
}
