import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { BoardView } from "./BoardView";
import { renderWithProviders } from "../test/utils";
import { resetMockState, state } from "../test/msw-server";

describe("BoardView", () => {
  beforeEach(() => {
    resetMockState();
    state.tasks = [
      {
        id: 1, epic_id: 100, author_id: 1, title: "T1", description: null,
        status: "todo", priority: "med", assignee_id: null, due_date: null,
        position: 0, created_at: "", updated_at: "", labels: [],
      },
      {
        id: 2, epic_id: 100, author_id: 1, title: "T2", description: null,
        status: "in_progress", priority: "med", assignee_id: null, due_date: null,
        position: 0, created_at: "", updated_at: "", labels: [],
      },
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
    renderWithProviders(<BoardView epicId={100} workspaceId={1} />);
    const card = await screen.findByTestId("task-1");
    const targetCol = screen.getByTestId("column-done");

    const dataTransfer = {
      data: {} as Record<string, string>,
      setData(k: string, v: string) { this.data[k] = v; },
      getData(k: string) { return this.data[k] ?? ""; },
    };
    fireEvent.dragStart(card, { dataTransfer });
    fireEvent.drop(targetCol, { dataTransfer });

    await waitFor(() => expect(state.tasks.find((t) => t.id === 1)?.status).toBe("done"));
  });
});
