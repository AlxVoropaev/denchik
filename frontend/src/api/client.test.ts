import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw-server";
import { useAuthStore } from "../store/auth";
import { ApiError, api, setAuthRedirect } from "./client";

describe("api client", () => {
  it("throws ApiError with detail on 4xx", async () => {
    server.use(
      http.get("*/boom", () =>
        HttpResponse.json({ detail: "kaboom" }, { status: 400 }),
      ),
    );
    await expect(api.get("/boom")).rejects.toMatchObject({
      message: "kaboom",
      status: 400,
    });
    await expect(api.get("/boom")).rejects.toBeInstanceOf(ApiError);
  });

  it("returns parsed JSON on 200", async () => {
    server.use(http.get("*/ping", () => HttpResponse.json({ ok: true })));
    await expect(api.get("/ping")).resolves.toEqual({ ok: true });
  });

  describe("401 handling", () => {
    let redirect: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      redirect = vi.fn();
      setAuthRedirect(redirect);
      useAuthStore.setState({
        user: { id: 1, email: "x@y.z", display_name: "X" },
      });
    });

    afterEach(() => {
      setAuthRedirect(null);
      useAuthStore.setState({ user: null });
    });

    it("clears the auth store and redirects on 401 from a non-auth route", async () => {
      server.use(
        http.get("*/workspaces", () => new HttpResponse(null, { status: 401 })),
      );
      await expect(api.get("/workspaces")).rejects.toBeInstanceOf(ApiError);
      expect(useAuthStore.getState().user).toBeNull();
      expect(redirect).toHaveBeenCalledWith("/auth");
    });

    it("does not redirect on 401 from /auth/* routes", async () => {
      server.use(
        http.get("*/auth/me", () => new HttpResponse(null, { status: 401 })),
      );
      await expect(api.get("/auth/me")).rejects.toBeInstanceOf(ApiError);
      // /auth/me 401 is the normal "not logged in" signal — AuthPage handles it.
      // We must not preempt that with a redirect (which would cause a loop on /auth itself).
      expect(redirect).not.toHaveBeenCalled();
    });
  });
});
