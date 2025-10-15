import { useEffect, useState } from "react";
import { getYears } from "../api"; 

export default function DateFilter({ value, onChange }) {
  const [years, setYears] = useState(["All"]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const { years } = await getYears();
        if (alive && Array.isArray(years) && years.length) {
          setYears(years);
        }
      } catch (e) {
        setYears(["All", "2025-10", "2025-09", "2025-08"]);
      } finally {
        setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, []);

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-600">Year</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={loading}
        className="inline-flex h-9 items-center rounded-lg border border-gray-300 bg-white px-3 text-sm leading-5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        {years.map((y) => (
          <option key={y} value={y}>{y}</option>
        ))}
      </select>
    </div>
  );
}
