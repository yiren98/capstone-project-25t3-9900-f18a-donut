import React from "react";
import icSetting from "../../assets/icons/Setting.png";
import icLogout from "../../assets/icons/Logout.png";

export default function BottomUtilities({ onSetting = () => {}, onLogout = () => {}, className = "" }) {
  return (
    <div className={`w-[57px] ${className}`}>
      <div className="flex flex-col items-center gap-4 rounded-full bg-white border border-[rgb(236,234,230)] px-3 py-4 shadow-sm">
        <button aria-label="Setting" onClick={onSetting} className="outline-none">
          <div className="flex items-center justify-center h-11 w-11 rounded-full bg-transparent">
            <img src={icSetting} alt="Setting" className="h-5 w-5 opacity-80" />
          </div>
        </button>
        <button aria-label="Logout" onClick={onLogout} className="outline-none">
          <div className="flex items-center justify-center h-11 w-11 rounded-full bg-transparent">
            <img src={icLogout} alt="Logout" className="h-5 w-5 opacity-80" />
          </div>
        </button>
      </div>
    </div>
  );
}
