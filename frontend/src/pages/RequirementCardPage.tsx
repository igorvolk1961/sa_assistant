import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Comment, Position, Requirement, Stakeholder, Task, TaskType } from "../api/types";
import { useProject } from "./ProjectLayout";

const TYPES: TaskType[] = ["feature", "analysis", "documentation", "testing"];

export function RequirementCardPage() {
  const project = useProject();
  const { requirementId } = useParams();
  const [requirement, setRequirement] = useState<Requirement | null>(null);
  const [stakeholder, setStakeholder] = useState<Stakeholder | null>(null);
  const [position, setPosition] = useState<Position | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [newTask, setNewTask] = useState({ short_description: "", type: "feature" as TaskType });
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!requirementId) return;
    try {
      const loaded = await api.get<Requirement>(
        `/projects/${project.id}/requirements/${requirementId}`,
      );
      setRequirement(loaded);
      const stakeholders = await api.get<Stakeholder[]>(`/projects/${project.id}/stakeholders`);
      const found = stakeholders.find((s) => s.id === loaded.stakeholder_id) ?? null;
      setStakeholder(found);
      if (found) {
        const positions = await api.get<Position[]>("/reference/positions");
        setPosition(positions.find((p) => p.id === found.position_id) ?? null);
      }
      setTasks(
        await api.get<Task[]>(`/projects/${project.id}/requirements/${requirementId}/tasks`),
      );
      setComments(
        await api.get<Comment[]>(
          `/projects/${project.id}/comments?entity_type=requirement&entity_id=${requirementId}`,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id, requirementId]);

  async function run(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  if (error) return <div className="error">{error}</div>;
  if (!requirement) return <div>Загрузка требования…</div>;

  return (
    <>
      <div className="row">
        <h2>{requirement.title}</h2>
        <span className="badge">{requirement.type}</span>
        <span className={`badge ${requirement.importance}`}>{requirement.importance}</span>
      </div>

      <div className="card">
        <p>{requirement.description ?? requirement.short_description ?? "Описание не задано."}</p>
        <p className="muted">
          Стейкхолдер:{" "}
          {stakeholder
            ? `${[stakeholder.last_name, stakeholder.first_name].filter(Boolean).join(" ") || "Абстрактный"} · ${position?.name ?? "тип?"}`
            : "—"}
        </p>
      </div>

      <div className="card">
        <h3>Связанные задачи</h3>
        <ul>
          {tasks.map((task) => (
            <li key={task.id}>
              <Link to={`../tasks/${task.id}`}>
                #{task.number} {task.short_description}
              </Link>{" "}
              <span className={`badge ${task.status}`}>{task.status}</span>
            </li>
          ))}
          {tasks.length === 0 && <li className="muted">Задач пока нет.</li>}
        </ul>
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            if (!newTask.short_description) return;
            void run(() =>
              api.post(`/projects/${project.id}/tasks`, {
                requirement_id: requirement.id,
                type: newTask.type,
                short_description: newTask.short_description,
              }),
            );
            setNewTask({ ...newTask, short_description: "" });
          }}
        >
          <input
            placeholder="Краткое описание задачи"
            value={newTask.short_description}
            onChange={(e) => setNewTask({ ...newTask, short_description: e.target.value })}
          />
          <select
            value={newTask.type}
            onChange={(e) => setNewTask({ ...newTask, type: e.target.value as TaskType })}
          >
            {TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <button>Создать задачу</button>
        </form>
      </div>

      <div className="card">
        <h3>Комментарии</h3>
        <ul>
          {comments.map((c) => (
            <li key={c.id}>
              <span className="badge">{c.author_role_snapshot ?? "guest"}</span> {c.body}
            </li>
          ))}
          {comments.length === 0 && <li className="muted">Нет комментариев.</li>}
        </ul>
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            if (!comment) return;
            void run(() =>
              api.post(`/projects/${project.id}/comments`, {
                entity_type: "requirement",
                entity_id: requirement.id,
                body: comment,
              }),
            );
            setComment("");
          }}
        >
          <input placeholder="Комментарий" value={comment} onChange={(e) => setComment(e.target.value)} />
          <button>Отправить</button>
        </form>
      </div>
    </>
  );
}
