import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useMe, useLogout } from "./hooks/useAuth";
import { AuthPage } from "./pages/AuthPage";
import { TaskPage } from "./pages/TaskPage";
import { WorkspacePage } from "./pages/WorkspacePage";

export function App() {
  const me = useMe();
  const logout = useLogout();
  const location = useLocation();
  const navigate = useNavigate();

  if (me.isLoading) return <div style={{ padding: 24 }}>Loading…</div>;

  if (!me.data) {
    if (location.pathname !== "/login") return <Navigate to="/login" replace />;
    return (
      <Routes>
        <Route path="/login" element={<AuthPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <strong>denchik</strong>
        <Link to="/" className={location.pathname === "/" ? "active" : ""}>Home</Link>
        <span className="spacer" />
        <span>{me.data.display_name}</span>
        <button
          onClick={() => logout.mutate(undefined, { onSuccess: () => navigate("/login") })}
          style={{ background: "transparent", color: "#fff", border: "1px solid rgba(255,255,255,0.3)", padding: "6px 10px", borderRadius: 4 }}
        >
          Logout
        </button>
      </header>
      <Routes>
        <Route path="/" element={<WorkspacePage />} />
        <Route path="/w/:wsId/:view" element={<WorkspacePage />} />
        <Route path="/w/:wsId/task/:taskId" element={<TaskPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
