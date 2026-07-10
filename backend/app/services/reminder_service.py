"""Reminders — materialization from document orders, read-time listing.

Auto reminders are materialized from a document's extracted orders (idempotent
upsert by source_document_id + source_order_index). Auto-close (a later matching
document fulfils the referral) and urgency escalation are computed at read time,
reusing the shared matching primitives in ``reminder_matching``.
"""
from __future__ import annotations

from datetime import date
from typing import Optional, List, Dict, Any
import uuid

from dateutil.relativedelta import relativedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document as DocumentModel
from app.models.reminder import Reminder
from app.db.mongodb import document_metadata_collection
from app.services.reminder_matching import (
    FOLLOW_UP_DOCUMENT_TYPES,
    _infer_order_target,
    _order_matches_candidate,
)

_RELATIVE_UNITS = {"day": "days", "week": "weeks", "month": "months", "year": "years"}

# Порядок срочности для сортировки активных напоминаний.
_URGENCY_RANK = {"overdue": 0, "urgent": 1, "soon": 2, "planned": 3, "no_date": 4}


def classify_urgency(due_date: Optional[date], today: date) -> tuple[str, Optional[int]]:
    """Уровень срочности и число дней до срока (read-time)."""
    if due_date is None:
        return "no_date", None
    days_left = (due_date - today).days
    if days_left < 0:
        level = "overdue"
    elif days_left <= 3:
        level = "urgent"
    elif days_left <= 14:
        level = "soon"
    else:
        level = "planned"
    return level, days_left


def _infer_kind(order: Dict[str, Any], target_type: Optional[str]) -> str:
    kind = order.get("kind")
    if kind in ("follow_up_appointment", "referral_research", "referral_specialist"):
        return kind
    # Бэкфилл/старые данные без явного kind: восстанавливаем по цели.
    if target_type == "Прием врача":
        return "follow_up_appointment"
    return "referral_research"


def _compute_due(order: Dict[str, Any], document_date: Optional[date]) -> tuple[Optional[date], Optional[str]]:
    """Явная дата из документа, либо document_date + относительный интервал."""
    explicit = order.get("due_date")
    if explicit:
        try:
            return date.fromisoformat(str(explicit)[:10]), "absolute"
        except (ValueError, TypeError):
            pass

    due_after = order.get("due_after")
    if isinstance(due_after, dict) and document_date:
        amount = due_after.get("amount")
        unit = due_after.get("unit")
        kwarg = _RELATIVE_UNITS.get(str(unit))
        if kwarg and isinstance(amount, (int, float)) and amount > 0:
            return document_date + relativedelta(**{kwarg: int(amount)}), "relative"

    return None, None


def _order_title(order: Dict[str, Any], target_type: Optional[str], target_subtype: Optional[str]) -> str:
    return order.get("title") or target_subtype or target_type or "Назначение"


async def sync_document_reminders(
    document: DocumentModel,
    orders: List[Dict[str, Any]],
    db: AsyncSession,
) -> None:
    """Идемпотентно материализовать авто-напоминания из orders документа.

    Обновляет описательные поля существующих строк; НЕ перетирает
    пользовательские status/resolution/note (status_source='manual').
    Удаляет авто-строки, которых больше нет в новом списке orders.
    """
    orders = orders or []

    existing_result = await db.execute(
        select(Reminder).where(Reminder.source_document_id == document.id)
    )
    existing_by_index: Dict[int, Reminder] = {
        r.source_order_index: r for r in existing_result.scalars().all()
    }

    seen_indexes: set[int] = set()

    for order_index, raw_order in enumerate(orders):
        if not isinstance(raw_order, dict):
            continue
        seen_indexes.add(order_index)

        target_type, target_subtype = _infer_order_target(raw_order)
        due_date, due_source = _compute_due(raw_order, document.document_date)
        row = existing_by_index.get(order_index)

        common = dict(
            kind=_infer_kind(raw_order, target_type),
            title=_order_title(raw_order, target_type, target_subtype),
            order_type=raw_order.get("order_type"),
            target_document_type=target_type,
            target_document_subtype=target_subtype,
            target_research_area=raw_order.get("target_research_area"),
            target_specialty=raw_order.get("target_specialty"),
            due_date=due_date,
            due_source=due_source,
        )

        if row is None:
            db.add(Reminder(
                user_id=document.user_id,
                origin="auto",
                source_document_id=document.id,
                source_order_index=order_index,
                status="active",
                status_source="auto",
                **common,
            ))
        else:
            # Описательные поля обновляем всегда; статус/резолюцию/note не трогаем.
            # Срок, заданный пользователем вручную (due_source='manual'), сохраняем.
            if row.due_source == "manual":
                common.pop("due_date", None)
                common.pop("due_source", None)
            for field, value in common.items():
                setattr(row, field, value)

    # Убрать авто-строки, которых больше нет в orders и которые не трогал пользователь.
    stale_indexes = [
        idx for idx, row in existing_by_index.items()
        if idx not in seen_indexes and row.status_source != "manual"
    ]
    if stale_indexes:
        await db.execute(
            delete(Reminder).where(
                Reminder.source_document_id == document.id,
                Reminder.source_order_index.in_(stale_indexes),
            )
        )


