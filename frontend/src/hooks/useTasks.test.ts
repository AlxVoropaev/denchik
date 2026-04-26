import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it } from "vitest";
import { useDeleteTask } from "./useTasks";
import { resetMockState, state } from "../test/msw-server";
import type { Task } from "../api/types";

function makeTask(id: number, epic_id: number): Task {
  return {
    id,
    epic_id,
    author_id: 1,
    title: `Task ${id}`,
    description: null,
    status: "todo",
    priority: "med",
    assignee_id: null,
    due_date: null,
    position: 0,
    created_at: "",
    updated_at: "",
    labels: [],
  };
}

function makeWrapper(qc: QueryClient) {
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children);
}

describe("useDeleteTask", () => {
  beforeEach(() => resetMockState());

  it("invalidates only the deleted task's epic list and removes the single-task entry", async () => {
    // Non-zero gcTime so the unobserved cache entries we seed via
    // setQueryData stay around long enough for us to inspect them after
    // the mutation settles.
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 60_000, staleTime: 0 } },
    });

    const epicA = 100;
    const epicB = 200;
    const taskId = 42;

    state.tasks = [makeTask(taskId, epicA)];

    // Seed cache: two epic lists and the single-task entry. None of them is
    // observed (no useQuery is mounted), so React Query will not refetch them
    // automatically. Invalidation must mark them stale; removeQueries must
    // drop the cached entry entirely.
    qc.setQueryData(["tasks", epicA], [makeTask(taskId, epicA)]);
    qc.setQueryData(["tasks", epicB], [makeTask(999, epicB)]);
    qc.setQueryData(["task", taskId], makeTask(taskId, epicA));

    const { result } = renderHook(() => useDeleteTask(), {
      wrapper: makeWrapper(qc),
    });

    result.current.mutate({ id: taskId, epicId: epicA });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // The deleted task's epic list is stale.
    expect(qc.getQueryState(["tasks", epicA])?.isInvalidated).toBe(true);
    // Other epic lists must NOT be touched.
    expect(qc.getQueryState(["tasks", epicB])?.isInvalidated).toBe(false);
    // The single-task entry is removed from the cache.
    expect(qc.getQueryState(["task", taskId])).toBeUndefined();
  });
});
