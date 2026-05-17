from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from app.db.postgres import get_db
from app.models.user import User
from app.models.document import Document
from app.models.subscription import PromoCode, PromoCodeActivation
from app.api.deps import get_current_admin_user
from app.schemas.admin import (
    PromoCodeCreate,
    PromoCodeUpdate,
    PromoCodeOut,
    AdminUserListItem,
    GrantProRequest,
    SetAdminRequest,
    AdminStats,
    SignupSourceCount,
)
from app.schemas.user import User as UserSchema
from app.services.subscription_service import SubscriptionService

router = APIRouter(dependencies=[Depends(get_current_admin_user)])


# ---------- Promo codes ----------

@router.get("/promocodes", response_model=List[PromoCodeOut])
async def list_promocodes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(PromoCode).order_by(PromoCode.created_at.desc())
    if is_active is not None:
        query = query.where(PromoCode.is_active == is_active)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/promocodes", response_model=PromoCodeOut, status_code=status.HTTP_201_CREATED)
async def create_promocode(
    data: PromoCodeCreate,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    code = (data.code or "").strip().upper()
    if not code:
        code = SubscriptionService.generate_code()

    existing = await db.execute(select(PromoCode.id).where(PromoCode.code == code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "duplicate_code"},
        )

    promo = PromoCode(
        code=code,
        duration_days=data.duration_days,
        max_activations=data.max_activations,
        expires_at=data.expires_at,
        comment=data.comment,
        created_by=admin.id,
    )
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    return promo


@router.patch("/promocodes/{promo_id}", response_model=PromoCodeOut)
async def update_promocode(
    promo_id: uuid.UUID,
    data: PromoCodeUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PromoCode).where(PromoCode.id == promo_id))
    promo = result.scalar_one_or_none()
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found")

    if data.is_active is not None:
        promo.is_active = data.is_active
    if data.comment is not None:
        promo.comment = data.comment

    await db.commit()
    await db.refresh(promo)
    return promo


@router.delete("/promocodes/{promo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_promocode(
    promo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PromoCode).where(PromoCode.id == promo_id))
    promo = result.scalar_one_or_none()
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found")

    if promo.activations_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "promo_has_activations"},
        )

    await db.delete(promo)
    await db.commit()


# ---------- Users ----------

@router.get("/users", response_model=List[AdminUserListItem])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    tier: Optional[str] = Query(None, regex="^(free|pro)$"),
    db: AsyncSession = Depends(get_db),
):
    docs_count = (
        select(Document.user_id, func.count(Document.id).label("docs_count"))
        .group_by(Document.user_id)
        .subquery()
    )

    query = (
        select(User, docs_count.c.docs_count)
        .outerjoin(docs_count, docs_count.c.user_id == User.id)
        .order_by(User.created_at.desc())
    )

    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))
    if tier:
        query = query.where(User.subscription_tier == tier)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    items: list[AdminUserListItem] = []
    for user, docs in result.all():
        items.append(
            AdminUserListItem(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                subscription_tier=user.subscription_tier,
                pro_expires_at=user.pro_expires_at,
                is_admin=user.is_admin,
                is_active=user.is_active,
                created_at=user.created_at,
                documents_count=int(docs or 0),
                signup_source=user.signup_source,
            )
        )
    return items


@router.post("/users/{user_id}/grant-pro", response_model=UserSchema)
async def grant_pro(
    user_id: uuid.UUID,
    body: GrantProRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await SubscriptionService.admin_grant_pro(user_id, body.days, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return user


@router.post("/users/{user_id}/revoke-pro", response_model=UserSchema)
async def revoke_pro(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await SubscriptionService.admin_revoke_pro(user_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return user


@router.post("/users/{user_id}/set-admin", response_model=UserSchema)
async def set_admin(
    user_id: uuid.UUID,
    body: SetAdminRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_admin = body.is_admin
    await db.commit()
    await db.refresh(user)
    return user


# ---------- Stats ----------

@router.get("/stats", response_model=AdminStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    pro_users = (
        await db.execute(
            select(func.count(User.id)).where(
                and_(User.subscription_tier == "pro", User.pro_expires_at > now)
            )
        )
    ).scalar_one()
    active_promocodes = (
        await db.execute(
            select(func.count(PromoCode.id)).where(
                and_(
                    PromoCode.is_active == True,
                    or_(PromoCode.expires_at.is_(None), PromoCode.expires_at > now),
                    PromoCode.activations_count < PromoCode.max_activations,
                )
            )
        )
    ).scalar_one()
    activations_this_month = (
        await db.execute(
            select(func.count(PromoCodeActivation.id)).where(
                PromoCodeActivation.activated_at >= month_start
            )
        )
    ).scalar_one()

    # Signups grouped by acquisition channel (signup_source). NULL covers users
    # registered before attribution tracking existed.
    source_col = func.coalesce(User.signup_source, "(не указан)")
    source_rows = (
        await db.execute(
            select(source_col, func.count(User.id))
            .group_by(source_col)
            .order_by(func.count(User.id).desc())
        )
    ).all()
    signups_by_source = [
        SignupSourceCount(source=str(source), count=int(count))
        for source, count in source_rows
    ]

    return AdminStats(
        total_users=int(total_users),
        pro_users=int(pro_users),
        active_promocodes=int(active_promocodes),
        activations_this_month=int(activations_this_month),
        signups_by_source=signups_by_source,
    )
