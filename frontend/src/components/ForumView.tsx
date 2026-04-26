import { Link } from "react-router-dom";
import { useForum } from "../hooks/useForum";

export function ForumView({
  epicGroupId,
  workspaceId,
}: {
  epicGroupId: number;
  workspaceId: number;
}) {
  const { data, isLoading } = useForum(epicGroupId);
  if (isLoading) return <div style={{ padding: 16 }}>Loading…</div>;
  if (!data) return null;
  return (
    <div className="forum" data-testid="forum">
      <h2>{data.name}</h2>
      {data.subforums.length === 0 && <p>No epics yet.</p>}
      {data.subforums.map((sub) => (
        <div key={sub.epic_id} className="subforum" data-testid={`subforum-${sub.epic_id}`}>
          <h3>{sub.name}</h3>
          {sub.topics.length === 0 && (
            <div className="topic-row">
              <span className="meta">No topics yet.</span>
              <span />
              <span />
            </div>
          )}
          {sub.topics.map((topic) => (
            <div className="topic-row" key={topic.task_id}>
              <Link to={`/w/${workspaceId}/task/${topic.task_id}`}>{topic.title}</Link>
              <span className="meta">{topic.comment_count} comments</span>
              <span className="meta">
                {topic.last_comment_at
                  ? new Date(topic.last_comment_at).toLocaleString()
                  : new Date(topic.created_at).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
