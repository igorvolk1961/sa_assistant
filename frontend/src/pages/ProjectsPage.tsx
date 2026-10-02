import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Project } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useCurrentProject } from "../project/CurrentProjectContext";

export function ProjectsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { setCurrentProject } = useCurrentProject();
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");

  async function load() {
    try {
      setProjects(await api.get<Project[]>("/projects"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function createProject(event: React.FormEvent) {
    event.preventDefault();
    await api.post<Project>("/projects", { name });
    setName("");
    await load();
  }

  function open(project: Project) {
    setCurrentProject(project);
    navigate(`/projects/${project.id}/tasks`);
  }

  return (
    <>
      <div className="row">
        <h2>Проекты</h2>
        <div className="spacer" />
        {user?.is_service_owner && (
          <form className="row" onSubmit={createProject}>
            <input
              placeholder="Название проекта"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <button className="primary">Создать проект</button>
          </form>
        )}
      </div>
      {error && <div className="error">{error}</div>}
      <div className="grid">
        {projects.map((project) => (
          <div className="card" key={project.id}>
            <div className="row">
              <strong>{project.name}</strong>
              <div className="spacer" />
              <span className={`badge ${project.status}`}>{project.status}</span>
            </div>
            {project.description && <p className="muted">{project.description}</p>}
            <button className="primary" onClick={() => open(project)}>
              Открыть
            </button>
          </div>
        ))}
        {projects.length === 0 && <p className="muted">Нет доступных проектов.</p>}
      </div>
    </>
  );
}
