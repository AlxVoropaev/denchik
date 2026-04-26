import { useParams } from "react-router-dom";
import { TaskDetail } from "../components/TaskDetail";

export function TaskPage() {
  const { taskId } = useParams();
  const id = Number(taskId);
  if (!Number.isFinite(id)) return <div>Bad task id</div>;
  return <TaskDetail taskId={id} />;
}
