"""Global reference data. Editable by the service owner only."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_service_owner
from app.db.session import get_session
from app.models import (
    LlmModel,
    MandatoryQuestion,
    NfrType,
    Position,
    PromptTemplate,
    SttModel,
)
from app.schemas.reference import (
    LlmModelCreate,
    LlmModelOut,
    MandatoryQuestionCreate,
    MandatoryQuestionOut,
    MandatoryQuestionUpdate,
    NfrTypeCreate,
    NfrTypeOut,
    PositionCreate,
    PositionOut,
    PositionUpdate,
    PromptTemplateCreate,
    PromptTemplateOut,
    SttModelCreate,
    SttModelOut,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_service_owner)],
)


def _not_found(name: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found")


# ----------------------------- Positions -----------------------------
@router.get("/positions", response_model=list[PositionOut])
async def list_positions(session: AsyncSession = Depends(get_session)) -> list[Position]:
    return list((await session.execute(select(Position).order_by(Position.code))).scalars())


@router.post("/positions", response_model=PositionOut, status_code=status.HTTP_201_CREATED)
async def create_position(
    payload: PositionCreate, session: AsyncSession = Depends(get_session)
) -> Position:
    if (
        await session.execute(select(Position).where(Position.code == payload.code))
    ).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Code already exists")
    position = Position(**payload.model_dump())
    session.add(position)
    await session.commit()
    await session.refresh(position)
    return position


@router.patch("/positions/{position_id}", response_model=PositionOut)
async def update_position(
    position_id: uuid.UUID,
    payload: PositionUpdate,
    session: AsyncSession = Depends(get_session),
) -> Position:
    position = await session.get(Position, position_id)
    if position is None:
        raise _not_found("Position")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(position, field, value)
    await session.commit()
    await session.refresh(position)
    return position


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    position_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> None:
    position = await session.get(Position, position_id)
    if position is None:
        raise _not_found("Position")
    if position.is_system:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="System position cannot be deleted"
        )
    await session.delete(position)
    await session.commit()


# ----------------------------- Mandatory questions -----------------------------
@router.get("/mandatory-questions", response_model=list[MandatoryQuestionOut])
async def list_questions(
    position_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[MandatoryQuestion]:
    stmt = select(MandatoryQuestion).order_by(MandatoryQuestion.sort_order)
    if position_id is not None:
        stmt = stmt.where(MandatoryQuestion.position_id == position_id)
    return list((await session.execute(stmt)).scalars())


@router.post(
    "/mandatory-questions",
    response_model=MandatoryQuestionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_question(
    payload: MandatoryQuestionCreate, session: AsyncSession = Depends(get_session)
) -> MandatoryQuestion:
    if await session.get(Position, payload.position_id) is None:
        raise _not_found("Position")
    question = MandatoryQuestion(**payload.model_dump())
    session.add(question)
    await session.commit()
    await session.refresh(question)
    return question


@router.patch("/mandatory-questions/{question_id}", response_model=MandatoryQuestionOut)
async def update_question(
    question_id: uuid.UUID,
    payload: MandatoryQuestionUpdate,
    session: AsyncSession = Depends(get_session),
) -> MandatoryQuestion:
    question = await session.get(MandatoryQuestion, question_id)
    if question is None:
        raise _not_found("Question")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(question, field, value)
    await session.commit()
    await session.refresh(question)
    return question


@router.delete("/mandatory-questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> None:
    question = await session.get(MandatoryQuestion, question_id)
    if question is None:
        raise _not_found("Question")
    await session.delete(question)
    await session.commit()


# ----------------------------- NFR types -----------------------------
@router.get("/nfr-types", response_model=list[NfrTypeOut])
async def list_nfr_types(session: AsyncSession = Depends(get_session)) -> list[NfrType]:
    return list((await session.execute(select(NfrType).order_by(NfrType.code))).scalars())


@router.post("/nfr-types", response_model=NfrTypeOut, status_code=status.HTTP_201_CREATED)
async def create_nfr_type(
    payload: NfrTypeCreate, session: AsyncSession = Depends(get_session)
) -> NfrType:
    nfr_type = NfrType(**payload.model_dump())
    session.add(nfr_type)
    await session.commit()
    await session.refresh(nfr_type)
    return nfr_type


@router.delete("/nfr-types/{nfr_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_nfr_type(
    nfr_type_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> None:
    nfr_type = await session.get(NfrType, nfr_type_id)
    if nfr_type is None:
        raise _not_found("NFR type")
    await session.delete(nfr_type)
    await session.commit()


# ----------------------------- LLM models -----------------------------
@router.get("/llm-models", response_model=list[LlmModelOut])
async def list_llm_models(session: AsyncSession = Depends(get_session)) -> list[LlmModel]:
    return list((await session.execute(select(LlmModel))).scalars())


@router.post("/llm-models", response_model=LlmModelOut, status_code=status.HTTP_201_CREATED)
async def create_llm_model(
    payload: LlmModelCreate, session: AsyncSession = Depends(get_session)
) -> LlmModel:
    model = LlmModel(**payload.model_dump())
    session.add(model)
    await session.commit()
    await session.refresh(model)
    return model


@router.delete("/llm-models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_model(
    model_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> None:
    model = await session.get(LlmModel, model_id)
    if model is None:
        raise _not_found("LLM model")
    await session.delete(model)
    await session.commit()


# ----------------------------- STT models -----------------------------
@router.get("/stt-models", response_model=list[SttModelOut])
async def list_stt_models(session: AsyncSession = Depends(get_session)) -> list[SttModel]:
    return list((await session.execute(select(SttModel))).scalars())


@router.post("/stt-models", response_model=SttModelOut, status_code=status.HTTP_201_CREATED)
async def create_stt_model(
    payload: SttModelCreate, session: AsyncSession = Depends(get_session)
) -> SttModel:
    model = SttModel(**payload.model_dump())
    session.add(model)
    await session.commit()
    await session.refresh(model)
    return model


@router.delete("/stt-models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stt_model(
    model_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> None:
    model = await session.get(SttModel, model_id)
    if model is None:
        raise _not_found("STT model")
    await session.delete(model)
    await session.commit()


# ----------------------------- Prompt templates -----------------------------
@router.get("/prompt-templates", response_model=list[PromptTemplateOut])
async def list_prompt_templates(
    session: AsyncSession = Depends(get_session),
) -> list[PromptTemplate]:
    return list((await session.execute(select(PromptTemplate))).scalars())


@router.post(
    "/prompt-templates", response_model=PromptTemplateOut, status_code=status.HTTP_201_CREATED
)
async def create_prompt_template(
    payload: PromptTemplateCreate, session: AsyncSession = Depends(get_session)
) -> PromptTemplate:
    template = PromptTemplate(**payload.model_dump())
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


@router.delete("/prompt-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt_template(
    template_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> None:
    template = await session.get(PromptTemplate, template_id)
    if template is None:
        raise _not_found("Prompt template")
    await session.delete(template)
    await session.commit()
