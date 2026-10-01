"""Polymorphic comments and comment attachments (guests may comment)."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_project_role
from app.core.enums import RoleCode
from app.db.session import get_session
from app.models import (
    Artifact,
    Comment,
    CommentAttachment,
    Meeting,
    Project,
    Requirement,
    Stakeholder,
    Task,
    User,
)
from app.schemas.comment import CommentAttachmentOut, CommentCreate, CommentOut
from app.services.files import file_response
from app.services.storage import LocalStorage, get_storage

router = APIRouter(prefix="/projects/{project_id}", tags=["comments"])

_VIEW = (RoleCode.admin, RoleCode.system_analyst, RoleCode.employee, RoleCode.guest)

_ENTITY_MODELS = {
    "task": Task,
    "requirement": Requirement,
    "stakeholder": Stakeholder,
    "meeting": Meeting,
    "artifact": Artifact,
}


async def _validate_entity(
    session: AsyncSession, project_id: uuid.UUID, entity_type: str, entity_id: uuid.UUID
) -> None:
    model = _ENTITY_MODELS.get(entity_type)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unsupported entity_type; expected one of {sorted(_ENTITY_MODELS)}",
        )
    obj = await session.get(model, entity_id)
    if obj is None or obj.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Entity does not belong to the project",
        )


async def _comment_or_404(
    session: AsyncSession, project_id: uuid.UUID, comment_id: uuid.UUID
) -> Comment:
    comment = await session.get(Comment, comment_id)
    if comment is None or comment.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    return comment


@router.get("/comments", response_model=list[CommentOut])
async def list_comments(
    entity_type: str,
    entity_id: uuid.UUID,
    include_deleted: bool = False,
    limit: int = 200,
    offset: int = 0,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[Comment]:
    project, _, role = ctx
    if include_deleted and role != RoleCode.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view deleted comments",
        )
    stmt = select(Comment).where(
        Comment.project_id == project.id,
        Comment.entity_type == entity_type,
        Comment.entity_id == entity_id,
    )
    if not include_deleted:
        stmt = stmt.where(Comment.deleted_at.is_(None))
    return list(
        (
            await session.execute(
                stmt.order_by(Comment.created_at).limit(limit).offset(offset)
            )
        )
        .scalars()
        .all()
    )


@router.post("/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(
    payload: CommentCreate,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> Comment:
    project, actor, role = ctx
    await _validate_entity(session, project.id, payload.entity_type, payload.entity_id)
    comment = Comment(
        project_id=project.id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        author_user_id=actor.id,
        author_role_snapshot=role,
        body=payload.body,
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    return comment


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(RoleCode.admin)),
    session: AsyncSession = Depends(get_session),
) -> None:
    project, actor, _ = ctx
    comment = await _comment_or_404(session, project.id, comment_id)
    comment.deleted_at = datetime.now(UTC)
    comment.deleted_by = actor.id
    await session.commit()


@router.get("/comments/{comment_id}/attachments", response_model=list[CommentAttachmentOut])
async def list_comment_attachments(
    comment_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
) -> list[CommentAttachment]:
    project, _, _ = ctx
    await _comment_or_404(session, project.id, comment_id)
    return list(
        (
            await session.execute(
                select(CommentAttachment).where(CommentAttachment.comment_id == comment_id)
            )
        )
        .scalars()
        .all()
    )


@router.post(
    "/comments/{comment_id}/attachments",
    response_model=CommentAttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_comment_attachment(
    comment_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
    storage: LocalStorage = Depends(get_storage),
    file: UploadFile = File(...),
) -> CommentAttachment:
    project, actor, _ = ctx
    await _comment_or_404(session, project.id, comment_id)
    data = await file.read()
    key = await storage.save_async(data, filename=file.filename or "file", prefix="comments")
    attachment = CommentAttachment(
        comment_id=comment_id,
        storage_key=key,
        filename=file.filename,
        mime_type=file.content_type,
        size_bytes=len(data),
        uploaded_by=actor.id,
    )
    session.add(attachment)
    await session.commit()
    await session.refresh(attachment)
    return attachment


@router.get("/comments/{comment_id}/attachments/{attachment_id}/content")
async def download_comment_attachment(
    comment_id: uuid.UUID,
    attachment_id: uuid.UUID,
    ctx: tuple[Project, User, RoleCode] = Depends(require_project_role(*_VIEW)),
    session: AsyncSession = Depends(get_session),
    storage: LocalStorage = Depends(get_storage),
) -> Response:
    project, _, _ = ctx
    await _comment_or_404(session, project.id, comment_id)
    attachment = await session.get(CommentAttachment, attachment_id)
    if attachment is None or attachment.comment_id != comment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return await file_response(
        storage,
        storage_key=attachment.storage_key,
        filename=attachment.filename,
        mime_type=attachment.mime_type,
    )
