import React, { useRef, useState } from "react";
import PostFeedList from "./PostFeedList";
import PostFeedDetail from "./PostFeedDetail";

export default function PostFeed({
  className = "",
  year,
  month,
  filterFlipKey,
  sentiment = null,
  subtheme = "",
  dimension = "",
}) {
  // The key (tag or ID) of the currently viewed post
  const [activeKey, setActiveKey] = useState(null);

  // Reference to the outer flip-card container
  const flipRef = useRef(null);

  // Trigger flip to show the detail view
  const openDetail = (key) => {
    if (!key) return;
    setActiveKey(key);

    if (flipRef.current) {
      flipRef.current.style.transform = "rotateY(180deg)";
    }
  };

  // Return to the list view (flip back)
  const backToList = () => {
    setActiveKey(null);

    if (flipRef.current) {
      flipRef.current.style.transform = "rotateY(0deg)";
    }
  };

  return (
    <section
      className={`relative rounded-2xl border border-[rgb(200,190,170)] shadow-sm ${className}`}
      style={{
        background: "#ede5d6ff",
        padding: "0.9rem 0.7rem 0.9rem",
        overflow: "hidden",
        perspective: "1200px", // Enables 3D flipping effect
      }}
    >
      <div
        ref={flipRef}
        className="relative h-full w-full transition-transform duration-500"
        style={{ transformStyle: "preserve-3d" }}
      >
        {/* Front side: List view */}
        <div className="absolute inset-0" style={{ backfaceVisibility: "hidden" }}>
          <PostFeedList
            year={year}
            month={month}
            filterFlipKey={filterFlipKey}
            sentiment={sentiment}
            subtheme={subtheme}
            dimension={dimension}
            onOpenPost={openDetail}
          />
        </div>

        {/* Back side: Detail view */}
        <div
          className="absolute inset-0 overflow-hidden"
          style={{ transform: "rotateY(180deg)", backfaceVisibility: "hidden" }}
        >
          {activeKey && (
            <PostFeedDetail
              postKey={activeKey}
              onBack={backToList}
            />
          )}
        </div>
      </div>
    </section>
  );
}
