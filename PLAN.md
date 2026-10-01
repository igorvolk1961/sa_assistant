# План реализации: «Помощник системного аналитика» (sa_assistant) — v2

> v2 учитывает ответы на открытые вопросы (фон — Procrastinate, хостинг — Beget.ru, источники записи — telemost.yandex и ПО онлайн-курсов, архив — только admin) и 30 новых требований (карточки сущностей, требования↔стейкхолдер↔задачи, подзадачи, файлы и комментарии).

## 1. Цель и контекст

Продакшн-реди приложение для сопровождения системного аналитика: учёт проектов, сотрудников и стейкхолдеров, встречи с аудиозаписью и транскрибацией (live + batch, с диаризацией), LLM-анализ бесед, артефакты, требования (BR/FR/NFR), задачи и подзадачи с файлами и комментариями, диаграммы C4/BPMN.

Контекст: учебный курс по системному анализу с ролевыми играми. Роли воспроизводят саму игру: администратор, системный аналитик, сотрудник, гость (наблюдатель). В перспективе — основа общего командного проекта.

## 2. Утверждённые решения

### 2.1 Стек
- Backend: Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2.
- БД: PostgreSQL. Realtime/кеш/сессии STT: Redis (pub/sub, буферы live-сессий). **Очередь фоновых задач: Procrastinate** (PostgreSQL-based, asyncio; отдельный брокер не нужен).
- Realtime: WebSocket (транскрибация, уведомления, статусы задач).
- Хранилище файлов: S3-совместимое. **Хостинг: Beget.ru с Docker**; PostgreSQL и S3-совместимое хранилище разворачиваются внутри Docker.
- Frontend: React + TypeScript (Vite), MediaRecorder, bpmn-js, рендер Structurizr DSL.
- Аудио: ffmpeg.
- Провайдеры: абстракции `STTProvider`/`LLMProvider`; STT по умолчанию — Yandex SpeechKit, LLM — настраиваемый.

### 2.2 Роли и доступ (per-project)
- Роль задаётся **в рамках проекта** (`project_memberships` + `membership_roles`); роли: `admin`, `system_analyst`, `employee`, `guest`.
- Одна роль в проекте, кроме пары `admin + system_analyst`.
- Аналитик в проекте ровно один; admin может передать роль.
- Админов может быть несколько; **владелец** (`is_owner`) неизменяем.
- Гость не имеет участия и видит **все `open`-проекты**; комментирует везде (в т.ч. задачи); admin удаляет комментарии (soft-delete).
- **Доступ к `closed`/`archived` — только у admin** (не у участников).
- Администратор только: назначает роли, правит глобальные справочники, настраивает проект. Действия аналитика — только при роли `system_analyst`.
- Регистрация: логин/пароль + обязательные ФИО. Новый пользователь — гость.

### 2.3 Сотрудники и стейкхолдеры (новая модель акторов)
- В проекте существуют две самостоятельные карточки актора, обе могут быть связаны с пользователем системы:
  - **Сотрудник** (`employees`): исполнитель задач. Связь с пользователем опциональна. **Пользователю в рамках одного проекта соответствует ровно один сотрудник с теми же ФИО**; один сотрудник может совмещать несколько должностей. Задачи назначаются на сотрудника, а не на должность.
  - **Стейкхолдер** (`stakeholders`): тип (должность) **обязателен**; связь с пользователем опциональна.
- **Вакантная должность**: сотрудник без привязанного пользователя (`user_id IS NULL`). При удалении связи «пользователь↔сотрудник» задачи остаются за сотрудником, но **без исполнителя**.
- **Абстрактный стейкхолдер**: стейкхолдер без пользователя (`user_id IS NULL`). Удаление связи «пользователь↔стейкхолдер» возвращает его в абстрактное состояние.
- Сотрудник может иметь **несколько должностей** (`employee_positions`).
- Назначение должности/статуса стейкхолдера пользователю выполняется **в рамках текущего проекта** и создаёт соответствующего сотрудника и/или стейкхолдера.
- При создании пользователя его можно сразу связать с ранее созданным сотрудником или стейкхолдером.
- Карточка сотрудника: общий список его задач и подзадач со статусом и признаком «задача/подзадача» (`parent_task_id IS NULL` vs не NULL); создание новой назначенной ему задачи; переход к карточкам задач.
- Карточка стейкхолдера: создание связанных требований; переход к карточкам требований; переход к карточке пользователя.

