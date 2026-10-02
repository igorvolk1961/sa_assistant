import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "../api/client";
import type { Employee, Position, Stakeholder } from "../api/types";
import { useProject } from "./ProjectLayout";

export function ActorsPage() {
  const project = useProject();
  const location = useLocation();
  const isStakeholders = location.pathname.endsWith("stakeholders");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [employeePositions, setEmployeePositions] = useState<Record<string, string[]>>({});
  const [employeeForm, setEmployeeForm] = useState({ user_id: "", last_name: "", first_name: "" });
  const [stakeholderForm, setStakeholderForm] = useState({
    position_id: "",
    organization: "",
    last_name: "",
    first_name: "",
  });
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setPositions(await api.get<Position[]>("/reference/positions"));
      const loadedEmployees = await api.get<Employee[]>(`/projects/${project.id}/employees`);
      setEmployees(loadedEmployees);
      const map: Record<string, string[]> = {};
      for (const employee of loadedEmployees) {
        const positionsOfEmployee = await api.get<Position[]>(
          `/projects/${project.id}/employees/${employee.id}/positions`,
        );
        map[employee.id] = positionsOfEmployee.map((p) => p.id);
      }
      setEmployeePositions(map);
      setStakeholders(await api.get<Stakeholder[]>(`/projects/${project.id}/stakeholders`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id, isStakeholders]);

  async function run(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  return (
    <>
      <h3>{isStakeholders ? "Стейкхолдеры" : "Сотрудники"}</h3>
      {error && <div className="error">{error}</div>}

      {isStakeholders ? (
        <>
          <table>
            <thead>
              <tr>
                <th>Имя</th>
                <th>Тип</th>
                <th>Организация</th>
                <th>Пользователь</th>
              </tr>
            </thead>
            <tbody>
              {stakeholders.map((stakeholder) => (
                <tr key={stakeholder.id}>
                  <td>
                    {[stakeholder.last_name, stakeholder.first_name].filter(Boolean).join(" ") ||
                      "Абстрактный"}
                  </td>
                  <td>
                    {positions.find((p) => p.id === stakeholder.position_id)?.name ?? "—"}
                  </td>
                  <td>{stakeholder.organization ?? "—"}</td>
                  <td>
                    {stakeholder.user_id ? (
                      <span className="badge">связан</span>
                    ) : (
                      <span className="badge">абстрактный</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="card" style={{ marginTop: 16 }}>
            <h3>Новый стейкхолдер</h3>
            <form
              className="row"
              onSubmit={(e) => {
                e.preventDefault();
                void run(() => api.post(`/projects/${project.id}/stakeholders`, stakeholderForm));
                setStakeholderForm({ position_id: "", organization: "", last_name: "", first_name: "" });
              }}
            >
              <select
                value={stakeholderForm.position_id}
                onChange={(e) =>
                  setStakeholderForm({ ...stakeholderForm, position_id: e.target.value })
                }
                required
              >
                <option value="">— тип (обязательно) —</option>
                {positions
                  .filter((p) => p.usable_as_stakeholder_type)
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
              </select>
              <input
                placeholder="Фамилия"
                value={stakeholderForm.last_name}
                onChange={(e) =>
                  setStakeholderForm({ ...stakeholderForm, last_name: e.target.value })
                }
              />
              <input
                placeholder="Имя"
                value={stakeholderForm.first_name}
                onChange={(e) =>
                  setStakeholderForm({ ...stakeholderForm, first_name: e.target.value })
                }
              />
              <input
                placeholder="Организация"
                value={stakeholderForm.organization}
                onChange={(e) =>
                  setStakeholderForm({ ...stakeholderForm, organization: e.target.value })
                }
              />
              <button className="primary">Создать</button>
            </form>
          </div>
        </>
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>Имя</th>
                <th>Должности</th>
                <th>Статус</th>
                <th>Добавить должность</th>
              </tr>
            </thead>
            <tbody>
              {employees.map((employee) => (
                <tr key={employee.id}>
                  <td>
                    {[employee.last_name, employee.first_name].filter(Boolean).join(" ") || "—"}
                  </td>
                  <td>
                    {(employeePositions[employee.id] ?? [])
                      .map((id) => positions.find((p) => p.id === id)?.name)
                      .filter(Boolean)
                      .join(", ") || "—"}
                  </td>
                  <td>
                    {employee.user_id ? (
                      <span className="badge">занята</span>
                    ) : (
                      <span className="badge">вакансия</span>
                    )}
                  </td>
                  <td>
                    <select
                      defaultValue=""
                      onChange={(e) => {
                        const value = e.target.value;
                        if (value)
                          void run(() =>
                            api.post(`/projects/${project.id}/employees/${employee.id}/positions`, {
                              position_id: value,
                            }),
                          );
                        e.target.value = "";
                      }}
                    >
                      <option value="">—</option>
                      {positions
                        .filter(
                          (p) =>
                            p.assignable_as_position &&
                            !(employeePositions[employee.id] ?? []).includes(p.id),
                        )
                        .map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name}
                          </option>
                        ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="card" style={{ marginTop: 16 }}>
            <h3>Новый сотрудник</h3>
            <form
              className="row"
              onSubmit={(e) => {
                e.preventDefault();
                void run(() => api.post(`/projects/${project.id}/employees`, employeeForm));
                setEmployeeForm({ user_id: "", last_name: "", first_name: "" });
              }}
            >
              <input
                placeholder="ID пользователя (для связи) или оставьте пустым"
                value={employeeForm.user_id}
                onChange={(e) => setEmployeeForm({ ...employeeForm, user_id: e.target.value })}
              />
              <input
                placeholder="Фамилия (для вакансии)"
                value={employeeForm.last_name}
                onChange={(e) => setEmployeeForm({ ...employeeForm, last_name: e.target.value })}
              />
              <input
                placeholder="Имя (для вакансии)"
                value={employeeForm.first_name}
                onChange={(e) => setEmployeeForm({ ...employeeForm, first_name: e.target.value })}
              />
              <button className="primary">Создать</button>
            </form>
          </div>
        </>
      )}
    </>
  );
}
