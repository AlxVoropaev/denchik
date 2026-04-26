import { useEffect, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { BoardView } from "../components/BoardView";
import { ForumView } from "../components/ForumView";
import { useEpicGroups, useCreateEpicGroup, useEpics, useCreateEpic } from "../hooks/useEpics";
import { workspaces } from "../api/endpoints";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export function WorkspacePage() {
  const { wsId, view } = useParams();
  const parsed = Number(wsId);
  const workspaceId = Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  const navigate = useNavigate();
  const wsQuery = useQuery({ queryKey: ["workspaces"], queryFn: workspaces.list });
  const groups = useEpicGroups(workspaceId);
  const [groupId, setGroupId] = useState<number | null>(null);
  const epics = useEpics(groupId);
  const [epicId, setEpicId] = useState<number | null>(null);
  const createGroup = useCreateEpicGroup();
  const createEpic = useCreateEpic();

  console.log(
    "[WorkspacePage] render " +
      JSON.stringify({
        wsIdParam: wsId,
        workspaceId,
        view,
        wsQuery: {
          status: wsQuery.status,
          fetchStatus: wsQuery.fetchStatus,
          dataLen: wsQuery.data?.length,
          data: wsQuery.data,
          error: wsQuery.error ? String(wsQuery.error) : null,
        },
        groups: {
          status: groups.status,
          fetchStatus: groups.fetchStatus,
          dataLen: groups.data?.length,
          data: groups.data,
          error: groups.error ? String(groups.error) : null,
        },
        groupId,
        epics: {
          status: epics.status,
          fetchStatus: epics.fetchStatus,
          dataLen: epics.data?.length,
          data: epics.data,
          error: epics.error ? String(epics.error) : null,
        },
        epicId,
      }),
  );

  useEffect(() => {
    if (groups.data && groups.data.length > 0 && groupId == null) {
      setGroupId(groups.data[0].id);
    }
  }, [groups.data, groupId]);
  useEffect(() => {
    if (epics.data && epics.data.length > 0 && epicId == null) {
      setEpicId(epics.data[0].id);
    }
  }, [epics.data, epicId]);

  if (!wsQuery.data) {
    return <div style={{ padding: 24 }}>Loading…</div>;
  }
  if (wsQuery.data.length === 0) {
    return <CreateFirstWorkspace />;
  }
  if (workspaceId == null) {
    return <Navigate to={`/w/${wsQuery.data[0].id}/board`} replace />;
  }

  const currentView = view === "forum" ? "forum" : "board";

  return (
    <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", height: "100%" }}>
      <aside style={{ background: "#fff", borderRight: "1px solid #dfe1e6", padding: 12 }}>
        <h4>Epic groups</h4>
        {(groups.data ?? []).map((g) => (
          <div key={g.id}>
            <button
              style={{ background: "none", border: "none", color: groupId === g.id ? "#0747a6" : "inherit", fontWeight: 600 }}
              onClick={() => { setGroupId(g.id); setEpicId(null); }}
            >
              {g.name}
            </button>
          </div>
        ))}
        <NewItemInput placeholder="+ New group" onSubmit={(name) => createGroup.mutate({ workspaceId, name })} />

        {groupId && (
          <>
            <h4 style={{ marginTop: 16 }}>Epics</h4>
            {(epics.data ?? []).map((e) => (
              <div key={e.id}>
                <button
                  style={{ background: "none", border: "none", color: epicId === e.id ? "#0747a6" : "inherit" }}
                  onClick={() => setEpicId(e.id)}
                >
                  {e.name}
                </button>
              </div>
            ))}
            <NewItemInput
              placeholder="+ New epic"
              onSubmit={(name) => createEpic.mutate({ epicGroupId: groupId, name })}
            />
          </>
        )}

        <div style={{ marginTop: 24 }}>
          <button onClick={() => navigate(`/w/${workspaceId}/board`)} style={{ marginRight: 8 }}>Board</button>
          <button onClick={() => navigate(`/w/${workspaceId}/forum`)}>Forum</button>
        </div>
      </aside>
      <main style={{ overflow: "auto" }}>
        {currentView === "forum" && groupId ? (
          <ForumView epicGroupId={groupId} workspaceId={workspaceId} />
        ) : epicId ? (
          <BoardView epicId={epicId} workspaceId={workspaceId} />
        ) : (
          <div style={{ padding: 16 }}>Pick or create an epic to get started.</div>
        )}
      </main>
    </div>
  );
}

function NewItemInput({ placeholder, onSubmit }: { placeholder: string; onSubmit: (name: string) => void }) {
  const [v, setV] = useState("");
  const submit = () => {
    const trimmed = v.trim();
    if (!trimmed) return;
    console.log(`[NewItemInput "${placeholder}"] submit "${trimmed}"`);
    onSubmit(trimmed);
    setV("");
  };
  return (
    <form
      style={{ display: "flex", gap: 4, marginTop: 6 }}
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <input
        style={{ flex: 1, padding: 6 }}
        placeholder={placeholder}
        value={v}
        onChange={(e) => setV(e.target.value)}
        onKeyDown={(e) => {
          console.log(
            `[NewItemInput "${placeholder}"] keydown key=${e.key} composing=${(e.nativeEvent as KeyboardEvent).isComposing} value="${v}"`,
          );
        }}
      />
      <button type="submit" disabled={!v.trim()} style={{ padding: "6px 10px" }}>
        Add
      </button>
    </form>
  );
}

function CreateFirstWorkspace() {
  const [name, setName] = useState("");
  const navigate = useNavigate();
  const qc = useQueryClient();
  const create = useMutation({
    mutationFn: (n: string) => {
      console.log("[CreateFirstWorkspace] mutate start", n);
      return workspaces.create(n);
    },
    onSuccess: async (ws) => {
      console.log("[CreateFirstWorkspace] success", ws);
      await qc.invalidateQueries({ queryKey: ["workspaces"] });
      console.log("[CreateFirstWorkspace] cache invalidated, navigating");
      navigate(`/w/${ws.id}/board`);
    },
    onError: (e) => console.error("[CreateFirstWorkspace] error", e),
  });
  return (
    <div className="auth-card">
      <h2>Create your first workspace</h2>
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Workspace name" />
      <button
        disabled={create.isPending || !name.trim()}
        onClick={() => create.mutate(name.trim())}
      >
        {create.isPending ? "Creating…" : "Create"}
      </button>
    </div>
  );
}
