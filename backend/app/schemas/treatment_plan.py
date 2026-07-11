"""Схемы графа плана лечения (проекция поверх documents + reminders)."""
import datetime as dt
from typing import List, Optional
import uuid

from pydantic import BaseModel

# Тип узла: приём / анализ / инструментальное / функциональное / прочее
NodeKind = str  # consultation | lab | instrumental | functional | other
# Состояние узла в графе (read-time): выполнено / просрочено / планируется
NodeStatus = str  # done | overdue | planned


class PlanNode(BaseModel):
    id: str
    kind: NodeKind
    status: NodeStatus
    title: str
    subtitle: Optional[str] = None          # специальность / врач
    date: Optional[dt.date] = None          # дата факта (для done)
    due_date: Optional[dt.date] = None      # срок (для planned/overdue)
    doctor: Optional[str] = None
    facility: Optional[str] = None
    specialty: Optional[str] = None
    summary: Optional[str] = None
    document_type: Optional[str] = None
    document_id: Optional[uuid.UUID] = None  # для done-узлов — исходный документ
    merge_count: int = 0                     # число входящих направлений (>1 → схождение)


class PlanEdge(BaseModel):
    source: str        # id узла-родителя (документ, породивший направление)
    target: str        # id узла-цели (результат или планируемый шаг)
    kind: str          # follow_up_appointment | referral_research | referral_specialist


class PlanEpisode(BaseModel):
    id: str                    # стабильный id эпизода (id корневого узла)
    title: str
    root_id: str
    custom_name: bool = False  # имя задано вручную (rename-override)
    node_ids: List[str]
    done: int
    total: int
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None


class PlanOverrideOut(BaseModel):
    id: uuid.UUID
    kind: str
    anchor_key: str
    other_key: Optional[str] = None
    title: Optional[str] = None


class PlanGraph(BaseModel):
    episodes: List[PlanEpisode]
    nodes: List[PlanNode]
    edges: List[PlanEdge]
    overrides: List[PlanOverrideOut] = []
    generated_at: dt.datetime


class PlanOverrideCreate(BaseModel):
    kind: str                          # rename | merge
    anchor_key: str
    other_key: Optional[str] = None    # merge
    title: Optional[str] = None        # rename
