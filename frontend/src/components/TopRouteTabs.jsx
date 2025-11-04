import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import clsx from "clsx";

export default function TopRouteTabs({
  dashboardPath = "/dashboard",
  culturePath = "/culture-analysis",
  highlightColor = "#e4d9cdff", 
  className = "",
}) {
  const location = useLocation();
  const navigate = useNavigate();

  const tabs = [
    { label: "Dashboard", path: dashboardPath },
    { label: "Culture Analysis", path: culturePath },
  ];

  const activeIndex = location.pathname.startsWith(culturePath) ? 1 : 0;

  return (
    <div className={clsx("w-full", className)}>
      <div
        className={clsx(
          "relative w-full p-1 rounded-full bg-white",
          "shadow-inner",
          "shadow-[inset_3px_3px_10px_rgba(0,0,0,0.10),inset_-3px_-3px_12px_rgba(255,255,255,0.95)]",
          "ring-0"
        )}
      >
        <div
          aria-hidden
          className={clsx(
            "absolute top-1 bottom-1 left-1 rounded-full",
            "shadow-[0_6px_18px_rgba(0,0,0,0.12)]",
            "transition-transform duration-300 ease-out",
            "motion-reduce:transition-none"
          )}
          style={{
            width: "calc(50% - 4px)",
            transform: activeIndex ? "translateX(100%)" : "translateX(0)",
            backgroundColor: highlightColor,
          }}
        />

        <div className="relative z-10 grid grid-cols-2 w-full">
          {tabs.map((t, i) => {
            const active = i === activeIndex;
            return (
              <button
                key={t.path}
                onClick={() => navigate(t.path)}
                className={clsx(
                  "h-10 md:h-11 rounded-full",
                  "flex items-center justify-center select-none",
                  "text-sm md:text-base font-semibold tracking-wide",
                  "transition-colors duration-200",
                  active ? "text-[#6D6559]" : "text-[#4b463f] hover:text-black/70",

                  "focus:outline-none focus-visible:ring-2 focus-visible:ring-[#e6e1d9] focus-visible:ring-offset-2 focus-visible:ring-offset-transparent rounded-full"
                )}
                aria-pressed={active}
                aria-current={active ? "page" : undefined}
              >
                {t.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
