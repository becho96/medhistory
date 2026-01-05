from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pydantic import BaseModel
import httpx
import secrets

from app.db.postgres import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, User as UserSchema, Token
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from app.api.deps import get_current_user

router = APIRouter()

# Google OAuth URLs
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class GoogleAuthCallback(BaseModel):
    code: str
    state: str | None = None

@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    
    # Check if user exists
    query = select(User).where(User.email == user_data.email)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user

@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login user and return access token"""
    
    # Get user
    query = select(User).where(User.email == credentials.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return Token(access_token=access_token)

@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user


# ==================== Google OAuth ====================

@router.get("/google")
async def google_auth():
    """
    Redirect to Google OAuth consent screen.
    Returns the URL for frontend to redirect to.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
        "prompt": "select_account",  # Always show account selection
    }
    
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    auth_url = f"{GOOGLE_AUTH_URL}?{query_string}"
    
    return {"auth_url": auth_url, "state": state}


@router.post("/google/callback", response_model=Token)
async def google_auth_callback(
    callback_data: GoogleAuthCallback,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Google OAuth callback.
    Exchange authorization code for tokens and create/login user.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": callback_data.code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code"
            )
        
        token_data = token_response.json()
        google_access_token = token_data.get("access_token")
        
        if not google_access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No access token received from Google"
            )
        
        # Get user info from Google
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_access_token}"}
        )
        
        if userinfo_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )
        
        google_user = userinfo_response.json()
    
    google_id = google_user.get("id")
    email = google_user.get("email")
    full_name = google_user.get("name")
    
    if not google_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user data from Google"
        )
    
    # Try to find existing user by google_id or email
    query = select(User).where(
        or_(User.google_id == google_id, User.email == email)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user:
        # Update google_id if user was found by email but doesn't have google_id
        if not user.google_id:
            user.google_id = google_id
            await db.commit()
    else:
        # Create new user
        user = User(
            email=email,
            full_name=full_name,
            google_id=google_id,
            # No password_hash - user can only login via Google
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return Token(access_token=access_token)

