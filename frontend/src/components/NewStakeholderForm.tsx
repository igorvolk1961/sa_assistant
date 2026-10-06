import { useState } from "react";
import { api } from "../api/client";
import type { Position, Project, Stakeholder } from "../api/types";

interface Props {
  project: Project;
  positions: Position[];
  onCreated: (stakeholder: Stakeholder) => void;
}

export function NewStakeholderForm({ project, positions, onCreated }: Props) {
  const [values, setValues] = useState({
    position_id: "",
    last_name: "",
    first_name: "",
    organization: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!values.position_id) {
      setError("Укажите тип стейкхолдера");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await api.post<Stakeholder>(
        `/projects/${project.id}/stakeholders`,
        values,
      );
      onCreated(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="form-column">
      <select
        value={values.position_id}
        onChange={(e) => setValues({ ...values, position_id: e.target.value })}
      >
        <option value="">— тип (обязательно) —</option>
        {positions
          .filter((position) => position.usable_as_stakeholder_type)
          .map((position) => (
            <option key={position.id} value={position.id}>
              {position.name}
            </option>
          ))}
      </select>
      <input
        placeholder="Фамилия"
        value={values.last_name}
        onChange={(e) => setValues({ ...values, last_name: e.target.value })}
      />
      <input
        placeholder="Имя"
        value={values.first_name}
        onChange={(e) => setValues({ ...values, first_name: e.target.value })}
      />
      <input
        placeholder="Организация"
        value={values.organization}
        onChange={(e) => setValues({ ...values, organization: e.target.value })}
      />
      {error && <div className="error">{error}</div>}
      <button type="button" className="primary" disabled={busy} onClick={() => void submit()}>
        Создать стейкхолдера
      </button>
    </div>
  );
}
