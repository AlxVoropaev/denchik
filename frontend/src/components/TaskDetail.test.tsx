import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TaskDetail } from "./TaskDetail";
import { renderWithProviders } from "../test/utils";
import { resetMockState, server, state } from "../test/msw-server";

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
    expect(state.comments[0]?.body).toBe("Hello world");
  });

  it("changes status via select", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TaskDetail taskId={1} />);
    await waitFor(() => expect(screen.getByText("Buy milk")).toBeInTheDocument());
    await user.selectOptions(screen.getByLabelText(/Status/i), "done");
    await waitFor(() => expect(state.tasks[0]?.status).toBe("done"));
  });

  it("closes the title editor on a successful save", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TaskDetail taskId={1} />);
    await waitFor(() => expect(screen.getByText("Buy milk")).toBeInTheDocument());

    await user.click(screen.getByRole("heading", { name: "Buy milk" }));
    const input = screen.getByDisplayValue("Buy milk");
    await user.clear(input);
    await user.type(input, "Buy oat milk");
    input.blur();

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Buy oat milk" })).toBeInTheDocument(),
    );
    expect(screen.queryByDisplayValue("Buy oat milk")).not.toBeInTheDocument();
  });

  it("keeps the title editor open and shows an error when save fails", async () => {
    server.use(
      http.patch("*/tasks/:id", () => HttpResponse.json({ detail: "boom" }, { status: 500 })),
    );
    const user = userEvent.setup();
    renderWithProviders(<TaskDetail taskId={1} />);
    await waitFor(() => expect(screen.getByText("Buy milk")).toBeInTheDocument());

    await user.click(screen.getByRole("heading", { name: "Buy milk" }));
    const input = screen.getByDisplayValue("Buy milk");
    await user.clear(input);
    await user.type(input, "Buy oat milk");
    input.blur();

    // Editor stays open with the typed value preserved.
    await waitFor(() =>
      expect(screen.getByText(/couldn['’]t save|failed to save/i)).toBeInTheDocument(),
    );
    expect(screen.getByDisplayValue("Buy oat milk")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Buy oat milk" })).not.toBeInTheDocument();
  });

  it("disables Post until the comment input has non-empty content", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TaskDetail taskId={1} />);
    await waitFor(() => expect(screen.getByText("Buy milk")).toBeInTheDocument());

    const button = screen.getByRole("button", { name: /post/i });
    expect(button).toBeDisabled();

    await user.type(screen.getByPlaceholderText(/Add a comment/i), "   ");
    expect(button).toBeDisabled();

    await user.type(screen.getByPlaceholderText(/Add a comment/i), "hi");
    expect(button).toBeEnabled();
  });

  it("does not double-fire the create-comment mutation on rapid clicks", async () => {
    const handler = vi.fn(async ({ params, request }) => {
      const id = Number(params.id);
      const body = (await request.json()) as { body: string };
      // Delay so the first click is still pending while the second click happens.
      await new Promise((r) => setTimeout(r, 50));
      const c = {
        id: state.nextId++,
        task_id: id,
        parent_comment_id: null,
        author_id: 1,
        body: body.body,
        created_at: new Date().toISOString(),
        edited_at: null,
      };
      state.comments.push(c);
      return HttpResponse.json(c, { status: 201 });
    });
    server.use(http.post("*/tasks/:id/comments", handler));

    const user = userEvent.setup();
    renderWithProviders(<TaskDetail taskId={1} />);
    await waitFor(() => expect(screen.getByText("Buy milk")).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText(/Add a comment/i), "once");
    const button = screen.getByRole("button", { name: /post/i });
    await user.click(button);
    await user.click(button);

    await waitFor(() => expect(state.comments).toHaveLength(1));
    // Give any extra in-flight call a chance to land.
    await new Promise((r) => setTimeout(r, 100));
    expect(handler).toHaveBeenCalledTimes(1);
    expect(state.comments).toHaveLength(1);
  });

  it("preserves the typed comment when create-comment fails", async () => {
    server.use(
      http.post("*/tasks/:id/comments", () =>
        HttpResponse.json({ detail: "boom" }, { status: 500 }),
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<TaskDetail taskId={1} />);
    await waitFor(() => expect(screen.getByText("Buy milk")).toBeInTheDocument());

    const textarea = screen.getByPlaceholderText(/Add a comment/i) as HTMLTextAreaElement;
    await user.type(textarea, "Hello world");
    await user.click(screen.getByRole("button", { name: /post/i }));

    await waitFor(() =>
      expect(screen.getByText(/couldn['’]t post|failed to post/i)).toBeInTheDocument(),
    );
    expect(textarea.value).toBe("Hello world");
    expect(state.comments).toHaveLength(0);
  });
});
