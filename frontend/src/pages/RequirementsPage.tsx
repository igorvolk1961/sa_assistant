import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type {
  NfrType,
  Position,
  Requirement,
  RequirementEpic,
  RequirementType,
  Stakeholder,
} from "../api/types";
import { NewStakeholderForm } from "../components/NewStakeholderForm";
import { SelectWithCreate } from "../components/SelectWithCreate";
import { compareRequirementCode } from "../utils/sort";
import { useProject } from "./ProjectLayout";

const TYPES: RequirementType[] = ["business", "functional", "nonfunctional"];

interface Group {
  key: string;
  label: string;
  sort: number;
  items: Requirement[];
}

export function RequirementsPage() {
  const project = useProject();
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [epics, setEpics] = useState<RequirementEpic[]>([]);
  const [nfrTypes, setNfrTypes] = useState<NfrType[]>([]);
  const [newEpic, setNewEpic] = useState("");
  const [form, setForm] = useState({
    title: "",
    type: "functional" as RequirementType,
    short_description: "",
    stakeholder_id: "",
    epic_id: "",
    nfr_type_id: "",
  });
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setRequirements(
        await api.get<Requirement[]>(`/projects/${project.id}/requirements?limit=500`),
      );
      setStakeholders(await api.get<Stakeholder[]>(`/projects/${project.id}/stakeholders`));
      setPositions(await api.get<Position[]>("/reference/positions"));
      setEpics(await api.get<RequirementEpic[]>(`/projects/${project.id}/epics`));
      setNfrTypes(await api.get<NfrType[]>("/reference/nfr-types"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  async function reloadStakeholders() {
    setStakeholders(await api.get<Stakeholder[]>(`/projects/${project.id}/stakeholders`));
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

  function buildGroups(items: Requirement[], kind: "epic" | "nfr"): Group[] {
    const groups = new Map<string, Group>();
    for (const requirement of items) {
      const refId = kind === "epic" ? requirement.epic_id : requirement.nfr_type_id;
      const key = refId ?? "__none";
      if (!groups.has(key)) {
        let label = kind === "epic" ? "Без эпика" : "Без группы NFR";
        let sort = 9999;
        if (kind === "epic" && refId) {
          const epic = epics.find((e) => e.id === refId);
          label = epic?.name ?? "—";
          sort = epic?.sort_order ?? 9999;
        }
        if (kind === "nfr" && refId) {
          const nfr = nfrTypes.find((n) => n.id === refId);
          label = nfr?.name ?? nfr?.code ?? "—";
        }
        groups.set(key, { key, label, sort, items: [] });
      }
      groups.get(key)!.items.push(requirement);
    }
    return [...groups.values()]
      .sort((a, b) => a.sort - b.sort || a.label.localeCompare(b.label))
      .map((group) => ({
        ...group,
        items: [...group.items].sort((a, b) => compareRequirementCode(a.code, b.code)),
      }));
  }

  async function addEpic(event: FormEvent) {
    event.preventDefault();
    if (!newEpic) return;
    setError(null);
    try {
      await api.post(`/projects/${project.id}/epics`, { name: newEpic });
      setNewEpic("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  async function deleteEpic(epicId: string) {
    setError(null);
    try {
      await api.del(`/projects/${project.id}/epics/${epicId}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await api.post(`/projects/${project.id}/requirements`, {
        ...form,
        stakeholder_id: form.stakeholder_id || undefined,
        epic_id: form.epic_id || undefined,
        nfr_type_id: form.nfr_type_id || undefined,
      });
      setForm({ ...form, title: "", short_description: "" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  function renderTable(items: Requirement[]) {
    return (
      <table>
        <thead>
          <tr>
            <th>Код</th>
            <th>Название</th>
            <th>Тип</th>
            <th>Важность</th>
            <th>Приоритет</th>
            <th>Статус</th>
            <th>Стейкхолдер</th>
          </tr>
        </thead>
        <tbody>
          {items.map((requirement) => (
            <tr key={requirement.id}>
              <td className="muted">{requirement.code ?? "—"}</td>
              <td>
                <Link to={requirement.id}>{requirement.title}</Link>
              </td>
              <td>{requirement.type}</td>
              <td>
                <span className={`badge ${requirement.importance}`}>{requirement.importance}</span>
              </td>
              <td>{requirement.priority_moscow ?? "—"}</td>
              <td>{requirement.implementation_status ?? "—"}</td>
              <td className="muted">
                {requirement.stakeholder_id ? stakeholderLabel(requirement.stakeholder_id) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  const functionalGroups = buildGroups(
    requirements.filter((r) => r.type !== "nonfunctional"),
    "epic",
  );
  const nfrGroups = buildGroups(
    requirements.filter((r) => r.type === "nonfunctional"),
    "nfr",
  );

  return (
    <>
      <div className="row">
        <h3>Требования</h3>
        <div className="spacer" />
        <form className="row" onSubmit={addEpic}>
          <input
            placeholder="Новый эпик"
            value={newEpic}
            onChange={(e) => setNewEpic(e.target.value)}
          />
          <button className="primary">Добавить эпик</button>
        </form>
      </div>
      {error && <div className="error">{error}</div>}

      {functionalGroups.map((group) => (
        <div key={group.key} className="card">
          <div className="row">
            <h4 style={{ margin: 0 }}>{group.label}</h4>
            <span className="muted">({group.items.length})</span>
            <div className="spacer" />
            {group.key !== "__none" && (
              <button className="danger" onClick={() => void deleteEpic(group.key)}>
                Удалить эпик
              </button>
            )}
          </div>
          {renderTable(group.items)}
        </div>
      ))}

      {nfrGroups.map((group) => (
        <div key={group.key} className="card">
          <h4 style={{ marginTop: 0 }}>
            {group.label} <span className="muted">({group.items.length})</span>
          </h4>
          {renderTable(group.items)}
        </div>
      ))}

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Новое требование</h3>
        <form onSubmit={create} className="row" style={{ alignItems: "flex-end" }}>
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
          <label>
            Эпик
            <select
              value={form.epic_id}
              onChange={(e) => setForm({ ...form, epic_id: e.target.value })}
            >
              <option value="">— без эпика —</option>
              {epics.map((epic) => (
                <option key={epic.id} value={epic.id}>
                  {epic.name}
                </option>
              ))}
            </select>
          </label>
          {form.type === "nonfunctional" && (
            <label>
              Группа NFR
              <select
                value={form.nfr_type_id}
                onChange={(e) => setForm({ ...form, nfr_type_id: e.target.value })}
              >
                <option value="">— без группы —</option>
                {nfrTypes.map((nfr) => (
                  <option key={nfr.id} value={nfr.id}>
                    {nfr.name ?? nfr.code}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div style={{ flex: 2 }}>
            <div className="muted">Стейкхолдер</div>
            <SelectWithCreate
              options={stakeholders}
              value={form.stakeholder_id}
              onChange={(id) => setForm({ ...form, stakeholder_id: id })}
              getLabel={(s) => stakeholderLabel(s.id)}
              reload={reloadStakeholders}
              createLabel="+ Создать"
              modalTitle="Новый стейкхолдер"
              placeholder="— без стейкхолдера —"
              renderCreateForm={({ onCreated }) => (
                <NewStakeholderForm
                  project={project}
                  positions={positions}
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
