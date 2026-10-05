import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type {
  Position,
  Requirement,
  RequirementType,
  Stakeholder,
} from "../api/types";
import { useProject } from "./ProjectLayout";

const TYPES: RequirementType[] = ["business", "functional", "nonfunctional"];

export function RequirementsPage() {
  const project = useProject();
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [form, setForm] = useState({
    title: "",
    type: "functional" as RequirementType,
    short_description: "",
    stakeholder_id: "",
  });
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setRequirements(
        await api.get<Requirement[]>(`/projects/${project.id}/requirements?limit=200`),
      );
      setStakeholders(await api.get<Stakeholder[]>(`/projects/${project.id}/stakeholders`));
      setPositions(await api.get<Position[]>("/reference/positions"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id]);

  function stakeholderLabel(id: string): string {
    const stakeholder = stakeholders.find((s) => s.id === id);
    if (!stakeholder) return "—";
    const position = positions.find((p) => p.id === stakeholder.position_id);
    const name = [stakeholder.last_name, stakeholder.first_name].filter(Boolean).join(" ");
    return `${name || "Абстрактный"} · ${position?.name ?? "тип?"}`;
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await api.post(`/projects/${project.id}/requirements`, form);
      setForm({ ...form, title: "", short_description: "" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  return (
    <>
      <h3>Требования</h3>
      {error && <div className="error">{error}</div>}
      <table>
        <thead>
          <tr>
            <th>Название</th>
            <th>Тип</th>
            <th>Важность</th>
            <th>Стейкхолдер</th>
          </tr>
        </thead>
        <tbody>
          {requirements.map((requirement) => (
            <tr key={requirement.id}>
              <td>
                <Link to={requirement.id}>{requirement.title}</Link>
              </td>
              <td>{requirement.type}</td>
              <td>
                <span className={`badge ${requirement.importance}`}>{requirement.importance}</span>
              </td>
              <td className="muted">{stakeholderLabel(requirement.stakeholder_id)}</td>
            </tr>
          ))}
          {requirements.length === 0 && (
            <tr>
              <td colSpan={4} className="muted">
                Нет требований.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Новое требование</h3>
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            void create(e);
          }}
        >
          <label style={{ flex: 2 }}>
            Название
            <input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              required
            />
          </label>
          <label>
            Тип
            <select
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value as RequirementType })}
            >
              {TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <SelectWithCreate
            options={stakeholders}
            value={form.stakeholder_id}
            onChange={(id) => setForm({ ...form, stakeholder_id: id })}
            getLabel={(s) => stakeholderLabel(s.id)}
            createButtonLabel="Создать стейкхолдера"
            modalTitle="Новый стейкхолдер"
            createForm={
              <NewStakeholderForm
                project={project}
                positions={positions}
                onCreated={reloadStakeholders}
              />
            }
          />
          <button className="primary">Создать</button>
        </form>
      </div>
    </>
  );
}
