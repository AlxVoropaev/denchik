import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import type {
  Comment,
  ForumView,
  Task,
  User,
} from "../api/types";

const BASE = "*";

export const state: {
  user: User | null;
  tasks: Task[];
  comments: Comment[];
  forum: ForumView | null;
  nextId: number;
} = {
  user: null,
  tasks: [],
  comments: [],
  forum: null,
  nextId: 1000,
};

export function resetMockState() {
  state.user = null;
  state.tasks = [];
  state.comments = [];
  state.forum = null;
  state.nextId = 1000;
}

export const handlers = [
  http.get(`${BASE}/auth/me`, () => {
    if (!state.user) return new HttpResponse(null, { status: 401 });
    return HttpResponse.json(state.user);
  }),
  http.post(`${BASE}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string };
    state.user = { id: 1, email: body.email, display_name: "Test" };
    return HttpResponse.json(state.user);
  }),
  http.post(`${BASE}/auth/register`, async ({ request }) => {
    const body = (await request.json()) as { email: string; display_name: string };
    state.user = { id: 1, email: body.email, display_name: body.display_name };
    return HttpResponse.json(state.user, { status: 201 });
  }),
  http.post(`${BASE}/auth/logout`, () => {
    state.user = null;
    return HttpResponse.json({ ok: true });
  }),

  http.get(`${BASE}/tasks`, ({ request }) => {
    const url = new URL(request.url);
    const epicId = Number(url.searchParams.get("epic_id"));
    return HttpResponse.json(state.tasks.filter((t) => t.epic_id === epicId));
  }),
  http.post(`${BASE}/tasks`, async ({ request }) => {
    const body = (await request.json()) as { epic_id: number; title: string; status?: Task["status"] };
    const task: Task = {
      id: state.nextId++,
      epic_id: body.epic_id,
      author_id: 1,
      title: body.title,
      description: null,
      status: body.status ?? "todo",
      priority: "med",
      assignee_id: null,
      due_date: null,
      position: state.tasks.filter((t) => t.epic_id === body.epic_id).length,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      labels: [],
    };
    state.tasks.push(task);
    return HttpResponse.json(task, { status: 201 });
  }),
  http.get(`${BASE}/tasks/:id`, ({ params }) => {
    const t = state.tasks.find((x) => x.id === Number(params.id));
    if (!t) return new HttpResponse(null, { status: 404 });
    return HttpResponse.json(t);
  }),
  http.patch(`${BASE}/tasks/:id`, async ({ params, request }) => {
    const id = Number(params.id);
    const body = (await request.json()) as Partial<Task>;
    const t = state.tasks.find((x) => x.id === id);
    if (!t) return new HttpResponse(null, { status: 404 });
    Object.assign(t, body);
    return HttpResponse.json(t);
  }),
  http.delete(`${BASE}/tasks/:id`, ({ params }) => {
    const id = Number(params.id);
    const idx = state.tasks.findIndex((x) => x.id === id);
    if (idx === -1) return new HttpResponse(null, { status: 404 });
    state.tasks.splice(idx, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  http.get(`${BASE}/tasks/:id/comments`, ({ params }) => {
    const id = Number(params.id);
    return HttpResponse.json(state.comments.filter((c) => c.task_id === id));
  }),
  http.post(`${BASE}/tasks/:id/comments`, async ({ params, request }) => {
    const id = Number(params.id);
    const body = (await request.json()) as { body: string; parent_comment_id?: number };
    if (body.parent_comment_id) {
      const parent = state.comments.find((c) => c.id === body.parent_comment_id);
      if (parent && parent.parent_comment_id != null) {
        return HttpResponse.json(
          { detail: "Comments can be nested only one level deep" },
          { status: 400 },
        );
      }
    }
    const c: Comment = {
      id: state.nextId++,
      task_id: id,
      parent_comment_id: body.parent_comment_id ?? null,
      author_id: 1,
      body: body.body,
      created_at: new Date().toISOString(),
      edited_at: null,
    };
    state.comments.push(c);
    return HttpResponse.json(c, { status: 201 });
  }),

  http.get(`${BASE}/forum/:id`, ({ params }) => {
    const id = Number(params.id);
    if (!state.forum) {
      return HttpResponse.json({
        epic_group_id: id,
        name: "Mock forum",
        subforums: [],
      });
    }
    return HttpResponse.json(state.forum);
  }),

  http.get(`${BASE}/workspaces`, () =>
    HttpResponse.json([{ id: 1, name: "Test", owner_id: 1 }]),
  ),
  http.get(`${BASE}/epic-groups`, () =>
    HttpResponse.json([{ id: 10, workspace_id: 1, name: "Backlog", position: 0 }]),
  ),
  http.get(`${BASE}/epics`, () =>
    HttpResponse.json([{ id: 100, epic_group_id: 10, name: "Auth", position: 0 }]),
  ),
];

export const server = setupServer(...handlers);
