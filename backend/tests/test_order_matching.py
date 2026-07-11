"""Tests for order (referral) auto-matching in documents endpoint."""
import uuid
from datetime import date

from app.api.v1.endpoints.documents import (
    FOLLOW_UP_DOCUMENT_TYPES,
    _infer_order_target,
    _order_matches_candidate,
)


def _visit_candidate(specialties):
    return {
        "id": uuid.uuid4(),
        "document_type": "Прием врача",
        "document_date": date(2026, 6, 25),
        "created_at": None,
        "title": "cardio.pdf",
        "document_subtype": None,
        "research_area": None,
        "specialties": specialties,
    }


CONSULTATION_ORDER = {
    "title": "Консультация кардиолога",
    "order_type": "consultation",
    "target_document_type": "Прием врача",
    "target_document_subtype": None,
    "target_research_area": None,
}


def test_doctor_visit_is_follow_up_type():
    assert "Прием врача" in FOLLOW_UP_DOCUMENT_TYPES


def test_infer_target_for_consultation_without_explicit_type():
    target_type, _ = _infer_order_target(
        {"order_type": "consultation", "title": "Консультация невролога"}
    )
    assert target_type == "Прием врача"


def test_consultation_matches_visit_with_same_specialty():
    assert _order_matches_candidate(
        CONSULTATION_ORDER, _visit_candidate(["Кардиология"])
    )


def test_consultation_rejects_visit_with_other_specialty():
    assert not _order_matches_candidate(
        CONSULTATION_ORDER, _visit_candidate(["Офтальмология"])
    )


def test_consultation_soft_matches_visit_without_specialties():
    assert _order_matches_candidate(CONSULTATION_ORDER, _visit_candidate(None))


def test_generic_consultation_soft_matches_any_visit():
    order = {
        "title": "Повторная консультация врача",
        "order_type": "consultation",
        "target_document_type": "Прием врача",
    }
    assert _order_matches_candidate(order, _visit_candidate(["Кардиология"]))


def test_lab_order_does_not_match_doctor_visit():
    order = {
        "title": "Липидограмма",
        "order_type": "lab",
        "target_document_type": "Результаты анализа",
        "target_document_subtype": "Биохимический анализ крови",
    }
    assert not _order_matches_candidate(order, _visit_candidate(["Кардиология"]))


def test_lab_order_still_matches_lab_result():
    order = {
        "title": "Липидограмма",
        "order_type": "lab",
        "target_document_type": "Результаты анализа",
        "target_document_subtype": "Биохимический анализ крови",
    }
    candidate = {
        "id": uuid.uuid4(),
        "document_type": "Результаты анализа",
        "document_date": date(2026, 6, 20),
        "created_at": None,
        "title": "biochem.pdf",
        "document_subtype": "Биохимический анализ крови",
        "research_area": None,
        "specialties": None,
    }
    assert _order_matches_candidate(order, candidate)
