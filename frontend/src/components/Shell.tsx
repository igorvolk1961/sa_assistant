import { useEffect, useState } from "react";
import type { ChangeEvent, ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Project } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useCurrentProject } from "../project/CurrentProjectContext";

export function Shell({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { currentProjectId, setCurrentProject } = useCurrentProject();
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    void api
      .get<Project[]>("/projects")
      .then(setProjects)
      .catch(() => undefined);
  }, []);

  function switchProject(event: ChangeEvent<HTMLSelectElement>) {
    const id = event.target.value;
    if (!id) return;
    const project = projects.find((p) => p.id === id);
    if (project) setCurrentProject(project);
    navigate(`/projects/${id}/tasks`);
  }

  return (
    <>
      <div className="topbar">
        <button onClick={() => navigate(-1)} title="Вернуться на предыдущую карточку">
          ← Назад
        </button>
        <strong>Помощник СА</strong>
        <select
          value={currentProjectId ?? ""}
          onChange={switchProject}
          title="Текущий проект"
          style={{ width: "auto", minWidth: 200 }}
        >
          <option value="">— проект —</option>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
        <div className="spacer" />
        <span className="muted">
          {user?.last_name} {user?.first_name}
          {user?.is_service_owner ? " · владелец сервиса" : ""}
        </span>
        <button
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          Выйти
        </button>
      </div>
      <div className="layout">{children}</div>
    </>
  );
}
