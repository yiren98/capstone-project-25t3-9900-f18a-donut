import React from "react";

export default function SentimentVenn({
  positive = 270,
  negative = 210,
  intersectionRate = 34.09,
  title = "Sentiment Analysis Statistics",
}) {

  const W = 294;    
  const H = 160;     
  const rL = 46;
  const rR = 42;
  const cxL = 115;
  const cyL = 77;   
  const cxR = cxL + 62;
  const cyR = cyL + 2;

  const YELLOW = "#F6C945";
  const GREY = "#D6D2C9";
  const BLACK = "#1F1F22";

  return (
    <div
      className="
        rounded-2xl border border-[#d6d0c5] bg-white/70 shadow-sm
        px-4 py-3 w-full
      "
    >
      <h3 className="text-[15px] font-semibold text-neutral-800 mb-1">
        {title}
      </h3>


      <div className="flex flex-col items-center">

        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="w-auto h-auto">
          <defs>
            <pattern id="diagonalHatch" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
              <rect width="6" height="6" fill="transparent" />
              <rect x="0" y="0" width="3" height="6" fill="white" opacity="0.9" />
            </pattern>
            <clipPath id="clipLeft"><circle cx={cxL} cy={cyL} r={rL} /></clipPath>
            <clipPath id="clipRight"><circle cx={cxR} cy={cyR} r={rR} /></clipPath>
          </defs>


          <circle cx={cxL} cy={cyL} r={rL} fill={YELLOW} />
          <circle cx={cxR} cy={cyR} r={rR} fill={GREY} />
          <g clipPath="url(#clipRight)">
            <circle cx={cxL} cy={cyL} r={rL} fill="url(#diagonalHatch)" />
          </g>


          <line x1={cxL - rL - 14} y1={cyL} x2={cxL - rL + 4} y2={cyL} stroke="#9a9a9a" strokeWidth="1.4" />
          <text x={cxL - rL - 18} y={cyL + 3} fontSize="13" fill={BLACK} textAnchor="end">{positive}</text>

          <line x1={cxR + rR + 14} y1={cyR} x2={cxR + rR - 4} y2={cyR} stroke="#9a9a9a" strokeWidth="1.4" />
          <text x={cxR + rR + 18} y={cyR + 3} fontSize="13" fill={BLACK} textAnchor="start">{negative}</text>


          <circle cx={cxL + rL * 0.45} cy={cyL + rL + 4} r="3.3" fill={BLACK} />
          <text x={cxL + rL * 0.45 + 7} y={cyL + rL + 8} fontSize="12" fill={BLACK}>
            {intersectionRate.toFixed(2)}%
          </text>
        </svg>


        <div className="flex items-center justify-center gap-3 mt-1">
          <StatPill label="Positive" value={positive} dotColor={YELLOW} />
          <StatPill label="Negative" value={negative} dotColor={GREY} />
        </div>
      </div>
    </div>
  );
}

function StatPill({ label, value, dotColor }) {
  return (
    <div className="rounded-full border border-[#e1dcd3] bg-white/95 px-3 py-2 flex items-center gap-2 shadow-sm">
      <span className="inline-block w-2 h-2 rounded-full" style={{ background: dotColor }} />
      <span className="text-[14px] font-semibold text-neutral-900 leading-none">{value}</span>
      <span className="text-[13px] text-neutral-600 leading-none">{label}</span>
    </div>
  );
}
