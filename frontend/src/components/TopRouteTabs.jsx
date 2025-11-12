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
          "relative w-full p-[4px] rounded-full bg-white overflow-hidden",
          "shadow-inner shadow-[inset_2px_2px_8px_rgba(0,0,0,0.1),inset_-2px_-2px_10px_rgba(255,255,255,0.95)]"
        )}
      >
        <div
          aria-hidden
          className={clsx(
            "absolute top-[4px] bottom-[4px] rounded-full transition-transform duration-300 ease-out",
            "shadow-[0_4px_10px_rgba(0,0,0,0.12)]"
          )}
          style={{
            width: "calc(50% - 6px)",
            transform: activeIndex ? "translateX(calc(100% + 2px))" : "translateX(0)",
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
                  active ? "text-[#6D6559]" : "text-[#4b463f] hover:text-black/70"
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
