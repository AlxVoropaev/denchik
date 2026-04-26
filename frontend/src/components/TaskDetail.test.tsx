import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { TaskDetail } from "./TaskDetail";
import { renderWithProviders } from "../test/utils";
import { resetMockState, state } from "../test/msw-server";

describe("TaskDetail", () => {
  beforeEach(() => {
    resetMockState();
    state.tasks = [
      {
        id: 1, epic_id: 100, author_id: 1, title: "Buy milk", description: "the good kind",
        status: "todo", priority: "med", assignee_id: null, due_date: null,
        position: 0, created_at: "", updated_at: "", labels: [],
      },
    ];
  });

  it("renders task and posts a comment", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TaskDetail taskId={1} />);
    await waitFor(() => expect(screen.getByText("Buy milk")).toBeInTheDocument());
    await user.type(screen.getByPlaceholderText(/Add a comment/i), "Hello world");
    await user.click(screen.getByRole("button", { name: /post/i }));
    await waitFor(() => expect(state.comments).toHaveLength(1));
    expect(state.comments[0].body).toBe("Hello world");
  });

  it("changes status via select", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TaskDetail taskId={1} />);
    await waitFor(() => expect(screen.getByText("Buy milk")).toBeInTheDocument());
    await user.selectOptions(screen.getByLabelText(/Status/i), "done");
    await waitFor(() => expect(state.tasks[0].status).toBe("done"));
  });
});
