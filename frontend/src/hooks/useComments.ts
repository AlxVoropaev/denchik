import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { comments } from "../api/endpoints";

export function useComments(taskId: number | null) {
  return useQuery({
    queryKey: ["comments", taskId],
    queryFn: () => comments.list(taskId!),
    enabled: taskId != null,
  });
}

export function useCreateComment(taskId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ body, parentId }: { body: string; parentId?: number }) =>
      comments.create(taskId, body, parentId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["comments", taskId] }),
  });
}
