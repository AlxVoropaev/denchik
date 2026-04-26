import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { tasks, type TaskCreate, type TaskUpdate } from "../api/endpoints";

export function useTasks(epicId: number | null) {
  return useQuery({
    queryKey: ["tasks", epicId],
    queryFn: () => tasks.list(epicId!),
    enabled: epicId != null,
  });
}

export function useTask(taskId: number | null) {
  return useQuery({
    queryKey: ["task", taskId],
    queryFn: () => tasks.get(taskId!),
    enabled: taskId != null,
  });
}

export function useCreateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TaskCreate) => tasks.create(data),
    onSuccess: (task) => {
      qc.invalidateQueries({ queryKey: ["tasks", task.epic_id] });
    },
  });
}

export function useUpdateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: TaskUpdate }) =>
      tasks.update(id, data),
    onSuccess: (task) => {
      qc.invalidateQueries({ queryKey: ["tasks", task.epic_id] });
      qc.invalidateQueries({ queryKey: ["task", task.id] });
    },
  });
}

export function useDeleteTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id }: { id: number; epicId: number }) => tasks.remove(id),
    onSuccess: (_data, { id, epicId }) => {
      qc.invalidateQueries({ queryKey: ["tasks", epicId] });
      qc.removeQueries({ queryKey: ["task", id] });
    },
  });
}