### 2.4 Требования → Задачи → Подзадачи (новая обязательная цепочка)
- **Требование обязательно связано со стейкхолдером**; в ссылке отображается тип стейкхолдера, переход — на карточку стейкхолдера.
- **Задача обязательно связана с требованием**; если требования ещё нет — его можно создать прямо из карточки задачи.
- На карточке требования можно создавать связанные задачи и переходить на их карточки.
- На карточке стейкхолдера можно создавать требования и переходить на их карточки.
- Задачи образуют иерархию: задача → подзадачи (`parent_task_id`). Подзадачи наследуют принадлежность требованию/проекту.
- Зависимости «от завершения каких задач зависит начало» — DAG; на карточке виден и обратный список (кто зависит от неё).
- Все списки задач и подзадач показывают краткое описание.

### 2.5 Задачи: тип, важность, статусы
- **Тип:** новая функциональность, улучшение, исправление ошибки, анализ, документирование, тестирование, код-ревью.
- **Важность:** низкая, средняя, высокая, критическая.
- **Статусы:** открыта, взята в работу, отклонена, отложена, завершена полностью, полное завершение отложено. Начальный статус — «открыта».
- **Краткое описание (обязательно)** и **полное описание (опционально)** у каждой задачи/подзадачи.
- **Номер задачи** в рамках проекта (для сортировки по номеру).
- **Задачи назначаются на сотрудника, а не на должность.** При назначении задачи/подзадачи можно сначала выбрать тип должности и из сотрудников проекта с этим типом выбрать исполнителя, либо выбрать сотрудника напрямую.
- При создании подзадачи исполнителем можно выбрать себя или другого сотрудника.
- К задаче/подзадаче крепятся файлы; комментарии зарегистрированных пользователей (включая гостя); к комментариям можно крепить файлы; файлы просматриваются с карточки задачи.

### 2.5.1 Задачи сбора информации (тип «анализ») — частный случай
- Задачи сбора информации — это задачи типа `analysis` («анализ»); отдельный флаг не нужен.
- Для задач типа «анализ» действует цикл приёмки: сдача результата → «на проверке» → аналитик принимает («завершена») или отклоняет («отклонена», обязательный комментарий) → возврат на доработку.
- Для остальных типов задач цикл приёмки не применяется.

### 2.6 Справочники
Все глобальные, правит администратор: роли; должности/типы стейкхолдеров; обязательные вопросы по типу; типовые NFR; модели STT; модели LLM; шаблоны промптов.

### 2.7 Анализ «на лету»
Только подсказка следующего вопроса: детерминированные кандидаты (незаданные обязательные вопросы по типу стейкхолдера) + накопленный транскрипт → LLM выбирает/переформулирует. Троттлинг обязателен.

### 2.8 Источники аудио и внешние материалы
- Запись нашим сервисом (MediaRecorder), а также **внешние материалы**: аудио и готовые транскрипты из telemost.yandex и ПО онлайн-курсов.
- К беседе можно приложить файлы с аудио и текстом транскрибации; они обрабатываются так же, как данные, полученные сервисом.
- Текст транскрибации можно просмотреть и отредактировать.
- Аудиозаписи хранятся **до явного удаления владельцем сервиса** (автоочистки нет).

### 2.9 Навигация и главная страница
- С любой карточки можно вернуться на карточку, с которой был выполнен переход (стек навигации на клиенте).
- На главной странице всем доступен выбор **текущего проекта**.
- На главной — карточка «Мои задачи»: задачи по всем должностям пользователя + созданные им подзадачи в рамках текущего проекта; сортировка по дате/времени назначения и номеру; фильтры по статусу и важности; переход к карточкам подзадач.

