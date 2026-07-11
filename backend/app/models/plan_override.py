from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.postgres import Base


class PlanOverride(Base):
    """Ручная правка выведенного графа плана лечения (Phase 1b).

    Якорится на СТАБИЛЬНЫЕ ключи узлов (doc:<document_id>), а не на
    волатильный выведенный id эпизода — чтобы правки переживали рост графа.
      kind='rename' : anchor_key = узел эпизода; title = имя
      kind='merge'  : anchor_key + other_key = принудительный union
      kind='cut'    : anchor_key = источник ребра, other_key = цель (отложено)
    """
    __tablename__ = "plan_overrides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    kind = Column(String(16), nullable=False)     # rename | merge | cut
    anchor_key = Column(Text, nullable=False)
    other_key = Column(Text, nullable=True)
    title = Column(String(200), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
