from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.postgres import get_db
from app.models.user import User
from app.models.consent import UserConsent
from app.schemas.user import (
    UserCreate, UserLogin, User as UserSchema, Token, UserUpdate, REQUIRED_CONSENTS,
)
from app.core.security import get_password_hash, verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user.

    152-ФЗ: requires explicit consent for processing of special category
    personal data (medical data). Both 'terms_and_privacy' and
    'special_category' consents must be present in the payload, each
    pinned to the sha256 of the legal text the user saw.
    """

    missing = [c for c in REQUIRED_CONSENTS if c not in user_data.consents]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required consents: {', '.join(missing)}",
        )

    query = select(User).where(User.email == user_data.email)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
    )
    db.add(user)
    await db.flush()  # populate user.id before consent rows

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    for consent_type, document_version in user_data.consents.items():
        if consent_type not in REQUIRED_CONSENTS:
            continue
        db.add(UserConsent(
            user_id=user.id,
            consent_type=consent_type,
            document_version=document_version,
            ip_address=client_ip,
            user_agent=user_agent,
        ))

    await db.commit()
    await db.refresh(user)

    return user


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login user and return access token"""

    query = select(User).where(User.email == credentials.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    access_token = create_access_token(data={"sub": str(user.id)})

    return Token(access_token=access_token)


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user


@router.patch("/me", response_model=UserSchema)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user information"""

    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    if user_update.birth_date is not None:
        current_user.birth_date = user_update.birth_date

    if user_update.gender is not None:
        from app.models.user import GenderEnum
        current_user.gender = GenderEnum(user_update.gender)

    await db.commit()
    await db.refresh(current_user)

    return current_user
