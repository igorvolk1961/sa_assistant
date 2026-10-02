import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type {
  Comment,
  Employee,
  Requirement,
  Task,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useProject } from "./ProjectLayout";

interface Assignment {
  id: string;
  task_id: string;
  employee_id: string;
}
interface Version {
  id: string;
  version_no: number;
  result_text: string | null;
  review_status: string | null;
  review_comment: string | null;
}
interface Attachment {
  id: string;
  filename: string | null;
  mime_type: string | null;
  size_bytes: number | null;
}

export function TaskCardPage() {
  const project = useProject();
  const { taskId } = useParams();
  const { user } = useAuth();
  const base = `/projects/${project.id}/tasks/${taskId}`;
  const [task, setTask] = useState<Task | null>(null);
  const [requirement, setRequirement] = useState<Requirement | null>(null);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [dependencies, setDependencies] = useState<Task[]>([]);
  const [dependents, setDependents] = useState<Task[]>([]);
  const [allTasks, setAllTasks] = useState<Task[]>([]);
  const [subtasks, setSubtasks] = useState<Task[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [versions, setVersions] = useState<Version[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [comment, setComment] = useState("");
  const [subtaskTitle, setSubtaskTitle] = useState("");
  const [resultText, setResultText] = useState("");
  const [reviewComment, setReviewComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!taskId) return;
    try {
      const loaded = await api.get<Task>(base);
      setTask(loaded);
      setRequirement(await api.get<Requirement>(`/projects/${project.id}/requirements/${loaded.requirement_id}`));
      setEmployees(await api.get<Employee[]>(`/projects/${project.id}/employees`));
      setAssignments(await api.get<Assignment[]>(`${base}/assignments`));
      setDependencies(await api.get<Task[]>(`${base}/dependencies`));
      setDependents(await api.get<Task[]>(`${base}/dependents`));
      setSubtasks(await api.get<Task[]>(`/projects/${project.id}/tasks?parent_task_id=${taskId}`));
      setAllTasks(await api.get<Task[]>(`/projects/${project.id}/tasks?limit=200`));
      setComments(
        await api.get<Comment[]>(
          `/projects/${project.id}/comments?entity_type=task&entity_id=${taskId}`,
        ),
      );
      setVersions(await api.get<Version[]>(`${base}/versions`));
      setAttachments(await api.get<Attachment[]>(`${base}/attachments`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id, taskId]);

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
  if (!task) return <div>Загрузка задачи…</div>;

  const isAnalysis = task.type === "analysis";
  const assignedIds = new Set(assignments.map((a) => a.employee_id));

  return (
    <>
      <div className="row">
        <h2>
          #{task.number} {task.short_description}
        </h2>
        <span className={`badge ${task.importance}`}>{task.importance}</span>
        <span className={`badge ${task.status}`}>{task.status}</span>
        <span className="badge">{task.parent_task_id ? "подзадача" : "задача"}</span>
      </div>

      <div className="card">
        <p className="muted">
          Требование:{" "}
          {requirement ? (
            <Link to={`../requirements/${requirement.id}`}>{requirement.title}</Link>
          ) : (
            "…"
          )}
        </p>
        <p>{task.description ?? "Полное описание не задано."}</p>
        {task.prompt && (
          <p className="muted">
            Промпт: <code>{task.prompt}</code>
          </p>
        )}
      </div>

      <div className="card">
        <h3>Исполнители</h3>
        <div className="row">
          {assignments.map((a) => {
            const employee = employees.find((e) => e.id === a.employee_id);
            return (
              <span key={a.id} className="badge">
                {employee
                  ? `${employee.last_name ?? ""} ${employee.first_name ?? ""}`
                  : a.employee_id}
                {employee?.user_id === null && " (вакансия)"}
                <button
                  className="danger"
                  style={{ marginLeft: 8 }}
                  onClick={() => run(() => api.del(`${base}/assignments/${a.employee_id}`))}
                >
                  ×
                </button>
              </span>
            );
          })}
          {assignments.length === 0 && <span className="muted">Нет исполнителей (задача в пуле).</span>}
        </div>
        <select
          defaultValue=""
          onChange={(e) => {
            const value = e.target.value;
            if (value) void run(() => api.post(`${base}/assignments`, { employee_id: value }));
            e.target.value = "";
          }}
        >
          <option value="">Назначить сотрудника…</option>
          {employees
            .filter((employee) => !assignedIds.has(employee.id))
            .map((employee) => (
              <option key={employee.id} value={employee.id}>
                {employee.last_name} {employee.first_name}
                {employee.user_id === null ? " (вакансия)" : ""}
              </option>
            ))}
        </select>
      </div>

      <div className="card">
        <h3>Зависимости</h3>
        <div className="row">
          {dependencies.map((dep) => (
            <span key={dep.id} className="badge">
              ← #{dep.number} {dep.short_description}
              <button
                className="danger"
                style={{ marginLeft: 8 }}
                onClick={() => run(() => api.del(`${base}/dependencies/${dep.id}`))}
              >
                ×
              </button>
            </span>
          ))}
          {dependencies.length === 0 && <span className="muted">Нет зависимостей.</span>}
        </div>
        <select
          defaultValue=""
          onChange={(e) => {
            const value = e.target.value;
            if (value) void run(() => api.post(`${base}/dependencies`, { depends_on_task_id: value }));
            e.target.value = "";
          }}
        >
          <option value="">Добавить зависимость…</option>
          {allTasks
            .filter((t) => t.id !== task.id)
            .map((t) => (
              <option key={t.id} value={t.id}>
                #{t.number} {t.short_description}
              </option>
            ))}
        </select>
        {dependents.length > 0 && (
          <p className="muted">
            От неё зависят:{" "}
            {dependents.map((t) => (
              <Link key={t.id} to={`../${t.id}`} style={{ marginRight: 8 }}>
                #{t.number}
              </Link>
            ))}
          </p>
        )}
      </div>

      <div className="card">
        <h3>Подзадачи</h3>
        <ul>
          {subtasks.map((sub) => (
            <li key={sub.id}>
              <Link to={`../${sub.id}`}>
                #{sub.number} {sub.short_description}
              </Link>{" "}
              <span className={`badge ${sub.status}`}>{sub.status}</span>
            </li>
          ))}
          {subtasks.length === 0 && <li className="muted">Нет подзадач.</li>}
        </ul>
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            if (!subtaskTitle) return;
            void run(() =>
              api.post(`/projects/${project.id}/tasks`, {
                requirement_id: task.requirement_id,
                type: "feature",
                short_description: subtaskTitle,
                parent_task_id: task.id,
              }),
            );
            setSubtaskTitle("");
          }}
        >
          <input
            placeholder="Краткое описание подзадачи"
            value={subtaskTitle}
            onChange={(e) => setSubtaskTitle(e.target.value)}
          />
          <button>Создать подзадачу</button>
        </form>
      </div>

      {isAnalysis && (
        <div className="card">
          <h3>Приёмка (задача типа «анализ»)</h3>
          {user && (
            <>
              <textarea
                placeholder="Результат"
                value={resultText}
                onChange={(e) => setResultText(e.target.value)}
              />
              <button
                className="primary"
                onClick={() => run(() => api.post(`${base}/submit`, { result_text: resultText }))}
              >
                Сдать на проверку
              </button>
              <div className="row" style={{ marginTop: 8 }}>
                <input
                  placeholder="Комментарий при отклонении (обязателен)"
                  value={reviewComment}
                  onChange={(e) => setReviewComment(e.target.value)}
                />
                <button onClick={() => run(() => api.post(`${base}/review`, { accept: true }))}>
                  Принять
                </button>
                <button
                  className="danger"
                  onClick={() =>
                    run(() => api.post(`${base}/review`, { accept: false, comment: reviewComment }))
                  }
                >
                  Отклонить
                </button>
              </div>
            </>
          )}
          {versions.length > 0 && (
            <ul className="muted">
              {versions.map((v) => (
                <li key={v.id}>
                  v{v.version_no} — {v.review_status ?? "—"} {v.review_comment ? `(${v.review_comment})` : ""}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="card">
        <h3>Файлы</h3>
        <ul>
          {attachments.map((a) => (
            <li key={a.id}>
              <button
                onClick={() =>
                  void api.download(`${base}/attachments/${a.id}/content`, a.filename ?? "file")
                }
              >
                {a.filename}
              </button>
            </li>
          ))}
          {attachments.length === 0 && <li className="muted">Нет файлов.</li>}
        </ul>
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            const input = e.currentTarget.elements.namedItem("file") as HTMLInputElement;
            const file = input.files?.[0];
            if (!file) return;
            const form = new FormData();
            form.append("file", file);
            void run(() => api.upload(`${base}/attachments`, form));
            input.value = "";
          }}
        >
          <input type="file" name="file" />
          <button>Загрузить</button>
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
                entity_type: "task",
                entity_id: task.id,
                body: comment,
              }),
            );
            setComment("");
          }}
        >
          <input
            placeholder="Комментарий"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <button>Отправить</button>
        </form>
      </div>
    </>
  );
}