### 2.10 Панель ресурсов владельца сервиса
- Владельцу сервиса доступна панель со статусами ресурсов платформы развёртывания: занятое и доступное место БД и файлового хранилища, а также базовые метрики (нагрузка/очередь).

## 3. Архитектура

Модульный монолит + Procrastinate (worker поверх PostgreSQL). Redis — pub/sub, буферы и состояние live-сессий STT.

```
React SPA ── REST/WS ──> FastAPI
                         ├─ auth / RBAC (per-project)
                         ├─ admin (справочники)
                         ├─ projects / memberships / roles
                         ├─ employees / stakeholders (карточки, связи с users, вакансии)
                         ├─ meetings / external files / transcripts
                         ├─ stt orchestrator  ──> провайдеры STT
                         ├─ llm orchestrator  ──> провайдеры LLM
                         ├─ requirements / artifacts / diagrams
                         └─ tasks (иерархия + DAG) / files / comments / notifications
   PostgreSQL (данные + очередь Procrastinate)   Redis (pub-sub, STT-сессии)   S3/MinIO
```

## 4. Модель данных

Полный DDL — в Приложении A. Группы:

### 4.1 Глобальные справочники
`users`, `roles`, `positions` (должность = тип стейкхолдера), `mandatory_questions`, `nfr_types`, `llm_models`, `stt_models`, `prompt_templates`, `provider_credentials`.

### 4.2 Проекты, роли, акторы
`projects`, `project_memberships`, `membership_roles`, `employees` (user_id NULL = вакансия), `employee_positions`, `stakeholders` (position_id NOT NULL, user_id NULL = абстрактный).

### 4.3 Встречи, внешние материалы, транскрибация
`meetings`, `meeting_participants`, `meeting_files` (аудио/транскрипт из внешних источников), `audio_recordings` (source: internal/telemost/course_software/external), `transcription_jobs`, `transcript_segments`, `segment_question_links`, `meeting_question_coverage`.

### 4.4 Требования, артефакты, диаграммы
`requirements` (stakeholder_id NOT NULL, short_description, importance), `artifacts`, `analysis_runs`, `diagrams`.

### 4.5 Задачи
`tasks` (number per project, parent_task_id, requirement_id NOT NULL, type, importance, status, short_description), `task_dependencies`, `task_assignments` (employee_id), `task_attachments`, `task_result_versions`, `comments` (полиморфные), `comment_attachments`, `notifications`, `audit_log`.

### 4.6 Инварианты в БД
- Ровно один аналитик на проект (частичный уникальный индекс).
- Одна роль на проект, кроме `{admin, system_analyst}` (триггер).
- Владельца нельзя снять с admin и удалить его membership (триггер).
- `requirements.stakeholder_id NOT NULL`; `tasks.requirement_id NOT NULL`.
- `stakeholders.position_id NOT NULL` (тип обязателен).
- `UNIQUE(project_id, number)` для задач.
- Запрет циклов в `task_dependencies` (триггер + топосортировка).
- `CHECK`: при отклонении/возврате комментарий не пуст.
- Статус `on_review` допустим только для задач типа `analysis`.
- Доступ к `closed`/`archived` — только admin (RLS/политика).
- Ключевые действия — в `audit_log`.

## 5. Этапы и задачи

### M0. Каркас и инфраструктура
Структура `backend/`, `frontend/`, `deploy/`; docker-compose (postgres, redis, minio, app, worker); pydantic-settings; FastAPI app factory + `/health`; Alembic; CI (ruff/mypy/pytest, frontend lint+typecheck).
- Приёмка: `docker compose up` поднимает пустой API + PostgreSQL + Redis + MinIO; Procrastinate worker стартует; тесты/линтеры проходят.

### M1. Аутентификация, пользователи, гости
`POST /auth/register` (ФИО), `login`, `refresh`; новый пользователь — гость; `GET/PATCH /me`; видимость проектов (`open` — всем, архив — только admin).
- Приёмка: регистрация/логин; гость видит `open`-проекты и не видит архив.

