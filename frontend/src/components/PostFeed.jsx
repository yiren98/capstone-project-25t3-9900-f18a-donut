import React from "react";

export default function PostFeed({
  className = "",
  items = [
    {
      id: 1,
      title: "Rio Tinto to boost renewable investments across Australia",
      author: "Floyd Miles",
      time: "2021-11-02",
      likes: 128,
      bgColor: "#EAE6DE",
    },
    {
      id: 2,
      title: "Employee discussion: leadership transparency & internal culture",
      author: "Cody Fisher",
      time: "2022-02-11",
      likes: 76,
      bgColor: "#e5dfbecc",
    },
    {
      id: 3,
      title: "The Guardian: Rio Tinto’s sustainability report highlights progress",
      author: "Jenny Wilson",
      time: "2023-07-11",
      likes: 203,
      bgColor: "#EAE6DE",
    },
    {
      id: 4,
      title: "Community partnership update: education & training programs",
      author: "Jane Cooper",
      time: "2024-11-07",
      likes: 97,
      bgColor: "#e5dfbecc",
    },
    {
      id: 5,
      title: "ESG dashboard: Q2 highlights & next targets",
      author: "Dianne Russell",
      time: "2025-07-07",
      likes: 164,
      bgColor: "#e5dfbecc",
    },
    {
      id: 6,
      title: "Market view: commodities & demand outlook",
      author: "Jacob Jones",
      time: "2025-10-10",
      likes: 88,
      bgColor: "#EAE6DE",
    },
  ],
  cardBg = "rgba(126, 25, 25, 0.75)",
}) {
  const Heart = ({ className = "w-3.5 h-3.5" }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className={className}>
      <path
        d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 1 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );

  return (
    <section
      className={`rounded-2xl border border-[rgb(200,190,170)] shadow-sm ${className}`}
      style={{
        backgroundColor: "#ede5d6ff",
        padding: "1.2rem 0.7rem 1.3rem",
      }}
    >

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {items.map((it) => (
          <div
            key={it.id}
            className="border border-white/60 rounded-xl px-5 py-4 shadow-sm flex flex-col justify-between transition-all hover:translate-y-[-1px]"
            style={{
              backgroundColor: it.bgColor || cardBg,
            }}
          >
            <div className="text-[15px] md:text-[16px] font-semibold text-neutral-900 leading-snug mb-2 line-clamp-2">
              {it.title}
            </div>
            <div className="flex items-center justify-between text-sm text-neutral-500">
              <span>{it.author}</span>
              <div className="flex items-center gap-3">
                <span>{it.time}</span>
                <span className="flex items-center gap-1">
                  <Heart className="w-3.5 h-3.5" />
                  {it.likes}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
