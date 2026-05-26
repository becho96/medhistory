"""API endpoints for user feedback submissions."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.postgres import get_db
from app.models.user import User
from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter()


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """Persist a feedback message together with a metadata snapshot.

    The client supplies free-form metadata in ``client_meta`` (viewport,
    screen size, dpr, route). User identity is taken from the JWT —
    never from the request body — so a malicious client cannot spoof it.
    """
    record = Feedback(
        user_id=current_user.id,
        user_email=current_user.email,
        message=payload.message,
        url=payload.url,
        user_agent=payload.user_agent,
        client_meta=payload.client_meta or {},
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return FeedbackResponse(id=record.id, created_at=record.created_at)
