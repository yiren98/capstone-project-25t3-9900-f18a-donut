export default function RegionFilter({ value, onChange }) {
  const regions = ["All", "Australia", "American", "United Kingdom", "Canada", "South Africa", "Singapore"];
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-600">Region</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="inline-flex h-9 items-center rounded-lg border border-gray-300 bg-white px-3 text-sm leading-5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
>
        {regions.map((r) => (
          <option key={r} value={r}>{r}</option>
        ))}
      </select>
    </div>
  );
}