# План реализации: «Помощник системного аналитика» (sa_assistant)

## 1. Цель и контекст

Продакшн-реди приложение для сопровождения системного аналитика: учёт проектов и персоний, ведение встреч с аудиозаписью и транскрибацией (live + batch, с диаризацией), LLM-анализ бесед, артефакты (View/Glossary/Use Case/User Story), постановка задач сбора информации сотрудникам (с DAG-зависимостями), формирование требований (BR/FR/NFR) и диаграмм C4/BPMN.

Контекст: учебный курс по системному анализу с ролевыми играми. Роли воспроизводят саму игру: администратор, системный аналитик, сотрудник, гость (наблюдатель). В перспективе — основа общего командного проекта.

## 2. Утверждённые решения

### 2.1 Стек
- Backend: Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2.
- БД: PostgreSQL. Realtime/кеш/сессии STT: Redis.
- Фон: Celery или ARQ (выбрать ARQ, если не нужны сложные цепочки; Celery — если понадобятся периодические ретраи/beat).
- Realtime: WebSocket (транскрибация, уведомления, статусы задач).
- Хранилище файлов: S3-совместимое (MinIO on-prem / Yandex Object Storage), presigned URLs.
- Frontend: React + TypeScript (Vite), MediaRecorder для записи, bpmn-js для BPMN, рендер Structurizr DSL для C4.
- Аудио-обработка: ffmpeg (конвертация/нарезка).
- Провайдеры: абстракции `STTProvider` и `LLMProvider`; по умолчанию STT — Yandex SpeechKit, LLM — настраиваемый.

### 2.2 Роли и доступ (per-project)
- Роль задаётся **в рамках проекта** через участие (`project_memberships` + `membership_roles`).
- Роли: `admin`, `system_analyst`, `employee`, `guest` (глобальный справочник).
- У пользователя одна роль в проекте, **кроме пары `admin + system_analyst`** (разрешена).
- Аналитик в проекте **ровно один**; admin может передать роль аналитика.
- Админов может быть несколько. **Владелец** (`is_owner`) — неизменяем; снять с роли admin нельзя.
- Гость не имеет участия и видит **все проекты со статусом `open`**, может комментировать везде; admin может удалять комментарии (soft-delete).
- Доступ к `closed`/`archived` (архив) — у **любого admin** проекта.
- Администратор только: назначает роли, редактирует глобальные справочники, настраивает проект. Действия аналитика доступны лишь при наличии роли `system_analyst`.
- Регистрация: логин/пароль + обязательные ФИО (фамилия, имя, отчество). Новый пользователь — гость по умолчанию.

### 2.3 Должности и типы стейкхолдеров
- Каталог должностей **глобальный** и совпадает с каталогом типов стейкхолдеров.
- Назначение должности пользователю — **в рамках проекта** (`membership_positions`).
- Сотрудник/аналитик может иметь несколько должностей; аналитик может ставить задачи сам себе.

### 2.4 Задачи сбора информации
- Задача может быть **без исполнителя**; список таких задач — ключевой экран аналитика.
- Исполнителя можно переназначать; хранится история назначений.
- Результат сдаётся текстом и/или вложением; версии результата сохраняются.
- Отклонение аналитиком → возврат на доработку с обязательным комментарием.
- Зависимости задач — DAG; задачи без выполненных предков недоступны к работе; распараллеливание определяется DAG.

### 2.5 Справочники
Все глобальные, правит администратор: роли; должности/типы стейкхолдеров; обязательные вопросы по типу; типовые NFR; модели STT (с признаками streaming/diarization и лимитом сессии); модели LLM; шаблоны промптов.

### 2.6 Анализ «на лету»
Только подсказка следующего вопроса. Гибрид: детерминированные кандидаты = незаданные обязательные вопросы для типа стейкхолдера + накопленный транскрипт; LLM выбирает/переформулирует. Вызов LLM троттлится (по паузе речи/кнопке/интервалу), не на каждый сегмент.

## 3. Архитектура

Модульный монолит (не микросервисы) с чётким разделением модулей и очередью фоновых задач.

