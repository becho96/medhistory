"""Subscription tier resolution, quota enforcement, and promo code activation.

The quota is per-billing-owner per calendar month:
- A user without a family owner billing themselves is the billing owner.
- A user who is a member in family_relations bills against the family owner.
- All documents uploaded by the owner OR any of the owner's family members
  are summed into a single monthly counter against the owner's tier limit.

Pro tier is granted with an explicit expiry (pro_expires_at). Expiry is
resolved lazily in get_effective_tier — when we observe an expired row
during a normal request, we downgrade in place.
"""

import secrets
import string
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional

from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.family import FamilyRelation
from app.models.document import Document
from app.models.subscription import PromoCode, PromoCodeActivation


Tier = Literal["free", "pro"]

FREE_MONTHLY_LIMIT = 2
PRO_MONTHLY_LIMIT = 100


@dataclass
class UsageInfo:
    tier: Tier
    limit: int
    used: int
    remaining: int
    pro_expires_at: Optional[datetime]
    billing_owner_id: uuid.UUID
    is_billing_owner: bool


@dataclass
class ActivationResult:
    tier: Tier
    pro_expires_at: datetime
    duration_days: int


class QuotaExceededError(Exception):
    def __init__(self, used: int, limit: int, tier: Tier, reset_at: datetime):
        self.used = used
        self.limit = limit
        self.tier = tier
        self.reset_at = reset_at
        super().__init__(f"Quota exceeded: {used}/{limit} ({tier})")


PromoCodeFailReason = Literal[
    "not_found", "inactive", "expired", "exhausted", "already_used"
]


class PromoCodeError(Exception):
    def __init__(self, reason: PromoCodeFailReason):
        self.reason = reason
        super().__init__(f"Promo code error: {reason}")


