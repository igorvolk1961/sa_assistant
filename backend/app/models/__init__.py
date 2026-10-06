"""All ORM models. Import this module so Alembic sees every table."""

from app.db.base import Base
from app.models.actor import Employee, EmployeePosition, Stakeholder
from app.models.interaction import AuditLog, Comment, CommentAttachment, Notification
from app.models.meeting import (
    AudioRecording,
    Meeting,
    MeetingFile,
    MeetingParticipant,
    MeetingQuestionCoverage,
    SegmentQuestionLink,
    TranscriptionJob,
    TranscriptSegment,
)
from app.models.project import MembershipRole, Project, ProjectMembership
from app.models.reference import (
    LlmModel,
    MandatoryQuestion,
    NfrType,
    Position,
    PromptTemplate,
    ProviderCredential,
    SttModel,
)
from app.models.requirement import AnalysisRun, Artifact, Diagram, Requirement, RequirementEpic
from app.models.task import (
    Task,
    TaskAssignment,
    TaskAttachment,
    TaskDependency,
    TaskResultVersion,
)
from app.models.user import Role, User

__all__ = [
    "AnalysisRun",
    "Artifact",
    "AudioRecording",
    "AuditLog",
    "Base",
    "Comment",
    "CommentAttachment",
    "Diagram",
    "Employee",
    "EmployeePosition",
    "LlmModel",
    "MandatoryQuestion",
    "Meeting",
    "MeetingFile",
    "MeetingParticipant",
    "MeetingQuestionCoverage",
    "MembershipRole",
    "NfrType",
    "Notification",
    "Position",
    "Project",
    "ProjectMembership",
    "PromptTemplate",
    "ProviderCredential",
    "Requirement",
    "RequirementEpic",
    "Role",
    "SegmentQuestionLink",
    "Stakeholder",
    "SttModel",
    "Task",
    "TaskAssignment",
    "TaskAttachment",
    "TaskDependency",
    "TaskResultVersion",
    "TranscriptSegment",
    "TranscriptionJob",
    "User",
]