async def _load_candidates(user_id: uuid.UUID, db: AsyncSession) -> List[Dict[str, Any]]:
    """Завершённые документы-кандидаты для авто-закрытия (как в orders_summary)."""
    result = await db.execute(
        select(DocumentModel).where(
            DocumentModel.user_id == user_id,
            DocumentModel.document_type.in_(list(FOLLOW_UP_DOCUMENT_TYPES)),
            DocumentModel.processing_status == "completed",
        )
    )
    candidate_docs = result.scalars().all()
    candidate_ids = [str(d.id) for d in candidate_docs if d.mongodb_metadata_id]

    meta_by_id: Dict[str, Dict[str, Any]] = {}
    if candidate_ids:
        cursor = document_metadata_collection.find(
            {"document_id": {"$in": candidate_ids}},
            {
                "document_id": 1,
                "classification.document_subtype": 1,
                "classification.research_area": 1,
                "classification.specialties": 1,
            },
        )
        for m in await cursor.to_list(length=len(candidate_ids)):
            classification = m.get("classification", {}) or {}
            meta_by_id[m.get("document_id")] = {
                "document_subtype": classification.get("document_subtype"),
                "research_area": classification.get("research_area"),
                "specialties": classification.get("specialties"),
            }

    candidates = []
    for d in candidate_docs:
        meta = meta_by_id.get(str(d.id), {})
        candidates.append({
            "id": d.id,
            "document_type": d.document_type,
            "document_date": d.document_date,
            "created_at": d.created_at,
            "title": d.original_filename,
            "document_subtype": meta.get("document_subtype"),
            "research_area": meta.get("research_area"),
            "specialties": meta.get("specialties"),
        })
    return candidates


def _reminder_as_order(row: Reminder) -> Dict[str, Any]:
    return {
        "title": row.title,
        "order_type": row.order_type,
        "target_document_type": row.target_document_type,
        "target_document_subtype": row.target_document_subtype,
        "target_research_area": row.target_research_area,
    }


