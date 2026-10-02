import { useState } from "react";
import type { FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: { pathname?: string } } };
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({
    login: "",
    password: "",
    last_name: "",
    first_name: "",
    middle_name: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "login") {
        await login(form.login, form.password);
      } else {
        await register({
          login: form.login,
          password: form.password,
          last_name: form.last_name,
          first_name: form.first_name,
          middle_name: form.middle_name || undefined,
        });
      }
      navigate(location.state?.from?.pathname ?? "/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="layout" style={{ maxWidth: 420, marginTop: 80 }}>
      <div className="card">
        <h2>Помощник системного аналитика</h2>
        <div className="tabs">
          <button
            className={`tab ${mode === "login" ? "active" : ""}`}
            onClick={() => setMode("login")}
          >
            Вход
          </button>
          <button
            className={`tab ${mode === "register" ? "active" : ""}`}
            onClick={() => setMode("register")}
          >
            Регистрация
          </button>
        </div>
        <form onSubmit={submit} className="row" style={{ flexDirection: "column", alignItems: "stretch" }}>
          <input
            placeholder="Логин"
            value={form.login}
            onChange={(e) => setForm({ ...form, login: e.target.value })}
            required
          />
          <input
            type="password"
            placeholder="Пароль (мин. 8 символов)"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
          {mode === "register" && (
            <>
              <input
                placeholder="Фамилия"
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                required
              />
              <input
                placeholder="Имя"
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                required
              />
              <input
                placeholder="Отчество"
                value={form.middle_name}
                onChange={(e) => setForm({ ...form, middle_name: e.target.value })}
              />
            </>
          )}
          {error && <div className="error">{error}</div>}
          <button className="primary" disabled={busy}>
            {mode === "login" ? "Войти" : "Зарегистрироваться"}
          </button>
        </form>
      </div>
    </div>
  );
}
