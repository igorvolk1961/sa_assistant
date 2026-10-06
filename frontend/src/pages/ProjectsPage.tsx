import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Project } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useCurrentProject } from "../project/CurrentProjectContext";

export function ProjectsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { currentProjectId, setCurrentProject } = useCurrentProject();
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

  async function rename(project: Project) {
    const name = window.prompt("Новое название проекта", project.name);
    if (!name || name === project.name) return;
    setError(null);
    try {
      const updated = await api.patch<Project>(`/projects/${project.id}`, { name });
      if (currentProjectId === project.id) setCurrentProject(updated);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  async function remove(project: Project) {
    if (!window.confirm(`Удалить проект «${project.name}» со всем содержимым?`)) return;
    setError(null);
    try {
      await api.del(`/projects/${project.id}`);
      if (currentProjectId === project.id) setCurrentProject(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
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
            <div className="row">
              <button className="primary" onClick={() => open(project)}>
                Открыть
              </button>
              <button onClick={() => void rename(project)}>Переименовать</button>
              <button className="danger" onClick={() => void remove(project)}>
                Удалить
              </button>
            </div>
          </div>
        ))}
        {projects.length === 0 && <p className="muted">Нет доступных проектов.</p>}
      </div>
    </>
  );
}
