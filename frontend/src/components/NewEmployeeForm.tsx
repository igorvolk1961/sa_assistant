import { useState } from "react";
import { api } from "../api/client";
import type { Employee, Project } from "../api/types";

interface Props {
  project: Project;
  onCreated: (employee: Employee) => void;
}

export function NewEmployeeForm({ project, onCreated }: Props) {
  const [mode, setMode] = useState<"vacant" | "user">("vacant");
  const [values, setValues] = useState({ user_id: "", first_name: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setError(null);
    let payload: Record<string, string>;
    if (mode === "user") {
      if (!values.user_id) {
        setError("Укажите ID пользователя");
        return;
      }
      payload = { user_id: values.user_id };
    } else {
      if (!values.first_name) {
        setError("Укажите название");
        return;
      }
      payload = { first_name: values.first_name };
    }
    setBusy(true);
    try {
      const created = await api.post<Employee>(`/projects/${project.id}/employees`, payload);
      onCreated(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="form-column">
      <div className="row">
        <label className="row" style={{ gap: 4 }}>
          <input
            type="radio"
            style={{ width: "auto" }}
            checked={mode === "vacant"}
            onChange={() => setMode("vacant")}
          />
          Вакантный тип должности
        </label>
        <label className="row" style={{ gap: 4 }}>
          <input
            type="radio"
            style={{ width: "auto" }}
            checked={mode === "user"}
            onChange={() => setMode("user")}
          />
          Связать с пользователем
        </label>
      </div>
      {mode === "user" ? (
        <input
          placeholder="ID пользователя"
          value={values.user_id}
          onChange={(e) => setValues({ ...values, user_id: e.target.value })}
        />
      ) : (
        <input
          placeholder="Название"
          value={values.first_name}
          onChange={(e) => setValues({ ...values, first_name: e.target.value })}
        />
      )}
      {error && <div className="error">{error}</div>}
      <button type="button" className="primary" disabled={busy} onClick={() => void submit()}>
        Создать должность
      </button>
    </div>
  );
}
