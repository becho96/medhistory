"""Seed a rich demo medical history into a fresh demo account.

Runs INSIDE the backend container (has app deps + DB access), calling the real
`DocumentService.upload_document` service layer so every file goes through the
production pipeline (MinIO + Postgres + Mongo + Gemini classification/vision +
lab extraction + embeddings) while bypassing the HTTP upload quota.

After each upload it PINS the structured classification, injects deterministic
`lab_results`, and reconciles reminders from the manifest's `orders` — so the
demo structure (two disjoint plan episodes + three forgotten referrals) is
deterministic even though document *reading* is done by the real LLM.

Idempotent-ish: documents already present (by filename) are skipped. For a
clean rebuild run teardown_demo.py first.

Usage (inside the backend container, cwd /app):
    python -m scripts.demo_seed.seed_demo
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))  # /app

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import AsyncSessionLocal
from app.db.mongodb import document_metadata_collection
from app.models.user import User, GenderEnum
from app.models.family import FamilyRelation, RelationType
from app.models.consent import UserConsent
from app.models.document import Document
from app.core.security import get_password_hash
from app.services.document_service import DocumentService
from app.services.reminder_service import sync_document_reminders, list_reminders
from app.services import treatment_plan

from . import config as C

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

_CONTENT_TYPE = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
}


class _Upload:
    """Minimal Starlette-UploadFile shim (DocumentService reads filename /
    content_type / await read())."""

    def __init__(self, content: bytes, filename: str, content_type: str):
        self._content = content
        self.filename = filename
        self.content_type = content_type

    async def read(self) -> bytes:  # noqa: D401
        return self._content


# ---------------------------------------------------------------------------
# lab flags
# ---------------------------------------------------------------------------
def _num(text: str):
    m = re.search(r"-?\d+(?:[.,]\d+)?", text or "")
    return float(m.group().replace(",", ".")) if m else None


def _flag(value: str, ref: str) -> str:
    v = _num(value)
    if v is None:
        return "N"
    ref = (ref or "").strip()
    rng = re.match(r"^\s*(-?\d+(?:[.,]\d+)?)\s*[-–]\s*(-?\d+(?:[.,]\d+)?)", ref)
    if rng:
        lo, hi = float(rng.group(1).replace(",", ".")), float(rng.group(2).replace(",", "."))
        return "L" if v < lo else "H" if v > hi else "N"
    if ref.startswith("<"):
        hi = _num(ref)
        return "H" if hi is not None and v > hi else "N"
    if ref.startswith(">"):
        lo = _num(ref)
        return "L" if lo is not None and v < lo else "N"
    return "N"


def _lab_result(row: list) -> dict:
    name, value, unit, ref = (row + ["", "", "", ""])[:4]
    return {
        "test_name": name,
        "value": value,
        "unit": unit,
        "reference_range": ref,
        "flag": _flag(value, ref),
    }


def _to_ai_order(o: dict) -> dict:
    order = {
        "title": o["title"],
        "kind": o["kind"],
        "order_type": o["order_type"],
        "target_document_type": o["target_document_type"],
        "target_document_subtype": o.get("target_document_subtype"),
        "target_research_area": o.get("target_research_area"),
        "target_specialty": o.get("target_specialty"),
    }
    if o.get("due_date"):
        order["due_date"] = o["due_date"]
    elif o.get("due_after_days"):
        order["due_after"] = {"amount": o["due_after_days"], "unit": "day"}
    return order


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------
async def get_or_create_owner(db: AsyncSession) -> tuple[User, bool]:
    res = await db.execute(select(User).where(User.email == C.OWNER_EMAIL))
    user = res.scalar_one_or_none()
    if user:
        return user, False
    now = datetime.now(timezone.utc)
    user = User(
        email=C.OWNER_EMAIL,
        password_hash=get_password_hash(C.OWNER_PASSWORD),
        full_name=C.OWNER_NAME,
        birth_date=C.OWNER_BIRTH,
        gender=GenderEnum.female,
        is_active=True,
        subscription_tier="pro",
        pro_expires_at=now + timedelta(days=3650),
        pro_source="admin",
        signup_source="demo",
    )
    db.add(user)
    await db.flush()
    for ctype, version in C.CONSENT_HASHES.items():
        db.add(UserConsent(user_id=user.id, consent_type=ctype, document_version=version))
    await db.commit()
    await db.refresh(user)
    return user, True


async def get_or_create_child(db: AsyncSession, owner: User) -> tuple[User, bool]:
    res = await db.execute(
        select(User)
        .join(FamilyRelation, FamilyRelation.member_id == User.id)
        .where(FamilyRelation.owner_id == owner.id, User.full_name == C.CHILD_NAME)
    )
    child = res.scalar_one_or_none()
    if child:
        return child, False
    child = User(
        full_name=C.CHILD_NAME,
        birth_date=C.CHILD_BIRTH,
        gender=GenderEnum.female,
        is_active=True,
        subscription_tier="free",
    )
    db.add(child)
    await db.flush()
    db.add(FamilyRelation(owner_id=owner.id, member_id=child.id,
                          relation_type=RelationType.CHILD))
    await db.commit()
    await db.refresh(child)
    return child, True


# ---------------------------------------------------------------------------
# per-document
# ---------------------------------------------------------------------------
async def _existing_filenames(db: AsyncSession, user_id) -> set[str]:
    res = await db.execute(
        select(Document.original_filename).where(Document.user_id == user_id)
    )
    return set(res.scalars().all())


async def pin_and_reconcile(db: AsyncSession, doc: Document, entry: dict,
                            patient_name: str) -> None:
    # 1. Pin Postgres columns deterministically.
    doc.document_type = entry["document_type"]
    doc.document_date = date.fromisoformat(entry["date"])
    doc.patient_name = patient_name
    doc.medical_facility = entry["clinic"]
    doc.processing_status = "completed"
    await db.flush()

    # 2. Merge / upsert MongoDB metadata (keep AI reading, pin classification).
    existing = await document_metadata_collection.find_one({"document_id": str(doc.id)}) or {}
    classification = dict(existing.get("classification") or {})
    classification.update({
        "document_subtype": entry.get("document_subtype"),
        "research_area": entry.get("research_area"),
        "specialties": entry.get("specialties"),
        "doctor_name": entry.get("doctor"),
        "medical_facility": entry["clinic"],
        "document_language": "ru",
    })
    extracted = dict(existing.get("extracted_data") or {})
    if not extracted.get("full_text"):
        extracted["full_text"] = entry.get("body", "")
        extracted["full_text_source"] = "seed_fallback"
    if not extracted.get("summary"):
        extracted["summary"] = _fallback_summary(entry)
    if entry.get("lab_rows"):
        extracted["lab_results"] = [_lab_result(r) for r in entry["lab_rows"]]

    now = datetime.utcnow()
    await document_metadata_collection.update_one(
        {"document_id": str(doc.id)},
        {
            "$set": {
                "document_id": str(doc.id),
                "user_id": str(doc.user_id),
                "classification": classification,
                "extracted_data": extracted,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    if not doc.mongodb_metadata_id:
        meta = await document_metadata_collection.find_one({"document_id": str(doc.id)}, {"_id": 1})
        if meta:
            doc.mongodb_metadata_id = str(meta["_id"])
    await db.flush()

    # 3. Reconcile reminders from the manifest orders (deterministic structure).
    orders = [_to_ai_order(o) for o in entry.get("orders", [])]
    await sync_document_reminders(doc, orders, db)
    await db.commit()


def _fallback_summary(entry: dict) -> str:
    parts = [entry["document_type"], entry["clinic"], entry["date"]]
    if entry.get("doctor"):
        parts.append(entry["doctor"])
    return " · ".join(str(p) for p in parts)


async def seed_document(db: AsyncSession, entry: dict, user_id, patient_name: str) -> str:
    path = OUT / entry["filename"]
    content = path.read_bytes()
    ext = entry["filename"].rsplit(".", 1)[-1].lower()
    shim = _Upload(content, entry["filename"], _CONTENT_TYPE.get(ext, "application/octet-stream"))
    try:
        doc = await DocumentService.upload_document(shim, user_id, db)
    except Exception as exc:  # AI/dup/other — recover the row if it exists
        await db.rollback()
        res = await db.execute(
            select(Document).where(
                Document.user_id == user_id,
                Document.original_filename == entry["filename"],
            )
        )
        doc = res.scalar_one_or_none()
        if doc is None:
            return f"FAIL {entry['code']} {entry['filename']}: {exc}"
    await pin_and_reconcile(db, doc, entry, patient_name)
    status = "ok"
    return f"  {entry['code']:4} {entry['document_type']:30} {entry['date']}  {status}"


# ---------------------------------------------------------------------------
# verification
# ---------------------------------------------------------------------------
async def verify(db: AsyncSession, owner: User) -> None:
    today = date.today()
    print("\n=== VERIFICATION (owner) ===")
    plan = await treatment_plan.build_plan_graph(owner.id, db, today)
    episodes = plan.get("episodes", [])
    print(f"Plan episodes: {len(episodes)}")
    for ep in episodes:
        title = ep.get("custom_title") or ep.get("title") or ep.get("id")
        print(f"  · {title}  (nodes: {len(ep.get('node_ids', ep.get('nodes', [])) or [])})")

    reminders = await list_reminders(owner.id, db, today, include_resolved=True)
    active = [r for r in reminders if r.get("status") == "active"]
    done = [r for r in reminders if r.get("status") == "done"]
    overdue = [r for r in active if r.get("urgency_level") == "overdue"]
    print(f"Reminders: total={len(reminders)} closed={len(done)} "
          f"active={len(active)} overdue={len(overdue)}")
    print("Active (unclosed) referrals:")
    for r in active:
        print(f"  · [{r.get('urgency_level')}] {r.get('title')}  "
              f"→ {r.get('target_specialty') or r.get('target_document_type') or ''} "
              f"(due {r.get('due_date')})")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
async def main() -> None:
    index = json.loads((OUT / "index.json").read_text(encoding="utf-8"))
    # optional smoke-test filter: --codes A01,A02,B01,F01,C08
    only = None
    for arg in sys.argv[1:]:
        if arg.startswith("--codes="):
            only = {c.strip() for c in arg.split("=", 1)[1].split(",") if c.strip()}
    if only:
        index = [e for e in index if e["code"] in only]
    print(f"Loaded manifest index: {len(index)} documents"
          + (f" (filtered to {sorted(only)})" if only else ""))

    async with AsyncSessionLocal() as db:  # type: AsyncSession
        owner, created_o = await get_or_create_owner(db)
        child, created_c = await get_or_create_child(db, owner)
        print(f"Owner:  {owner.email}  id={owner.id}  ({'created' if created_o else 'exists'})")
        print(f"Child:  {C.CHILD_NAME}  id={child.id}  ({'created' if created_c else 'exists'})")

        by_profile = {"owner": (owner.id, C.OWNER_PATIENT), "child": (child.id, C.CHILD_PATIENT)}
        existing = {
            "owner": await _existing_filenames(db, owner.id),
            "child": await _existing_filenames(db, child.id),
        }

        print("\n=== SEEDING DOCUMENTS ===")
        n_seeded = n_skipped = 0
        for entry in index:
            profile = entry["profile"]
            user_id, patient_name = by_profile[profile]
            if entry["filename"] in existing[profile]:
                n_skipped += 1
                continue
            line = await seed_document(db, entry, user_id, patient_name)
            print(line)
            if line.strip().startswith("FAIL"):
                pass
            else:
                n_seeded += 1

        print(f"\nSeeded: {n_seeded} | Skipped(existing): {n_skipped}")
        await verify(db, owner)
        print("\nDONE.")
        print(f"Login: {C.OWNER_EMAIL} / {C.OWNER_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
