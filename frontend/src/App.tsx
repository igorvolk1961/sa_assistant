import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import { Shell } from "./components/Shell";
import { ActorsPage } from "./pages/ActorsPage";
import { LoginPage } from "./pages/LoginPage";
import { MeetingsPage } from "./pages/MeetingsPage";
import { MembersPage } from "./pages/MembersPage";
import { ProjectLayout } from "./pages/ProjectLayout";
import { ProjectsPage } from "./pages/ProjectsPage";
import { RequirementCardPage } from "./pages/RequirementCardPage";
import { RequirementsPage } from "./pages/RequirementsPage";
import { TaskCardPage } from "./pages/TaskCardPage";
import { TasksPage } from "./pages/TasksPage";

function ProtectedShell() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="layout">Загрузка…</div>;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  return (
    <Shell>
      <Outlet />
    </Shell>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedShell />}>
        <Route index element={<ProjectsPage />} />
        <Route path="/projects/:projectId" element={<ProjectLayout />}>
          <Route index element={<Navigate to="tasks" replace />} />
          <Route path="tasks" element={<TasksPage />} />
          <Route path="tasks/:taskId" element={<TaskCardPage />} />
          <Route path="requirements" element={<RequirementsPage />} />
          <Route path="requirements/:requirementId" element={<RequirementCardPage />} />
          <Route path="meetings" element={<MeetingsPage />} />
          <Route path="employees" element={<ActorsPage />} />
          <Route path="stakeholders" element={<ActorsPage />} />
          <Route path="members" element={<MembersPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
