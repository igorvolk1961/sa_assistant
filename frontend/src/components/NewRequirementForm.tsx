import { useState } from "react";
import { api } from "../api/client";
import type {
  Position,
  Project,
  Requirement,
  RequirementType,
  Stakeholder,
} from "../api/types";
import { NewStakeholderForm } from "./NewStakeholderForm";
import { SelectWithCreate } from "./SelectWithCreate";

const TYPES: RequirementType[] = ["business", "functional", "nonfunctional"];

interface Props {
  project: Project;
  stakeholders: Stakeholder[];
  positions: Position[];
  reloadStakeholders: () => Promise<void>;
  onCreated: (requirement: Requirement) => void;
}

export function NewRequirementForm({
  project,
  stakeholders,
  positions,
  reloadStakeholders,
  onCreated,
}: Props) {
  const [values, setValues] = useState({
    title: "",
    type: "functional" as RequirementType,
    short_description: "",
    stakeholder_id: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function stakeholderLabel(id: string): string {
    const stakeholder = stakeholders.find((s) => s.id === id);
    if (!stakeholder) return "—";
    const position = positions.find((p) => p.id === stakeholder.position_id);
    const name = [stakeholder.last_name, stakeholder.first_name].filter(Boolean).join(" ");
    return `${name || "Абстрактный"} · ${position?.name ?? "тип?"}`;
  }

  async function submit() {
    if (!values.title || !values.stakeholder_id) {
      setError("Укажите название и стейкхолдера");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await api.post<Requirement>(
        `/projects/${project.id}/requirements`,
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
      <input
        placeholder="Название требования"
        value={values.title}
        onChange={(e) => setValues({ ...values, title: e.target.value })}
      />
      <select
        value={values.type}
        onChange={(e) => setValues({ ...values, type: e.target.value as RequirementType })}
      >
        {TYPES.map((type) => (
          <option key={type} value={type}>
            {type}
          </option>
        ))}
      </select>
      <SelectWithCreate
        options={stakeholders}
        value={values.stakeholder_id}
        onChange={(id) => setValues({ ...values, stakeholder_id: id })}
        getLabel={(stakeholder) => stakeholderLabel(stakeholder.id)}
        reload={reloadStakeholders}
        createLabel="+ Стейкхолдер"
        modalTitle="Новый стейкхолдер"
        placeholder="— стейкхолдер —"
        renderCreateForm={({ onCreated: onStakeholderCreated }) => (
          <NewStakeholderForm
            project={project}
            positions={positions}
            onCreated={onStakeholderCreated}
          />
        )}
      />
      <input
        placeholder="Краткое описание (необязательно)"
        value={values.short_description}
        onChange={(e) => setValues({ ...values, short_description: e.target.value })}
      />
      {error && <div className="error">{error}</div>}
      <button type="button" className="primary" disabled={busy} onClick={() => void submit()}>
        Создать требование
      </button>
    </div>
  );
}
