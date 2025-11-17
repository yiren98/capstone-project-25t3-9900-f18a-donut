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

  // Two-tab layout. Each tab corresponds to a main route.
  const tabs = [
    { label: "Dashboard", path: dashboardPath },
    { label: "Culture Analysis", path: culturePath },
  ];

  // Determine which tab should appear active based on the current URL.
  // If the location starts with culturePath → highlight the second tab.
  const activeIndex = location.pathname.startsWith(culturePath) ? 1 : 0;

  return (
    <div className={clsx("w-full", className)}>
      {/* Outer container that provides the rounded pill background */}
      <div
        className={clsx(
          "relative w-full p-[4px] rounded-full bg-white overflow-hidden",
          // Soft, inset neu-ish shadow for the white pill
          "shadow-inner shadow-[inset_2px_2px_8px_rgba(0,0,0,0.1),inset_-2px_-2px_10px_rgba(255,255,255,0.95)]"
        )}
      >
        {/* The animated highlight bar that slides between the two tabs */}
        <div
          aria-hidden
          className={clsx(
            "absolute top-[4px] bottom-[4px] rounded-full transition-transform duration-300 ease-out",
            "shadow-[0_4px_10px_rgba(0,0,0,0.12)]"
          )}
          style={{
            // width covers half of the pill minus small padding
            width: "calc(50% - 6px)",
            // slide to right when Culture Analysis tab is active
            transform: activeIndex
              ? "translateX(calc(100% + 2px))"
              : "translateX(0)",
            backgroundColor: highlightColor,
          }}
        />

        {/* Foreground layer holding the actual tab buttons */}
        <div className="relative z-10 grid grid-cols-2 w-full">
          {tabs.map((t, i) => {
            const active = i === activeIndex;

            return (
              <button
                key={t.path}
                onClick={() => navigate(t.path)}
                // Tab content styling
                className={clsx(
                  "h-10 md:h-11 rounded-full",
                  "flex items-center justify-center select-none",
                  "text-sm md:text-base font-semibold tracking-wide",
                  "transition-colors duration-200",
                  active
                    ? "text-[#6D6559]"                // Active text color
                    : "text-[#4b463f] hover:text-black/70" // Inactive text
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