### M2. Глобальные справочники (admin)
CRUD `positions`, `mandatory_questions`, `nfr_types`, `llm_models`, `stt_models`, `prompt_templates`; сиды; шифрование `provider_credentials`; подсказка по ключу Yandex.
- Приёмка: запись только admin (иначе 403).

### M3. Проекты, роли, текущий проект
`POST /projects` (создатель → admin + is_owner); close/archive; участники и роли; передача роли аналитика (атомарно); защита владельца; выбор текущего проекта.
- Приёмка: ровно один аналитик; владельца нельзя разжаловать; архив только admin.

### M4. Сотрудники и стейкхолдеры
1. Карточки сотрудника и стейкхолдера; тип стейкхолдера обязателен.
2. Связь с пользователем (опц.); абстрактный стейкхолдер; вакантная должность.
3. Назначение должностей сотруднику в проекте; несколько должностей.
4. На карточке пользователя — назначение должности/статуса стейкхолдера в текущем проекте (создаёт сотрудника/стейкхолдера); удаление связи (сотрудник → вакансия, задачи без исполнителя; стейкхолдер → абстрактный).
5. При создании пользователя — связь с ранее созданным сотрудником/стейкхолдером.
- Приёмка: на пользователя в проекте — ровно один сотрудник с теми же ФИО; связи создаются/удаляются с указанными последствиями; переходы между карточками работают.

### M5. Встречи, внешние материалы, ручной журнал
1. CRUD встреч и участников; статусы.
2. Загрузка внешних аудио и транскриптов (telemost/course software) как `meeting_files`; обработка наравне с внутренними.
3. Ручной журнал (`transcript_segments` source=manual); просмотр и редактирование текста.
4. Coverage обязательных вопросов; экран «незаданные вопросы».
- Приёмка: внешний транскрипт импортируется и редактируется; coverage корректен.

### M6. Аудио и batch-транскрибация с диаризацией
Presigned upload; `audio_recordings` (source); Procrastinate-задача; адаптер Yandex batch STT (`speakerLabeling`); запись сегментов; замена live-текста; выбор модели; ретраи/ошибки.
- Приёмка: файл транскрибируется с разделением спикеров; результат редактируем.

### M7. Live-транскрибация и подсказка вопроса
WebSocket; буферы в Redis; менеджер сессий (чанки/ротация по `session_limit_sec`/склейка); live-подсказка следующего вопроса (кандидаты + контекст → LLM, троттлинг); UI журнала и индикатора.
- Приёмка: встреча > лимита не обрывается; подсказка учитывает незаданные вопросы.

### M8. Требования и LLM-артефакты
1. CRUD требований с обязательной связью со стейкхолдером; краткое описание, важность, тип (BR/FR/NFR), типовые NFR.
2. Создание задач из карточки требования и требований из карточки стейкхолдера/задачи.
3. LLM-анализ встречи (View, Ограничения/риски, Glossary, Use Case, User Stories) → `artifacts`; ручной режим (промпт для внешнего чата + вставка ответа).
4. Автогенерация последовательности задач сбора (DAG) через LLM; генерация поисковых промптов.
- Приёмка: требования связаны со стейкхолдером; артефакты создаются; промпт можно скопировать и вернуть результат.

### M9. Задачи, подзадачи, зависимости, файлы, комментарии
1. CRUD задач и подзадач: тип, важность, статус (начальный «открыта»), краткое и полное описание, номер в проекте.
2. Обязательная связь с требованием; создание требования из карточки задачи.
3. Назначение/переназначение на сотрудника (история); фильтр «тип должности → сотрудники проекта» или прямой выбор сотрудника; назначение себя/другого при создании подзадачи.
4. DAG-зависимости + обратный список; запрет циклов.
5. Файлы к задачам; комментарии (в т.ч. гость); файлы к комментариям; просмотр файлов.
6. Задачи типа «анализ» (сбор информации): сдача → «на проверке» → приёмка/отклонение с обязательным комментарием; возврат на доработку; версии результата. Прочие типы — без цикла приёмки.
7. Уведомления (WS + `notifications`).
- Приёмка: полный цикл задача→подзадача→сдача→(возврат)→приёмка; история и файлы сохраняются.

