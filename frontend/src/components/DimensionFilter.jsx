const DIMENSIONS = [
  "All","Collaboration","Diversity","Inclusion",
  "Belonging","Innovation","Leadership","Recognition","Respect",
];

export default function DimensionFilter({ value, onChange }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-stone">Dimension</span>
      <select
        value={value}
        onChange={(e)=>onChange(e.target.value)}
        className="inline-flex h-9 items-center rounded-lg border border-gray-300 bg-white px-3 text-sm leading-5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
>
        {DIMENSIONS.map(d => <option key={d} value={d}>{d}</option>)}
      </select>
    </div>
  );
}
