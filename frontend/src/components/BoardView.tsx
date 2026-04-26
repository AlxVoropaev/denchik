import { useNavigate } from "react-router-dom";
import { useTasks, useUpdateTask } from "../hooks/useTasks";
import type { Task, TaskStatus } from "../api/types";
import { QuickAddTask } from "./QuickAddTask";

const COLUMNS: { status: TaskStatus; label: string }[] = [
  { status: "todo", label: "To do" },
  { status: "in_progress", label: "In progress" },
  { status: "done", label: "Done" },
];

export function BoardView({ epicId, workspaceId }: { epicId: number; workspaceId: number }) {
  const { data, isLoading } = useTasks(epicId);
  const update = useUpdateTask();
  const navigate = useNavigate();

  if (isLoading) return <div style={{ padding: 16 }}>Loading…</div>;
  const tasks = data ?? [];

  function onDrop(status: TaskStatus, e: React.DragEvent) {
    e.preventDefault();
    const id = Number(e.dataTransfer.getData("text/plain"));
    if (!id) return;
    update.mutate({ id, data: { status } });
  }

  return (
    <div className="board" data-testid="board">
      {COLUMNS.map((col) => {
        const items = tasks.filter((t) => t.status === col.status);
        return (
          <div
            key={col.status}
            className="column"
            data-testid={`column-${col.status}`}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => onDrop(col.status, e)}
          >
            <h3>{col.label}</h3>
            {items.map((t: Task) => (
              <div
                key={t.id}
                className="task-card"
                draggable
                data-testid={`task-${t.id}`}
                onDragStart={(e) => e.dataTransfer.setData("text/plain", String(t.id))}
                onClick={() => navigate(`/w/${workspaceId}/task/${t.id}`)}
              >
                {t.title}
              </div>
            ))}
            <QuickAddTask epicId={epicId} defaultStatus={col.status} />
          </div>
        );
      })}
    </div>
  );
}