```
React SPA ── REST/WS ──> FastAPI
                         ├─ auth / RBAC (per-project)
                         ├─ admin (справочники)
                         ├─ projects / memberships / positions
                         ├─ persons / stakeholders / meetings
                         ├─ stt orchestrator  ──> провайдеры STT
                         ├─ llm orchestrator  ──> провайдеры LLM
                         ├─ artifacts / requirements / diagrams
                         └─ tasks (DAG) / notifications / comments
         PostgreSQL   Redis (pub-sub, сессии STT)   S3/MinIO   ARQ/Celery worker
```

Режимы одного STT-сервиса: `live` (без стабильной диаризации, сессия ограничена — чанкование и ротация) и `batch` (диаризация, перезапись live-текста). Формат хранения: см. §4.

## 4. Модель данных

Схема согласована. Основные группы таблиц и обязательные ограничения.

### 4.1 Глобальные справочники
`users` (логин, password_hash, ФИО, is_active), `roles`, `positions` (флаги `assignable_as_position`, `usable_as_stakeholder_type`), `mandatory_questions`, `nfr_types`, `llm_models`, `stt_models` (streaming/diarization/session_limit_sec), `prompt_templates`, `provider_credentials` (секреты шифровать, например Fernet).

### 4.2 Проекты, участие, должности
`projects` (status: open/closed/archived), `project_memberships` (is_owner), `membership_roles`, `membership_positions`, `project_stakeholders`, `persons` (внешние стейкхолдеры, опционально `user_id`).

### 4.3 Встречи и транскрибация
`meetings`, `meeting_participants`, `audio_recordings` (storage_key), `transcription_jobs` (mode live/batch/hybrid, session_limit_sec, external_job_id), `transcript_segments` (speaker_label, source), `segment_question_links`, `meeting_question_coverage`.

### 4.4 Артефакты и требования
`analysis_runs`, `artifacts` (view/glossary/use_case/user_story/constraint/risk, content jsonb, version), `requirements` (business/functional/nonfunctional, nfr_type_id), `diagrams` (c4_context/c4_container/c4_component/bpmn, format, content, version).

### 4.5 Задачи и взаимодействие
`info_tasks` (status: unassigned/assigned/in_progress/on_review/accepted/rejected/cancelled), `task_dependencies`, `task_assignments` (assigned_at/unassigned_at), `task_result_versions` (review_status, review_comment), `task_attachments`, `comments` (полиморфная привязка entity_type/entity_id, author_role_snapshot, soft-delete), `notifications`, `audit_log`.

### 4.6 Обязательные инварианты в БД
- `UNIQUE(project_id) WHERE role_code='system_analyst'` — ровно один аналитик на проект.
- Триггер на `membership_roles`: не более одной роли, кроме набора `{admin, system_analyst}`.
- Триггер: владельца (`is_owner=true`) нельзя снять с роли admin и удалить его membership.
- `task_assignments` может отсутствовать (задача без исполнителя).
- `CHECK`: при `review_status='rejected'` поле `review_comment` не пустое.
- Триггер на `task_dependencies`: запрет циклов (плюс топосортировка в сервисе).
- Политика доступа: `open`-проекты видят все; `closed/archived` — только admin проекта.
- Все ключевые изменения (роли, должности, приемка/отклонение, удаление комментариев) — в `audit_log`.

Полный DDL приведён в Приложении A.

## 5. Этапы и задачи (ordered)

### M0. Каркас и инфраструктура
1. Структура репозитория: `backend/` (FastAPI), `frontend/` (React+TS), `deploy/` (docker-compose: postgres, redis, minio, app, worker), `plans/`.
2. Docker Compose для локального старта; `.env.example`; конфиг через pydantic-settings; секреты не в репозитории.
3. FastAPI app factory, healthcheck `/health`, OpenAPI, базовое логирование, OpenTelemetry (по желанию).
4. Alembic init; async-движок SQLAlchemy; базовые модели.
5. CI: lint (ruff), typecheck (mypy), pytest; frontend lint+typecheck.
   - Приёмка: `docker compose up` поднимает пустой API + PostgreSQL + Redis + MinIO; тесты и линтеры проходят.

