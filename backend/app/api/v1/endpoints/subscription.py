from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.subscription import (
    SubscriptionInfo,
    ActivatePromoCodeRequest,
    ActivatePromoCodeResponse,
)
from app.services.subscription_service import (
    SubscriptionService,
    PromoCodeError,
)

router = APIRouter()


@router.get("/me", response_model=SubscriptionInfo)
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    usage = await SubscriptionService.get_usage(current_user.id, db)
    return SubscriptionInfo(
        tier=usage.tier,
        limit=usage.limit,
        used=usage.used,
        remaining=usage.remaining,
        pro_expires_at=usage.pro_expires_at,
        billing_owner_id=usage.billing_owner_id,
        is_billing_owner=usage.is_billing_owner,
    )


@router.post("/activate", response_model=ActivatePromoCodeResponse)
async def activate_promocode(
    body: ActivatePromoCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await SubscriptionService.activate_promocode(current_user, body.code, db)
    except PromoCodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "promo_invalid", "reason": e.reason},
        )

    usage = await SubscriptionService.get_usage(current_user.id, db)
    return ActivatePromoCodeResponse(
        subscription=SubscriptionInfo(
            tier=usage.tier,
            limit=usage.limit,
            used=usage.used,
            remaining=usage.remaining,
            pro_expires_at=usage.pro_expires_at,
            billing_owner_id=usage.billing_owner_id,
            is_billing_owner=usage.is_billing_owner,
        ),
        duration_days=result.duration_days,
        activated_until=result.pro_expires_at,
    )
