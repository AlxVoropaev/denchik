import { useState } from "react";
import { useComments, useCreateComment } from "../hooks/useComments";
import { useTask, useUpdateTask } from "../hooks/useTasks";
import type { Comment } from "../api/types";

export function TaskDetail({ taskId }: { taskId: number }) {
  const { data: task, isLoading } = useTask(taskId);
  const update = useUpdateTask();
  const { data: comments } = useComments(taskId);
  const createComment = useCreateComment(taskId);
  // Editor-open state intentionally takes precedence over server-side task
  // changes; we never clobber an in-progress edit when `task` updates.
  const [editingTitle, setEditingTitle] = useState(false);
  const [title, setTitle] = useState("");
  const [titleError, setTitleError] = useState<string | null>(null);
  const [editingDesc, setEditingDesc] = useState(false);
  const [desc, setDesc] = useState("");
  const [descError, setDescError] = useState<string | null>(null);
  const [newComment, setNewComment] = useState("");
  const [commentError, setCommentError] = useState<string | null>(null);
  const [replyTo, setReplyTo] = useState<number | null>(null);
  const [replyBody, setReplyBody] = useState("");
  const [replyError, setReplyError] = useState<string | null>(null);

  if (isLoading || !task) return <div>Loading…</div>;

  // Group comments: top-level + their replies
  const top = (comments ?? []).filter((c) => c.parent_comment_id == null);
  const repliesOf = (id: number) =>
    (comments ?? []).filter((c) => c.parent_comment_id === id);

  const saveTitle = () => {
    setTitleError(null);
    update.mutate(
      { id: task.id, data: { title } },
      {
        onSuccess: () => setEditingTitle(false),
        onError: () => setTitleError("Couldn’t save title. Try again."),
      },
    );
  };

  const saveDesc = () => {
    setDescError(null);
    update.mutate(
      { id: task.id, data: { description: desc } },
      {
        onSuccess: () => setEditingDesc(false),
        onError: () => setDescError("Couldn’t save description. Try again."),
      },
    );
  };

  return (
    <div className="task-detail">
      {editingTitle ? (
        <div>
          <input
            autoFocus
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={saveTitle}
            onKeyDown={(e) => {
              if (e.key === "Enter") (e.target as HTMLInputElement).blur();
            }}
          />
          {titleError && <div className="error" role="alert">{titleError}</div>}
        </div>
      ) : (
        <h1 onClick={() => { setTitle(task.title); setTitleError(null); setEditingTitle(true); }}>{task.title}</h1>
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
        <div>
          <textarea
            autoFocus
            value={desc}
            rows={6}
            style={{ width: "100%" }}
            onChange={(e) => setDesc(e.target.value)}
            onBlur={saveDesc}
          />
          {descError && <div className="error" role="alert">{descError}</div>}
        </div>
      ) : (
        <div
          className="desc"
          onClick={() => {
            setDesc(task.description ?? "");
            setDescError(null);
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
        disabled={createComment.isPending || !newComment.trim()}
        onClick={() => {
          const body = newComment.trim();
          if (!body) return;
          setCommentError(null);
          createComment.mutate(
            { body },
            {
              onSuccess: () => setNewComment(""),
              onError: () => setCommentError("Couldn’t post comment. Try again."),
            },
          );
        }}
      >
        Post
      </button>
      {commentError && <div className="error" role="alert">{commentError}</div>}

      {top.map((c: Comment) => (
        <div key={c.id}>
          <div className="comment">
            <div style={{ whiteSpace: "pre-wrap" }}>{c.body}</div>
            <button onClick={() => { setReplyTo(replyTo === c.id ? null : c.id); setReplyError(null); }}>Reply</button>
          </div>
          {repliesOf(c.id).map((r) => (
            <div key={r.id} className="comment reply">
              <div style={{ whiteSpace: "pre-wrap" }}>{r.body}</div>
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
                disabled={createComment.isPending || !replyBody.trim()}
                onClick={() => {
                  const body = replyBody.trim();
                  if (!body) return;
                  setReplyError(null);
                  createComment.mutate(
                    { body, parentId: c.id },
                    {
                      onSuccess: () => {
                        setReplyBody("");
                        setReplyTo(null);
                      },
                      onError: () => setReplyError("Couldn’t post reply. Try again."),
                    },
                  );
                }}
              >
                Send reply
              </button>
              {replyError && <div className="error" role="alert">{replyError}</div>}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