### M1. Аутентификация, пользователи, гости
1. `POST /auth/register` (логин, пароль, ФИО), `POST /auth/login`, `POST /auth/refresh`; хеш пароля (argon2/bcrypt).
2. Новый пользователь — гость. Резолвинг доступа: нет membership → роль `guest`.
3. Политика видимости проектов: `open` — всем; `closed/archived` — admin проекта.
4. `GET /me`, `PATCH /me`.
   - Приёмка: регистрация/логин; гость видит список `open`-проектов и не видит архив.

### M2. Глобальные справочники (admin)
1. CRUD: `positions`, `mandatory_questions` (по position), `nfr_types`, `llm_models`, `stt_models`, `prompt_templates`.
2. Импорт/сид справочников; флаги `assignable_as_position` / `usable_as_stakeholder_type`.
3. Шифрование `provider_credentials`; API для сохранения ключей; подсказка по получению ключа Yandex SpeechKit (текст в UI).
   - Приёмка: только admin редактирует; роли/гость получают 403 на запись.

### M3. Проекты, участие, должности, персоны
1. `POST /projects` (создатель → admin + is_owner), `POST /projects/{id}/close` (+ архивный доступ для admin).
2. Управление участниками: `POST /projects/{id}/members`; назначение/смена роли (`PATCH .../roles`); защита владельца.
3. Передача роли аналитика (атомарно: снять у прежнего, назначить новому), уникальность.
4. Назначение должностей в проекте (`membership_positions`); самоназначение аналитиком допустимо.
5. `persons` и `project_stakeholders` (тип = position).
6. При понижении до гостя: незакрытые задачи → `unassigned` (транзакционно).
   - Приёмка: ровно один аналитик; владельца нельзя разжаловать; одна роль на проект кроме admin+SA.

### M4. Встречи и ручной журнал
1. CRUD встреч, участников; статусы planned/in_progress/completed/cancelled.
2. Ручной ввод вопросов/ответов → `transcript_segments` (source=manual).
3. Coverage обязательных вопросов (`meeting_question_coverage`), связь сегмент↔вопрос.
4. Экран «незаданные обязательные вопросы».
   - Приёмка: журнал собирается вручную, coverage считается корректно.

### M5. Аудио и batch-транскрибация с диаризацией
1. Presigned upload в S3/MinIO; `audio_recordings`; ffmpeg-нормализация.
2. Очередь `transcription_jobs`; адаптер Yandex batch STT с `speakerLabeling`.
3. Запись результата в `transcript_segments` (source=asr_batch, speaker_label); замена live-текста при наличии.
4. Выбор STT-модели; состояние job, ретраи, ошибки.
   - Приёмка: загруженный файл транскрибируется с разделением спикеров; результат редактируем.

### M6. Live-транскрибация и подсказка вопроса
1. WebSocket `/meetings/{id}/transcribe`: приём аудиочанков, буферизация в Redis.
2. Менеджер сессий STT: чанкование, ротация по `session_limit_sec`, склейка с перекрытием, стабильность текста.
3. Live-подсказка следующего вопроса: кандидаты = незаданные обязательные + контекст → LLM (троттлинг, стриминг ответа).
4. UI: live-журнал, индикатор оставшихся обязательных вопросов, кнопка «подсказать».
   - Приёмка: встреча > лимита сессии не обрывается; подсказка учитывает незаданные вопросы; LLM не вызывается на каждый сегмент.

### M7. LLM-анализ и артефакты
1. Абстракция `LLMProvider` + адаптеры (YandexGPT, GigaChat, OpenAI-совместимые); выбор модели в запросе/настройках.
2. Первичный анализ встречи: View, Ограничения и риски, Glossary, Use Case, User Stories → `artifacts` (jsonb, версии); ручное редактирование.
3. Ручной режим: сформировать промпт для внешнего ИИ-чата и принять вставленный ответ (`analysis_runs`/`artifacts`, source=manual).
4. Авто-формирование последовательности задач сбора информации (DAG + распараллеливание) через LLM; возможность правки.
5. Генерация промптов для поисковых запросов в интернете.
   - Приёмка: анализ создаёт артефакты; промпт можно скопировать и вернуть результат вручную; задачи формируются и редактируются.

