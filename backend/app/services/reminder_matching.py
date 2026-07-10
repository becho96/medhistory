"""Shared referral/order matching primitives.

Extracted from the documents endpoint so that both the document card
(orders_summary) and the reminders feature use one implementation of
target inference and candidate matching (auto-close).
"""
from typing import Optional, Dict, Any

ORDER_TARGET_TYPES = {
    "lab": "Результаты анализа",
    "analysis": "Результаты анализа",
    "instrumental": "Инструментальное исследование",
    "imaging": "Инструментальное исследование",
    "functional": "Функциональная диагностика",
    "consultation": "Прием врача",
}

FOLLOW_UP_DOCUMENT_TYPES = set(ORDER_TARGET_TYPES.values())

ORDER_KEYWORDS = [
    ("Результаты анализа", None, ["анализ", "кров", "моч", "кал", "гормон", "биохим", "бактериолог", "серолог"]),
    ("Инструментальное исследование", "УЗИ", ["узи", "эхо"]),
    ("Инструментальное исследование", "МРТ", ["мрт", "магнитно"]),
    ("Инструментальное исследование", "КТ", ["кт", "компьютерн"]),
    ("Инструментальное исследование", "Рентген", ["рентген", "флюорограф"]),
    ("Функциональная диагностика", "ЭКГ (электрокардиография)", ["экг", "электрокардиограф"]),
    ("Функциональная диагностика", "ЭЭГ (электроэнцефалография)", ["ээг", "электроэнцефалограф"]),
    ("Функциональная диагностика", "Холтер-мониторирование", ["холтер"]),
    ("Функциональная диагностика", "Спирометрия", ["спирометр"]),
    ("Функциональная диагностика", "ФГДС (фиброгастродуоденоскопия)", ["фгдс", "гастроскоп"]),
    ("Функциональная диагностика", "Колоноскопия", ["колоноскоп"]),
]

# Корни подобраны так, чтобы находиться и в названии специальности
# («Кардиология»), и в тексте направления («консультация кардиолога»).
SPECIALTY_KEYWORDS = [
    ("Психотерапия", ["психотерап"]),
    ("Психиатрия", ["психиатр"]),
    ("Физиотерапия", ["физиотерап"]),
    ("Гастроэнтерология", ["гастроэнтеролог"]),
    ("Оториноларингология", ["оториноларинголог", "отоларинголог", "лор"]),
    ("Травматология и ортопедия", ["травматолог", "ортопед"]),
    ("Кардиология", ["кардиолог"]),
    ("Неврология", ["невролог"]),
    ("Эндокринология", ["эндокринолог"]),
    ("Офтальмология", ["офтальмолог", "окулист"]),
    ("Урология", ["уролог"]),
    ("Гинекология", ["гинеколог"]),
    ("Дерматология", ["дерматолог", "дерматовенеролог"]),
    ("Онкология", ["онколог"]),
    ("Пульмонология", ["пульмонолог"]),
    ("Нефрология", ["нефролог"]),
    ("Ревматология", ["ревматолог"]),
    ("Гематология", ["гематолог"]),
    ("Аллергология и иммунология", ["аллерголог", "иммунолог"]),
    ("Инфекционные болезни", ["инфекцио"]),
    ("Маммология", ["маммолог"]),
    ("Флебология", ["флеболог"]),
    ("Проктология", ["проктолог"]),
    ("Стоматология", ["стоматолог"]),
    ("Педиатрия", ["педиатр"]),
    ("Хирургия", ["хирург"]),
    ("Терапия", ["терапевт", "терапия"]),
]


def _normalize_text(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _match_specialties(text: str) -> set:
    return {
        specialty
        for specialty, keywords in SPECIALTY_KEYWORDS
        if any(keyword in text for keyword in keywords)
    }


def _infer_order_target(order: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    target_type = order.get("target_document_type")
    target_subtype = order.get("target_document_subtype")
    order_type = _normalize_text(order.get("order_type"))
    title = _normalize_text(order.get("title"))

    if not target_type and order_type in ORDER_TARGET_TYPES:
        target_type = ORDER_TARGET_TYPES[order_type]

    for doc_type, subtype, keywords in ORDER_KEYWORDS:
        if any(keyword in title for keyword in keywords):
            target_type = target_type or doc_type
            if target_type == doc_type:
                target_subtype = target_subtype or subtype
            break

    return target_type, target_subtype


def _order_matches_candidate(order: Dict[str, Any], candidate: Dict[str, Any]) -> bool:
    target_type, target_subtype = _infer_order_target(order)
    if not target_type or candidate.get("document_type") != target_type:
        return False

    target_subtype_norm = _normalize_text(target_subtype)
    candidate_subtype_norm = _normalize_text(candidate.get("document_subtype"))
    if (
        target_subtype_norm
        and candidate_subtype_norm
        and target_subtype_norm != candidate_subtype_norm
        and target_subtype_norm not in candidate_subtype_norm
        and candidate_subtype_norm not in target_subtype_norm
    ):
        return False

    target_research_area = _normalize_text(order.get("target_research_area"))
    candidate_research_area = _normalize_text(candidate.get("research_area"))
    if (
        target_research_area
        and candidate_research_area
        and target_research_area != candidate_research_area
        and target_research_area not in candidate_research_area
        and candidate_research_area not in target_research_area
    ):
        return False

    if target_type == "Прием врача":
        order_specialties = _match_specialties(_normalize_text(order.get("title")))
        candidate_specialties = _match_specialties(
            _normalize_text(" ".join(candidate.get("specialties") or []))
        )
        if (
            order_specialties
            and candidate_specialties
            and order_specialties.isdisjoint(candidate_specialties)
        ):
            return False

    return True
