import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw-server";
import { ApiError, api } from "./client";

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
});
