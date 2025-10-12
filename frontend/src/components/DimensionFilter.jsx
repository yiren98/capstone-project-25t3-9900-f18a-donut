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
        className="text-sm rounded-lg bg-white ring-1 ring-black/10 px-3 py-2 hover:ring-black/20"
      >
        {DIMENSIONS.map(d => <option key={d} value={d}>{d}</option>)}
      </select>
    </div>
  );
}
