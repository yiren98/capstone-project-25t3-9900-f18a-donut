// src/components/SuggestionSummary.jsx
import React, { useState } from "react";
import clsx from "clsx";

const SAMPLE = {
  report_title: "Corporate Culture — Overall Summary",
  section: {
    executive_briefing: {
      title: "Rio Tinto & Broader Market Sentiment",
      key_insights: [
        "Dominant negative sentiment on Rio Tinto stems from historical controversies (e.g., Juukan Gorge destruction) despite current operational expansions and partnerships (e.g., West Angelas project, Oyu Tolgoi mine settlement).",
        "Sector-wide scrutiny is rising: Increased regulatory and public scrutiny on mining ethics, supply chain transparency (e.g., rare earths, critical minerals), and corporate accountability, especially with U.S.-China trade dynamics.",
        "Opportunities in U.S. market expansion: U.S. market conditions (e.g., subsidies, energy costs) attract foreign firms (e.g., Australian mineral firms) despite home-country pressures, indicating strategic diversification.",
      ],
      sentiment_and_confidence: {
        overall_sentiment: "negative",
        summary:
          "Overall sentiment remains negative (167 negative vs. 174 positive comments, but negative themes dominate discourse), with high confidence (0.841 average) due to data volume and consistency.",
        counts: { positive: 174, negative: 167 },
        average_confidence: 0.841,
      },
      risks_and_opportunities: {
        risks: [
          {
            name: "Reputational degradation",
            description:
              "Continued association with past controversies (e.g., Juukan Gorge) may overshadow current operational achievements, affecting stakeholder trust.",
          },
          {
            name: "Regulatory tightening",
            description:
              "Increasing global focus on ethical sourcing and ESG factors may impose stricter compliance burdens.",
          },
          {
            name: "Competitive displacement",
            description:
              "As U.S. and other markets attract flexible competitors (e.g., Australian mineral firms expanding to the U.S.), Rio Tinto may face increased competition.",
          },
        ],
        opportunities: [
          {
            name: "Strategic partnerships",
            description:
              "Collaborations (e.g., with Mitsui, Nippon Steel) can enhance project credibility and resource sharing.",
          },
          {
            name: "U.S. market expansion",
            description:
              "The U.S. market’s growing demand for critical minerals and supportive policies (e.g., subsidies) offers growth avenues.",
          },
          {
            name: "Technological integration",
            description:
              "Advancements in mining technology and supply chain transparency can improve efficiency and accountability.",
          },
        ],
      },
      actionable_recommendations: [
        {
          recommendation:
            "Enhance transparency and communication on sustainability efforts and ethical sourcing to mitigate reputational risks.",
          ownership: "Corporate Communications Lead",
          impact: "Improved stakeholder trust and market positioning.",
        },
        {
          recommendation:
            "Diversify market presence by accelerating investments in U.S. and other regions with favorable regulations.",
          ownership: "Strategy & Business Development Teams",
          impact: "Reduced regional risk and access to growth markets.",
        },
        {
          recommendation:
            "Strengthen partnerships with governments, industry groups, and technology providers to ensure compliant and innovative operations.",
          ownership: "Partnerships & Legal Departments",
          impact: "Enhanced operational security and innovation pace.",
        },
      ],
      note: "These recommendations are based on available data and trends. Continuous monitoring of regulatory developments and competitor movements is advised.",
    },
  },
};

