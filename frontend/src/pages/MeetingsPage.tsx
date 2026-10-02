import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Meeting, Segment, Stakeholder } from "../api/types";
import { useProject } from "./ProjectLayout";

interface UnansweredQuestion {
  question_id: string;
  text: string;
  status: string;
}

export function MeetingsPage() {
  const project = useProject();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [segments, setSegments] = useState<Segment[]>([]);
  const [questions, setQuestions] = useState<UnansweredQuestion[]>([]);
  const [form, setForm] = useState({ title: "", stakeholder_id: "" });
  const [segmentText, setSegmentText] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setMeetings(await api.get<Meeting[]>(`/projects/${project.id}/meetings`));
      setStakeholders(await api.get<Stakeholder[]>(`/projects/${project.id}/stakeholders`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  async function loadMeeting(meetingId: string) {
    if (!meetingId) {
      setSegments([]);
      setQuestions([]);
      return;
    }
    setSegments(await api.get<Segment[]>(`/projects/${project.id}/meetings/${meetingId}/segments`));
    setQuestions(
      await api.get<UnansweredQuestion[]>(
        `/projects/${project.id}/meetings/${meetingId}/unanswered-questions`,
      ),
    );
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id]);

  useEffect(() => {
    void loadMeeting(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  async function run(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
      await load();
      await loadMeeting(selectedId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }

  return (
    <>
      <h3>Встречи</h3>
      {error && <div className="error">{error}</div>}
      <table>
        <thead>
          <tr>
            <th>Название</th>
            <th>Статус</th>
            <th>Действие</th>
          </tr>
        </thead>
        <tbody>
          {meetings.map((meeting) => (
            <tr key={meeting.id}>
              <td>
                <button className="tab" onClick={() => setSelectedId(meeting.id)}>
                  {meeting.title ?? meeting.id.slice(0, 8)}
                </button>
              </td>
              <td>
                <span className="badge">{meeting.status}</span>
              </td>
              <td>
                {meeting.status === "planned" && (
                  <button
                    onClick={() =>
                      run(() =>
                        api.patch(`/projects/${project.id}/meetings/${meeting.id}`, {
                          status: "in_progress",
                        }),
                      )
                    }
                  >
                    Начать
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>Новая встреча</h3>
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            void run(() => api.post(`/projects/${project.id}/meetings`, form));
            setForm({ title: "", stakeholder_id: "" });
          }}
        >
          <input
            placeholder="Название"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
          <select
            value={form.stakeholder_id}
            onChange={(e) => setForm({ ...form, stakeholder_id: e.target.value })}
          >
            <option value="">— стейкхолдер —</option>
            {stakeholders.map((s) => (
              <option key={s.id} value={s.id}>
                {[s.last_name, s.first_name].filter(Boolean).join(" ") || "Абстрактный"}
              </option>
            ))}
          </select>
          <button className="primary">Создать</button>
        </form>
      </div>

      {selectedId && (
        <>
          <div className="card">
            <h3>Обязательные вопросы (не заданные)</h3>
            <ul>
              {questions.map((q) => (
                <li key={q.question_id}>
                  {q.text} <span className="badge">{q.status}</span>
                </li>
              ))}
              {questions.length === 0 && <li className="muted">Все обязательные вопросы заданы.</li>}
            </ul>
          </div>

          <div className="card">
            <h3>Журнал беседы</h3>
            <ul>
              {segments.map((segment) => (
                <li key={segment.id}>
                  {segment.speaker_label && <span className="badge">{segment.speaker_label}</span>}{" "}
                  {segment.text} <span className="muted">({segment.source})</span>
                </li>
              ))}
              {segments.length === 0 && <li className="muted">Журнал пуст.</li>}
            </ul>
            <form
              className="row"
              onSubmit={(e) => {
                e.preventDefault();
                if (!segmentText) return;
                void run(() =>
                  api.post(`/projects/${project.id}/meetings/${selectedId}/segments`, {
                    text: segmentText,
                  }),
                );
                setSegmentText("");
              }}
            >
              <input
                placeholder="Реплика / вопрос-ответ"
                value={segmentText}
                onChange={(e) => setSegmentText(e.target.value)}
              />
              <button>Добавить</button>
            </form>
            <form
              className="row"
              style={{ marginTop: 8 }}
              onSubmit={(e) => {
                e.preventDefault();
                const input = e.currentTarget.elements.namedItem("file") as HTMLInputElement;
                const file = input.files?.[0];
                if (!file) return;
                const data = new FormData();
                data.append("kind", "transcript");
                data.append("source", "external");
                data.append("file", file);
                void run(() =>
                  api.upload(`/projects/${project.id}/meetings/${selectedId}/files`, data),
                );
                input.value = "";
              }}
            >
              <span className="muted">Импорт внешнего транскрипта (telemost/ПО курсов):</span>
              <input type="file" name="file" />
              <button>Загрузить</button>
            </form>
          </div>
        </>
      )}
    </>
  );
}
