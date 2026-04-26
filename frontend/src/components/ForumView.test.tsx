import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { ForumView } from "./ForumView";
import { renderWithProviders } from "../test/utils";
import { resetMockState, state } from "../test/msw-server";

describe("ForumView", () => {
  beforeEach(() => {
    resetMockState();
    state.forum = {
      epic_group_id: 10,
      name: "Backlog",
      subforums: [
        {
          epic_id: 100,
          name: "Auth",
          position: 0,
          topics: [
            {
              task_id: 1,
              title: "Login bug",
              author_id: 1,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              comment_count: 3,
              last_comment_author_id: 1,
              last_comment_at: new Date().toISOString(),
            },
          ],
        },
      ],
    };
  });

  it("renders subforums with topics", async () => {
    renderWithProviders(<ForumView epicGroupId={10} workspaceId={1} />);
    await waitFor(() => expect(screen.getByText("Auth")).toBeInTheDocument());
    expect(screen.getByText("Login bug")).toBeInTheDocument();
    expect(screen.getByText(/3 comments/)).toBeInTheDocument();
  });
});
