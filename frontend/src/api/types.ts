export type TaskStatus = "todo" | "in_progress" | "done";
export type TaskPriority = "low" | "med" | "high" | "urgent";

export interface User {
  id: number;
  email: string;
  display_name: string;
}

export interface Workspace {
  id: number;
  name: string;
  owner_id: number;
}

export interface EpicGroup {
  id: number;
  workspace_id: number;
  name: string;
  position: number;
}

export interface Epic {
  id: number;
  epic_group_id: number;
  name: string;
  position: number;
}

export interface Label {
  id: number;
  name: string;
  color: string;
}

export interface Task {
  id: number;
  epic_id: number;
  author_id: number;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  assignee_id: number | null;
  due_date: string | null;
  position: number;
  created_at: string;
  updated_at: string;
  labels: Label[];
}

export interface Comment {
  id: number;
  task_id: number;
  parent_comment_id: number | null;
  author_id: number;
  body: string;
  created_at: string;
  edited_at: string | null;
}

export interface Attachment {
  id: number;
  task_id: number;
  uploaded_by: number;
  filename: string;
  content_type: string;
  size: number;
  created_at: string;
}

export interface ForumTopic {
  task_id: number;
  title: string;
  author_id: number;
  created_at: string;
  updated_at: string;
  comment_count: number;
  last_comment_author_id: number | null;
  last_comment_at: string | null;
}

export interface ForumSubforum {
  epic_id: number;
  name: string;
  position: number;
  topics: ForumTopic[];
}

export interface ForumView {
  epic_group_id: number;
  name: string;
  subforums: ForumSubforum[];
}
