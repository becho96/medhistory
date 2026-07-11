"""Проекция «план лечения как граф» поверх documents + reminders.

Граф НЕ хранится отдельно — он выводится read-time:
- узлы-факты   — документы, участвующие в направлениях (источники и результаты);
- узлы-планы   — открытые напоминания как «фантомные» будущие шаги;
- рёбра        — направление «документ-источник → результат/план»;
- схождение    — несколько направлений с одной целью дают один узел (DAG);
- эпизод       — связная компонента графа направлений.

Эффективный статус и авто-закрытие переиспользуются из reminder_service
(single source of truth), детали узлов-документов добираются из Postgres+Mongo.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document as DocumentModel
from app.models.reminder import Reminder
from app.models.plan_override import PlanOverride
from app.db.mongodb import document_metadata_collection
from app.services.reminder_service import list_reminders

# document_type → тип узла графа
_DOC_TYPE_TO_KIND = {
    "Прием врача": "consultation",
    "Результаты анализа": "lab",
    "Инструментальное исследование": "instrumental",
    "Функциональная диагностика": "functional",
}


def _kind_from_doc_type(doc_type: Optional[str]) -> str:
    return _DOC_TYPE_TO_KIND.get(doc_type or "", "other")


def _normalize(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _phantom_signature(row: Optional[Reminder], item: Dict[str, Any]) -> str:
    """Ключ схождения открытых направлений: одинаковая цель → один узел.

    MVP: цель по типу/подтипу/области/специальности + нормализованный
    заголовок. Устойчивый канонический target_key — задача Фазы 2.
    """
    parts = [
        _normalize(item.get("target_document_type")),
        _normalize(getattr(row, "target_document_subtype", None)),
        _normalize(getattr(row, "target_research_area", None)),
        _normalize(item.get("target_specialty")),
        _normalize(item.get("title")),
    ]
    return "plan:" + "|".join(parts)


async def _load_node_documents(
    doc_ids: List[uuid.UUID], db: AsyncSession
) -> Dict[uuid.UUID, Dict[str, Any]]:
    """Детали документов-узлов: Postgres (тип/дата/файл) + Mongo (classification/summary)."""
    if not doc_ids:
        return {}

    result = await db.execute(select(DocumentModel).where(DocumentModel.id.in_(doc_ids)))
    docs = {d.id: d for d in result.scalars().all()}

    str_ids = [str(i) for i in doc_ids]
    meta: Dict[str, Dict[str, Any]] = {}
    cursor = document_metadata_collection.find(
        {"document_id": {"$in": str_ids}},
        {
            "document_id": 1,
            "classification.specialties": 1,
            "classification.document_subtype": 1,
            "classification.research_area": 1,
            "classification.doctor_name": 1,
            "extracted_data.summary": 1,
        },
    )
    for m in await cursor.to_list(length=len(str_ids)):
        classification = m.get("classification") or {}
        extracted = m.get("extracted_data") or {}
        meta[m.get("document_id")] = {
            "specialties": classification.get("specialties") or [],
            "document_subtype": classification.get("document_subtype"),
            "research_area": classification.get("research_area"),
            "doctor_name": classification.get("doctor_name"),
            "summary": extracted.get("summary"),
        }

    out: Dict[uuid.UUID, Dict[str, Any]] = {}
    for doc_id, d in docs.items():
        mm = meta.get(str(doc_id), {})
        specialties = mm.get("specialties") or []
        kind = _kind_from_doc_type(d.document_type)
        # Заголовок узла: для приёма — специальность, иначе подтип/тип.
        if kind == "consultation":
            title = ("Приём · " + specialties[0]) if specialties else "Приём врача"
        else:
            title = mm.get("document_subtype") or d.document_type or d.original_filename
        out[doc_id] = {
            "kind": kind,
            "title": title,
            "date": d.document_date,
            "doctor": mm.get("doctor_name"),
            "facility": d.medical_facility,
            "specialty": ", ".join(specialties) if specialties else None,
            "summary": mm.get("summary"),
            "document_type": d.document_type,
        }
    return out


class _UnionFind:
    def __init__(self) -> None:
        self.parent: Dict[str, str] = {}

    def add(self, x: str) -> None:
        self.parent.setdefault(x, x)

    def find(self, x: str) -> str:
        self.add(x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:  # path compression
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


async def build_plan_graph(
    user_id: uuid.UUID, db: AsyncSession, today: date
) -> Dict[str, Any]:
    """Собрать граф плана лечения профиля (проекция, без записи)."""
    items = await list_reminders(user_id, db, today, include_resolved=True)

    rows = (
        await db.execute(select(Reminder).where(Reminder.user_id == user_id))
    ).scalars().all()
    row_by_id = {r.id: r for r in rows}

    override_rows = (
        await db.execute(select(PlanOverride).where(PlanOverride.user_id == user_id))
    ).scalars().all()
    merges = [(o.anchor_key, o.other_key) for o in override_rows if o.kind == "merge" and o.other_key]
    # Переименования: последнее по времени на якорь побеждает.
    rename_by_key: Dict[str, str] = {}
    for o in sorted(override_rows, key=lambda x: x.created_at or datetime.min):
        if o.kind == "rename" and o.title:
            rename_by_key[o.anchor_key] = o.title

    # Документы-узлы: источники направлений + документы, закрывшие направления.
    doc_ids: set[uuid.UUID] = set()
    for it in items:
        if it.get("source_document_id"):
            doc_ids.add(it["source_document_id"])
        if it.get("completed_document_id"):
            doc_ids.add(it["completed_document_id"])
    doc_details = await _load_node_documents(list(doc_ids), db)

    nodes: Dict[str, Dict[str, Any]] = {}
    edges: Dict[tuple, Dict[str, Any]] = {}
    parent_count: Dict[str, int] = defaultdict(int)

    def ensure_doc_node(doc_id: uuid.UUID) -> Optional[str]:
        if doc_id not in doc_details:
            return None
        nid = f"doc:{doc_id}"
        if nid not in nodes:
            d = doc_details[doc_id]
            nodes[nid] = {
                "id": nid, "kind": d["kind"], "status": "done", "title": d["title"],
                "subtitle": d["doctor"] or d["specialty"], "date": d["date"], "due_date": None,
                "doctor": d["doctor"], "facility": d["facility"], "specialty": d["specialty"],
                "summary": d["summary"], "document_type": d["document_type"],
                "document_id": doc_id, "merge_count": 0,
            }
        return nid

    def ensure_phantom_node(it: Dict[str, Any], status: str) -> str:
        row = row_by_id.get(it["id"])
        nid = _phantom_signature(row, it)
        if nid not in nodes:
            nodes[nid] = {
                "id": nid,
                "kind": _kind_from_doc_type(it.get("target_document_type")),
                "status": status,
                "title": it.get("title") or "Назначение",
                "subtitle": it.get("target_specialty"),
                "date": None,
                "due_date": it.get("due_date"),
                "doctor": None, "facility": None,
                "specialty": it.get("target_specialty"),
                "summary": None,
                "document_type": it.get("target_document_type"),
                "document_id": None, "merge_count": 0,
            }
        else:
            # Схождение: у разных направлений может отличаться срочность —
            # оставляем более срочный (overdue приоритетнее planned).
            if status == "overdue":
                nodes[nid]["status"] = "overdue"
        return nid

    for it in items:
        if it.get("status") == "dismissed":
            continue

        src_id = it.get("source_document_id")
        src_node = ensure_doc_node(src_id) if src_id else None

        if it.get("status") == "done" and it.get("completed_document_id"):
            tgt_node = ensure_doc_node(it["completed_document_id"])
        elif it.get("status") == "done":
            tgt_node = ensure_phantom_node(it, "done")  # закрыто вручную, без документа
        else:
            status = "overdue" if it.get("urgency_level") == "overdue" else "planned"
            tgt_node = ensure_phantom_node(it, status)

        if src_node and tgt_node and src_node != tgt_node:
            key = (src_node, tgt_node)
            if key not in edges:
                edges[key] = {"source": src_node, "target": tgt_node, "kind": it.get("kind")}
                parent_count[tgt_node] += 1

    for nid, cnt in parent_count.items():
        if nid in nodes:
            nodes[nid]["merge_count"] = cnt

    # Эпизоды = связные компоненты (неориентированно).
    uf = _UnionFind()
    for nid in nodes:
        uf.add(nid)
    for e in edges.values():
        uf.union(e["source"], e["target"])
    # Ручное слияние: принудительный union (только для существующих узлов).
    for a, b in merges:
        if a in nodes and b in nodes:
            uf.union(a, b)

    comps: Dict[str, List[str]] = defaultdict(list)
    for nid in nodes:
        comps[uf.find(nid)].append(nid)

    episodes: List[Dict[str, Any]] = []
    for member_ids in comps.values():
        member_nodes = [nodes[i] for i in member_ids]
        # Корень: узел без входящих направлений; приоритет приёму и ранней дате.
        roots = [n for n in member_nodes if parent_count.get(n["id"], 0) == 0]
        roots.sort(key=lambda n: (
            0 if n["kind"] == "consultation" else 1,
            n["date"] or date.max,
        ))
        root = roots[0] if roots else member_nodes[0]
        dates = [n["date"] for n in member_nodes if n["date"]]

        # Ручное имя: якорь на корень, иначе на любой узел компоненты.
        custom_title = rename_by_key.get(root["id"])
        if not custom_title:
            for mid in member_ids:
                if mid in rename_by_key:
                    custom_title = rename_by_key[mid]
                    break
        if custom_title:
            title = custom_title
        else:
            title = root["title"]
            if root["date"]:
                title += " · " + root["date"].strftime("%d.%m.%Y")

        episodes.append({
            "id": root["id"],
            "title": title,
            "root_id": root["id"],
            "custom_name": bool(custom_title),
            "node_ids": member_ids,
            "done": sum(1 for n in member_nodes if n["status"] == "done"),
            "total": len(member_nodes),
            "start_date": min(dates) if dates else None,
            "end_date": max(dates) if dates else None,
        })

    episodes.sort(key=lambda e: (e["start_date"] or date.max))

    return {
        "episodes": episodes,
        "nodes": list(nodes.values()),
        "edges": list(edges.values()),
        "overrides": [
            {"id": o.id, "kind": o.kind, "anchor_key": o.anchor_key, "other_key": o.other_key, "title": o.title}
            for o in override_rows
        ],
        "generated_at": datetime.utcnow(),
    }