### M10. Карточки и навигация; личный кабинет
1. Стек навигации «назад» (клиент).
2. Главная: выбор текущего проекта; карточка «Мои задачи» (все должности + созданные подзадачи) с сортировкой (дата/время назначения, номер) и фильтрами (статус, важность).
3. Карточки задачи/подзадачи, требования, сотрудника, стейкхолдера, пользователя — переходы согласно §2.4 и §2.9.
- Приёмка: все переходы и возвраты работают; «Мои задачи» фильтруются/сортируются.

### M11. Диаграммы C4/BPMN
LLM → Structurizr DSL (C4 Context/Container/Component) и BPMN-XML (bpmn-js); версии; экспорт в **PNG и SVG**.
- Приёмка: диаграммы рендерятся, сохраняются, экспортируются в PNG/SVG.

### M12. Production hardening
Audit log, RLS для архива/гостей, rate-limit и circuit breaker для STT/LLM, ПДн/152-ФЗ (согласие на запись, шифрование, хранение аудио до явного удаления владельцем), мониторинг, бэкапы, нагрузочные тесты WebSocket и DAG, **панель ресурсов владельца** (занятое и доступное место БД и файлового хранилища, очередь).

## 6. Ключевые риски и failure modes

| Риск | Митигация |
|---|---|
| Диаризация недоступна в streaming | Live без спикеров; batch с диаризацией и заменой текста |
| Лимит длины live-сессии STT | Менеджер сессий: чанки/ротация/склейка, состояние в Redis |
| Стоимость/задержка LLM | Троттлинг; кандидаты детерминированы; LLM только выбирает/формулирует |
| Обрыв WebSocket | Клиентский буфер аудио, дозагрузка, идемпотентные сегменты |
| Цикл в DAG задач | Триггер + топосортировка |
| Вакансия/абстракция при удалении связи | Задачи сохраняются за вакансией (без исполнителя); стейкхолдер → абстрактный |
| Исчерпание места на Beget (БД/S3) | Панель ресурсов владельца, мониторинг и алерты |
| Утечка ПДн/ключей | Шифрование, RBAC per-project, audit, сроки хранения |
| Гонка при передаче роли аналитика | Транзакция + частичный уникальный индекс |

## 7. План проверки

- Unit: инварианты ролей/владельца, DAG, coverage, статусная машина, вакансии/абстракции.
- Integration (testcontainers: PostgreSQL, Redis, MinIO; Procrastinate worker): auth, RBAC, STT/LLM-адаптеры с моками, импорт внешних файлов.
- Contract: OpenAPI + типы frontend.
- E2E (Playwright): регистрация→роль→проект→сотрудник/стейкхолдер→встреча→требование→задача→подзадача→сдача→приёмка→артефакты→навигация назад.
- Load: многочасовая live-транскрибация с ротацией сессий.
- Security: доступ гостя/архива, отсутствие секретов в логах.
- Трассировка: каждое из 30 новых требований покрыто тестом (Приложение B).

## 8. Вне scope

- Мобильные приложения.
- Интеграция с ВКС по API (в external-режиме материалы загружаются файлами).
- SSO/OIDC; fine-tuning моделей.

## 9. Открытые вопросы

Все ранее открытые вопросы закрыты: «признак задачи» — это отметка «задача/подзадача»; Beget.ru с Docker подтверждён (PostgreSQL и S3 внутри Docker); диаграммы экспортируются в PNG/SVG; аудио хранится до явного удаления владельцем. Добавлено требование о панели ресурсов владельца (§2.10).

## Приложение A. DDL (v2)

Изменения относительно v1: удалены `persons` и `project_stakeholders`; добавлены `employees`, `employee_positions`, `stakeholders`, `meeting_files`, `comment_attachments`; `requirements` получил `stakeholder_id`, `short_description`, `importance`; `info_tasks` заменён на `tasks` (иерархия, тип, важность, новые статусы, номер).

