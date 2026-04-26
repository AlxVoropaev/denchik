import { useQuery } from "@tanstack/react-query";
import { forum } from "../api/endpoints";

export function useForum(epicGroupId: number | null) {
  return useQuery({
    queryKey: ["forum", epicGroupId],
    queryFn: () => forum.view(epicGroupId!),
    enabled: epicGroupId != null,
  });
}