def _find_match(row: Reminder, source_date: Optional[date], candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    order = _reminder_as_order(row)
    for candidate in candidates:
        if candidate["id"] == row.source_document_id:
            continue
        candidate_date = candidate.get("document_date")
        candidate_created = candidate.get("created_at")
        if source_date:
            if candidate_date and candidate_date < source_date:
                continue
            if not candidate_date and candidate_created and candidate_created.date() < source_date:
                continue
        if _order_matches_candidate(order, candidate):
            return candidate
    return None


async def list_reminders(
    user_id: uuid.UUID,
    db: AsyncSession,
    today: date,
    include_resolved: bool = False,
) -> List[Dict[str, Any]]:
    """Активные напоминания профиля с эскалацией, отсортированные по срочности.

    Авто-напоминания, для которых уже появился подходящий документ, считаются
    выполненными (read-time overlay) и в активный список не попадают.
    """
    result = await db.execute(select(Reminder).where(Reminder.user_id == user_id))
    reminders = result.scalars().all()

    # Данные документов-источников (заголовок/дата/специальность приёма) для отображения.
    source_ids = [r.source_document_id for r in reminders if r.source_document_id]
    source_docs: Dict[uuid.UUID, DocumentModel] = {}
    source_specialty_by_id: Dict[str, Optional[str]] = {}
    if source_ids:
        src_result = await db.execute(
            select(DocumentModel).where(DocumentModel.id.in_(source_ids))
        )
        source_docs = {d.id: d for d in src_result.scalars().all()}

        src_str_ids = [str(i) for i in source_ids]
        cursor = document_metadata_collection.find(
            {"document_id": {"$in": src_str_ids}},
            {"document_id": 1, "classification.specialties": 1},
        )
        for m in await cursor.to_list(length=len(src_str_ids)):
            specialties = (m.get("classification") or {}).get("specialties") or []
            source_specialty_by_id[m.get("document_id")] = ", ".join(specialties) if specialties else None

    candidates = await _load_candidates(user_id, db)

    items: List[Dict[str, Any]] = []
    for row in reminders:
        source_doc = source_docs.get(row.source_document_id) if row.source_document_id else None
        source_date = source_doc.document_date if source_doc else None

        # Эффективный статус: ручной приоритетнее; иначе read-time авто-закрытие.
        matched = None
        effective_status = row.status
        completed_document_id = row.completed_document_id
        if row.status_source != "manual" and row.status == "active":
            matched = _find_match(row, source_date, candidates)
            if matched:
                effective_status = "done"
                completed_document_id = matched["id"]

        if effective_status != "active" and not include_resolved:
            continue

        level, days_left = classify_urgency(row.due_date, today)
        items.append({
            "id": row.id,
            "origin": row.origin,
            "kind": row.kind,
            "title": row.title,
            "due_date": row.due_date,
            "urgency_level": level,
            "days_left": days_left,
            "status": effective_status,
            "target_document_type": row.target_document_type,
            "target_specialty": row.target_specialty,
            "note": row.note,
            "source_document_id": row.source_document_id,
            "source_document_title": source_doc.original_filename if source_doc else None,
            "source_document_date": source_date,
            "source_specialty": source_specialty_by_id.get(str(row.source_document_id)) if row.source_document_id else None,
            "completed_document_id": completed_document_id,
            "created_at": row.created_at,
        })

    items.sort(key=lambda it: (
        _URGENCY_RANK.get(it["urgency_level"], 9),
        it["days_left"] if it["days_left"] is not None else 10**6,
    ))
    return items


async def get_owned_reminder(reminder_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> Optional[Reminder]:
    result = await db.execute(
        select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id)
    )
    return result.scalar_one_or_none()


# Обратный маппинг статуса напоминания в контракт карточки документа
# (DocumentOrderStatus), чтобы UI карточки не менялся после унификации.
def _reminder_to_card_status(status: str, resolution: Optional[str]) -> str:
    if status == "active":
        return "pending"
    if status == "done":
        return "completed"
    return "incorrect" if resolution == "incorrect" else "not_required"


async def build_orders_summary_map(
    user_id: uuid.UUID,
    documents: List[DocumentModel],
    db: AsyncSession,
) -> Dict[str, Dict[str, Any]]:
    """orders_summary для карточек документов, собранный из строк reminders.

    Тот же контракт, что и прежняя реализация на Mongo-orders: статус карточки,
    is_active, автозакрытие (read-time overlay) и matched_document_*.
    """
    doc_ids = [d.id for d in documents]
    if not doc_ids:
        return {}

    result = await db.execute(
        select(Reminder).where(Reminder.source_document_id.in_(doc_ids))
    )
    reminders = result.scalars().all()
    if not reminders:
        return {}

    source_dates = {d.id: d.document_date for d in documents}
    candidates = await _load_candidates(user_id, db)

    by_doc: Dict[uuid.UUID, List[Reminder]] = {}
    for r in reminders:
        by_doc.setdefault(r.source_document_id, []).append(r)

    summaries: Dict[str, Dict[str, Any]] = {}
    for doc_id, rows in by_doc.items():
        items = []
        for r in sorted(rows, key=lambda x: x.source_order_index or 0):
            matched = None
            effective_status = r.status
            if r.status_source != "manual" and r.status == "active":
                matched = _find_match(r, source_dates.get(doc_id), candidates)
                if matched:
                    effective_status = "done"

            card_status = _reminder_to_card_status(effective_status, r.resolution)
            items.append({
                "order_index": r.source_order_index,
                "title": r.title,
                "order_type": r.order_type,
                "target_document_type": r.target_document_type,
                "target_document_subtype": r.target_document_subtype,
                "target_research_area": r.target_research_area,
                "status": card_status,
                "status_source": r.status_source,
                "is_active": card_status == "pending",
                "matched_document_id": matched["id"] if matched else None,
                "matched_document_date": matched.get("document_date") if matched else None,
                "matched_document_title": matched.get("title") if matched else None,
            })

        if items:
            summaries[str(doc_id)] = {
                "total": len(items),
                "completed": sum(1 for it in items if it["status"] == "completed"),
                "pending": sum(1 for it in items if it["status"] == "pending"),
                "dismissed": sum(1 for it in items if it["status"] in {"not_required", "incorrect"}),
                "items": items,
            }

    return summaries