### M8. Задачи сбора, результаты, уведомления
1. CRUD `info_tasks`; зависимости-DAG; запрет циклов; сортировка/приоритеты.
2. Экран аналитика «задачи без исполнителя»; назначение/переназначение (история).
3. Сдача результата (текст и/или файлы) → `task_result_versions` + `task_attachments`.
4. Приёмка/отклонение с обязательным комментарием; возврат в работу; версионирование результатов.
5. Передача результата другим сотрудникам с учётом последовательности (DAG).
6. Уведомления (WS + `notifications`): исполнителю о назначении, аналитику о сдаче; просмотр результата из окна оповещения.
7. Гости: комментарии к задачам и прочим сущностям; admin soft-delete.
   - Приёмка: полный цикл задача→сдача→(возврат)→приёмка; уведомления доходят; история сохраняется.

### M9. Требования и диаграммы
1. Ручное и автоматическое формирование BR/FR/NFR; подсказка типовых NFR из `nfr_types`; генерация через API LLM или промпт для ИИ-чата.
2. C4: LLM → Structurizr DSL → рендер (Context/Container/Component); версии.
3. BPMN: LLM → BPMN-XML → bpmn-js; версии.
4. Экспорт диаграмм (SVG/PNG/XML/DSL).
   - Приёмка: диаграммы рендерятся и сохраняются; требования создаются в обоих режимах.

### M10. Production hardening
1. Audit log покрывает все критичные операции; RLS/политики для архивов и гостей.
2. Rate-limit и circuit breaker для внешних STT/LLM; таймауты, ретраи, бюджеты.
3. ПДн/152-ФЗ: согласие на запись, сроки хранения, шифрование, on-prem провайдеры.
4. Мониторинг (метрики, трейсы), алерты; бэкапы БД и S3.
5. Нагрузочное тестирование WebSocket-транскрибации; тесты DAG.

## 6. Ключевые риски и failure modes

| Риск | Митигация |
|---|---|
| Диаризация недоступна в streaming | Live без спикеров; batch с диаризацией и заменой текста |
| Лимит длины live-сессии STT | Менеджер сессий: чанки/ротация/склейка, состояние в Redis |
| Стоимость/задержка LLM при live | Троттлинг, кандидаты детерминированы, LLM только выбирает/формулирует |
| Обрыв WebSocket/сети при встрече | Буферизация аудио на клиенте, дозагрузка, idempotent сегменты |
| Цикл в DAG задач | Триггер + топосортировка; запрет сохранения |
| Утечка ПДн/ключей | Шифрование секретов, RBAC per-project, audit, сроки хранения |
| Гонка при передаче роли аналитика | Транзакция + частичный уникальный индекс |
| Потеря истории при возврате задачи | Версионирование результата, soft-delete комментариев |

## 7. План проверки

- Unit: инварианты ролей, владелец, DAG, coverage, статусная машина задач.
- Integration (testcontainers: PostgreSQL, Redis, MinIO): auth, RBAC per-project, STT/LLM адаптеры с моками.
- Contract: OpenAPI-схемы + типы frontend.
- E2E (Playwright): регистрация→роль→проект→встреча→задача→сдача→приёмка→артефакты.
- Load: многочасовая live-транскрибация с ротацией сессий.
- Security: проверка доступа гостя/архива, отсутствие секретов в логах.

## 8. Вне scope

- Мобильные приложения.
- Видеоконференц-платформа (интеграция с внешними ВКС — позже).
- Федеративная аутентификация (SSO/OIDC) — при необходимости отдельным этапом.
- Fine-tuning моделей.

## 9. Открытые вопросы

