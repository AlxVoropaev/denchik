import { useNavigate } from "react-router-dom";
import { useTasks, useUpdateTask } from "../hooks/useTasks";
import type { Task, TaskStatus } from "../api/types";
import { QuickAddTask } from "./QuickAddTask";

const COLUMNS: { status: TaskStatus; label: string }[] = [
  { status: "todo", label: "To do" },
  { status: "in_progress", label: "In progress" },
  { status: "done", label: "Done" },
];

/**
 * Compute the integer position for a task being inserted at `targetIndex`
 * inside `items` (already sorted by position, ascending). The dragged task
 * must already be excluded from `items`. Mirrors the backend convention of
 * `next_task_position = max(position) + 1` for empty columns.
 */
function computeDropPosition(items: Task[], targetIndex: number): number {
  if (items.length === 0) return 0;
  if (targetIndex <= 0) {
    return items[0]!.position - 1;
  }
  if (targetIndex >= items.length) {
    return items[items.length - 1]!.position + 1;
  }
  const prev = items[targetIndex - 1]!;
  const next = items[targetIndex]!;
  if (next.position - prev.position > 1) {
    return Math.floor((prev.position + next.position) / 2);
  }
  // Integer column collides — drop right after `prev`. The backend tie-breaks
  // by id so this orders the dragged card after `prev` even on a tie.
  return prev.position + 1;
}

export function BoardView({ epicId, workspaceId }: { epicId: number; workspaceId: number }) {
  const { data, isLoading } = useTasks(epicId);
  const update = useUpdateTask();
  const navigate = useNavigate();

  if (isLoading) return <div style={{ padding: 16 }}>Loading…</div>;
  const tasks = data ?? [];

  function columnItems(status: TaskStatus): Task[] {
    return tasks
      .filter((t) => t.status === status)
      .sort((a, b) => a.position - b.position || a.id - b.id);
  }

  function handleDrop(targetStatus: TaskStatus, targetIndex: number, e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    const id = Number(e.dataTransfer.getData("text/plain"));
    if (!id) return;
    const dragged = tasks.find((t) => t.id === id);
    if (!dragged) return;

    const targetItems = columnItems(targetStatus).filter((t) => t.id !== id);
    let clampedIndex = targetIndex;
    if (clampedIndex < 0) clampedIndex = 0;
    if (clampedIndex > targetItems.length) clampedIndex = targetItems.length;

    const position = computeDropPosition(targetItems, clampedIndex);

    // Skip the request when nothing actually changes (same column, same slot,
    // same position) so we don't churn the backend on accidental drops.
    if (dragged.status === targetStatus && dragged.position === position) {
      return;
    }

    update.mutate({ id, data: { status: targetStatus, position } });
  }

  return (
    <div className="board" data-testid="board">
      {COLUMNS.map((col) => {
        const items = columnItems(col.status);
        return (
          <div
            key={col.status}
            className="column"
            data-testid={`column-${col.status}`}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => handleDrop(col.status, items.length, e)}
          >
            <h3>{col.label}</h3>
            {items.map((t: Task, idx: number) => (
              <div
                key={t.id}
                className="task-card"
                draggable
                data-testid={`task-${t.id}`}
                onDragStart={(e) => e.dataTransfer.setData("text/plain", String(t.id))}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => handleDrop(col.status, idx, e)}
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
