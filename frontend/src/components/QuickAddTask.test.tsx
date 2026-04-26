import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { QuickAddTask } from "./QuickAddTask";
import { renderWithProviders } from "../test/utils";
import { resetMockState, state } from "../test/msw-server";

describe("QuickAddTask", () => {
  beforeEach(() => resetMockState());

  it("creates a task in two actions: click + type + Enter", async () => {
    const user = userEvent.setup();
    renderWithProviders(<QuickAddTask epicId={100} />);

    await user.click(screen.getByRole("button", { name: /add task/i }));
    const input = await screen.findByPlaceholderText(/Task title/i);
    await user.type(input, "Buy milk{Enter}");

    await waitFor(() => expect(state.tasks).toHaveLength(1));
    expect(state.tasks[0].title).toBe("Buy milk");
    expect(state.tasks[0].status).toBe("todo");
  });

  it("Esc cancels", async () => {
    const user = userEvent.setup();
    renderWithProviders(<QuickAddTask epicId={100} />);
    await user.click(screen.getByRole("button", { name: /add task/i }));
    const input = await screen.findByPlaceholderText(/Task title/i);
    fireEvent.keyDown(input, { key: "Escape" });
    expect(await screen.findByRole("button", { name: /add task/i })).toBeInTheDocument();
    expect(state.tasks).toHaveLength(0);
  });
});
