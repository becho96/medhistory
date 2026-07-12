"""Declarative manifest of the demo medical history (~60 documents).

Two structurally-disjoint care tracks over ~24 months:
  * Track A — gastroenterology (ЖКТ): therapist → gastroenterologist → ФГДС →
    H. pylori → treatment → follow-ups.
  * Track B — phlebology / vascular: phlebologist → duplex ultrasound of leg
    veins → coagulogram → follow-ups.

Plus standalone background documents (annual check-ups, screening, misc
certificates) that give variety and multiple clinics but do not form referral
chains, and a family child profile.

Each entry additionally carries the *expected* classification and the
*expected* referrals (`orders`). The seed driver pins classification and
reconciles reminders to these after the AI has read each file, so the demo
structure (2 disjoint plan episodes + 3 forgotten referrals) is deterministic
even though document reading itself goes through the real Gemini pipeline.
"""
from __future__ import annotations

from typing import Any

from . import templates as T

PATIENT_OWNER = "Соколова О.Н."
PATIENT_CHILD = "Соколова С.А."

# --- clinics -----------------------------------------------------------------
SM = "СМ-Клиника"
MEDSI = "Медси"
K31 = "Клиника К+31"
POLY = "Городская поликлиника № 180"
INVITRO = "Лаборатория ИНВИТРО"
GEMOTEST = "Лаборатория Гемотест"
HELIX = "Лаборатория Хеликс"
MRTE = "Центр диагностики МРТ-Эксперт"
FANTASY = "Детская клиника «Фэнтези»"

# --- doctors -----------------------------------------------------------------
DR_THERAPIST = "Иванова Е.П."
DR_GASTRO = "Петров С.А."
DR_PHLEBO = "Смирнова О.В."
DR_OPHTH = "Кузнецова М.И."
DR_ENT = "Волков Д.Н."
DR_DERMA = "Орлова Т.В."
DR_GYN = "Никитина А.Р."
DR_FUNC = "Морозов В.Г."
DR_RAD = "Лебедев К.С."
DR_PED = "Зайцева Н.Ю."


def _order(kind: str, title: str, order_type: str, target_type: str, *,
           subtype: str | None = None, area: str | None = None,
           specialty: str | None = None, due_after_days: int | None = None,
           due_date: str | None = None) -> dict[str, Any]:
    return {
        "kind": kind,
        "title": title,
        "order_type": order_type,
        "target_document_type": target_type,
        "target_document_subtype": subtype,
        "target_research_area": area,
        "target_specialty": specialty,
        "due_after_days": due_after_days,
        "due_date": due_date,
    }


