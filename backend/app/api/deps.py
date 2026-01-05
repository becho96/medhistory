from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
import uuid

from app.db.postgres import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.family import FamilyRelation

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Get user from database
    query = select(User).where(User.id == uuid.UUID(user_id))
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def get_profile_user_id(
    x_profile_id: Optional[str] = Header(None, alias="X-Profile-Id"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> uuid.UUID:
    """
    Get the profile user ID for the request.
    If X-Profile-Id header is provided, validates access and returns that ID.
    Otherwise, returns the current user's ID.
    
    This enables working with family member profiles.
    """
    if x_profile_id is None:
        return current_user.id
    
    try:
        profile_id = uuid.UUID(x_profile_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid profile ID format"
        )
    
    # If requesting own profile, allow
    if profile_id == current_user.id:
        return current_user.id
    
    # Check if current user has access to this profile
    relation_query = select(FamilyRelation).where(
        and_(
            FamilyRelation.owner_id == current_user.id,
            FamilyRelation.member_id == profile_id
        )
    )
    result = await db.execute(relation_query)
    relation = result.scalar_one_or_none()
    
    if not relation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this profile"
        )
    
    return profile_id

