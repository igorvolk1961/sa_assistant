import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Member, RoleCode } from "../api/types";
import { useProject } from "./ProjectLayout";

const ROLES: RoleCode[] = ["admin", "system_analyst", "employee", "guest"];

export function MembersPage() {
  const project = useProject();
  const [members, setMembers] = useState<Member[]>([]);
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState<RoleCode>("employee");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setMembers(await api.get<Member[]>(`/projects/${project.id}/members`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id]);

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
      <h3>Участники проекта</h3>
      {error && <div className="error">{error}</div>}
      <table>
        <thead>
          <tr>
            <th>Пользователь (ID)</th>
            <th>Роли</th>
            <th>Владелец</th>
            <th>Изменить роль</th>
          </tr>
        </thead>
        <tbody>
          {members.map((member) => (
            <tr key={member.id}>
              <td className="muted">{member.user_id}</td>
              <td>{member.roles.join(", ")}</td>
              <td>{member.is_owner ? "да" : ""}</td>
              <td>
                {!member.is_owner && (
                  <select
                    value={member.roles[0] ?? ""}
                    onChange={(e) =>
                      run(() =>
                        api.put(`/projects/${project.id}/members/${member.id}/roles`, {
                          roles: [e.target.value],
                        }),
                      )
                    }
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Добавить участника</h3>
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            void run(() => api.post(`/projects/${project.id}/members`, { user_id: userId, role }));
            setUserId("");
          }}
        >
          <input
            placeholder="ID пользователя"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            required
          />
          <select value={role} onChange={(e) => setRole(e.target.value as RoleCode)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <button className="primary">Добавить</button>
        </form>
        <form
          className="row"
          style={{ marginTop: 8 }}
          onSubmit={(e) => {
            e.preventDefault();
            void run(() =>
              api.post(`/projects/${project.id}/analyst/transfer`, { user_id: userId }),
            );
          }}
        >
          <span className="muted">Передать роль аналитика пользователю:</span>
          <button>Передать аналитика</button>
        </form>
      </div>
    </>
  );
}
