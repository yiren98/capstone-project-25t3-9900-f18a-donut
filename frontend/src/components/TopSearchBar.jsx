// src/components/TopSearchBar.jsx
import React from "react";
import SearchIcon from "../../assets/icons/Search.png";

export default function TopSearchBar({
  groupWidth = 700,  
  buttonWidth = 84,  
  height = 44,      
}) {
  return (

    <div className="w-full flex items-center">

      <div className="flex items-center gap-3" style={{ width: groupWidth }}>

        <div
          className="flex items-center bg-white rounded-full border border-[rgb(236,234,230)]
                     shadow-[0_2px_8px_rgba(0,0,0,0.08)] px-3 flex-1"
          style={{ height }}
        >
          <img src={SearchIcon} alt="Search" className="h-4 w-4 mr-2 opacity-60" />
          <input
            type="text"
            placeholder="Search by keyword"
            className="w-full outline-none text-[14px] text-neutral-800 placeholder-neutral-400 bg-transparent"
          />
        </div>

        <button
          className="rounded-full bg-black text-white text-[14px] font-medium hover:opacity-90 active:opacity-80 transition"
          style={{ width: buttonWidth, height }}
        >
          Search
        </button>
      </div>
    </div>
  );
}
