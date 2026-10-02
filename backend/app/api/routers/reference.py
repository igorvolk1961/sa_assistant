"""Read-only reference data available to any authenticated user."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models import NfrType, Position, Role
from app.schemas.reference import NfrTypeOut, PositionOut

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get("/positions", response_model=list[PositionOut])
async def list_positions(
    _=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Position]:
    return list((await session.execute(select(Position).order_by(Position.code))).scalars())


@router.get("/nfr-types", response_model=list[NfrTypeOut])
async def list_nfr_types(
    _=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[NfrType]:
    return list((await session.execute(select(NfrType).order_by(NfrType.code))).scalars())


@router.get("/roles", response_model=list[dict])
async def list_roles(
    _=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    roles = (await session.execute(select(Role))).scalars().all()
    return [{"code": role.code.value, "name": role.name} for role in roles]
