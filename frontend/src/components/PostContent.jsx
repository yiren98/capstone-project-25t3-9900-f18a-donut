// src/components/PostContent.jsx

export default function PostContent({ post }) {
  return (
    <article className="rounded-2xl bg-white shadow-sm ring-1 ring-black/5 p-6 mt-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500 mb-2">
        <span className="bg-gray-100 rounded px-2 py-0.5">
          {post.location || "Global"}
        </span>
        <span>{post.time}</span>
        <span className="ml-auto text-gray-400 uppercase">{post.source}</span>
      </div>

      <h1 className="text-2xl font-bold text-gray-900 mb-2">
        {post.title || "(No Title)"}
      </h1>
      <p className="text-sm text-gray-700 mb-1">@{post.author || "unknown"}</p>

      <p className="mt-3 text-gray-800 leading-relaxed whitespace-pre-line">
        {post.content || "(No content)"}
      </p>

      <div className="mt-4 text-sm text-gray-500 flex flex-wrap items-center gap-3">
        <span>👍 {post.score ?? 0}</span>
        {post.tag && (
          <span className="text-blue-600 font-medium">#{post.tag}</span>
        )}
        {post.initial_dimensions && (
          <span className="text-gray-400">
            🧩 {post.initial_dimensions}
          </span>
        )}
      </div>
    </article>
  );
}
