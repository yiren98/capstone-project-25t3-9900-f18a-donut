export default function SentimentTabs({ value, onChange }) {
  const Btn = ({ v, label }) => {
    const active = value === v;
    return (
      <button
        onClick={() => onChange(v)}
        className={[
          "px-4 py-1.5 text-sm rounded-lg transition",
          active ? "bg-white shadow-sm ring-1 ring-black/5" : ""
        ].join(" ").trim()}
      >
        {label}
      </button>
    );
  };
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-stone">Sentiment</span>
      <div className="inline-flex items-center rounded-xl bg-gray-100 p-1">
        <Btn v="all" label="All" />
        <Btn v="positive" label="Positive" />
        <Btn v="negative" label="Negative" />
      </div>
    </div>
  );
}
