import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { epicGroups, epics } from "../api/endpoints";

export function useEpicGroups(workspaceId: number | null) {
  console.log("[useEpicGroups] workspaceId =", workspaceId, "enabled =", workspaceId != null);
  return useQuery({
    queryKey: ["epic-groups", workspaceId],
    queryFn: () => epicGroups.list(workspaceId!),
    enabled: workspaceId != null,
  });
}

export function useCreateEpicGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ workspaceId, name }: { workspaceId: number; name: string }) => {
      console.log("[useCreateEpicGroup] mutate", { workspaceId, name });
      return epicGroups.create(workspaceId, name);
    },
    onSuccess: (g) => {
      console.log("[useCreateEpicGroup] success", g);
      qc.invalidateQueries({ queryKey: ["epic-groups", g.workspace_id] });
    },
    onError: (e) => console.error("[useCreateEpicGroup] error", e),
  });
}

export function useEpics(epicGroupId: number | null) {
  console.log("[useEpics] epicGroupId =", epicGroupId, "enabled =", epicGroupId != null);
  return useQuery({
    queryKey: ["epics", epicGroupId],
    queryFn: () => epics.list(epicGroupId!),
    enabled: epicGroupId != null,
  });
}

export function useCreateEpic() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ epicGroupId, name }: { epicGroupId: number; name: string }) => {
      console.log("[useCreateEpic] mutate", { epicGroupId, name });
      return epics.create(epicGroupId, name);
    },
    onSuccess: (e) => {
      console.log("[useCreateEpic] success", e);
      qc.invalidateQueries({ queryKey: ["epics", e.epic_group_id] });
    },
    onError: (e) => console.error("[useCreateEpic] error", e),
  });
}