const sections = [
  {
    title: "Executive Briefing",
    content: (
      <>
        <p className="text-sm text-neutral-700 mb-2">
          {SAMPLE.section.executive_briefing.title}
        </p>
        <ul className="space-y-2 text-sm text-neutral-800">
          {SAMPLE.section.executive_briefing.key_insights.map((t, i) => (
            <li key={i} className="pl-4 relative">
              <span className="absolute left-0 top-[9px] h-1.5 w-1.5 rounded-full bg-neutral-400" />
              {t}
            </li>
          ))}
        </ul>
      </>
    ),
  },
  {
    title: "Sentiment & Confidence",
    content: (
      <>
        <p className="text-sm text-neutral-700 mb-2">
          {SAMPLE.section.executive_briefing.sentiment_and_confidence.summary}
        </p>
        <div className="flex flex-wrap gap-2 text-xs">
          {[
            `Positive ${SAMPLE.section.executive_briefing.sentiment_and_confidence.counts.positive}`,
            `Negative ${SAMPLE.section.executive_briefing.sentiment_and_confidence.counts.negative}`,
            `Avg. confidence ${SAMPLE.section.executive_briefing.sentiment_and_confidence.average_confidence}`,
            `Overall ${SAMPLE.section.executive_briefing.sentiment_and_confidence.overall_sentiment}`,
          ].map((x, i) => (
            <span
              key={i}
              className="px-2 py-1 rounded-full bg-white border border-[#eee7db]"
            >
              {x}
            </span>
          ))}
        </div>
      </>
    ),
  },
  {
    title: "Risks & Opportunities",
    content: (
      <div className="grid md:grid-cols-2 gap-3">
        {["risks", "opportunities"].map((t) => (
          <div
            key={t}
            className="rounded-xl border border-[#eee7db] bg-white/60 p-3"
          >
            <div className="text-sm font-medium mb-2">
              {t === "risks" ? "Risks" : "Opportunities"}
            </div>
            <ul className="space-y-2 text-sm text-neutral-800">
              {SAMPLE.section.executive_briefing.risks_and_opportunities[t].map(
                (x, i) => (
                  <li key={i} className="pl-4 relative">
                    <span className="absolute left-0 top-[9px] h-1.5 w-1.5 rounded-full bg-neutral-400" />
                    <span className="font-medium">{x.name}:</span>{" "}
                    {x.description}
                  </li>
                ),
              )}
            </ul>
          </div>
        ))}
      </div>
    ),
  },
  {
    title: "Actionable Recommendations",
    content: (
      <div className="space-y-3">
        {SAMPLE.section.executive_briefing.actionable_recommendations.map(
          (a, i) => (
            <div
              key={i}
              className="p-3 rounded-xl bg-white shadow-sm border border-[#eee7db]"
            >
              <div className="text-[15px] font-medium mb-1">
                {a.recommendation}
              </div>
              <div className="text-xs text-neutral-500">
                Owner: {a.ownership} · Impact: {a.impact}
              </div>
            </div>
          ),
        )}
      </div>
    ),
  },
];

export default function SuggestionSummary({ className = "" }) {
  const [page, setPage] = useState(0);
  const pageSize = 2;
  const maxPage = Math.ceil(sections.length / pageSize) - 1;

  return (
    <div
      className={clsx(
        "rounded-2xl border border-[#d6d0c5] shadow-sm px-6 py-5 flex flex-col",
        className,
        "!bg-[rgba(97, 81, 14, 1)]", //
      )}
    >
      <h2 className="text-lg font-semibold mb-1">Suggested Insights Summary</h2>
      <p className="text-neutral-600 text-sm mb-4">
        System-curated recommendations based on posts, news & comments.
      </p>

      <div className="space-y-6">
        {sections
          .slice(page * pageSize, page * pageSize + pageSize)
          .map((sec, i) => (
            <div key={i}>
              <div className="text-[15px] font-semibold mb-2">{sec.title}</div>
              {sec.content}
            </div>
          ))}
      </div>

      <div className="mt-4 flex justify-between text-sm">
        <button
          disabled={page === 0}
          onClick={() => setPage((p) => p - 1)}
          className="px-3 py-1 rounded-full border border-[#e2dcd4] disabled:opacity-40"
        >
          ⯇
        </button>
        <button
          disabled={page === maxPage}
          onClick={() => setPage((p) => p + 1)}
          className="px-3 py-1 rounded-full border border-[#e2dcd4] disabled:opacity-40"
        >
          ⯈
        </button>
      </div>
    </div>
  );
}
