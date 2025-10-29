import React from "react";
import icDashboard from "../../assets/icons/dashboard.png";
import icReddit from "../../assets/icons/Forum.png";
import icNews from "../../assets/icons/news.png";

export default function SidebarNav({ active = "dashboard", onChange = () => {}, className = "" }) {
  const items = [
    { key: "dashboard", icon: icDashboard, label: "Dashboard" },
    { key: "reddit", icon: icReddit, label: "Reddit" },
    { key: "news", icon: icNews, label: "News" },
  ];

  return (
    <div className={`w-[57px] flex justify-center self-auto ${className}`}>
      <nav className="flex flex-col items-center gap-3 rounded-full bg-white p-3 border border-[rgb(236,234,230)] w-full shadow-sm">
        {items.map((it) => {
          const isActive = active === it.key;
          return (
            <button key={it.key} aria-label={it.label} onClick={() => onChange(it.key)} className="outline-none">
              <div className={`flex items-center justify-center h-11 w-11 rounded-full ${isActive ? "bg-[#1f1f22]" : "bg-transparent"}`}>
                <img src={it.icon} alt={it.label} className={`h-5 w-5 ${isActive ? "invert" : "opacity-80"}`} />
              </div>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
