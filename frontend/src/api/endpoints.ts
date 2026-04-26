import { api } from "./client";
import type {
  Attachment,
  Comment,
  Epic,
  EpicGroup,
  ForumView,
  Label,
  Task,
  TaskPriority,
  TaskStatus,
  User,
  Workspace,
} from "./types";

export const auth = {
  register: (email: string, password: string, display_name: string) =>
    api.post<User>("/auth/register", { email, password, display_name }),
  login: (email: string, password: string) =>
    api.post<User>("/auth/login", { email, password }),
  logout: () => api.post<{ ok: boolean }>("/auth/logout"),
  me: () => api.get<User>("/auth/me"),
};

export const workspaces = {
  list: () => api.get<Workspace[]>("/workspaces"),
  create: (name: string) => api.post<Workspace>("/workspaces", { name }),
};

export const epicGroups = {
  list: (workspace_id: number) =>
    api.get<EpicGroup[]>(`/epic-groups?workspace_id=${workspace_id}`),
  create: (workspace_id: number, name: string) =>
    api.post<EpicGroup>("/epic-groups", { workspace_id, name }),
  remove: (id: number) => api.del(`/epic-groups/${id}`),
};

export const epics = {
  list: (epic_group_id: number) =>
    api.get<Epic[]>(`/epics?epic_group_id=${epic_group_id}`),
  create: (epic_group_id: number, name: string) =>
    api.post<Epic>("/epics", { epic_group_id, name }),
  remove: (id: number) => api.del(`/epics/${id}`),
};

export interface TaskCreate {
  epic_id: number;
  title: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  assignee_id?: number | null;
  due_date?: string | null;
  label_ids?: number[];
}

export interface TaskUpdate {
  title?: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: TaskPriority;
  assignee_id?: number | null;
  due_date?: string | null;
  epic_id?: number;
  position?: number;
  label_ids?: number[];
}

export const tasks = {
  list: (epic_id: number) => api.get<Task[]>(`/tasks?epic_id=${epic_id}`),
  get: (id: number) => api.get<Task>(`/tasks/${id}`),
  create: (data: TaskCreate) => api.post<Task>("/tasks", data),
  update: (id: number, data: TaskUpdate) => api.patch<Task>(`/tasks/${id}`, data),
  remove: (id: number) => api.del(`/tasks/${id}`),
};

export const comments = {
  list: (task_id: number) => api.get<Comment[]>(`/tasks/${task_id}/comments`),
  create: (task_id: number, body: string, parent_comment_id?: number) =>
    api.post<Comment>(`/tasks/${task_id}/comments`, { body, parent_comment_id }),
  remove: (task_id: number, id: number) => api.del(`/tasks/${task_id}/comments/${id}`),
};

export const labels = {
  list: (workspace_id: number) =>
    api.get<Label[]>(`/labels?workspace_id=${workspace_id}`),
  create: (workspace_id: number, name: string, color: string) =>
    api.post<Label>("/labels", { workspace_id, name, color }),
};

export const attachments = {
  list: (task_id: number) => api.get<Attachment[]>(`/tasks/${task_id}/attachments`),
  upload: (task_id: number, file: File) =>
    api.upload<Attachment>(`/tasks/${task_id}/attachments`, file),
  downloadUrl: (id: number) =>
    `${(import.meta.env.VITE_API_URL as string | undefined) ?? "/api"}/attachments/${id}/download`,
};

export const forum = {
  view: (epic_group_id: number) => api.get<ForumView>(`/forum/${epic_group_id}`),
};
