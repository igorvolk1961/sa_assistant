import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type {
  Importance,
  Position,
  Requirement,
  Stakeholder,
  Task,
  TaskStatus,
  TaskType,
} from "../api/types";
import { NewRequirementForm } from "../components/NewRequirementForm";
import { SelectWithCreate } from "../components/SelectWithCreate";
import { compareRequirementCode } from "../utils/sort";
import { useProject } from "./ProjectLayout";

const TYPES: TaskType[] = [
  "feature",
  "improvement",
  "bugfix",
  "analysis",
  "documentation",
  "testing",
  "code_review",
];
const IMPORTANCE: Importance[] = ["low", "medium", "high", "critical"];
const STATUSES: TaskStatus[] = [
  "open",
  "in_progress",
  "on_review",
  "rejected",
  "postponed",
  "completed",
  "completion_postponed",
];

export function TasksPage() {
  const project = useProject();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [mode, setMode] = useState<"mine" | "all">("mine");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [importanceFilter, setImportanceFilter] = useState<string>("");
  const [form, setForm] = useState({
    short_description: "",
    description: "",
    type: "feature" as TaskType,
    importance: "medium" as Importance,
    requirement_id: "",
  });
  const [error, setError] = useState<string | null>(null);

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (statusFilter) params.set("status_filter", statusFilter);
    if (importanceFilter) params.set("importance", importanceFilter);
    const suffix = params.toString() ? `?${params}` : "";
    return `${mode === "mine" ? "/my-tasks" : "/tasks"}${suffix}`;
  }, [mode, statusFilter, importanceFilter]);

  async function load() {
    try {
      setTasks(await api.get<Task[]>(`/projects/${project.id}${query}`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  async function reloadRequirements() {
    setRequirements(
      await api.get<Requirement[]>(`/projects/${project.id}/requirements?limit=200`),
    );
  }

  async function reloadStakeholders() {
    setStakeholders(await api.get<Stakeholder[]>(`/projects/${project.id}/stakeholders`));
  }

  useEffect(() => {
    void api
      .get<Requirement[]>(`/projects/${project.id}/requirements?limit=200`)
      .then(setRequirements)
      .catch(() => undefined);
    void api
      .get<Stakeholder[]>(`/projects/${project.id}/stakeholders`)
      .then(setStakeholders)
      .catch(() => undefined);
    void api
      .get<Position[]>("/reference/positions")
      .then(setPositions)
      .catch(() => undefined);
  }, [project.id]);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id, query]);

  async function createTask(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!form.requirement_id) {
      setError("Выберите или создайте требование");
      return;
    }
    try {
      await api.post(`/projects/${project.id}/tasks`, form);
      setForm({ ...form, short_description: "", description: "" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  const sortedRequirements = [...requirements].sort((a, b) =>
    compareRequirementCode(a.code, b.code),
  );

  return (
    <>
      <div className="row">
        <button
          className={`tab ${mode === "mine" ? "active" : ""}`}
          onClick={() => setMode("mine")}
        >
          Мои задачи
        </button>
        <button
          className={`tab ${mode === "all" ? "active" : ""}`}
          onClick={() => setMode("all")}
        >
          Все задачи
        </button>
        <div className="spacer" />
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">Все статусы</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select value={importanceFilter} onChange={(e) => setImportanceFilter(e.target.value)}>
          <option value="">Любая важность</option>
          {IMPORTANCE.map((i) => (
            <option key={i} value={i}>
              {i}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="error">{error}</div>}

      <table>
        <thead>
          <tr>
            <th>№</th>
            <th>Краткое описание</th>
            <th>Тип</th>
            <th>Важность</th>
            <th>Статус</th>
            <th>Исполнители</th>
            <th>Вид</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => (
            <tr key={task.id}>
              <td>{task.number}</td>
              <td>
                <Link to={`${task.id}`}>{task.short_description}</Link>
              </td>
              <td>{task.type}</td>
              <td>
                <span className={`badge ${task.importance}`}>{task.importance}</span>
              </td>
              <td>
                <span className={`badge ${task.status}`}>{task.status}</span>
              </td>
              <td>
                {task.assignees.length > 0
                  ? task.assignees
                      .map((assignee) =>
                        assignee.is_vacant ? `${assignee.name} (вак.)` : assignee.name,
                      )
                      .join(", ")
                  : "—"}
              </td>
              <td className="muted">{task.parent_task_id ? "подзадача" : "задача"}</td>
            </tr>
          ))}
          {tasks.length === 0 && (
            <tr>
              <td colSpan={7} className="muted">
                Нет задач.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Новая задача</h3>
        <form onSubmit={createTask} className="row" style={{ alignItems: "flex-end" }}>
          <label style={{ flex: 2 }}>
            Краткое описание
            <input
              value={form.short_description}
              onChange={(e) => setForm({ ...form, short_description: e.target.value })}
              required
            />
          </label>
          <label>
            Тип
            <select
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value as TaskType })}
            >
              {TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label>
            Важность
            <select
              value={form.importance}
              onChange={(e) => setForm({ ...form, importance: e.target.value as Importance })}
            >
              {IMPORTANCE.map((i) => (
                <option key={i} value={i}>
                  {i}
                </option>
              ))}
            </select>
          </label>
          <div style={{ flex: 2 }}>
            <div className="muted">Требование</div>
            <SelectWithCreate
              options={sortedRequirements}
              value={form.requirement_id}
              onChange={(id) => setForm({ ...form, requirement_id: id })}
              getLabel={(requirement) => requirement.title}
              reload={reloadRequirements}
              createLabel="+ Создать"
              modalTitle="Новое требование"
              placeholder="— выберите —"
              renderCreateForm={({ onCreated }) => (
                <NewRequirementForm
                  project={project}
                  stakeholders={stakeholders}
                  positions={positions}
                  reloadStakeholders={reloadStakeholders}
                  onCreated={onCreated}
                />
              )}
            />
          </div>
          <button className="primary">Создать</button>
        </form>
      </div>
    </>
  );
}
