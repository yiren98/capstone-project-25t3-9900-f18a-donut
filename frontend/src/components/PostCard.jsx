// src/components/PostCard.jsx
import { useNavigate } from "react-router-dom";

/**
 * @param {object} props
 * @param {object} props.data - 
 *   { id, title, content, author, time, score, tag, source }
 * @param {boolean} [props.clickable=true] - 
 * @param {string} [props.type="post"] - 
 * @param {function} [props.onClick] - 
 */
export default function PostCard({ data, clickable = true, type = "post", onClick }) {
  const navigate = useNavigate();

  const handleClick = () => {
    if (onClick) return onClick(data);
    if (clickable && type === "post") {
      navigate(`/post/${data.id}`);
    }
  };

  return (
    <div
      onClick={handleClick}
      className={`rounded-2xl border border-gray-200 bg-white dark:bg-zinc-900 p-4 shadow-sm hover:shadow-md transition-all cursor-${clickable ? "pointer" : "default"}`}
    >
      {}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 line-clamp-2">
        {data.title || "(Untitled)"}
      </h3>

      {}
      {data.content && (
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300 line-clamp-2">
          {data.content}
        </p>
      )}

      {}
      <div className="mt-3 flex flex-wrap items-center gap-x-3 text-xs text-gray-500">
        {data.author && <span>👤 {data.author}</span>}
        {data.time && <span>🕒 {data.time}</span>}
        {data.score !== undefined && <span>👍 {data.score}</span>}
        {data.source && <span>📄 {data.source}</span>}
      </div>

      {}
      {data.tag && (
        <div className="mt-3 text-xs text-blue-600 dark:text-blue-400 font-medium">
          #{data.tag}
        </div>
      )}
    </div>
  );
}
