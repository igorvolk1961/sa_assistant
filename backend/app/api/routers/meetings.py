"""Meetings, external materials, manual transcript journal and question coverage."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_project_role
from app.core.enums import (
    CoverageStatus,
    MediaSource,
    MeetingFileKind,
    MeetingStatus,
    RoleCode,
    SegmentSource,
)
from app.db.session import get_session
from app.models import (
    AudioRecording,
    Employee,
    MandatoryQuestion,
    Meeting,
    MeetingFile,
    MeetingParticipant,
    MeetingQuestionCoverage,
    Project,
    SegmentQuestionLink,
    Stakeholder,
    TranscriptSegment,
    User,
)
from app.schemas.meeting import (
    CoverageOut,
    MeetingCreate,
    MeetingFileOut,
    MeetingOut,
    MeetingUpdate,
    SegmentCreate,
    SegmentOut,
    SegmentQuestionLinkCreate,
    SegmentUpdate,
    UnansweredQuestionOut,
)
from app.services.storage import LocalStorage, get_storage

router = APIRouter(prefix="/projects/{project_id}", tags=["meetings"])

_VIEW = (RoleCode.admin, RoleCode.system_analyst, RoleCode.employee, RoleCode.guest)
_EDIT = (RoleCode.admin, RoleCode.system_analyst, RoleCode.employee)
_MANAGE = (RoleCode.admin, RoleCode.system_analyst)


async def _meeting_or_404(
    session: AsyncSession, project_id: uuid.UUID, meeting_id: uuid.UUID
) -> Meeting:
    meeting = await session.get(Meeting, meeting_id)
    if meeting is None or meeting.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    return meeting


async def _validate_refs(
    session: AsyncSession, project_id: uuid.UUID, model, ids: list[uuid.UUID], name: str
) -> None:
    for ref_id in ids:
        obj = await session.get(model, ref_id)
        if obj is None or obj.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{name} {ref_id} does not belong to the project",
            )


@router.get("/meetings", response_model=list[MeetingOut])
async def list_meetings(
    limit: int = 100,
    offset: int = 0,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[Meeting]:
    project, _, _ = ctx
    return list(
        (
            await session.execute(
                select(Meeting)
                .where(Meeting.project_id == project.id)
                .order_by(Meeting.scheduled_at.desc().nullslast())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )


@router.post("/meetings", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    payload: MeetingCreate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_EDIT)),
    session: AsyncSession = Depends(get_session),
) -> Meeting:
    project, actor, _ = ctx
    if payload.stakeholder_id is not None:
        await _validate_refs(
            session, project.id, Stakeholder, [payload.stakeholder_id], "Stakeholder"
        )
    await _validate_refs(
        session, project.id, Employee, payload.participant_employee_ids, "Employee"
    )
    await _validate_refs(
        session, project.id, Stakeholder, payload.participant_stakeholder_ids, "Stakeholder"
    )
    meeting = Meeting(
        project_id=project.id,
        title=payload.title,
        stakeholder_id=payload.stakeholder_id,
        scheduled_at=payload.scheduled_at,
        status=MeetingStatus.planned,
        created_by=actor.id,
    )
    session.add(meeting)
    await session.flush()
    for employee_id in payload.participant_employee_ids:
        session.add(MeetingParticipant(meeting_id=meeting.id, employee_id=employee_id))
    for stakeholder_id in payload.participant_stakeholder_ids:
        session.add(MeetingParticipant(meeting_id=meeting.id, stakeholder_id=stakeholder_id))
    await session.commit()
    await session.refresh(meeting)
    return meeting


@router.get("/meetings/{meeting_id}", response_model=MeetingOut)
async def get_meeting(
    meeting_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> Meeting:
    project, _, _ = ctx
    return await _meeting_or_404(session, project.id, meeting_id)


@router.patch("/meetings/{meeting_id}", response_model=MeetingOut)
async def update_meeting(
    meeting_id: uuid.UUID,
    payload: MeetingUpdate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_EDIT)),
    session: AsyncSession = Depends(get_session),
) -> Meeting:
    project, _, _ = ctx
    meeting = await _meeting_or_404(session, project.id, meeting_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("stakeholder_id") is not None:
        await _validate_refs(
            session, project.id, Stakeholder, [data["stakeholder_id"]], "Stakeholder"
        )
    if payload.status == MeetingStatus.in_progress and meeting.started_at is None:
        meeting.started_at = datetime.now(UTC)
    if payload.status in (MeetingStatus.completed, MeetingStatus.cancelled):
        meeting.ended_at = datetime.now(UTC)
    for field, value in data.items():
        setattr(meeting, field, value)
    await session.commit()
    await session.refresh(meeting)
    return meeting


@router.delete("/meetings/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(
    meeting_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> None:
    project, _, _ = ctx
    meeting = await _meeting_or_404(session, project.id, meeting_id)
    await session.delete(meeting)
    await session.commit()


# ----------------------------- External files -----------------------------
@router.get("/meetings/{meeting_id}/files", response_model=list[MeetingFileOut])
async def list_meeting_files(
    meeting_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[MeetingFile]:
    project, _, _ = ctx
    await _meeting_or_404(session, project.id, meeting_id)
    return list(
        (
            await session.execute(
                select(MeetingFile)
                .where(MeetingFile.meeting_id == meeting_id)
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )


@router.post(
    "/meetings/{meeting_id}/files",
    response_model=MeetingFileOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_meeting_file(
    meeting_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_EDIT)),
    session: AsyncSession = Depends(get_session),
    storage: LocalStorage = Depends(get_storage),
    kind: MeetingFileKind = Form(...),
    source: MediaSource = Form(MediaSource.external),
    transcript_text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
) -> MeetingFile:
    project, actor, _ = ctx
    meeting = await _meeting_or_404(session, project.id, meeting_id)
    if file is None and not (kind == MeetingFileKind.transcript and transcript_text):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Provide a file, or transcript_text for a transcript",
        )
    storage_key = ""
    size_bytes: int | None = None
    content_type: str | None = None
    filename: str | None = None
    if file is not None:
        data = await file.read()
        storage_key = await storage.save_async(
            data, filename=file.filename or "upload", prefix="meetings"
        )
        size_bytes = len(data)
        content_type = file.content_type
        filename = file.filename
    meeting_file = MeetingFile(
        meeting_id=meeting.id,
        kind=kind,
        source=source,
        storage_key=storage_key,
        filename=filename,
        mime_type=content_type,
        size_bytes=size_bytes,
        transcript_text=transcript_text,
        uploaded_by=actor.id,
    )
    session.add(meeting_file)
    await session.flush()
    if kind == MeetingFileKind.audio and storage_key:
        session.add(
            AudioRecording(
                meeting_id=meeting.id,
                source=source,
                meeting_file_id=meeting_file.id,
                storage_key=storage_key,
                mime_type=content_type,
                size_bytes=size_bytes,
            )
        )
    if kind == MeetingFileKind.transcript and transcript_text:
        for line in transcript_text.splitlines():
            text = line.strip()
            if text:
                session.add(
                    TranscriptSegment(
                        meeting_id=meeting.id,
                        text=text,
                        source=SegmentSource.external,
                        created_by=actor.id,
                    )
                )
    await session.commit()
    await session.refresh(meeting_file)
    return meeting_file


# ----------------------------- Transcript journal -----------------------------
@router.get("/meetings/{meeting_id}/segments", response_model=list[SegmentOut])
async def list_segments(
    meeting_id: uuid.UUID,
    limit: int = 200,
    offset: int = 0,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[TranscriptSegment]:
    project, _, _ = ctx
    await _meeting_or_404(session, project.id, meeting_id)
    return list(
        (
            await session.execute(
                select(TranscriptSegment)
                .where(TranscriptSegment.meeting_id == meeting_id)
                .order_by(TranscriptSegment.start_ms.asc().nullsfirst())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )


@router.post(
    "/meetings/{meeting_id}/segments",
    response_model=SegmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_segment(
    meeting_id: uuid.UUID,
    payload: SegmentCreate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_EDIT)),
    session: AsyncSession = Depends(get_session),
) -> TranscriptSegment:
    project, actor, _ = ctx
    await _meeting_or_404(session, project.id, meeting_id)
    segment = TranscriptSegment(
        meeting_id=meeting_id,
        text=payload.text,
        speaker_label=payload.speaker_label,
        start_ms=payload.start_ms,
        end_ms=payload.end_ms,
        source=SegmentSource.manual,
        created_by=actor.id,
    )
    session.add(segment)
    await session.commit()
    await session.refresh(segment)
    return segment


@router.patch("/meetings/{meeting_id}/segments/{segment_id}", response_model=SegmentOut)
async def update_segment(
    meeting_id: uuid.UUID,
    segment_id: uuid.UUID,
    payload: SegmentUpdate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_EDIT)),
    session: AsyncSession = Depends(get_session),
) -> TranscriptSegment:
    project, _, _ = ctx
    await _meeting_or_404(session, project.id, meeting_id)
    segment = await session.get(TranscriptSegment, segment_id)
    if segment is None or segment.meeting_id != meeting_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(segment, field, value)
    if segment.source in (SegmentSource.asr_live, SegmentSource.asr_batch):
        segment.source = SegmentSource.asr_edited
    segment.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(segment)
    return segment


@router.delete(
    "/meetings/{meeting_id}/segments/{segment_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_segment(
    meeting_id: uuid.UUID,
    segment_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_EDIT)),
    session: AsyncSession = Depends(get_session),
) -> None:
    project, _, _ = ctx
    await _meeting_or_404(session, project.id, meeting_id)
    segment = await session.get(TranscriptSegment, segment_id)
    if segment is None or segment.meeting_id != meeting_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    await session.delete(segment)
    await session.commit()


# ----------------------------- Question coverage -----------------------------
@router.get("/meetings/{meeting_id}/coverage", response_model=list[CoverageOut])
async def get_coverage(
    meeting_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[MeetingQuestionCoverage]:
    project, _, _ = ctx
    await _meeting_or_404(session, project.id, meeting_id)
    return list(
        (
            await session.execute(
                select(MeetingQuestionCoverage).where(
                    MeetingQuestionCoverage.meeting_id == meeting_id
                )
            )
        )
        .scalars()
        .all()
    )


@router.get(
    "/meetings/{meeting_id}/unanswered-questions", response_model=list[UnansweredQuestionOut]
)
async def unanswered_questions(
    meeting_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[UnansweredQuestionOut]:
    project, _, _ = ctx
    meeting = await _meeting_or_404(session, project.id, meeting_id)
    if meeting.stakeholder_id is None:
        return []
    stakeholder = await session.get(Stakeholder, meeting.stakeholder_id)
    if stakeholder is None:
        return []
    questions = list(
        (
            await session.execute(
                select(MandatoryQuestion)
                .where(
                    MandatoryQuestion.position_id == stakeholder.position_id,
                    MandatoryQuestion.is_active.is_(True),
                )
                .order_by(MandatoryQuestion.sort_order)
            )
        )
        .scalars()
        .all()
    )
    coverage = {
        row.question_id: row.status
        for row in (
            await session.execute(
                select(MeetingQuestionCoverage).where(
                    MeetingQuestionCoverage.meeting_id == meeting_id
                )
            )
        )
        .scalars()
        .all()
    }
    result: list[UnansweredQuestionOut] = []
    for question in questions:
        current = coverage.get(question.id, CoverageStatus.unanswered)
        if current != CoverageStatus.answered:
            result.append(
                UnansweredQuestionOut(
                    question_id=question.id,
                    text=question.text,
                    position_id=question.position_id,
                    status=current,
                )
            )
    return result


@router.post(
    "/meetings/{meeting_id}/segments/{segment_id}/questions",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def link_segment_question(
    meeting_id: uuid.UUID,
    segment_id: uuid.UUID,
    payload: SegmentQuestionLinkCreate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_EDIT)),
    session: AsyncSession = Depends(get_session),
) -> None:
    project, _, _ = ctx
    await _meeting_or_404(session, project.id, meeting_id)
    segment = await session.get(TranscriptSegment, segment_id)
    if segment is None or segment.meeting_id != meeting_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    if await session.get(MandatoryQuestion, payload.question_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
        )
    link = await session.get(SegmentQuestionLink, (segment_id, payload.question_id))
    if link is None:
        session.add(SegmentQuestionLink(segment_id=segment_id, question_id=payload.question_id))
    coverage = await session.get(MeetingQuestionCoverage, (meeting_id, payload.question_id))
    if coverage is None:
        coverage = MeetingQuestionCoverage(
            meeting_id=meeting_id, question_id=payload.question_id
        )
        session.add(coverage)
    coverage.status = CoverageStatus.answered
    coverage.segment_id = segment_id
    await session.commit()


@router.delete(
    "/meetings/{meeting_id}/segments/{segment_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_segment_question(
    meeting_id: uuid.UUID,
    segment_id: uuid.UUID,
    question_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_EDIT)),
    session: AsyncSession = Depends(get_session),
) -> None:
    project, _, _ = ctx
    await _meeting_or_404(session, project.id, meeting_id)
    segment = await session.get(TranscriptSegment, segment_id)
    if segment is None or segment.meeting_id != meeting_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found")
    await session.execute(
        delete(SegmentQuestionLink).where(
            SegmentQuestionLink.segment_id == segment_id,
            SegmentQuestionLink.question_id == question_id,
        )
    )
    remaining_segment = (
        await session.execute(
            select(SegmentQuestionLink.segment_id)
            .where(SegmentQuestionLink.question_id == question_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    coverage = await session.get(MeetingQuestionCoverage, (meeting_id, question_id))
    if coverage is not None:
        if remaining_segment is None:
            coverage.status = CoverageStatus.unanswered
            coverage.segment_id = None
        else:
            coverage.segment_id = remaining_segment
    await session.commit()
