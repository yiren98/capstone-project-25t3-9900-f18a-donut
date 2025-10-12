export default function KpiCards({ total, pos, neg, enps }) {
  const Card = ({ label, value, valueClass = "" }) => (
    <div className="rounded-2xl bg-white shadow-sm ring-1 ring-black/5 p-6
                    flex items-center justify-between min-h-[92px]">
      <span className="text-xs uppercase tracking-wider text-gray-500">{label}</span>
      <span className={`text-4xl font-semibold ${valueClass}`}>{value}</span>
    </div>
  );
  const enpsColor = Number(enps) >= 0 ? "text-green-600" : "text-red-600";
  const enpsText = Number.isFinite(enps) ? enps.toFixed?.(2) ?? enps : "-";

  return (
    <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card label="TOTAL"    value={total ?? "-"} />
      <Card label="POSITIVE" value={pos ?? "-"} valueClass="text-green-600" />
      <Card label="NEGATIVE" value={neg ?? "-"} valueClass="text-red-600" />
      <Card label="ENPS"     value={enpsText} valueClass={enpsColor} />
    </section>
  );
}
