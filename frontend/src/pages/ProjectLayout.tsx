import { useEffect, useState } from "react";
import { NavLink, Outlet, useOutletContext, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Project } from "../api/types";
import { useCurrentProject } from "../project/CurrentProjectContext";

interface ProjectOutlet {
  project: Project;
}

export function useProject(): Project {
  return useOutletContext<ProjectOutlet>().project;
}

const TABS = [
  { to: "tasks", label: "Задачи" },
  { to: "requirements", label: "Требования" },
  { to: "meetings", label: "Встречи" },
  { to: "employees", label: "Должности" },
  { to: "stakeholders", label: "Стейкхолдеры" },
  { to: "members", label: "Участники" },
];

export function ProjectLayout() {
  const { projectId } = useParams();
  const { setCurrentProject } = useCurrentProject();
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    api
      .get<Project>(`/projects/${projectId}`)
      .then((loaded) => {
        setProject(loaded);
        setCurrentProject(loaded);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Ошибка"));
  }, [projectId, setCurrentProject]);

  if (error) return <div className="error">{error}</div>;
  if (!project) return <div>Загрузка проекта…</div>;

  return (
    <>
      <div className="row">
        <h2>{project.name}</h2>
        <span className={`badge ${project.status}`}>{project.status}</span>
      </div>
      <nav className="tabs">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) => `tab ${isActive ? "active" : ""}`}
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <Outlet context={{ project }} />
    </>
  );
}
