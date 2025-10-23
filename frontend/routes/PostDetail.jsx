// src/routes/PostDetail.jsx
import { useParams, Link } from "react-router-dom";
import { useEffect, useState, useCallback } from "react";

import { getPostDetail, getPostComments } from "../src/api.js";
import PostContent from "../src/components/PostContent.jsx";
import CommentThread from "../src/components/CommentThread.jsx";

export default function PostDetail() {
  const { id } = useParams();
  const [post, setPost] = useState(null);
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const [detail, cRes] = await Promise.all([
        getPostDetail(id),
        getPostComments({ id }),
      ]);
      setPost(detail || null);
      setComments(cRes?.items || []);
    } catch (err) {
      setError(err?.message || "Failed to load post details");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <div className="p-8 text-gray-600">Loading…</div>;
  if (error)
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="mb-4 text-red-600">{error}</div>
        <button
          onClick={load}
          className="rounded-lg border px-3 py-1.5 text-sm hover:bg-gray-50"
        >
          Retry
        </button>
      </div>
    );
  if (!post) return <div className="p-8 text-gray-600">Post not found.</div>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <Link
        to="/Dashboard"
        className="text-sm text-blue-600 hover:text-blue-800 underline"
      >
        ← Back to Dashboard
      </Link>

      <PostContent post={post} />

      <section className="mt-8">
        <h2 className="text-xl font-semibold mb-4">
          Comments ({comments.length})
        </h2>
        <CommentThread comments={comments} />
      </section>
    </div>
  );
}