```sql
-- ===================== РАСШИРЕНИЯ =====================
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()

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

CREATE TABLE nfr_types        (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), code text UNIQUE, name text, description text);
CREATE TABLE llm_models       (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider text, model_code text, display_name text, is_default boolean DEFAULT false, params jsonb);
CREATE TABLE stt_models       (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider text, model_code text, display_name text,
                               is_default boolean DEFAULT false,
                               supports_streaming boolean, supports_diarization boolean,
                               session_limit_sec int);
CREATE TABLE prompt_templates (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), purpose text, name text, template text, is_system boolean DEFAULT false);
CREATE TABLE provider_credentials (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider text, scope text,
                               encrypted_secret bytea, created_at timestamptz DEFAULT now());

-- ===================== ПРОЕКТЫ, РОЛИ, УЧАСТИЕ =====================
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

-- ===================== АКТОРЫ: СОТРУДНИКИ И СТЕЙКХОЛДЕРЫ =====================
-- Сотрудник; user_id IS NULL => вакантная должность
CREATE TABLE employees (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id  uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id     uuid REFERENCES users(id),
  last_name   text,
  first_name  text,
  middle_name text,
  created_by  uuid REFERENCES users(id),
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, user_id)     -- один сотрудник-персона на проект (NULL допускает много вакансий)
);

CREATE TABLE employee_positions (
  employee_id uuid NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  position_id uuid NOT NULL REFERENCES positions(id),
  assigned_by uuid REFERENCES users(id),
  assigned_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (employee_id, position_id)
);

-- Стейкхолдер; position_id обязателен (тип); user_id IS NULL => абстрактный
CREATE TABLE stakeholders (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  position_id  uuid NOT NULL REFERENCES positions(id),
  user_id      uuid REFERENCES users(id),
  last_name    text,
  first_name   text,
  middle_name  text,
  organization text,
  notes        text,
  created_by   uuid REFERENCES users(id),
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- ===================== ВСТРЕЧИ, ВНЕШНИЕ МАТЕРИАЛЫ, ТРАНСКРИБАЦИЯ =====================
CREATE TYPE meeting_status AS ENUM ('planned','in_progress','completed','cancelled');

CREATE TABLE meetings (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id     uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title          text,
  stakeholder_id uuid REFERENCES stakeholders(id),
  status         meeting_status NOT NULL DEFAULT 'planned',
  scheduled_at   timestamptz,
  started_at     timestamptz,
  ended_at       timestamptz,
  created_by     uuid REFERENCES users(id)
);

CREATE TABLE meeting_participants (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  meeting_id     uuid NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  user_id        uuid REFERENCES users(id),
  employee_id    uuid REFERENCES employees(id),
  stakeholder_id uuid REFERENCES stakeholders(id),
  meeting_role   text,
  CHECK (num_nonnulls(user_id, employee_id, stakeholder_id) = 1)
);

CREATE TYPE media_source AS ENUM ('internal','telemost','course_software','external');
CREATE TYPE meeting_file_kind AS ENUM ('audio','transcript');

-- Внешние аудио и готовые транскрипты, приложенные к беседе
CREATE TABLE meeting_files (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  meeting_id      uuid NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  kind            meeting_file_kind NOT NULL,
  source          media_source NOT NULL DEFAULT 'external',
  storage_key     text NOT NULL,
  filename        text,
  mime_type       text,
  size_bytes      bigint,
  transcript_text text,                 -- если kind='transcript'
  uploaded_by     uuid REFERENCES users(id),
  uploaded_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE audio_recordings (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  meeting_id   uuid NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  source       media_source NOT NULL DEFAULT 'internal',
  meeting_file_id uuid REFERENCES meeting_files(id),
  storage_key  text NOT NULL,
  mime_type    text,
  duration_sec int,
  size_bytes   bigint,
  checksum     text,
  created_at   timestamptz NOT NULL DEFAULT now()
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

CREATE TYPE segment_source AS ENUM ('manual','asr_live','asr_batch','asr_edited','external');

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
  updated_at    timestamptz DEFAULT now(),
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

-- ===================== ТРЕБОВАНИЯ, АРТЕФАКТЫ, ДИАГРАММЫ =====================
CREATE TYPE requirement_type AS ENUM ('business','functional','nonfunctional');
CREATE TYPE importance AS ENUM ('low','medium','high','critical');

CREATE TABLE requirements (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id        uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  stakeholder_id    uuid NOT NULL REFERENCES stakeholders(id),   -- обязательная связь
  type              requirement_type NOT NULL,
  title             text NOT NULL,
  short_description text,
  description       text,
  nfr_type_id       uuid REFERENCES nfr_types(id),
  importance        importance NOT NULL DEFAULT 'medium',
  status            text DEFAULT 'draft',
  source            text,
  created_by        uuid REFERENCES users(id),
  created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE artifacts (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  meeting_id uuid REFERENCES meetings(id),
  type       text NOT NULL CHECK (type IN ('view','glossary','use_case','user_story','constraint','risk')),
  content    jsonb NOT NULL,
  source     text NOT NULL DEFAULT 'auto' CHECK (source IN ('auto','manual')),
  version    int NOT NULL DEFAULT 1,
  created_by uuid REFERENCES users(id),
  created_at timestamptz DEFAULT now()
);

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

CREATE TYPE diagram_type AS ENUM ('c4_context','c4_container','c4_component','bpmn');
CREATE TABLE diagrams (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id       uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  type             diagram_type NOT NULL,
  name             text,
  format           text DEFAULT 'dsl',
  content          text,
  version          int DEFAULT 1,
  generated_by_llm boolean DEFAULT true,
  created_by       uuid REFERENCES users(id),
  created_at       timestamptz DEFAULT now()
);

-- ===================== ЗАДАЧИ И ПОДЗАДАЧИ =====================
CREATE TYPE task_type AS ENUM ('feature','improvement','bugfix','analysis','documentation','testing','code_review');
CREATE TYPE task_status AS ENUM ('open','in_progress','on_review','rejected','postponed','completed','completion_postponed');

CREATE TABLE tasks (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id        uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  number            int NOT NULL,                        -- номер в рамках проекта
  parent_task_id    uuid REFERENCES tasks(id) ON DELETE CASCADE,  -- подзадача
  requirement_id    uuid NOT NULL REFERENCES requirements(id),    -- обязательная связь
  type              task_type NOT NULL,
  importance        importance NOT NULL DEFAULT 'medium',
  status            task_status NOT NULL DEFAULT 'open',
  short_description text NOT NULL,
  description       text,                                -- полное описание
  prompt            text,
  due_at            timestamptz,
  sort_order        int DEFAULT 0,
  created_by        uuid REFERENCES users(id),
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, number)
);

CREATE TABLE task_dependencies (
  task_id            uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  depends_on_task_id uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  PRIMARY KEY (task_id, depends_on_task_id),
  CHECK (task_id <> depends_on_task_id)
);

-- Исполнитель — сотрудник (может быть вакантным: без пользователя)
CREATE TABLE task_assignments (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id       uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  employee_id   uuid NOT NULL REFERENCES employees(id),
  assigned_by   uuid REFERENCES users(id),
  assigned_at   timestamptz NOT NULL DEFAULT now(),
  unassigned_at timestamptz
);

CREATE TABLE task_attachments (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id     uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  storage_key text NOT NULL,
  filename    text,
  mime_type   text,
  size_bytes  bigint,
  uploaded_by uuid REFERENCES users(id),
  uploaded_at timestamptz DEFAULT now()
);

-- Версии результата для задач сбора информации (совместимо с приёмкой/возвратом)
CREATE TABLE task_result_versions (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id        uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  version_no     int NOT NULL,
  result_text    text,
  submitted_by   uuid REFERENCES users(id),
  submitted_at   timestamptz DEFAULT now(),
  review_status  text CHECK (review_status IN ('pending','accepted','rejected')),
  review_comment text,
  UNIQUE (task_id, version_no),
  CHECK (review_status IS DISTINCT FROM 'rejected' OR (review_comment IS NOT NULL AND length(review_comment) > 0))
);

-- ===================== КОММЕНТАРИИ, ФАЙЛЫ КОММЕНТАРИЕВ, УВЕДОМЛЕНИЯ, АУДИТ =====================
CREATE TABLE comments (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id           uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  entity_type          text NOT NULL,     -- task | requirement | stakeholder | meeting | artifact
  entity_id            uuid NOT NULL,
  author_user_id       uuid REFERENCES users(id),
  author_role_snapshot role_code,
  body                 text NOT NULL,
  created_at           timestamptz DEFAULT now(),
  deleted_at           timestamptz,
  deleted_by           uuid REFERENCES users(id)
);
CREATE INDEX ix_comments_entity ON comments (entity_type, entity_id);

CREATE TABLE comment_attachments (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  comment_id  uuid NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
  storage_key text NOT NULL,
  filename    text,
  mime_type   text,
  size_bytes  bigint,
  uploaded_by uuid REFERENCES users(id),
  uploaded_at timestamptz DEFAULT now()
);

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

-- ===================== ИНДЕКСЫ ПОД ЭКРАНЫ =====================
CREATE INDEX ix_tasks_project_status   ON tasks (project_id, status);
CREATE INDEX ix_tasks_parent           ON tasks (parent_task_id);
CREATE INDEX ix_tasks_requirement      ON tasks (requirement_id);
CREATE INDEX ix_assignments_employee   ON task_assignments (employee_id);
CREATE INDEX ix_requirements_stakehold ON requirements (stakeholder_id);
```