1. **Способ фоновых задач:** ARQ или Celery (влияет на структуру worker и ретраи).
2. **Закрытый проект:** виден только admin или всем участникам read-only как архив (уточнить перед M3).
3. **Внешние ВКС:** запись берётся из браузера или из конференц-системы.
4. **Хостинг и ПДн:** российское облако/on-prem и требования к хранению аудио (сроки).

## Приложение A. DDL (согласованная схема)

```sql
-- ===================== ГЛОБАЛЬНЫЕ СПРАВОЧНИКИ =====================
CREATE TYPE role_code AS ENUM ('admin','system_analyst','employee','guest');

CREATE TABLE users (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  login         text NOT NULL UNIQUE,
  password_hash text NOT NULL,
  last_name     text NOT NULL,
  first_name    text NOT NULL,
  middle_name   text,
  is_active     boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE roles (code role_code PRIMARY KEY, name text NOT NULL);

CREATE TABLE positions (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code          text NOT NULL UNIQUE,
  name          text NOT NULL,
  assignable_as_position boolean NOT NULL DEFAULT true,
  usable_as_stakeholder_type boolean NOT NULL DEFAULT true,
  is_system     boolean NOT NULL DEFAULT false
);

CREATE TABLE mandatory_questions (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  position_id  uuid NOT NULL REFERENCES positions(id),
  text         text NOT NULL,
  is_mandatory boolean NOT NULL DEFAULT true,
  sort_order   int  NOT NULL DEFAULT 0,
  is_active    boolean NOT NULL DEFAULT true
);

CREATE TABLE nfr_types       (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), code text UNIQUE, name text, description text);
CREATE TABLE llm_models      (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider text, model_code text, display_name text, is_default boolean DEFAULT false, params jsonb);
CREATE TABLE stt_models      (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider text, model_code text, display_name text,
                              is_default boolean DEFAULT false,
                              supports_streaming boolean, supports_diarization boolean,
                              session_limit_sec int);
CREATE TABLE prompt_templates(id uuid PRIMARY KEY DEFAULT gen_random_uuid(), purpose text, name text, template text, is_system boolean DEFAULT false);
CREATE TABLE provider_credentials (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider text, scope text,
                              encrypted_secret bytea, created_at timestamptz DEFAULT now());

-- ===================== ПЕРСОНАЛИИ =====================
CREATE TABLE persons (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  last_name   text NOT NULL,
  first_name  text NOT NULL,
  middle_name text,
  user_id     uuid UNIQUE REFERENCES users(id),
  organization text,
  email       text,
  phone       text
);

-- ===================== ПРОЕКТЫ И УЧАСТИЕ =====================
CREATE TYPE project_status AS ENUM ('open','closed','archived');

CREATE TABLE projects (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code        text UNIQUE,
  name        text NOT NULL,
  description text,
  status      project_status NOT NULL DEFAULT 'open',
  created_by  uuid REFERENCES users(id),
  created_at  timestamptz NOT NULL DEFAULT now(),
  closed_at   timestamptz
);

CREATE TABLE project_memberships (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id    uuid NOT NULL REFERENCES users(id),
  is_owner   boolean NOT NULL DEFAULT false,
  joined_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, user_id),
  UNIQUE (id, project_id)
);

CREATE TABLE membership_roles (
  membership_id uuid NOT NULL,
  role_code     role_code NOT NULL,
  project_id    uuid NOT NULL,
  PRIMARY KEY (membership_id, role_code),
  FOREIGN KEY (membership_id, project_id)
      REFERENCES project_memberships(id, project_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX uq_one_analyst_per_project
  ON membership_roles (project_id) WHERE role_code = 'system_analyst';

CREATE TABLE membership_positions (
  membership_id uuid NOT NULL REFERENCES project_memberships(id) ON DELETE CASCADE,
  position_id   uuid NOT NULL REFERENCES positions(id),
  assigned_by   uuid REFERENCES users(id),
  assigned_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (membership_id, position_id)
);

CREATE TABLE project_stakeholders (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id  uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  person_id   uuid NOT NULL REFERENCES persons(id),
  position_id uuid REFERENCES positions(id),
  notes       text,
  UNIQUE (project_id, person_id, position_id)
);

-- ===================== ВСТРЕЧИ, АУДИО, ТРАНСКРИБАЦИЯ =====================
CREATE TYPE meeting_status AS ENUM ('planned','in_progress','completed','cancelled');

CREATE TABLE meetings (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id            uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title                 text,
  stakeholder_person_id uuid REFERENCES persons(id),
  status                meeting_status NOT NULL DEFAULT 'planned',
  scheduled_at          timestamptz,
  started_at            timestamptz,
  ended_at              timestamptz,
  created_by            uuid REFERENCES users(id)
);

CREATE TABLE meeting_participants (
  meeting_id   uuid NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  person_id    uuid NOT NULL REFERENCES persons(id),
  meeting_role text,
  PRIMARY KEY (meeting_id, person_id)
);

CREATE TABLE audio_recordings (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  meeting_id uuid NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  storage_key text NOT NULL,
  mime_type  text,
  duration_sec int,
  size_bytes bigint,
  checksum   text,
  created_at timestamptz DEFAULT now()
);

CREATE TYPE job_status AS ENUM ('queued','running','done','failed');
CREATE TYPE transcribe_mode AS ENUM ('live','batch','hybrid');

CREATE TABLE transcription_jobs (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recording_id    uuid REFERENCES audio_recordings(id) ON DELETE CASCADE,
  stt_model_id    uuid REFERENCES stt_models(id),
  mode            transcribe_mode NOT NULL,
  status          job_status NOT NULL DEFAULT 'queued',
  language        text DEFAULT 'ru-RU',
  session_limit_sec int,
  external_job_id text,
  started_at      timestamptz,
  finished_at     timestamptz,
  error           text
);

CREATE TYPE segment_source AS ENUM ('manual','asr_live','asr_batch','asr_edited');

CREATE TABLE transcript_segments (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  meeting_id    uuid NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  recording_id  uuid REFERENCES audio_recordings(id),
  start_ms      int,
  end_ms        int,
  speaker_label text,
  text          text NOT NULL,
  source        segment_source NOT NULL DEFAULT 'manual',
  confidence    numeric(4,3),
  created_by    uuid REFERENCES users(id),
  created_at    timestamptz DEFAULT now()
);

CREATE TABLE segment_question_links (
  segment_id  uuid NOT NULL REFERENCES transcript_segments(id) ON DELETE CASCADE,
  question_id uuid NOT NULL REFERENCES mandatory_questions(id),
  PRIMARY KEY (segment_id, question_id)
);

CREATE TABLE meeting_question_coverage (
  meeting_id  uuid NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  question_id uuid NOT NULL REFERENCES mandatory_questions(id),
  status      text NOT NULL DEFAULT 'unanswered'
              CHECK (status IN ('unanswered','asked','answered')),
  segment_id  uuid REFERENCES transcript_segments(id),
  PRIMARY KEY (meeting_id, question_id)
);

-- ===================== АРТЕФАКТЫ АНАЛИЗА =====================
CREATE TABLE analysis_runs (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  meeting_id   uuid REFERENCES meetings(id),
  llm_model_id uuid REFERENCES llm_models(id),
  kind         text,
  status       job_status NOT NULL DEFAULT 'queued',
  prompt       text,
  response     jsonb,
  created_by   uuid REFERENCES users(id),
  created_at   timestamptz DEFAULT now()
);

CREATE TYPE artifact_type AS ENUM ('view','glossary','use_case','user_story','constraint','risk');
CREATE TABLE artifacts (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  meeting_id uuid REFERENCES meetings(id),
  type       artifact_type NOT NULL,
  content    jsonb NOT NULL,
  source     text NOT NULL DEFAULT 'auto' CHECK (source IN ('auto','manual')),
  version    int NOT NULL DEFAULT 1,
  created_by uuid REFERENCES users(id),
  created_at timestamptz DEFAULT now()
);

CREATE TYPE requirement_type AS ENUM ('business','functional','nonfunctional');
CREATE TABLE requirements (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id  uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  type        requirement_type NOT NULL,
  title       text NOT NULL,
  description text,
  nfr_type_id uuid REFERENCES nfr_types(id),
  priority    int,
  status      text DEFAULT 'draft',
  source      text,
  created_by  uuid REFERENCES users(id),
  created_at  timestamptz DEFAULT now()
);

CREATE TYPE diagram_type AS ENUM ('c4_context','c4_container','c4_component','bpmn');
CREATE TABLE diagrams (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id      uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  type            diagram_type NOT NULL,
  name            text,
  format          text DEFAULT 'dsl',
  content         text,
  version         int DEFAULT 1,
  generated_by_llm boolean DEFAULT true,
  created_by      uuid REFERENCES users(id),
  created_at      timestamptz DEFAULT now()
);

-- ===================== ЗАДАЧИ СБОРА ИНФОРМАЦИИ =====================
CREATE TYPE task_status AS ENUM ('unassigned','assigned','in_progress','on_review','accepted','rejected','cancelled');

CREATE TABLE info_tasks (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id  uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title       text NOT NULL,
  description text,
  prompt      text,
  status      task_status NOT NULL DEFAULT 'unassigned',
  due_at      timestamptz,
  sort_order  int DEFAULT 0,
  created_by  uuid REFERENCES users(id),
  created_at  timestamptz DEFAULT now()
);

CREATE TABLE task_dependencies (
  task_id            uuid NOT NULL REFERENCES info_tasks(id) ON DELETE CASCADE,
  depends_on_task_id uuid NOT NULL REFERENCES info_tasks(id) ON DELETE CASCADE,
  PRIMARY KEY (task_id, depends_on_task_id),
  CHECK (task_id <> depends_on_task_id)
);

CREATE TABLE task_assignments (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id       uuid NOT NULL REFERENCES info_tasks(id) ON DELETE CASCADE,
  membership_id uuid NOT NULL REFERENCES project_memberships(id),
  assigned_by   uuid REFERENCES users(id),
  assigned_at   timestamptz NOT NULL DEFAULT now(),
  unassigned_at timestamptz
);

CREATE TABLE task_result_versions (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id        uuid NOT NULL REFERENCES info_tasks(id) ON DELETE CASCADE,
  version_no     int NOT NULL,
  result_text    text,
  submitted_by   uuid REFERENCES users(id),
  submitted_at   timestamptz DEFAULT now(),
  review_status  text CHECK (review_status IN ('pending','accepted','rejected')),
  review_comment text,
  UNIQUE (task_id, version_no)
);

CREATE TABLE task_attachments (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  result_version_id uuid NOT NULL REFERENCES task_result_versions(id) ON DELETE CASCADE,
  storage_key       text NOT NULL,
  filename          text,
  mime_type         text,
  size_bytes        bigint,
  uploaded_by       uuid REFERENCES users(id),
  uploaded_at       timestamptz DEFAULT now()
);

-- ===================== КОММЕНТАРИИ, УВЕДОМЛЕНИЯ, АУДИТ =====================
CREATE TABLE comments (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id           uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  entity_type          text NOT NULL,
  entity_id            uuid NOT NULL,
  author_user_id       uuid REFERENCES users(id),
  author_role_snapshot role_code,
  body                 text NOT NULL,
  created_at           timestamptz DEFAULT now(),
  deleted_at           timestamptz,
  deleted_by           uuid REFERENCES users(id)
);
CREATE INDEX ix_comments_entity ON comments (entity_type, entity_id);

CREATE TABLE notifications (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES users(id),
  type       text NOT NULL,
  payload    jsonb,
  is_read    boolean DEFAULT false,
  created_at timestamptz DEFAULT now()
);

CREATE TABLE audit_log (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id uuid REFERENCES users(id),
  project_id    uuid REFERENCES projects(id),
  action        text NOT NULL,
  entity_type   text,
  entity_id     uuid,
  before        jsonb,
  after         jsonb,
  created_at    timestamptz DEFAULT now()
);
```