class SubscriptionService:

    @staticmethod
    async def get_billing_owner_id(user_id: uuid.UUID, db: AsyncSession) -> uuid.UUID:
        """Return the user whose tier and quota are consumed by `user_id`'s
        document operations. If user is a family member, that's the owner;
        otherwise it's the user themselves."""
        query = (
            select(FamilyRelation.owner_id)
            .where(FamilyRelation.member_id == user_id)
            .order_by(FamilyRelation.created_at.asc())
            .limit(1)
        )
        result = await db.execute(query)
        owner_id = result.scalar_one_or_none()
        return owner_id if owner_id is not None else user_id

    @staticmethod
    async def get_effective_tier(user_id: uuid.UUID, db: AsyncSession) -> Tier:
        """Resolve current tier for the user's billing owner, lazily downgrading
        Pro if pro_expires_at has passed."""
        owner_id = await SubscriptionService.get_billing_owner_id(user_id, db)

        result = await db.execute(
            select(User.subscription_tier, User.pro_expires_at).where(User.id == owner_id)
        )
        row = result.one_or_none()
        if row is None:
            return "free"

        tier, expires = row
        if tier == "pro":
            if expires is None or expires <= datetime.now(timezone.utc):
                await db.execute(
                    update(User)
                    .where(User.id == owner_id)
                    .values(subscription_tier="free", pro_expires_at=None, pro_source=None)
                )
                await db.commit()
                return "free"
            return "pro"
        return "free"

    @staticmethod
    def get_monthly_limit(tier: Tier) -> int:
        return PRO_MONTHLY_LIMIT if tier == "pro" else FREE_MONTHLY_LIMIT

    @staticmethod
    async def _list_billed_user_ids(owner_id: uuid.UUID, db: AsyncSession) -> list[uuid.UUID]:
        """All user_ids whose documents count against owner_id's quota:
        the owner + every family member they manage."""
        result = await db.execute(
            select(FamilyRelation.member_id).where(FamilyRelation.owner_id == owner_id)
        )
        member_ids = [row[0] for row in result.all()]
        return [owner_id, *member_ids]

    @staticmethod
    def _month_start(now: Optional[datetime] = None) -> datetime:
        ref = now or datetime.now(timezone.utc)
        return ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def _next_month_start(now: Optional[datetime] = None) -> datetime:
        start = SubscriptionService._month_start(now)
        if start.month == 12:
            return start.replace(year=start.year + 1, month=1)
        return start.replace(month=start.month + 1)

    @staticmethod
    async def count_used_this_month(billing_owner_id: uuid.UUID, db: AsyncSession) -> int:
        billed_ids = await SubscriptionService._list_billed_user_ids(billing_owner_id, db)
        month_start = SubscriptionService._month_start()
        result = await db.execute(
            select(func.count(Document.id)).where(
                and_(
                    Document.user_id.in_(billed_ids),
                    Document.created_at >= month_start,
                )
            )
        )
        return int(result.scalar_one())

    @staticmethod
    async def get_usage(user_id: uuid.UUID, db: AsyncSession) -> UsageInfo:
        owner_id = await SubscriptionService.get_billing_owner_id(user_id, db)
        tier = await SubscriptionService.get_effective_tier(user_id, db)
        limit = SubscriptionService.get_monthly_limit(tier)
        used = await SubscriptionService.count_used_this_month(owner_id, db)

        result = await db.execute(select(User.pro_expires_at).where(User.id == owner_id))
        pro_expires_at = result.scalar_one_or_none()

        return UsageInfo(
            tier=tier,
            limit=limit,
            used=used,
            remaining=max(0, limit - used),
            pro_expires_at=pro_expires_at,
            billing_owner_id=owner_id,
            is_billing_owner=(owner_id == user_id),
        )

    @staticmethod
    async def assert_can_upload(user_id: uuid.UUID, db: AsyncSession) -> None:
        usage = await SubscriptionService.get_usage(user_id, db)
        if usage.used >= usage.limit:
            raise QuotaExceededError(
                used=usage.used,
                limit=usage.limit,
                tier=usage.tier,
                reset_at=SubscriptionService._next_month_start(),
            )

    @staticmethod
    async def activate_promocode(user: User, code: str, db: AsyncSession) -> ActivationResult:
        """Validate and apply a promo code. Cumulative if Pro is already active."""
        normalized = code.strip()
        if not normalized:
            raise PromoCodeError("not_found")

        # Lock the promo row for the duration of the transaction to safely
        # increment activations_count against max_activations.
        result = await db.execute(
            select(PromoCode).where(PromoCode.code == normalized).with_for_update()
        )
        promo = result.scalar_one_or_none()
        if promo is None:
            raise PromoCodeError("not_found")
        if not promo.is_active:
            raise PromoCodeError("inactive")
        if promo.expires_at is not None and promo.expires_at <= datetime.now(timezone.utc):
            raise PromoCodeError("expired")
        if promo.activations_count >= promo.max_activations:
            raise PromoCodeError("exhausted")

        # Prevent the same user activating the same code twice. The UNIQUE
        # constraint on (promo_code_id, user_id) is the source of truth; we
        # check explicitly to return a friendlier error.
        existing = await db.execute(
            select(PromoCodeActivation.id).where(
                and_(
                    PromoCodeActivation.promo_code_id == promo.id,
                    PromoCodeActivation.user_id == user.id,
                )
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise PromoCodeError("already_used")

        now = datetime.now(timezone.utc)
        base = user.pro_expires_at if user.pro_expires_at and user.pro_expires_at > now else now
        new_expiry = base + timedelta(days=promo.duration_days)

        promo.activations_count += 1
        user.subscription_tier = "pro"
        user.pro_expires_at = new_expiry
        user.pro_source = "promo"

        activation = PromoCodeActivation(
            promo_code_id=promo.id,
            user_id=user.id,
            pro_extended_to=new_expiry,
        )
        db.add(activation)
        await db.commit()
        await db.refresh(user)

        return ActivationResult(
            tier="pro",
            pro_expires_at=new_expiry,
            duration_days=promo.duration_days,
        )

    @staticmethod
    async def admin_grant_pro(target_user_id: uuid.UUID, days: int, db: AsyncSession) -> User:
        if days <= 0:
            raise ValueError("days must be positive")

        result = await db.execute(select(User).where(User.id == target_user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError("user not found")

        now = datetime.now(timezone.utc)
        base = user.pro_expires_at if user.pro_expires_at and user.pro_expires_at > now else now
        user.subscription_tier = "pro"
        user.pro_expires_at = base + timedelta(days=days)
        user.pro_source = "admin"
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def admin_revoke_pro(target_user_id: uuid.UUID, db: AsyncSession) -> User:
        result = await db.execute(select(User).where(User.id == target_user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError("user not found")
        user.subscription_tier = "free"
        user.pro_expires_at = None
        user.pro_source = None
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    def generate_code(length: int = 12) -> str:
        """Generate a URL-safe, uppercase promo code."""
        alphabet = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))
