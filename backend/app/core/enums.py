"""Python enums mirroring the PostgreSQL enum types.

Values must match the DDL in PLAN.md (Приложение A).
"""

from enum import StrEnum


class RoleCode(StrEnum):
    admin = "admin"
    system_analyst = "system_analyst"
    employee = "employee"
    guest = "guest"


class ProjectStatus(StrEnum):
    open = "open"
    closed = "closed"
    archived = "archived"


class MeetingStatus(StrEnum):
    planned = "planned"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class MediaSource(StrEnum):
    internal = "internal"
    telemost = "telemost"
    course_software = "course_software"
    external = "external"


class MeetingFileKind(StrEnum):
    audio = "audio"
    transcript = "transcript"


class JobStatus(StrEnum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class TranscribeMode(StrEnum):
    live = "live"
    batch = "batch"
    hybrid = "hybrid"


class SegmentSource(StrEnum):
    manual = "manual"
    asr_live = "asr_live"
    asr_batch = "asr_batch"
    asr_edited = "asr_edited"
    external = "external"


class RequirementType(StrEnum):
    business = "business"
    functional = "functional"
    nonfunctional = "nonfunctional"


class Importance(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TaskType(StrEnum):
    feature = "feature"
    improvement = "improvement"
    bugfix = "bugfix"
    analysis = "analysis"
    documentation = "documentation"
    testing = "testing"
    code_review = "code_review"


class TaskStatus(StrEnum):
    open = "open"
    in_progress = "in_progress"
    on_review = "on_review"
    rejected = "rejected"
    postponed = "postponed"
    completed = "completed"
    completion_postponed = "completion_postponed"


class DiagramType(StrEnum):
    c4_context = "c4_context"
    c4_container = "c4_container"
    c4_component = "c4_component"
    bpmn = "bpmn"


class ReviewStatus(StrEnum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class CoverageStatus(StrEnum):
    unanswered = "unanswered"
    asked = "asked"
    answered = "answered"