def _doc(code: str, profile: str, date: str, doc_type: str, clinic: str,
         doctor: str | None, built: tuple, *, fmt: str = "pdf",
         handwritten: bool = False, subtype: str | None = None,
         area: str | None = None, specialty: list[str] | None = None,
         orders: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    # lab() returns a 3-tuple (title, body, rows); others return (title, body).
    lab_rows: list | None = None
    if len(built) == 3:
        title, body, lab_rows = built
    else:
        title, body = built
    return {
        "code": code,
        "profile": profile,
        "date": date,
        "document_type": doc_type,
        "document_subtype": subtype,
        "research_area": area,
        "specialties": specialty,
        "clinic": clinic,
        "doctor": doctor,
        "title": title,
        "body": body,
        "lab_rows": lab_rows,
        "format": fmt,
        "handwritten": handwritten,
        "orders": orders or [],
    }


def build_manifest() -> list[dict[str, Any]]:
    P = PATIENT_OWNER
    docs: list[dict[str, Any]] = []

    # =====================================================================
    # BACKGROUND — annual check-up #1 (2024-07)  [standalone, no chains]
    # =====================================================================
    docs.append(_doc(
        "C01", "owner", "2024-07-15", "Прием врача", POLY, DR_THERAPIST,
        T.appointment(
            clinic=POLY, doc_date="2024-07-15", patient=P, doctor=DR_THERAPIST,
            specialty_label="Терапия",
            complaint="жалоб активно не предъявляет, профилактический осмотр (диспансеризация).",
            anamnesis="хронические заболевания отрицает. Наследственность по ССЗ отягощена.",
            exam="состояние удовлетворительное. АД 128/82 мм рт.ст. ЧСС 74. ИМТ 26,4.",
            diagnosis="Здорова. Группа здоровья II. Пограничная гиперхолестеринемия.",
            icd="Z00.0",
            treatment=["Модификация образа жизни, гиполипидемическая диета."],
        ),
        specialty=["Терапия"],
    ))
    docs.append(_doc(
        "C02", "owner", "2024-07-15", "Функциональная диагностика", POLY, DR_FUNC,
        T.functional(
            clinic=POLY, doc_date="2024-07-15", patient=P, doctor=DR_FUNC,
            study="ЭКГ (электрокардиография)",
            protocol="Ритм синусовый, регулярный. ЧСС 72 уд/мин. ЭОС нормальная. Нарушений проводимости не выявлено.",
            conclusion="Вариант нормы.",
        ),
        subtype="ЭКГ (электрокардиография)",
    ))
    docs.append(_doc(
        "C03", "owner", "2024-07-16", "Инструментальное исследование", POLY, DR_RAD,
        T.imaging(
            clinic=POLY, doc_date="2024-07-16", patient=P, doctor=DR_RAD,
            modality="Флюорография", area="Грудная клетка",
            protocol="Лёгочные поля прозрачны, очаговых и инфильтративных теней нет. Корни структурны. Синусы свободны. Сердце в норме.",
            conclusion="Патологии органов грудной клетки не выявлено.",
        ),
        subtype="Флюорография", area="Грудная клетка",
    ))
    docs.append(_doc(
        "C04", "owner", "2024-07-15", "Результаты анализа", INVITRO, None,
        T.lab(
            clinic=INVITRO, doc_date="2024-07-15", patient=P, doctor=None,
            panel="Общий анализ крови",
            rows=[
                ("Гемоглобин", "116", "г/л", "120 - 140"),
                ("Эритроциты", "4.2", "10^12/л", "3.9 - 4.7"),
                ("Лейкоциты", "6.1", "10^9/л", "4.0 - 9.0"),
                ("Тромбоциты", "245", "10^9/л", "180 - 320"),
                ("СОЭ", "12", "мм/ч", "2 - 20"),
                ("Гематокрит", "36", "%", "35 - 45"),
            ],
            conclusion="Гемоглобин ниже референса — лёгкая анемия.",
        ),
        subtype="Общий анализ крови",
    ))
    docs.append(_doc(
        "C05", "owner", "2024-07-15", "Результаты анализа", INVITRO, None,
        T.lab(
            clinic=INVITRO, doc_date="2024-07-15", patient=P, doctor=None,
            panel="Общий анализ мочи",
            rows=[
                ("Цвет", "соломенно-жёлтый", "", "соломенно-жёлтый"),
                ("Плотность", "1018", "", "1010 - 1025"),
                ("pH", "6.0", "", "5.0 - 7.0"),
                ("Белок", "не обнаружен", "", "не обнаружен"),
                ("Лейкоциты", "2-3", "в п/з", "0 - 5"),
            ],
            conclusion="Без патологии.",
        ),
        subtype="Общий анализ мочи",
    ))
    docs.append(_doc(
        "C06", "owner", "2024-07-15", "Результаты анализа", INVITRO, None,
        T.lab(
            clinic=INVITRO, doc_date="2024-07-15", patient=P, doctor=None,
            panel="Биохимический анализ крови",
            rows=[
                ("Глюкоза", "5.9", "ммоль/л", "3.9 - 6.1"),
                ("АЛТ", "22", "Ед/л", "0 - 34"),
                ("АСТ", "24", "Ед/л", "0 - 31"),
                ("Билирубин общий", "12.4", "мкмоль/л", "3.4 - 20.5"),
                ("Креатинин", "72", "мкмоль/л", "53 - 97"),
            ],
            conclusion="Показатели в пределах нормы.",
        ),
        subtype="Биохимический анализ крови",
    ))
    docs.append(_doc(
        "C07", "owner", "2024-07-20", "Результаты анализа", INVITRO, None,
        T.lab(
            clinic=INVITRO, doc_date="2024-07-20", patient=P, doctor=None,
            panel="Липидный профиль",
            rows=[
                ("Холестерин общий", "6.3", "ммоль/л", "< 5.2"),
                ("ЛПНП (LDL)", "4.2", "ммоль/л", "< 3.0"),
                ("ЛПВП (HDL)", "1.3", "ммоль/л", "> 1.2"),
                ("Триглицериды", "1.9", "ммоль/л", "< 1.7"),
            ],
            conclusion="Гиперхолестеринемия, повышен ЛПНП.",
        ),
        subtype="Биохимический анализ крови",
    ))

    # =====================================================================
    # TRACK A — gastroenterology (ЖКТ)
    # =====================================================================
    docs.append(_doc(
        "A01", "owner", "2024-08-05", "Прием врача", SM, DR_THERAPIST,
        T.appointment(
            clinic=SM, doc_date="2024-08-05", patient=P, doctor=DR_THERAPIST,
            specialty_label="Терапия",
            complaint="боли и жжение в эпигастрии натощак и после еды, изжога в течение месяца.",
            anamnesis="погрешности в питании, стрессовая нагрузка. Ранее не обследовалась.",
            exam="язык обложен белым налётом. Живот мягкий, болезненный в эпигастрии.",
            diagnosis="Функциональная диспепсия. Подозрение на хронический гастрит.",
            icd="K30",
            treatment=["Ингибитор протонной помпы 20 мг утром 14 дней.",
                       "Дробное питание, исключить острое и жирное."],
            referrals=[
                "Консультация врача-гастроэнтеролога в течение 2 недель.",
                "Контроль общего анализа крови через 1 месяц.",
                "Консультация врача-эндокринолога в плановом порядке в течение 1 месяца (по поводу пограничной гликемии).",
            ],
        ),
        specialty=["Терапия"],
        orders=[
            _order("referral_specialist", "Консультация гастроэнтеролога",
                   "consultation", "Прием врача", specialty="Гастроэнтерология",
                   due_after_days=14),
            _order("referral_research", "Контроль общего анализа крови",
                   "lab", "Результаты анализа", subtype="Общий анализ крови",
                   due_after_days=30),
            # UNCLOSED #1 — endocrinologist consult, never fulfilled
            _order("referral_specialist", "Консультация эндокринолога",
                   "consultation", "Прием врача", specialty="Эндокринология",
                   due_after_days=30),
        ],
    ))
    docs.append(_doc(
        "A02", "owner", "2024-08-28", "Результаты анализа", GEMOTEST, None,
        T.lab(
            clinic=GEMOTEST, doc_date="2024-08-28", patient=P, doctor=None,
            panel="Общий анализ крови",
            rows=[
                ("Гемоглобин", "119", "г/л", "120 - 140"),
                ("Эритроциты", "4.3", "10^12/л", "3.9 - 4.7"),
                ("Лейкоциты", "6.4", "10^9/л", "4.0 - 9.0"),
                ("Тромбоциты", "251", "10^9/л", "180 - 320"),
                ("СОЭ", "14", "мм/ч", "2 - 20"),
            ],
            conclusion="Сохраняется погранично низкий гемоглобин.",
        ),
        subtype="Общий анализ крови",
    ))
    docs.append(_doc(
        "A03", "owner", "2024-08-20", "Прием врача", SM, DR_GASTRO,
        T.appointment(
            clinic=SM, doc_date="2024-08-20", patient=P, doctor=DR_GASTRO,
            specialty_label="Гастроэнтерология",
            complaint="боли в эпигастрии, изжога, тяжесть после еды.",
            anamnesis="направлена терапевтом. Приём ИПП с частичным эффектом.",
            exam="живот мягкий, болезненность в эпигастрии и пилородуоденальной зоне.",
            diagnosis="Хронический гастрит, обострение. Гастроэзофагеальная рефлюксная болезнь.",
            icd="K29.5",
            treatment=["Продолжить ИПП 20 мг 2 раза в день до результатов обследования."],
            referrals=[
                "Направление на ФГДС (фиброгастродуоденоскопию).",
                "Анализ на Helicobacter pylori (IgG).",
                "УЗИ органов брюшной полости в течение 1 месяца.",
            ],
        ),
        specialty=["Гастроэнтерология"],
        orders=[
            _order("referral_research", "ФГДС", "functional",
                   "Функциональная диагностика",
                   subtype="ФГДС (фиброгастродуоденоскопия)", due_after_days=14),
            _order("referral_research", "Анализ на Helicobacter pylori",
                   "lab", "Результаты анализа", subtype="Серологический анализ",
                   due_after_days=14),
            _order("follow_up_appointment", "Повторный приём гастроэнтеролога после обследования",
                   "consultation", "Прием врача", specialty="Гастроэнтерология",
                   due_after_days=30),
            # UNCLOSED #2 — abdominal ultrasound, never done
            _order("referral_research", "УЗИ органов брюшной полости",
                   "instrumental", "Инструментальное исследование",
                   subtype="УЗИ", area="Брюшная полость", due_after_days=30),
        ],
    ))
    docs.append(_doc(
        "A04", "owner", "2024-09-03", "Функциональная диагностика", MRTE, DR_GASTRO,
        T.functional(
            clinic=MRTE, doc_date="2024-09-03", patient=P, doctor=DR_GASTRO,
            study="ФГДС (фиброгастродуоденоскопия)",
            protocol="Пищевод свободно проходим, слизистая розовая. Кардия смыкается не полностью. "
                     "Желудок: слизистая антрального отдела гиперемирована, отёчна, единичные эрозии. "
                     "Луковица ДПК без особенностей. Выполнен быстрый уреазный тест.",
            conclusion="Эрозивный гастрит антрального отдела. Недостаточность кардии. Уреазный тест положительный.",
        ),
        subtype="ФГДС (фиброгастродуоденоскопия)",
    ))
    docs.append(_doc(
        "A05", "owner", "2024-09-06", "Результаты анализа", GEMOTEST, None,
        T.lab(
            clinic=GEMOTEST, doc_date="2024-09-06", patient=P, doctor=None,
            panel="Антитела к Helicobacter pylori, IgG",
            rows=[
                ("Helicobacter pylori, IgG", "3.6", "Ед/мл", "< 0.9"),
            ],
            conclusion="Положительно. Инфицирование Helicobacter pylori.",
        ),
        subtype="Серологический анализ",
    ))
    docs.append(_doc(
        "A06", "owner", "2024-09-18", "Прием врача", SM, DR_GASTRO,
        T.appointment(
            clinic=SM, doc_date="2024-09-18", patient=P, doctor=DR_GASTRO,
            specialty_label="Гастроэнтерология",
            complaint="сохраняется дискомфорт в эпигастрии, но менее выражен.",
            anamnesis="по ФГДС — эрозивный гастрит, H. pylori положительный.",
            exam="живот мягкий, умеренная болезненность в эпигастрии.",
            diagnosis="Хронический эрозивный гастрит, ассоциированный с H. pylori.",
            icd="K29.5",
            treatment=[
                "Эрадикационная терапия 14 дней: ИПП + амоксициллин + кларитромицин.",
                "Ребамипид 100 мг 3 раза в день 4 недели.",
            ],
            referrals=[
                "Контроль общего и биохимического анализа крови через 1,5 месяца.",
                "Повторный приём гастроэнтеролога через 3 месяца.",
            ],
        ),
        specialty=["Гастроэнтерология"],
        orders=[
            _order("referral_research", "Контроль биохимического анализа крови",
                   "lab", "Результаты анализа",
                   subtype="Биохимический анализ крови", due_after_days=45),
            _order("follow_up_appointment", "Повторный приём гастроэнтеролога",
                   "consultation", "Прием врача", specialty="Гастроэнтерология",
                   due_after_days=90),
        ],
    ))
    docs.append(_doc(
        "A07", "owner", "2024-11-06", "Результаты анализа", INVITRO, None,
        T.lab(
            clinic=INVITRO, doc_date="2024-11-06", patient=P, doctor=None,
            panel="Биохимический анализ крови",
            rows=[
                ("Глюкоза", "5.7", "ммоль/л", "3.9 - 6.1"),
                ("АЛТ", "26", "Ед/л", "0 - 34"),
                ("АСТ", "25", "Ед/л", "0 - 31"),
                ("Билирубин общий", "11.8", "мкмоль/л", "3.4 - 20.5"),
                ("Железо сывороточное", "9.1", "мкмоль/л", "9.0 - 30.4"),
            ],
            conclusion="Без значимых отклонений, железо на нижней границе.",
        ),
        subtype="Биохимический анализ крови",
    ))
    docs.append(_doc(
        "A08", "owner", "2024-12-20", "Прием врача", SM, DR_GASTRO,
        T.appointment(
            clinic=SM, doc_date="2024-12-20", patient=P, doctor=DR_GASTRO,
            specialty_label="Гастроэнтерология",
            complaint="жалоб практически нет, изжога не беспокоит.",
            anamnesis="завершена эрадикационная терапия, переносимость хорошая.",
            exam="живот безболезненный.",
            diagnosis="Хронический гастрит, ремиссия. Состояние после эрадикации H. pylori.",
            icd="K29.5",
            treatment=["Диспансерное наблюдение. При необходимости ИПП по требованию."],
        ),
        specialty=["Гастроэнтерология"],
    ))

    # =====================================================================
    # TRACK B — phlebology / vascular (сосуды)
    # =====================================================================
    docs.append(_doc(
        "B01", "owner", "2024-10-10", "Прием врача", MEDSI, DR_PHLEBO,
        T.appointment(
            clinic=MEDSI, doc_date="2024-10-10", patient=P, doctor=DR_PHLEBO,
            specialty_label="Флебология",
            complaint="тяжесть, отёчность и ноющие боли в ногах к вечеру, видимые вены на левой голени.",
            anamnesis="стоячая работа, две беременности в анамнезе. Наследственность по варикозу.",
            exam="варикозно расширенные вены в бассейне БПВ слева, отёк голеней к вечеру, трофических нарушений нет.",
            diagnosis="Варикозная болезнь нижних конечностей. Хроническая венозная недостаточность C2.",
            icd="I83.9",
            treatment=["Компрессионный трикотаж 2 класса.",
                       "Венотоники (диосмин) 2 месяца."],
            referrals=[
                "УЗДС (дуплексное сканирование) вен нижних конечностей в течение 2 недель.",
                "Коагулограмма.",
                "Консультация сосудистого хирурга в течение 1 месяца.",
            ],
        ),
        specialty=["Флебология"],
        orders=[
            _order("referral_research", "УЗДС вен нижних конечностей",
                   "instrumental", "Инструментальное исследование",
                   subtype="УЗИ", area="Сосуды", due_after_days=14),
            _order("referral_research", "Коагулограмма", "lab",
                   "Результаты анализа", subtype="Другой анализ",
                   due_after_days=14),
            _order("follow_up_appointment", "Повторный приём флеболога после УЗДС",
                   "consultation", "Прием врача", specialty="Флебология",
                   due_after_days=35),
            # UNCLOSED #3 — vascular surgeon consult, never done
            _order("referral_specialist", "Консультация сосудистого хирурга",
                   "consultation", "Прием врача", specialty="Хирургия",
                   due_after_days=30),
        ],
    ))
    docs.append(_doc(
        "B02", "owner", "2024-10-22", "Инструментальное исследование", MRTE, DR_FUNC,
        T.imaging(
            clinic=MRTE, doc_date="2024-10-22", patient=P, doctor=DR_FUNC,
            modality="УЗИ", area="Сосуды",
            protocol="Дуплексное сканирование вен нижних конечностей. Глубокие вены проходимы, "
                     "клапаны состоятельны. Большая подкожная вена слева расширена до 7 мм, "
                     "клапанная недостаточность на уровне соустья и на бедре. Тромбов нет.",
            conclusion="Варикозная трансформация БПВ слева с клапанной недостаточностью. Глубокие вены без тромбоза.",
        ),
        subtype="УЗИ", area="Сосуды",
    ))
    docs.append(_doc(
        "B03", "owner", "2024-10-25", "Результаты анализа", GEMOTEST, None,
        T.lab(
            clinic=GEMOTEST, doc_date="2024-10-25", patient=P, doctor=None,
            panel="Коагулограмма",
            rows=[
                ("МНО", "1.05", "", "0.85 - 1.15"),
                ("Протромбиновый индекс", "98", "%", "70 - 130"),
                ("АЧТВ", "31", "сек", "26 - 36"),
                ("Фибриноген", "3.2", "г/л", "2.0 - 4.0"),
                ("Д-димер", "310", "нг/мл", "< 500"),
            ],
            conclusion="Показатели гемостаза в пределах нормы.",
        ),
        subtype="Другой анализ",
    ))
    docs.append(_doc(
        "B04", "owner", "2024-11-15", "Прием врача", MEDSI, DR_PHLEBO,
        T.appointment(
            clinic=MEDSI, doc_date="2024-11-15", patient=P, doctor=DR_PHLEBO,
            specialty_label="Флебология",
            complaint="на фоне компрессии и венотоников тяжесть в ногах уменьшилась.",
            anamnesis="по УЗДС — варикоз БПВ слева, глубокие вены проходимы.",
            exam="отёк голеней уменьшился, кожа без трофических изменений.",
            diagnosis="Варикозная болезнь, ХВН C2. Показана плановая эндовазальная облитерация БПВ слева.",
            icd="I83.9",
            treatment=["Продолжить компрессионный трикотаж.",
                       "Планово рассмотреть ЭВЛК БПВ слева."],
            referrals=[
                "Контрольное УЗДС вен нижних конечностей через 6 месяцев.",
                "Повторный приём флеболога через 6 месяцев.",
            ],
        ),
        specialty=["Флебология"],
        orders=[
            _order("referral_research", "Контрольное УЗДС вен нижних конечностей",
                   "instrumental", "Инструментальное исследование",
                   subtype="УЗИ", area="Сосуды", due_after_days=180),
            _order("follow_up_appointment", "Повторный приём флеболога",
                   "consultation", "Прием врача", specialty="Флебология",
                   due_after_days=180),
        ],
    ))
    docs.append(_doc(
        "B05", "owner", "2025-05-22", "Инструментальное исследование", MRTE, DR_FUNC,
        T.imaging(
            clinic=MRTE, doc_date="2025-05-22", patient=P, doctor=DR_FUNC,
            modality="УЗИ", area="Сосуды",
            protocol="Контрольное дуплексное сканирование вен нижних конечностей. "
                     "Динамика прежняя: БПВ слева расширена, клапанная недостаточность сохраняется. "
                     "Глубокие вены проходимы, тромбозов нет.",
            conclusion="Варикозная болезнь без отрицательной динамики. Показана плановая ЭВЛК.",
        ),
        subtype="УЗИ", area="Сосуды",
    ))
    docs.append(_doc(
        "B06", "owner", "2025-06-05", "Прием врача", MEDSI, DR_PHLEBO,
        T.appointment(
            clinic=MEDSI, doc_date="2025-06-05", patient=P, doctor=DR_PHLEBO,
            specialty_label="Флебология",
            complaint="состояние стабильное, выраженного дискомфорта нет.",
            anamnesis="контрольное УЗДС без отрицательной динамики.",
            exam="умеренный варикоз БПВ слева, трофики нет.",
            diagnosis="Варикозная болезнь, ХВН C2, стабильное течение.",
            icd="I83.9",
            treatment=["Плановая ЭВЛК по желанию пациентки.",
                       "Компрессионная терапия постоянно."],
        ),
        specialty=["Флебология"],
    ))

    # =====================================================================
    # BACKGROUND — standalone visits, screening, repeat labs (variety)
    # =====================================================================
    docs.append(_doc(
        "C08", "owner", "2024-09-25", "Прием врача", K31, DR_OPHTH,
        T.appointment(
            clinic=K31, doc_date="2024-09-25", patient=P, doctor=DR_OPHTH,
            specialty_label="Офтальмология",
            complaint="снижение зрения вдаль, усталость глаз при работе за компьютером.",
            anamnesis="очки ранее не носила.",
            exam="Visus OD 0.7, OS 0.6. Глазное дно без патологии. ВГД в норме.",
            diagnosis="Миопия слабой степени обоих глаз.",
            icd="H52.1",
            treatment=["Подобрана коррекция очками для дали.",
                       "Гимнастика для глаз, режим зрительных нагрузок."],
        ),
        specialty=["Офтальмология"], fmt="image", handwritten=True,
    ))
    docs.append(_doc(
        "C09", "owner", "2025-01-14", "Прием врача", MEDSI, DR_ENT,
        T.appointment(
            clinic=MEDSI, doc_date="2025-01-14", patient=P, doctor=DR_ENT,
            specialty_label="Оториноларингология (ЛОР)",
            complaint="заложенность носа, боль в области лба, выделения из носа более недели.",
            anamnesis="после перенесённой ОРВИ.",
            exam="слизистая носа отёчна, гнойное отделяемое в среднем носовом ходе.",
            diagnosis="Острый гайморит (верхнечелюстной синусит).",
            icd="J32.0",
            treatment=["Антибактериальная терапия 7 дней.",
                       "Промывание носа, деконгестанты коротким курсом."],
        ),
        specialty=["Оториноларингология (ЛОР)"], fmt="image", handwritten=True,
    ))
    docs.append(_doc(
        "C10", "owner", "2025-02-08", "Инструментальное исследование", POLY, DR_RAD,
        T.imaging(
            clinic=POLY, doc_date="2025-02-08", patient=P, doctor=DR_RAD,
            modality="Маммография", area="Молочные железы",
            protocol="Маммография в двух проекциях. Структура железистой ткани соответствует возрасту. "
                     "Очаговых образований, микрокальцинатов и патологических теней не выявлено.",
            conclusion="BI-RADS 1. Патологии не выявлено. Скрининг через 2 года.",
        ),
        subtype="Маммография", area="Молочные железы",
    ))
    docs.append(_doc(
        "C11", "owner", "2025-03-12", "Прием врача", K31, DR_GYN,
        T.appointment(
            clinic=K31, doc_date="2025-03-12", patient=P, doctor=DR_GYN,
            specialty_label="Акушерство и гинекология",
            complaint="профилактический осмотр.",
            anamnesis="менструальный цикл регулярный, две беременности, двое родов.",
            exam="наружные и внутренние половые органы без патологии. Взят мазок на онкоцитологию.",
            diagnosis="Здорова. Профилактический гинекологический осмотр.",
            icd="Z01.4",
            treatment=["Осмотр через 12 месяцев."],
        ),
        specialty=["Акушерство и гинекология"],
    ))
    docs.append(_doc(
        "C12", "owner", "2025-03-12", "Инструментальное исследование", K31, DR_FUNC,
        T.imaging(
            clinic=K31, doc_date="2025-03-12", patient=P, doctor=DR_FUNC,
            modality="УЗИ", area="Органы малого таза",
            protocol="Матка обычных размеров, миометрий однородный. Эндометрий соответствует фазе цикла. "
                     "Яичники не увеличены, фолликулярный аппарат сохранён.",
            conclusion="Патологии органов малого таза не выявлено.",
        ),
        subtype="УЗИ", area="Органы малого таза",
    ))
    docs.append(_doc(
        "C13", "owner", "2025-03-20", "Результаты анализа", HELIX, None,
        T.lab(
            clinic=HELIX, doc_date="2025-03-20", patient=P, doctor=None,
            panel="Гормоны щитовидной железы",
            rows=[
                ("ТТГ", "2.4", "мЕд/л", "0.4 - 4.0"),
                ("Т4 свободный", "15.2", "пмоль/л", "9.0 - 19.0"),
                ("Антитела к ТПО", "8", "МЕ/мл", "< 34"),
            ],
            conclusion="Функция щитовидной железы не нарушена.",
        ),
        subtype="Гормональный анализ",
    ))
    docs.append(_doc(
        "C14", "owner", "2025-02-14", "Результаты анализа", HELIX, None,
        T.lab(
            clinic=HELIX, doc_date="2025-02-14", patient=P, doctor=None,
            panel="Ферритин, обмен железа",
            rows=[
                ("Ферритин", "12", "нг/мл", "13 - 150"),
                ("Железо сывороточное", "8.4", "мкмоль/л", "9.0 - 30.4"),
                ("Трансферрин", "3.4", "г/л", "2.0 - 3.6"),
            ],
            conclusion="Латентный дефицит железа.",
        ),
        subtype="Биохимический анализ крови",
    ))
    docs.append(_doc(
        "C15", "owner", "2025-04-05", "Результаты анализа", HELIX, None,
        T.lab(
            clinic=HELIX, doc_date="2025-04-05", patient=P, doctor=None,
            panel="Гликированный гемоглобин",
            rows=[
                ("Гликированный гемоглобин (HbA1c)", "5.7", "%", "4.0 - 6.0"),
                ("Глюкоза венозная", "5.6", "ммоль/л", "3.9 - 6.1"),
            ],
            conclusion="Нарушения углеводного обмена не выявлено.",
        ),
        subtype="Биохимический анализ крови",
    ))

    # --- annual check-up #2 (2025-07) ------------------------------------
    docs.append(_doc(
        "C16", "owner", "2025-07-14", "Прием врача", POLY, DR_THERAPIST,
        T.appointment(
            clinic=POLY, doc_date="2025-07-14", patient=P, doctor=DR_THERAPIST,
            specialty_label="Терапия",
            complaint="профилактический осмотр (диспансеризация).",
            anamnesis="наблюдается у гастроэнтеролога и флеболога, состояние стабильное.",
            exam="АД 124/80. ЧСС 70. ИМТ 25,6.",
            diagnosis="Практически здорова. Гиперхолестеринемия — положительная динамика.",
            icd="Z00.0",
            treatment=["Продолжить диету, приём препаратов железа курсами."],
        ),
        specialty=["Терапия"],
    ))
    docs.append(_doc(
        "C17", "owner", "2025-07-14", "Функциональная диагностика", POLY, DR_FUNC,
        T.functional(
            clinic=POLY, doc_date="2025-07-14", patient=P, doctor=DR_FUNC,
            study="ЭКГ (электрокардиография)",
            protocol="Ритм синусовый, ЧСС 68 уд/мин. ЭОС нормальная. Без острой патологии.",
            conclusion="Вариант нормы.",
        ),
        subtype="ЭКГ (электрокардиография)",
    ))
    docs.append(_doc(
        "C18", "owner", "2025-07-15", "Инструментальное исследование", POLY, DR_RAD,
        T.imaging(
            clinic=POLY, doc_date="2025-07-15", patient=P, doctor=DR_RAD,
            modality="Флюорография", area="Грудная клетка",
            protocol="Лёгочные поля без очаговых и инфильтративных изменений. Корни структурны.",
            conclusion="Без патологии.",
        ),
        subtype="Флюорография", area="Грудная клетка",
    ))
    docs.append(_doc(
        "C19", "owner", "2025-07-14", "Результаты анализа", INVITRO, None,
        T.lab(
            clinic=INVITRO, doc_date="2025-07-14", patient=P, doctor=None,
            panel="Общий анализ крови",
            rows=[
                ("Гемоглобин", "127", "г/л", "120 - 140"),
                ("Эритроциты", "4.5", "10^12/л", "3.9 - 4.7"),
                ("Лейкоциты", "5.8", "10^9/л", "4.0 - 9.0"),
                ("Тромбоциты", "263", "10^9/л", "180 - 320"),
                ("СОЭ", "9", "мм/ч", "2 - 20"),
            ],
            conclusion="Гемоглобин нормализовался.",
        ),
        subtype="Общий анализ крови",
    ))
    docs.append(_doc(
        "C20", "owner", "2025-07-14", "Результаты анализа", INVITRO, None,
        T.lab(
            clinic=INVITRO, doc_date="2025-07-14", patient=P, doctor=None,
            panel="Липидный профиль",
            rows=[
                ("Холестерин общий", "5.6", "ммоль/л", "< 5.2"),
                ("ЛПНП (LDL)", "3.3", "ммоль/л", "< 3.0"),
                ("ЛПВП (HDL)", "1.4", "ммоль/л", "> 1.2"),
                ("Триглицериды", "1.6", "ммоль/л", "< 1.7"),
            ],
            conclusion="Положительная динамика липидного профиля.",
        ),
        subtype="Биохимический анализ крови",
    ))
    docs.append(_doc(
        "C21", "owner", "2025-07-14", "Результаты анализа", INVITRO, None,
        T.lab(
            clinic=INVITRO, doc_date="2025-07-14", patient=P, doctor=None,
            panel="Общий анализ мочи",
            rows=[
                ("Плотность", "1020", "", "1010 - 1025"),
                ("pH", "5.5", "", "5.0 - 7.0"),
                ("Белок", "не обнаружен", "", "не обнаружен"),
                ("Лейкоциты", "1-2", "в п/з", "0 - 5"),
            ],
            conclusion="Без патологии.",
        ),
        subtype="Общий анализ мочи",
    ))

    # --- other standalone -------------------------------------------------
    docs.append(_doc(
        "C22", "owner", "2025-09-10", "Прием врача", SM, DR_DERMA,
        T.appointment(
            clinic=SM, doc_date="2025-09-10", patient=P, doctor=DR_DERMA,
            specialty_label="Дерматология",
            complaint="пигментное образование на коже спины, просит осмотреть.",
            anamnesis="образование существует давно, в последнее время без изменений.",
            exam="невус до 5 мм, правильной формы, равномерной окраски. Дерматоскопия — доброкачественный рисунок.",
            diagnosis="Меланоцитарный невус, доброкачественный.",
            icd="D22.5",
            treatment=["Наблюдение, фотофиксация. Удаление не показано."],
        ),
        specialty=["Дерматология"], fmt="image", handwritten=True,
    ))
    docs.append(_doc(
        "C23", "owner", "2025-10-08", "Функциональная диагностика", MEDSI, DR_FUNC,
        T.functional(
            clinic=MEDSI, doc_date="2025-10-08", patient=P, doctor=DR_FUNC,
            study="Суточный мониторинг АД",
            protocol="СМАД в течение 24 часов. Среднесуточное АД 128/79 мм рт.ст. "
                     "Ночное снижение АД достаточное. Эпизодов гипертензии не зарегистрировано.",
            conclusion="Показатели суточного профиля АД в пределах нормы.",
        ),
        subtype="Суточный мониторинг АД",
    ))
    docs.append(_doc(
        "C24", "owner", "2025-11-18", "Другое", POLY, DR_THERAPIST,
        T.certificate(
            clinic=POLY, doc_date="2025-11-18", patient=P, doctor=DR_THERAPIST,
            kind="Справка о вакцинации против гриппа",
            text="Соколовой О.Н. проведена вакцинация против сезонного гриппа "
                 "(вакцина «Совигрипп», серия 0824). Реакций на прививку не отмечено. "
                 "Справка выдана для предъявления по месту требования.",
        ),
        fmt="image", handwritten=True,
    ))
    docs.append(_doc(
        "C25", "owner", "2025-12-03", "Результаты анализа", GEMOTEST, None,
        T.lab(
            clinic=GEMOTEST, doc_date="2025-12-03", patient=P, doctor=None,
            panel="Витамин D, 25-OH",
            rows=[
                ("Витамин D, 25-OH", "22", "нг/мл", "30 - 100"),
            ],
            conclusion="Недостаточность витамина D. Рекомендована коррекция.",
        ),
        subtype="Другой анализ",
    ))
    docs.append(_doc(
        "C26", "owner", "2026-01-15", "Результаты анализа", INVITRO, None,
        T.lab(
            clinic=INVITRO, doc_date="2026-01-15", patient=P, doctor=None,
            panel="Общий анализ крови",
            rows=[
                ("Гемоглобин", "131", "г/л", "120 - 140"),
                ("Эритроциты", "4.6", "10^12/л", "3.9 - 4.7"),
                ("Лейкоциты", "6.0", "10^9/л", "4.0 - 9.0"),
                ("Тромбоциты", "258", "10^9/л", "180 - 320"),
                ("СОЭ", "8", "мм/ч", "2 - 20"),
            ],
            conclusion="Показатели в норме.",
        ),
        subtype="Общий анализ крови",
    ))
    docs.append(_doc(
        "C27", "owner", "2026-02-05", "Результаты анализа", INVITRO, None,
        T.lab(
            clinic=INVITRO, doc_date="2026-02-05", patient=P, doctor=None,
            panel="Липидный профиль",
            rows=[
                ("Холестерин общий", "5.0", "ммоль/л", "< 5.2"),
                ("ЛПНП (LDL)", "2.8", "ммоль/л", "< 3.0"),
                ("ЛПВП (HDL)", "1.5", "ммоль/л", "> 1.2"),
                ("Триглицериды", "1.4", "ммоль/л", "< 1.7"),
            ],
            conclusion="Липидный профиль в пределах целевых значений.",
        ),
        subtype="Биохимический анализ крови",
    ))
    docs.append(_doc(
        "C28", "owner", "2026-03-14", "Прием врача", MEDSI, DR_THERAPIST,
        T.appointment(
            clinic=MEDSI, doc_date="2026-03-14", patient=P, doctor=DR_THERAPIST,
            specialty_label="Терапия",
            complaint="кашель, насморк, повышение температуры до 37,8 в течение 3 дней.",
            anamnesis="контакт с болеющим ОРВИ.",
            exam="зев гиперемирован, в лёгких дыхание везикулярное, хрипов нет.",
            diagnosis="Острая респираторная вирусная инфекция.",
            icd="J06.9",
            treatment=["Обильное питьё, симптоматическая терапия.",
                       "Больничный лист на 5 дней."],
        ),
        specialty=["Терапия"],
    ))
    docs.append(_doc(
        "C29", "owner", "2026-03-14", "Функциональная диагностика", MEDSI, DR_FUNC,
        T.functional(
            clinic=MEDSI, doc_date="2026-03-14", patient=P, doctor=DR_FUNC,
            study="Спирометрия",
            protocol="ФЖЕЛ 3.6 л (98% от должного), ОФВ1 3.0 л (99%), индекс Тиффно 83%. "
                     "Проба с бронхолитиком отрицательная.",
            conclusion="Функция внешнего дыхания не нарушена.",
        ),
        subtype="Спирометрия",
    ))
    docs.append(_doc(
        "C30", "owner", "2026-04-22", "Другое", MEDSI, DR_THERAPIST,
        T.certificate(
            clinic=MEDSI, doc_date="2026-04-22", patient=P, doctor=DR_THERAPIST,
            kind="Выписка из амбулаторной карты",
            text="Выдана Соколовой О.Н. по запросу. За период наблюдения: хронический гастрит "
                 "в стадии ремиссии, варикозная болезнь нижних конечностей (ХВН C2), "
                 "миопия слабой степени. Хронические заболевания компенсированы. "
                 "Диспансерное наблюдение продолжается.",
        ),
    ))
    docs.append(_doc(
        "C31", "owner", "2026-05-16", "Функциональная диагностика", POLY, DR_FUNC,
        T.functional(
            clinic=POLY, doc_date="2026-05-16", patient=P, doctor=DR_FUNC,
            study="ЭКГ (электрокардиография)",
            protocol="Ритм синусовый, ЧСС 71 уд/мин. Без динамики по сравнению с предыдущими.",
            conclusion="Вариант нормы.",
        ),
        subtype="ЭКГ (электрокардиография)",
    ))
    docs.append(_doc(
        "C32", "owner", "2026-06-10", "Результаты анализа", INVITRO, None,
        T.lab(
            clinic=INVITRO, doc_date="2026-06-10", patient=P, doctor=None,
            panel="Общий анализ крови",
            rows=[
                ("Гемоглобин", "134", "г/л", "120 - 140"),
                ("Эритроциты", "4.6", "10^12/л", "3.9 - 4.7"),
                ("Лейкоциты", "5.9", "10^9/л", "4.0 - 9.0"),
                ("Тромбоциты", "260", "10^9/л", "180 - 320"),
                ("СОЭ", "7", "мм/ч", "2 - 20"),
            ],
            conclusion="Норма. Анемия разрешилась.",
        ),
        subtype="Общий анализ крови",
    ))
    docs.append(_doc(
        "C33", "owner", "2024-12-05", "Другое", POLY, None,
        T.certificate(
            clinic=POLY, doc_date="2024-12-05", patient=P, doctor=None,
            kind="Сертификат о профилактических прививках",
            text="Соколова О.Н. Сведения о вакцинации: дифтерия/столбняк (АДС-М) — ревакцинация "
                 "06.2021; COVID-19 — вакцинация 2021 г., ревакцинация 2022 г.; грипп — ежегодно. "
                 "Медицинских отводов нет.",
        ),
    ))
    docs.append(_doc(
        "C34", "owner", "2025-08-25", "Другое", POLY, DR_THERAPIST,
        T.certificate(
            clinic=POLY, doc_date="2025-08-25", patient=P, doctor=DR_THERAPIST,
            kind="Медицинская справка (в бассейн)",
            text="Выдана Соколовой О.Н. в том, что противопоказаний для посещения плавательного "
                 "бассейна нет. Осмотр дерматолога и терапевта пройден. Справка действительна 6 месяцев.",
        ),
        fmt="image", handwritten=True,
    ))
    docs.append(_doc(
        "C35", "owner", "2025-11-05", "Результаты анализа", HELIX, None,
        T.lab(
            clinic=HELIX, doc_date="2025-11-05", patient=P, doctor=None,
            panel="Биохимический анализ крови",
            rows=[
                ("Глюкоза", "5.5", "ммоль/л", "3.9 - 6.1"),
                ("АЛТ", "20", "Ед/л", "0 - 34"),
                ("АСТ", "22", "Ед/л", "0 - 31"),
                ("Креатинин", "70", "мкмоль/л", "53 - 97"),
                ("Мочевая кислота", "290", "мкмоль/л", "150 - 350"),
            ],
            conclusion="Без отклонений.",
        ),
        subtype="Биохимический анализ крови",
    ))

    docs.append(_doc(
        "C36", "owner", "2025-03-21", "Инструментальное исследование", HELIX, DR_FUNC,
        T.imaging(
            clinic=HELIX, doc_date="2025-03-21", patient=P, doctor=DR_FUNC,
            modality="УЗИ", area="Щитовидная железа",
            protocol="Щитовидная железа обычно расположена, не увеличена (объём 12,4 см³). "
                     "Эхоструктура однородная, узловых образований не выявлено. Регионарные лимфоузлы не увеличены.",
            conclusion="Патологии щитовидной железы не выявлено.",
        ),
        subtype="УЗИ", area="Щитовидная железа",
    ))
    docs.append(_doc(
        "C37", "owner", "2025-04-18", "Прием врача", SM, "Григорьев П.М.",
        T.appointment(
            clinic=SM, doc_date="2025-04-18", patient=P, doctor="Григорьев П.М.",
            specialty_label="Неврология",
            complaint="периодические головные боли давящего характера, связанные с усталостью.",
            anamnesis="работа за компьютером, нарушения сна. Очаговой симптоматики нет.",
            exam="неврологический статус без очаговой симптоматики. Напряжение перикраниальных мышц.",
            diagnosis="Головная боль напряжения.",
            icd="G44.2",
            treatment=["Нормализация режима сна и труда.",
                       "Магний, при болях — НПВП по требованию."],
        ),
        specialty=["Неврология"],
    ))
    docs.append(_doc(
        "C38", "owner", "2025-01-20", "Результаты анализа", INVITRO, None,
        T.lab(
            clinic=INVITRO, doc_date="2025-01-20", patient=P, doctor=None,
            panel="Общий анализ крови",
            rows=[
                ("Гемоглобин", "123", "г/л", "120 - 140"),
                ("Эритроциты", "4.4", "10^12/л", "3.9 - 4.7"),
                ("Лейкоциты", "6.2", "10^9/л", "4.0 - 9.0"),
                ("Тромбоциты", "255", "10^9/л", "180 - 320"),
                ("СОЭ", "11", "мм/ч", "2 - 20"),
            ],
            conclusion="Гемоглобин в пределах нормы, динамика положительная.",
        ),
        subtype="Общий анализ крови",
    ))
    docs.append(_doc(
        "C39", "owner", "2024-11-25", "Прием врача", POLY, DR_THERAPIST,
        T.appointment(
            clinic=POLY, doc_date="2024-11-25", patient=P, doctor=DR_THERAPIST,
            specialty_label="Терапия",
            complaint="утомляемость, ломкость ногтей; по анализам — снижение железа.",
            anamnesis="латентный дефицит железа по результатам обследования.",
            exam="кожа бледновата, АД 122/78. По органам без особенностей.",
            diagnosis="Латентный дефицит железа.",
            icd="E61.1",
            treatment=["Препараты железа внутрь курсом 2 месяца.",
                       "Контроль общего анализа крови и ферритина после курса."],
        ),
        specialty=["Терапия"],
    ))

    # =====================================================================
    # FAMILY — daughter Соня (~7 y.o.)
    # =====================================================================
    docs.append(_doc(
        "F01", "child", "2024-09-12", "Прием врача", FANTASY, DR_PED,
        T.appointment(
            clinic=FANTASY, doc_date="2024-09-12", patient=PATIENT_CHILD, doctor=DR_PED,
            specialty_label="Педиатрия",
            complaint="плановый профилактический осмотр перед поступлением в школу.",
            anamnesis="растёт и развивается по возрасту, привита по календарю.",
            exam="состояние удовлетворительное. Рост 122 см, вес 23 кг. По органам без патологии.",
            diagnosis="Здорова. Группа здоровья I.",
            icd="Z00.1",
            treatment=["Профилактический осмотр через 12 месяцев."],
        ),
        specialty=["Педиатрия"],
    ))
    docs.append(_doc(
        "F02", "child", "2024-09-12", "Результаты анализа", INVITRO, None,
        T.lab(
            clinic=INVITRO, doc_date="2024-09-12", patient=PATIENT_CHILD, doctor=None,
            panel="Общий анализ крови",
            rows=[
                ("Гемоглобин", "128", "г/л", "110 - 140"),
                ("Эритроциты", "4.4", "10^12/л", "3.8 - 4.9"),
                ("Лейкоциты", "6.8", "10^9/л", "5.0 - 12.0"),
                ("Тромбоциты", "290", "10^9/л", "180 - 400"),
                ("СОЭ", "6", "мм/ч", "2 - 15"),
            ],
            conclusion="Показатели соответствуют возрастной норме.",
        ),
        subtype="Общий анализ крови",
    ))
    docs.append(_doc(
        "F03", "child", "2024-09-14", "Другое", FANTASY, DR_PED,
        T.certificate(
            clinic=FANTASY, doc_date="2024-09-14", patient=PATIENT_CHILD, doctor=DR_PED,
            kind="Медицинская справка для поступления в школу (форма 026/у)",
            text="Соколова С.А. Осмотрена перед поступлением в 1 класс. Физическое развитие "
                 "среднее, гармоничное. Группа здоровья I, физкультурная группа основная. "
                 "Прививки по возрасту. Противопоказаний к обучению нет.",
        ),
    ))
    docs.append(_doc(
        "F04", "child", "2025-02-03", "Прием врача", FANTASY, DR_PED,
        T.appointment(
            clinic=FANTASY, doc_date="2025-02-03", patient=PATIENT_CHILD, doctor=DR_PED,
            specialty_label="Педиатрия",
            complaint="кашель, насморк, температура до 38,2 второй день.",
            anamnesis="заболела остро, в классе есть болеющие дети.",
            exam="зев гиперемирован, налётов нет. В лёгких дыхание жёсткое, хрипов нет.",
            diagnosis="Острая респираторная вирусная инфекция, острый ринофарингит.",
            icd="J06.9",
            treatment=["Обильное тёплое питьё, промывание носа.",
                       "Жаропонижающее при температуре выше 38,5.",
                       "Освобождение от школы на 7 дней."],
        ),
        specialty=["Педиатрия"], fmt="image", handwritten=True,
    ))
    docs.append(_doc(
        "F05", "child", "2025-02-05", "Другое", FANTASY, DR_PED,
        T.certificate(
            clinic=FANTASY, doc_date="2025-02-05", patient=PATIENT_CHILD, doctor=DR_PED,
            kind="Справка об освобождении от занятий",
            text="Соколова С.А. находилась на амбулаторном лечении по поводу ОРВИ с 03.02 по 09.02. "
                 "Освобождена от занятий в школе. Приступить к занятиям с 10.02.",
        ),
    ))
    docs.append(_doc(
        "F06", "child", "2025-09-15", "Прием врача", FANTASY, DR_PED,
        T.appointment(
            clinic=FANTASY, doc_date="2025-09-15", patient=PATIENT_CHILD, doctor=DR_PED,
            specialty_label="Педиатрия",
            complaint="плановая диспансеризация (8 лет).",
            anamnesis="за год перенесла ОРВИ дважды, хронических заболеваний нет.",
            exam="рост 128 см, вес 25 кг. Развитие по возрасту, по органам без патологии.",
            diagnosis="Здорова. Группа здоровья I.",
            icd="Z00.1",
            treatment=["Наблюдение по возрасту.",
                       "Рекомендована консультация окулиста при зрительной нагрузке."],
        ),
        specialty=["Педиатрия"],
    ))
    docs.append(_doc(
        "F07", "child", "2025-09-15", "Результаты анализа", INVITRO, None,
        T.lab(
            clinic=INVITRO, doc_date="2025-09-15", patient=PATIENT_CHILD, doctor=None,
            panel="Общий анализ мочи",
            rows=[
                ("Плотность", "1015", "", "1010 - 1025"),
                ("pH", "6.0", "", "5.0 - 7.0"),
                ("Белок", "не обнаружен", "", "не обнаружен"),
                ("Лейкоциты", "0-1", "в п/з", "0 - 5"),
            ],
            conclusion="Без патологии.",
        ),
        subtype="Общий анализ мочи",
    ))
    docs.append(_doc(
        "F08", "child", "2026-01-20", "Прием врача", FANTASY, DR_OPHTH,
        T.appointment(
            clinic=FANTASY, doc_date="2026-01-20", patient=PATIENT_CHILD, doctor=DR_OPHTH,
            specialty_label="Офтальмология",
            complaint="прищуривается при взгляде на доску в школе.",
            anamnesis="зрительная нагрузка возросла, много времени за планшетом.",
            exam="Visus OD 0.9, OS 0.9. Глазное дно без патологии.",
            diagnosis="Зрение в норме. Спазм аккомодации не выявлен.",
            icd="Z01.0",
            treatment=["Ограничить экранное время, гимнастика для глаз.",
                       "Повторный осмотр через год."],
        ),
        specialty=["Офтальмология"],
    ))

    return docs


# Convenience: the three intentionally-unclosed referrals (for verification).
UNCLOSED_REFERRALS = [
    ("A01", "Консультация эндокринолога", "Эндокринология"),
    ("A03", "УЗИ органов брюшной полости", "Брюшная полость"),
    ("B01", "Консультация сосудистого хирурга", "Хирургия"),
]


if __name__ == "__main__":
    m = build_manifest()
    from collections import Counter
    by_profile = Counter(d["profile"] for d in m)
    by_type = Counter(d["document_type"] for d in m)
    by_fmt = Counter(d["format"] for d in m)
    hw = sum(1 for d in m if d["handwritten"])
    print(f"TOTAL: {len(m)} docs | {dict(by_profile)}")
    print("by type:", dict(by_type))
    print("by format:", dict(by_fmt), "| handwritten:", hw)
    print("orders (referrals):", sum(len(d["orders"]) for d in m))
