function normId(x) {
  if (!x) return "";
  return String(x).trim().toLowerCase().replace(/^.*?_/, ""); 
}

export default function CommentThread({ comments = [] }) {
  if (!comments.length) {
    return <p className="text-sm text-gray-500">No comments yet.</p>;
  }

  const parents = comments.filter(c => Number(c.depth) === 0);
  const children = comments.filter(c => Number(c.depth) === 1);

  const parentMap = new Map();
  for (const p of parents) {
    parentMap.set(normId(p.comment_id), p);
  }

  const childGroups = new Map();
  for (const c of children) {
    const pid = normId(c.parent_id);
    if (!parentMap.has(pid)) continue;
    if (!childGroups.has(pid)) childGroups.set(pid, []);
    childGroups.get(pid).push(c);
  }

  const byScore = (a, b) => (b.score ?? 0) - (a.score ?? 0);

  parents.sort(byScore);
  for (const arr of childGroups.values()) arr.sort(byScore);

  return (
    <div className="space-y-3">
      {parents.map(p => {
        const pid = normId(p.comment_id);
        const kids = childGroups.get(pid) || [];
        return (
          <div key={p.comment_id} className="rounded-xl border p-4 bg-gray-50">
            <CommentItem comment={p} />
            {kids.length > 0 && (
              <div className="mt-2 pl-4 border-l-2 border-gray-200 space-y-2">
                {kids.map(k => (
                  <CommentItem key={k.comment_id} comment={k} isChild />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function CommentItem({ comment, isChild = false }) {
  return (
    <div
      className={`rounded-lg p-3 ${
        isChild ? "bg-white border border-gray-100" : "bg-gray-50"
      }`}
    >
      <div className="text-[11px] text-gray-500 flex justify-between">
        <span>@{comment.author || "unknown"}</span>
        <span>
          👍 {comment.score ?? 0} · {comment.time}
        </span>
      </div>
      <p className="mt-1 text-sm text-gray-800 whitespace-pre-line">
        {comment.content}
      </p>
    </div>
  );
}
