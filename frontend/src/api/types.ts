export type RoleCode = "admin" | "system_analyst" | "employee" | "guest";
export type ProjectStatus = "open" | "closed" | "archived";
export type TaskType =
  | "feature"
  | "improvement"
  | "bugfix"
  | "analysis"
  | "documentation"
  | "testing"
  | "code_review";
export type TaskStatus =
  | "open"
  | "in_progress"
  | "on_review"
  | "rejected"
  | "postponed"
  | "completed"
  | "completion_postponed";
export type Importance = "low" | "medium" | "high" | "critical";
export type RequirementType = "business" | "functional" | "nonfunctional";

export interface User {
  id: string;
  login: string;
  last_name: string;
  first_name: string;
  middle_name: string | null;
  is_active: boolean;
  is_service_owner: boolean;
}

export interface Project {
  id: string;
  code: string | null;
  name: string;
  description: string | null;
  status: ProjectStatus;
  created_at: string;
  closed_at: string | null;
}

export interface Member {
  id: string;
  project_id: string;
  user_id: string;
  is_owner: boolean;
  joined_at: string;
  roles: RoleCode[];
}

export interface Position {
  id: string;
  code: string;
  name: string;
  assignable_as_position: boolean;
  usable_as_stakeholder_type: boolean;
  is_system: boolean;
}

export interface Employee {
  id: string;
  project_id: string;
  user_id: string | null;
  last_name: string | null;
  first_name: string | null;
  middle_name: string | null;
}

export interface Stakeholder {
  id: string;
  project_id: string;
  position_id: string;
  user_id: string | null;
  last_name: string | null;
  first_name: string | null;
  middle_name: string | null;
  organization: string | null;
  notes: string | null;
}

export type ImplementationStatus =
  | "implemented"
  | "partial"
  | "missing"
  | "planned"
  | "unknown";
export type PriorityMoscow = "must" | "should" | "could" | "wont";

export interface Requirement {
  id: string;
  project_id: string;
  stakeholder_id: string | null;
  stakeholder_type_id: string | null;
  code: string | null;
  epic_id: string | null;
  type: RequirementType;
  title: string;
  short_description: string | null;
  description: string | null;
  acceptance_criteria: string | null;
  nfr_type_id: string | null;
  importance: Importance;
  priority_moscow: PriorityMoscow | null;
  implementation_status: ImplementationStatus | null;
  status: string | null;
  source: string | null;
  created_at: string;
}

export interface RequirementEpic {
  id: string;
  project_id: string;
  name: string;
  sort_order: number;
  created_at: string;
}

export interface NfrType {
  id: string;
  code: string | null;
  name: string | null;
  description: string | null;
}

export interface TaskAssignee {
  employee_id: string;
  name: string;
  is_vacant: boolean;
}

export interface Task {
  id: string;
  project_id: string;
  number: number;
  parent_task_id: string | null;
  requirement_id: string;
  type: TaskType;
  importance: Importance;
  status: TaskStatus;
  short_description: string;
  description: string | null;
  prompt: string | null;
  due_at: string | null;
  created_at: string;
  assignees: TaskAssignee[];
}

export interface Meeting {
  id: string;
  project_id: string;
  title: string | null;
  stakeholder_id: string | null;
  status: "planned" | "in_progress" | "completed" | "cancelled";
  scheduled_at: string | null;
  created_at: string;
}

export interface Segment {
  id: string;
  meeting_id: string;
  text: string;
  speaker_label: string | null;
  source: string;
  created_at: string;
}

export interface Comment {
  id: string;
  entity_type: string;
  entity_id: string;
  author_user_id: string | null;
  author_role_snapshot: RoleCode | null;
  body: string;
  created_at: string;
}

export interface Notification {
  id: string;
  type: string;
  payload: Record<string, unknown> | null;
  is_read: boolean;
  created_at: string;
}
