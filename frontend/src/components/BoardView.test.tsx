import { fireEvent, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { BoardView } from "./BoardView";
import { renderWithProviders } from "../test/utils";
import { resetMockState, server, state } from "../test/msw-server";
import type { Task } from "../api/types";

function makeTask(over: Partial<Task> & Pick<Task, "id" | "status" | "position">): Task {
  return {
    epic_id: 100,
    author_id: 1,
    title: `T${over.id}`,
    description: null,
    priority: "med",
    assignee_id: null,
    due_date: null,
    created_at: "",
    updated_at: "",
    labels: [],
    ...over,
  } as Task;
}

function makeDataTransfer() {
  return {
    data: {} as Record<string, string>,
    setData(k: string, v: string) {
      this.data[k] = v;
    },
    getData(k: string) {
      return this.data[k] ?? "";
    },
  };
}

/**
 * Capture every PATCH /tasks/:id body. Returns a ref-like array that the
 * test can assert on after the drop finishes.
 */
function capturePatches() {
  const captured: { id: number; body: Partial<Task> }[] = [];
  server.use(
    http.patch("*/tasks/:id", async ({ params, request }) => {
      const id = Number(params.id);
      const body = (await request.json()) as Partial<Task>;
      captured.push({ id, body });
      const t = state.tasks.find((x) => x.id === id);
      if (!t) return new HttpResponse(null, { status: 404 });
      Object.assign(t, body);
      return HttpResponse.json(t);
    }),
  );
  return captured;
}

describe("BoardView", () => {
  beforeEach(() => {
    resetMockState();
    state.tasks = [
      makeTask({ id: 1, status: "todo", position: 0, title: "T1" }),
      makeTask({ id: 2, status: "in_progress", position: 0, title: "T2" }),
    ];
  });

  it("shows three columns and tasks in the right column", async () => {
    renderWithProviders(<BoardView epicId={100} workspaceId={1} />);
    await waitFor(() => expect(screen.getByText("T1")).toBeInTheDocument());
    expect(screen.getByText("T2")).toBeInTheDocument();
    expect(screen.getByTestId("column-todo")).toContainElement(screen.getByText("T1"));
    expect(screen.getByTestId("column-in_progress")).toContainElement(screen.getByText("T2"));
  });

  it("dropping a card onto another column updates its status", async () => {
    const captured = capturePatches();
    renderWithProviders(<BoardView epicId={100} workspaceId={1} />);
    const card = await screen.findByTestId("task-1");
    const targetCol = screen.getByTestId("column-done");

    const dt = makeDataTransfer();
    fireEvent.dragStart(card, { dataTransfer: dt });
    fireEvent.drop(targetCol, { dataTransfer: dt });

    await waitFor(() => expect(state.tasks.find((t) => t.id === 1)?.status).toBe("done"));
    expect(captured).toHaveLength(1);
    expect(captured[0]!.body.status).toBe("done");
  });
});

describe("BoardView DnD position math", () => {
  beforeEach(() => {
    resetMockState();
  });

  it("dropping into a non-empty column at the top sets position below the first card", async () => {
    state.tasks = [
      // Column "todo" has three cards we'll move from.
      makeTask({ id: 10, status: "todo", position: 0, title: "A" }),
      makeTask({ id: 11, status: "todo", position: 1, title: "B" }),
      makeTask({ id: 12, status: "todo", position: 2, title: "C" }),
      // Column "in_progress" has two cards; we drop before the first.
      makeTask({ id: 20, status: "in_progress", position: 5, title: "X" }),
      makeTask({ id: 21, status: "in_progress", position: 6, title: "Y" }),
    ];
    const captured = capturePatches();

    renderWithProviders(<BoardView epicId={100} workspaceId={1} />);
    const card = await screen.findByTestId("task-11");
    // Drop ON the first card of the target column => insert-before semantics.
    const dropTarget = await screen.findByTestId("task-20");

    const dt = makeDataTransfer();
    fireEvent.dragStart(card, { dataTransfer: dt });
    fireEvent.drop(dropTarget, { dataTransfer: dt });

    await waitFor(() => expect(captured.length).toBeGreaterThan(0));
    expect(captured[0]!.id).toBe(11);
    expect(captured[0]!.body.status).toBe("in_progress");
    // First card had position 5; new top slot is one below that.
    expect(captured[0]!.body.position).toBe(4);
  });

  it("reordering inside the same column moves the card above its previous neighbor", async () => {
    state.tasks = [
      makeTask({ id: 30, status: "todo", position: 0, title: "A" }),
      makeTask({ id: 31, status: "todo", position: 1, title: "B" }),
      makeTask({ id: 32, status: "todo", position: 2, title: "C" }),
    ];
    const captured = capturePatches();

    renderWithProviders(<BoardView epicId={100} workspaceId={1} />);
    // Move card at index 1 (B) to position 0 by dropping before card at index 0 (A).
    const card = await screen.findByTestId("task-31");
    const dropTarget = await screen.findByTestId("task-30");

    const dt = makeDataTransfer();
    fireEvent.dragStart(card, { dataTransfer: dt });
    fireEvent.drop(dropTarget, { dataTransfer: dt });

    await waitFor(() => expect(captured.length).toBeGreaterThan(0));
    expect(captured[0]!.id).toBe(31);
    // Position must be strictly less than the current top card (position 0).
    expect(captured[0]!.body.position).toBeDefined();
    expect(captured[0]!.body.position!).toBeLessThan(0);
  });

  it("dropping into an empty column uses position 0", async () => {
    state.tasks = [
      makeTask({ id: 40, status: "todo", position: 0, title: "A" }),
    ];
    const captured = capturePatches();

    renderWithProviders(<BoardView epicId={100} workspaceId={1} />);
    const card = await screen.findByTestId("task-40");
    const targetCol = screen.getByTestId("column-done");

    const dt = makeDataTransfer();
    fireEvent.dragStart(card, { dataTransfer: dt });
    fireEvent.drop(targetCol, { dataTransfer: dt });

    await waitFor(() => expect(captured.length).toBeGreaterThan(0));
    expect(captured[0]!.id).toBe(40);
    expect(captured[0]!.body.status).toBe("done");
    expect(captured[0]!.body.position).toBe(0);
  });

  it("dropping at the end of a non-empty column appends with last.position + 1", async () => {
    state.tasks = [
      makeTask({ id: 50, status: "todo", position: 0, title: "A" }),
      makeTask({ id: 51, status: "in_progress", position: 3, title: "B" }),
      makeTask({ id: 52, status: "in_progress", position: 4, title: "C" }),
    ];
    const captured = capturePatches();

    renderWithProviders(<BoardView epicId={100} workspaceId={1} />);
    const card = await screen.findByTestId("task-50");
    const targetCol = screen.getByTestId("column-in_progress");

    const dt = makeDataTransfer();
    fireEvent.dragStart(card, { dataTransfer: dt });
    fireEvent.drop(targetCol, { dataTransfer: dt });

    await waitFor(() => expect(captured.length).toBeGreaterThan(0));
    expect(captured[0]!.id).toBe(50);
    expect(captured[0]!.body.status).toBe("in_progress");
    expect(captured[0]!.body.position).toBe(5);
  });
});
