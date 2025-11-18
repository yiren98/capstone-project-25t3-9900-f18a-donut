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
  // 当前正在查看的帖子 key（tag 或 id）
  const [activeKey, setActiveKey] = useState(null);

  // 外层卡片翻转容器
  const flipRef = useRef(null);

  const openDetail = (key) => {
    if (!key) return;
    setActiveKey(key);
    if (flipRef.current) {
      flipRef.current.style.transform = "rotateY(180deg)";
    }
  };

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
        perspective: "1200px",
      }}
    >
      <div
        ref={flipRef}
        className="relative h-full w-full transition-transform duration-500"
        style={{ transformStyle: "preserve-3d" }}
      >
        {/* 正面：列表视图 */}
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

        {/* 反面：详情视图 */}
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
