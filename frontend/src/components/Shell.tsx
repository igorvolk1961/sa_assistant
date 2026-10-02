import { useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";

export function Shell({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  return (
    <>
      <div className="topbar">
        <button onClick={() => navigate(-1)} title="Вернуться на предыдущую карточку">
          ← Назад
        </button>
        <strong>Помощник СА</strong>
        <div className="spacer" />
        <span className="muted">
          {user?.last_name} {user?.first_name}
          {user?.is_service_owner ? " · владелец сервиса" : ""}
        </span>
        <button
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          Выйти
        </button>
      </div>
      <div className="layout">{children}</div>
    </>
  );
}