## Приложение B. Трассировка новых требований

| № | Требование | Реализация |
|---|---|---|
| 1 | Внешние аудио/транскрипты к беседе | `meeting_files`, `audio_recordings.source`, импорт в M5 |
| 2 | Просмотр/редактирование транскрипта | `transcript_segments` (`updated_at`), API PATCH, M5 |
| 3 | Задача ↔ требование (обязательно), создание требования из задачи | `tasks.requirement_id NOT NULL`, UI M8/M9 |
| 4 | Краткое описание в списках | `tasks.short_description`, `requirements.short_description` |
| 5,7 | Задача → требование, требование → задачи | переходы карточек, M10 |
| 6,9 | Создание требований/задач со связанных карточек | UI M8/M9 |
| 8 | Требование ↔ стейкхолдер, тип в ссылке | `requirements.stakeholder_id`, join `positions` |
| 10,13,18 | Переходы на карточки стейкхолдера/пользователя/задач | навигация M10 |
| 11,12 | Связь стейкхолдера с пользователем; тип обязателен | `stakeholders.user_id`, `position_id NOT NULL` |
| 14 | Назначение должности/статуса на карточке пользователя; удаление связи | `employees`, `employee_positions`, `stakeholders`, M4 |
| 15 | Связь нового пользователя с сотрудником/стейкхолдером | M4 |
| 16,17,18 | Карточка сотрудника: список задач, создание и переход | M4/M9/M10 |
| 19 | Возврат на предыдущую карточку | навигационный стек (клиент), M10 |
| 20 | Выбор текущего проекта | M3/M10 |
| 21 | «Мои задачи» с сортировкой/фильтрами | API M10 (`project_id`, employee, filters) |
| 22,23 | Переход к подзадачам; создание подзадач с исполнителем | `tasks.parent_task_id`, `task_assignments`, M9 |
| 24 | Тип, важность, начальный статус; набор статусов | `task_type`, `importance`, `task_status`, M9 |
| 25,26 | Зависимости и обратный список | `task_dependencies`, M9 |
| 27,30 | Файлы к задачам и их просмотр | `task_attachments`, M9 |
| 28,29 | Комментарии (в т.ч. гость) и файлы к ним | `comments`, `comment_attachments`, M9 |
