import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { AuthPage } from "./AuthPage";
import { renderWithProviders } from "../test/utils";
import { resetMockState, state } from "../test/msw-server";

describe("AuthPage", () => {
  beforeEach(() => resetMockState());

  it("logs in", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AuthPage />);
    await user.type(screen.getByPlaceholderText(/Email/i), "alice@example.com");
    await user.type(screen.getByPlaceholderText(/Password/i), "secretpw");
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(state.user?.email).toBe("alice@example.com"));
  });
});
