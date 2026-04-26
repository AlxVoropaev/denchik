import { useState } from "react";
import { useComments, useCreateComment } from "../hooks/useComments";
import { useTask, useUpdateTask } from "../hooks/useTasks";
import type { Comment } from "../api/types";

export function TaskDetail({ taskId }: { taskId: number }) {
  const { data: task, isLoading } = useTask(taskId);
  const update = useUpdateTask();
  const { data: comments } = useComments(taskId);
  const createComment = useCreateComment(taskId);
  const [editingTitle, setEditingTitle] = useState(false);
  const [title, setTitle] = useState("");
  const [editingDesc, setEditingDesc] = useState(false);
  const [desc, setDesc] = useState("");
  const [newComment, setNewComment] = useState("");
  const [replyTo, setReplyTo] = useState<number | null>(null);
  const [replyBody, setReplyBody] = useState("");

  if (isLoading || !task) return <div>Loading…</div>;

  // Group comments: top-level + their replies
  const top = (comments ?? []).filter((c) => c.parent_comment_id == null);
  const repliesOf = (id: number) =>
    (comments ?? []).filter((c) => c.parent_comment_id === id);

  return (
    <div className="task-detail">
      {editingTitle ? (
        <input
          autoFocus
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={() => {
            update.mutate({ id: task.id, data: { title } });
            setEditingTitle(false);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") (e.target as HTMLInputElement).blur();
          }}
        />
      ) : (
        <h1 onClick={() => { setTitle(task.title); setEditingTitle(true); }}>{task.title}</h1>
      )}

      <div className="meta">
        <label>
          Status:{" "}
          <select
            value={task.status}
            onChange={(e) =>
              update.mutate({ id: task.id, data: { status: e.target.value as never } })
            }
          >
            <option value="todo">To do</option>
            <option value="in_progress">In progress</option>
            <option value="done">Done</option>
          </select>
        </label>
        <label style={{ marginLeft: 12 }}>
          Priority:{" "}
          <select
            value={task.priority}
            onChange={(e) =>
              update.mutate({ id: task.id, data: { priority: e.target.value as never } })
            }
          >
            <option value="low">Low</option>
            <option value="med">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </label>
      </div>

      <h3>Description</h3>
      {editingDesc ? (
        <textarea
          autoFocus
          value={desc}
          rows={6}
          style={{ width: "100%" }}
          onChange={(e) => setDesc(e.target.value)}
          onBlur={() => {
            update.mutate({ id: task.id, data: { description: desc } });
            setEditingDesc(false);
          }}
        />
      ) : (
        <div
          className="desc"
          onClick={() => {
            setDesc(task.description ?? "");
            setEditingDesc(true);
          }}
        >
          {task.description || <em>Click to add description…</em>}
        </div>
      )}

      <h3>Comments</h3>
      <textarea
        rows={2}
        placeholder="Add a comment…"
        style={{ width: "100%" }}
        value={newComment}
        onChange={(e) => setNewComment(e.target.value)}
      />
      <button
        onClick={() => {
          if (newComment.trim()) {
            createComment.mutate({ body: newComment.trim() });
            setNewComment("");
          }
        }}
      >
        Post
      </button>

      {top.map((c: Comment) => (
        <div key={c.id}>
          <div className="comment">
            <div>{c.body}</div>
            <button onClick={() => setReplyTo(replyTo === c.id ? null : c.id)}>Reply</button>
          </div>
          {repliesOf(c.id).map((r) => (
            <div key={r.id} className="comment reply">
              <div>{r.body}</div>
            </div>
          ))}
          {replyTo === c.id && (
            <div className="comment reply">
              <textarea
                rows={2}
                value={replyBody}
                onChange={(e) => setReplyBody(e.target.value)}
                placeholder="Reply…"
                style={{ width: "100%" }}
              />
              <button
                onClick={() => {
                  if (replyBody.trim()) {
                    createComment.mutate({ body: replyBody.trim(), parentId: c.id });
                    setReplyBody("");
                    setReplyTo(null);
                  }
                }}
              >
                Send reply
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
