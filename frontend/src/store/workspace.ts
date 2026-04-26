import { create } from "zustand";

interface WorkspaceState {
  currentWorkspaceId: number | null;
  currentEpicGroupId: number | null;
  setWorkspace: (id: number | null) => void;
  setEpicGroup: (id: number | null) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  currentWorkspaceId: null,
  currentEpicGroupId: null,
  setWorkspace: (currentWorkspaceId) => set({ currentWorkspaceId }),
  setEpicGroup: (currentEpicGroupId) => set({ currentEpicGroupId }),
}));
