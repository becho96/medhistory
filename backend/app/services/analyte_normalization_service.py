"""
Сервис нормализации названий анализов и конвертации единиц измерения.

Решает проблемы:
- Разные названия одного анализа в разных лабораториях
- Разные единицы измерения для одного анализа
- Необходимость конвертации значений для корректного сравнения

Пример использования:
    result = analyte_normalization_service.normalize_and_convert(
        test_name="Витамин D, 25-гидрокси",
        value="50",
        unit="нмоль/л"
    )
    # result = ("Витамин D (25-OH)", 20.0, "нг/мл", "Витамины и микроэлементы")
"""

import re
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class AnalyteStandard:
    """Стандарт для одного анализа"""
    canonical_name: str
    synonyms: List[str]
    category: str
    standard_unit: str
    # Словарь: исходная_единица -> коэффициент (value * коэффициент = стандартное значение)
    conversions: Dict[str, float]


# Справочник стандартов анализов
# Ключ - каноническое название, значение - AnalyteStandard
ANALYTE_STANDARDS: Dict[str, AnalyteStandard] = {}

# Инвертированный индекс: синоним -> каноническое название (строится автоматически)
_SYNONYM_INDEX: Dict[str, str] = {}


def _register_analyte(
    canonical_name: str,
    synonyms: List[str],
    category: str,
    standard_unit: str,
    conversions: Optional[Dict[str, float]] = None
) -> None:
    """Регистрирует анализ в справочнике"""
    if conversions is None:
        conversions = {}
    
    # Добавляем стандартную единицу с коэффициентом 1.0
    if standard_unit not in conversions:
        conversions[standard_unit] = 1.0
    
    ANALYTE_STANDARDS[canonical_name] = AnalyteStandard(
        canonical_name=canonical_name,
        synonyms=synonyms,
        category=category,
        standard_unit=standard_unit,
        conversions=conversions
    )
    
    # Обновляем индекс синонимов
    for synonym in synonyms:
        _SYNONYM_INDEX[synonym.lower().strip()] = canonical_name


# ============================================================================
# ОБЩИЙ АНАЛИЗ КРОВИ (ОАК)
# ============================================================================

_register_analyte(
    canonical_name="Гемоглобин",
    synonyms=["Гемоглобин", "Hemoglobin", "Hb", "HGB", "Hgb"],
    category="Общий анализ крови",
    standard_unit="г/л",
    conversions={
        "г/л": 1.0,
        "г/дл": 10.0,  # г/дл × 10 = г/л
        "g/L": 1.0,
        "g/dL": 10.0,
    }
)

_register_analyte(
    canonical_name="Эритроциты",
    synonyms=["Эритроциты", "RBC", "Красные кровяные тельца", "Red Blood Cells", "Эр."],
    category="Общий анализ крови",
    standard_unit="×10¹²/л",
    conversions={
        "×10¹²/л": 1.0,
        "10*12/л": 1.0,
        "х10^12/л": 1.0,
        "10^12/л": 1.0,
        "млн/мкл": 1.0,  # млн/мкл = ×10¹²/л
        "T/L": 1.0,
    }
)

_register_analyte(
    canonical_name="Лейкоциты",
    synonyms=["Лейкоциты", "WBC", "Белые кровяные тельца", "White Blood Cells", "Лейк."],
    category="Общий анализ крови",
    standard_unit="×10⁹/л",
    conversions={
        "×10⁹/л": 1.0,
        "10*9/л": 1.0,
        "х10^9/л": 1.0,
        "10^9/л": 1.0,
        "тыс/мкл": 1.0,  # тыс/мкл = ×10⁹/л
        "G/L": 1.0,
    }
)

_register_analyte(
    canonical_name="Тромбоциты",
    synonyms=["Тромбоциты", "PLT", "Platelets", "Кровяные пластинки", "Тр."],
    category="Общий анализ крови",
    standard_unit="×10⁹/л",
    conversions={
        "×10⁹/л": 1.0,
        "10*9/л": 1.0,
        "х10^9/л": 1.0,
        "10^9/л": 1.0,
        "тыс/мкл": 1.0,
        "G/L": 1.0,
    }
)

_register_analyte(
    canonical_name="Гематокрит",
    synonyms=["Гематокрит", "HCT", "Hematocrit", "Ht"],
    category="Общий анализ крови",
    standard_unit="%",
    conversions={
        "%": 1.0,
        "L/L": 100.0,  # доля × 100 = %
    }
)

_register_analyte(
    canonical_name="СОЭ",
    synonyms=["СОЭ", "Скорость оседания эритроцитов", "ESR", "Erythrocyte Sedimentation Rate"],
    category="Общий анализ крови",
    standard_unit="мм/ч",
    conversions={
        "мм/ч": 1.0,
        "мм/час": 1.0,
        "mm/h": 1.0,
        "mm/hr": 1.0,
    }
)

# Эритроцитарные индексы
_register_analyte(
    canonical_name="MCV",
    synonyms=["MCV", "Средний объём эритроцита", "Mean Corpuscular Volume", "Ср. объем эритроцита"],
    category="Общий анализ крови",
    standard_unit="фл",
    conversions={"фл": 1.0, "fL": 1.0}
)

_register_analyte(
    canonical_name="MCH",
    synonyms=["MCH", "Среднее содержание гемоглобина в эритроците", "Mean Corpuscular Hemoglobin"],
    category="Общий анализ крови",
    standard_unit="пг",
    conversions={"пг": 1.0, "pg": 1.0}
)

_register_analyte(
    canonical_name="MCHC",
    synonyms=["MCHC", "Средняя концентрация гемоглобина в эритроцитах", "Mean Corpuscular Hemoglobin Concentration"],
    category="Общий анализ крови",
    standard_unit="г/л",
    conversions={"г/л": 1.0, "г/дл": 10.0, "g/L": 1.0, "g/dL": 10.0}
)

_register_analyte(
    canonical_name="RDW",
    synonyms=["RDW", "Ширина распределения эритроцитов", "Red Cell Distribution Width", 
              "Ширина распределения эритроцитов по объему"],
    category="Общий анализ крови",
    standard_unit="%",
    conversions={"%": 1.0}
)

# Лейкоцитарная формула (абсолютные значения)
_register_analyte(
    canonical_name="Нейтрофилы (абс)",
    synonyms=["Нейтрофилы", "Нейтрофилы абс", "Neutrophils", "NEU", "NEUT", 
              "Сегментоядерные нейтрофилы", "Палочкоядерные нейтрофилы"],
    category="Общий анализ крови",
    standard_unit="×10⁹/л",
    conversions={
        "×10⁹/л": 1.0,
        "10*9/л": 1.0,
        "х10^9/л": 1.0,
        "тыс/мкл": 1.0,
    }
)

_register_analyte(
    canonical_name="Лимфоциты (абс)",
    synonyms=["Лимфоциты", "Лимфоциты абс", "Lymphocytes", "LYM", "LYMPH"],
    category="Общий анализ крови",
    standard_unit="×10⁹/л",
    conversions={
        "×10⁹/л": 1.0,
        "10*9/л": 1.0,
        "х10^9/л": 1.0,
        "тыс/мкл": 1.0,
    }
)

_register_analyte(
    canonical_name="Моноциты (абс)",
    synonyms=["Моноциты", "Моноциты абс", "Monocytes", "MON", "MONO"],
    category="Общий анализ крови",
    standard_unit="×10⁹/л",
    conversions={
        "×10⁹/л": 1.0,
        "10*9/л": 1.0,
        "х10^9/л": 1.0,
        "тыс/мкл": 1.0,
    }
)

_register_analyte(
    canonical_name="Эозинофилы (абс)",
    synonyms=["Эозинофилы", "Эозинофилы абс", "Eosinophils", "EOS"],
    category="Общий анализ крови",
    standard_unit="×10⁹/л",
    conversions={
        "×10⁹/л": 1.0,
        "10*9/л": 1.0,
        "х10^9/л": 1.0,
        "тыс/мкл": 1.0,
    }
)

_register_analyte(
    canonical_name="Базофилы (абс)",
    synonyms=["Базофилы", "Базофилы абс", "Basophils", "BAS", "BASO"],
    category="Общий анализ крови",
    standard_unit="×10⁹/л",
    conversions={
        "×10⁹/л": 1.0,
        "10*9/л": 1.0,
        "х10^9/л": 1.0,
        "тыс/мкл": 1.0,
    }
)

# Лейкоцитарная формула (проценты) - отдельные анализы
_register_analyte(
    canonical_name="Нейтрофилы (%)",
    synonyms=["Нейтрофилы %", "Neutrophils %", "NEU%", "NEUT%"],
    category="Общий анализ крови",
    standard_unit="%",
    conversions={"%": 1.0}
)

_register_analyte(
    canonical_name="Лимфоциты (%)",
    synonyms=["Лимфоциты %", "Lymphocytes %", "LYM%", "LYMPH%"],
    category="Общий анализ крови",
    standard_unit="%",
    conversions={"%": 1.0}
)

_register_analyte(
    canonical_name="Моноциты (%)",
    synonyms=["Моноциты %", "Monocytes %", "MON%", "MONO%"],
    category="Общий анализ крови",
    standard_unit="%",
    conversions={"%": 1.0}
)

_register_analyte(
    canonical_name="Эозинофилы (%)",
    synonyms=["Эозинофилы %", "Eosinophils %", "EOS%"],
    category="Общий анализ крови",
    standard_unit="%",
    conversions={"%": 1.0}
)

_register_analyte(
    canonical_name="Базофилы (%)",
    synonyms=["Базофилы %", "Basophils %", "BAS%", "BASO%"],
    category="Общий анализ крови",
    standard_unit="%",
    conversions={"%": 1.0}
)

# ============================================================================
# БИОХИМИЯ КРОВИ
# ============================================================================

_register_analyte(
    canonical_name="Глюкоза",
    synonyms=["Глюкоза", "Глюкоза крови", "Сахар крови", "Glucose", "GLU", "Сахар"],
    category="Биохимия крови",
    standard_unit="ммоль/л",
    conversions={
        "ммоль/л": 1.0,
        "mmol/L": 1.0,
        "мг/дл": 0.0555,  # мг/дл × 0.0555 = ммоль/л
        "mg/dL": 0.0555,
    }
)

_register_analyte(
    canonical_name="Креатинин",
    synonyms=["Креатинин", "Creatinine", "CREA", "Креатинин в сыворотке"],
    category="Биохимия крови",
    standard_unit="мкмоль/л",
    conversions={
        "мкмоль/л": 1.0,
        "µmol/L": 1.0,
        "umol/L": 1.0,
        "мг/дл": 88.4,  # мг/дл × 88.4 = мкмоль/л
        "mg/dL": 88.4,
    }
)

_register_analyte(
    canonical_name="Мочевина",
    synonyms=["Мочевина", "Urea", "BUN", "Мочевина в сыворотке"],
    category="Биохимия крови",
    standard_unit="ммоль/л",
    conversions={
        "ммоль/л": 1.0,
        "mmol/L": 1.0,
        "мг/дл": 0.357,  # мг/дл × 0.357 = ммоль/л
        "mg/dL": 0.357,
    }
)

_register_analyte(
    canonical_name="Мочевая кислота",
    synonyms=["Мочевая кислота", "Мочевая кислота в сыворотке", "Uric Acid", "UA"],
    category="Биохимия крови",
    standard_unit="мкмоль/л",
    conversions={
        "мкмоль/л": 1.0,
        "µmol/L": 1.0,
        "мг/дл": 59.48,  # мг/дл × 59.48 = мкмоль/л
        "mg/dL": 59.48,
    }
)

_register_analyte(
    canonical_name="Общий белок",
    synonyms=["Общий белок", "Белок", "Total Protein", "TP", "Белок общий"],
    category="Биохимия крови",
    standard_unit="г/л",
    conversions={"г/л": 1.0, "g/L": 1.0, "г/дл": 10.0, "g/dL": 10.0}
)

# Билирубин
_register_analyte(
    canonical_name="Билирубин общий",
    synonyms=["Билирубин общий", "Билирубин", "Total Bilirubin", "TBIL", "Билирубин общ."],
    category="Биохимия крови",
    standard_unit="мкмоль/л",
    conversions={
        "мкмоль/л": 1.0,
        "µmol/L": 1.0,
        "мг/дл": 17.1,  # мг/дл × 17.1 = мкмоль/л
        "mg/dL": 17.1,
    }
)

_register_analyte(
    canonical_name="Билирубин прямой",
    synonyms=["Билирубин прямой", "Direct Bilirubin", "DBIL", "Билирубин прям.", "Билирубин конъюгированный"],
    category="Биохимия крови",
    standard_unit="мкмоль/л",
    conversions={"мкмоль/л": 1.0, "µmol/L": 1.0, "мг/дл": 17.1, "mg/dL": 17.1}
)

_register_analyte(
    canonical_name="Билирубин непрямой",
    synonyms=["Билирубин непрямой", "Indirect Bilirubin", "IBIL", "Билирубин непрям.", "Билирубин неконъюгированный"],
    category="Биохимия крови",
    standard_unit="мкмоль/л",
    conversions={"мкмоль/л": 1.0, "µmol/L": 1.0, "мг/дл": 17.1, "mg/dL": 17.1}
)

# Печеночные ферменты
_register_analyte(
    canonical_name="АЛТ",
    synonyms=["АЛТ", "Аланинаминотрансфераза", "ALT", "ALAT", "GPT", "АлАТ"],
    category="Биохимия крови",
    standard_unit="Ед/л",
    conversions={"Ед/л": 1.0, "U/L": 1.0, "МЕ/л": 1.0, "IU/L": 1.0}
)

_register_analyte(
    canonical_name="АСТ",
    synonyms=["АСТ", "Аспартатаминотрансфераза", "AST", "ASAT", "GOT", "АсАТ"],
    category="Биохимия крови",
    standard_unit="Ед/л",
    conversions={"Ед/л": 1.0, "U/L": 1.0, "МЕ/л": 1.0, "IU/L": 1.0}
)

_register_analyte(
    canonical_name="ГГТ",
    synonyms=["ГГТ", "Гамма-глутамилтрансфераза", "GGT", "Gamma-GT", "ГГТП", "Гамма-ГТ"],
    category="Биохимия крови",
    standard_unit="Ед/л",
    conversions={"Ед/л": 1.0, "U/L": 1.0, "МЕ/л": 1.0, "IU/L": 1.0}
)

_register_analyte(
    canonical_name="Щелочная фосфатаза",
    synonyms=["Щелочная фосфатаза", "ALP", "Alkaline Phosphatase", "ЩФ"],
    category="Биохимия крови",
    standard_unit="Ед/л",
    conversions={"Ед/л": 1.0, "U/L": 1.0, "МЕ/л": 1.0, "IU/L": 1.0}
)

_register_analyte(
    canonical_name="ЛДГ",
    synonyms=["ЛДГ", "Лактатдегидрогеназа", "LDH", "Lactate Dehydrogenase"],
    category="Биохимия крови",
    standard_unit="Ед/л",
    conversions={"Ед/л": 1.0, "U/L": 1.0, "МЕ/л": 1.0, "IU/L": 1.0}
)

_register_analyte(
    canonical_name="Амилаза",
    synonyms=["Амилаза", "Альфа-амилаза", "Альфа-амилаза панкреатическая", "Amylase", "AMY"],
    category="Биохимия крови",
    standard_unit="Ед/л",
    conversions={"Ед/л": 1.0, "U/L": 1.0, "МЕ/л": 1.0, "IU/L": 1.0}
)

_register_analyte(
    canonical_name="Липаза",
    synonyms=["Липаза", "Lipase", "LIP"],
    category="Биохимия крови",
    standard_unit="Ед/л",
    conversions={"Ед/л": 1.0, "U/L": 1.0, "МЕ/л": 1.0, "IU/L": 1.0}
)

_register_analyte(
    canonical_name="Креатинкиназа",
    synonyms=["Креатинкиназа", "КФК", "CK", "Creatine Kinase", "CPK"],
    category="Биохимия крови",
    standard_unit="Ед/л",
    conversions={"Ед/л": 1.0, "U/L": 1.0, "МЕ/л": 1.0, "IU/L": 1.0}
)

# Электролиты
_register_analyte(
    canonical_name="Железо",
    synonyms=["Железо", "Железо в сыворотке", "Iron", "Fe", "Сывороточное железо"],
    category="Биохимия крови",
    standard_unit="мкмоль/л",
    conversions={
        "мкмоль/л": 1.0,
        "µmol/L": 1.0,
        "мкг/дл": 0.179,  # мкг/дл × 0.179 = мкмоль/л
        "µg/dL": 0.179,
    }
)

_register_analyte(
    canonical_name="Магний",
    synonyms=["Магний", "Magnesium", "Mg"],
    category="Биохимия крови",
    standard_unit="ммоль/л",
    conversions={"ммоль/л": 1.0, "mmol/L": 1.0, "мг/дл": 0.411, "mg/dL": 0.411}
)

_register_analyte(
    canonical_name="Кальций",
    synonyms=["Кальций", "Calcium", "Ca", "Кальций общий"],
    category="Биохимия крови",
    standard_unit="ммоль/л",
    conversions={"ммоль/л": 1.0, "mmol/L": 1.0, "мг/дл": 0.25, "mg/dL": 0.25}
)

_register_analyte(
    canonical_name="Калий",
    synonyms=["Калий", "Potassium", "K"],
    category="Биохимия крови",
    standard_unit="ммоль/л",
    conversions={"ммоль/л": 1.0, "mmol/L": 1.0, "мЭкв/л": 1.0, "mEq/L": 1.0}
)

_register_analyte(
    canonical_name="Натрий",
    synonyms=["Натрий", "Sodium", "Na"],
    category="Биохимия крови",
    standard_unit="ммоль/л",
    conversions={"ммоль/л": 1.0, "mmol/L": 1.0, "мЭкв/л": 1.0, "mEq/L": 1.0}
)

# ============================================================================
# ЛИПИДНЫЙ ПРОФИЛЬ
# ============================================================================

_register_analyte(
    canonical_name="Холестерин общий",
    synonyms=["Холестерин общий", "Холестерин", "Total Cholesterol", "TC", "CHOL"],
    category="Липидный профиль",
    standard_unit="ммоль/л",
    conversions={
        "ммоль/л": 1.0,
        "mmol/L": 1.0,
        "мг/дл": 0.0259,  # мг/дл × 0.0259 = ммоль/л
        "mg/dL": 0.0259,
    }
)

_register_analyte(
    canonical_name="Холестерин-ЛПВП",
    synonyms=["Холестерин-ЛПВП", "ЛПВП", "HDL", "HDL Cholesterol", "HDL-C", "Холестерин ЛПВП"],
    category="Липидный профиль",
    standard_unit="ммоль/л",
    conversions={"ммоль/л": 1.0, "mmol/L": 1.0, "мг/дл": 0.0259, "mg/dL": 0.0259}
)

_register_analyte(
    canonical_name="Холестерин-ЛПНП",
    synonyms=["Холестерин-ЛПНП", "ЛПНП", "LDL", "LDL Cholesterol", "LDL-C", "Холестерин ЛПНП"],
    category="Липидный профиль",
    standard_unit="ммоль/л",
    conversions={"ммоль/л": 1.0, "mmol/L": 1.0, "мг/дл": 0.0259, "mg/dL": 0.0259}
)

_register_analyte(
    canonical_name="Холестерин не-ЛПВП",
    synonyms=["Холестерин не-ЛПВП", "Non-HDL Cholesterol", "Non-HDL-C"],
    category="Липидный профиль",
    standard_unit="ммоль/л",
    conversions={"ммоль/л": 1.0, "mmol/L": 1.0, "мг/дл": 0.0259, "mg/dL": 0.0259}
)

_register_analyte(
    canonical_name="Триглицериды",
    synonyms=["Триглицериды", "Triglycerides", "TG", "TRIG"],
    category="Липидный профиль",
    standard_unit="ммоль/л",
    conversions={
        "ммоль/л": 1.0,
        "mmol/L": 1.0,
        "мг/дл": 0.0113,  # мг/дл × 0.0113 = ммоль/л
        "mg/dL": 0.0113,
    }
)

# ============================================================================
# КОАГУЛОГРАММА
# ============================================================================

_register_analyte(
    canonical_name="АЧТВ",
    synonyms=["АЧТВ", "Активированное частичное тромбопластиновое время", "APTT", "aPTT"],
    category="Коагулограмма",
    standard_unit="сек",
    conversions={"сек": 1.0, "с": 1.0, "sec": 1.0, "s": 1.0}
)

_register_analyte(
    canonical_name="Протромбиновое время",
    synonyms=["Протромбиновое время", "ПВ", "PT", "Prothrombin Time"],
    category="Коагулограмма",
    standard_unit="сек",
    conversions={"сек": 1.0, "с": 1.0, "sec": 1.0, "s": 1.0}
)

_register_analyte(
    canonical_name="Протромбин по Квику",
    synonyms=["Протромбин по Квику", "Prothrombin Activity", "Quick"],
    category="Коагулограмма",
    standard_unit="%",
    conversions={"%": 1.0}
)

_register_analyte(
    canonical_name="МНО",
    synonyms=["МНО", "INR", "International Normalized Ratio"],
    category="Коагулограмма",
    standard_unit="",
    conversions={"": 1.0}
)

_register_analyte(
    canonical_name="Фибриноген",
    synonyms=["Фибриноген", "Fibrinogen", "FIB"],
    category="Коагулограмма",
    standard_unit="г/л",
    conversions={"г/л": 1.0, "g/L": 1.0, "мг/дл": 0.01, "mg/dL": 0.01}
)

_register_analyte(
    canonical_name="Тромбиновое время",
    synonyms=["Тромбиновое время", "ТВ", "TT", "Thrombin Time"],
    category="Коагулограмма",
    standard_unit="сек",
    conversions={"сек": 1.0, "с": 1.0, "sec": 1.0, "s": 1.0}
)

_register_analyte(
    canonical_name="D-димер",
    synonyms=["D-димер", "D-dimer", "D-Dimer"],
    category="Коагулограмма",
    standard_unit="нг/мл",
    conversions={"нг/мл": 1.0, "ng/mL": 1.0, "мкг/л": 1.0, "µg/L": 1.0}
)

# ============================================================================
# ГОРМОНЫ
# ============================================================================

_register_analyte(
    canonical_name="ТТГ",
    synonyms=["ТТГ", "Тиреотропный гормон", "Тиреотропный гормон (ТТГ)", "TSH", "Thyroid Stimulating Hormone"],
    category="Гормоны",
    standard_unit="мМЕ/л",
    conversions={"мМЕ/л": 1.0, "mIU/L": 1.0, "мкМЕ/мл": 1.0, "µIU/mL": 1.0}
)

_register_analyte(
    canonical_name="Т4 свободный",
    synonyms=["Т4 свободный", "Тироксин свободный", "Тироксин свободный (св.Т4)", "Free T4", "FT4", "св.Т4"],
    category="Гормоны",
    standard_unit="пмоль/л",
    conversions={"пмоль/л": 1.0, "pmol/L": 1.0, "нг/дл": 12.87, "ng/dL": 12.87}
)

_register_analyte(
    canonical_name="Т3 свободный",
    synonyms=["Т3 свободный", "Трийодтиронин свободный", "Free T3", "FT3", "св.Т3"],
    category="Гормоны",
    standard_unit="пмоль/л",
    conversions={"пмоль/л": 1.0, "pmol/L": 1.0, "пг/мл": 1.536, "pg/mL": 1.536}
)

_register_analyte(
    canonical_name="ФСГ",
    synonyms=["ФСГ", "Фолликулостимулирующий гормон", "FSH", "Follicle Stimulating Hormone"],
    category="Гормоны",
    standard_unit="мМЕ/мл",
    conversions={"мМЕ/мл": 1.0, "mIU/mL": 1.0, "МЕ/л": 1.0, "IU/L": 1.0}
)

_register_analyte(
    canonical_name="ЛГ",
    synonyms=["ЛГ", "Лютеинизирующий гормон", "LH", "Luteinizing Hormone"],
    category="Гормоны",
    standard_unit="мМЕ/мл",
    conversions={"мМЕ/мл": 1.0, "mIU/mL": 1.0, "МЕ/л": 1.0, "IU/L": 1.0}
)

_register_analyte(
    canonical_name="Пролактин",
    synonyms=["Пролактин", "Prolactin", "PRL"],
    category="Гормоны",
    standard_unit="мМЕ/л",
    conversions={"мМЕ/л": 1.0, "mIU/L": 1.0, "нг/мл": 21.2, "ng/mL": 21.2, "мкг/л": 21.2, "µg/L": 21.2}
)

_register_analyte(
    canonical_name="Тестостерон",
    synonyms=["Тестостерон", "Testosterone", "TEST"],
    category="Гормоны",
    standard_unit="нмоль/л",
    conversions={"нмоль/л": 1.0, "nmol/L": 1.0, "нг/дл": 0.0347, "ng/dL": 0.0347}
)

_register_analyte(
    canonical_name="Эстрадиол",
    synonyms=["Эстрадиол", "Estradiol", "E2"],
    category="Гормоны",
    standard_unit="пмоль/л",
    conversions={"пмоль/л": 1.0, "pmol/L": 1.0, "пг/мл": 3.671, "pg/mL": 3.671}
)

_register_analyte(
    canonical_name="ГСПГ",
    synonyms=["ГСПГ", "Глобулин, связывающий половые гормоны", "SHBG", "Sex Hormone Binding Globulin"],
    category="Гормоны",
    standard_unit="нмоль/л",
    conversions={"нмоль/л": 1.0, "nmol/L": 1.0}
)

_register_analyte(
    canonical_name="Кортизол",
    synonyms=["Кортизол", "Cortisol"],
    category="Гормоны",
    standard_unit="нмоль/л",
    conversions={"нмоль/л": 1.0, "nmol/L": 1.0, "мкг/дл": 27.59, "µg/dL": 27.59}
)

_register_analyte(
    canonical_name="Инсулин",
    synonyms=["Инсулин", "Insulin", "INS"],
    category="Гормоны",
    standard_unit="мкМЕ/мл",
    conversions={"мкМЕ/мл": 1.0, "µIU/mL": 1.0, "мМЕ/л": 1.0, "mIU/L": 1.0}
)

# ============================================================================
# ВИТАМИНЫ И МИКРОЭЛЕМЕНТЫ
# ============================================================================

_register_analyte(
    canonical_name="Витамин D (25-OH)",
    synonyms=["Витамин D (25-OH)", "Витамин 25(OH) D", "Витамин D, 25-гидрокси", 
              "Витамин D, 25-гидрокси (кальциферол)", "25-OH Vitamin D", "Vitamin D", "25(OH)D"],
    category="Витамины и микроэлементы",
    standard_unit="нг/мл",
    conversions={
        "нг/мл": 1.0,
        "ng/mL": 1.0,
        "нмоль/л": 0.4,  # нмоль/л × 0.4 = нг/мл
        "nmol/L": 0.4,
    }
)

_register_analyte(
    canonical_name="Витамин B12",
    synonyms=["Витамин B12", "Vitamin B12", "Cobalamin", "Кобаламин", "B12"],
    category="Витамины и микроэлементы",
    standard_unit="пг/мл",
    conversions={
        "пг/мл": 1.0,
        "pg/mL": 1.0,
        "пмоль/л": 1.355,  # пмоль/л × 1.355 = пг/мл
        "pmol/L": 1.355,
    }
)

_register_analyte(
    canonical_name="Фолаты",
    synonyms=["Фолаты", "Фолиевая кислота", "Folate", "Folic Acid", "Витамин B9"],
    category="Витамины и микроэлементы",
    standard_unit="нг/мл",
    conversions={
        "нг/мл": 1.0,
        "ng/mL": 1.0,
        "нмоль/л": 0.441,  # нмоль/л × 0.441 = нг/мл
        "nmol/L": 0.441,
    }
)

_register_analyte(
    canonical_name="Ферритин",
    synonyms=["Ферритин", "Ferritin", "FER"],
    category="Витамины и микроэлементы",
    standard_unit="нг/мл",
    conversions={
        "нг/мл": 1.0,
        "ng/mL": 1.0,
        "мкг/л": 1.0,  # мкг/л = нг/мл
        "µg/L": 1.0,
    }
)

# ============================================================================
# МАРКЕРЫ ВОСПАЛЕНИЯ
# ============================================================================

_register_analyte(
    canonical_name="С-реактивный белок",
    synonyms=["С-реактивный белок", "СРБ", "CRP", "C-Reactive Protein", "С-реактивный белок (hs)"],
    category="Маркеры воспаления",
    standard_unit="мг/л",
    conversions={"мг/л": 1.0, "mg/L": 1.0, "мг/дл": 10.0, "mg/dL": 10.0}
)

_register_analyte(
    canonical_name="Ревматоидный фактор",
    synonyms=["Ревматоидный фактор", "РФ", "RF", "Rheumatoid Factor"],
    category="Маркеры воспаления",
    standard_unit="МЕ/мл",
    conversions={"МЕ/мл": 1.0, "IU/mL": 1.0}
)

_register_analyte(
    canonical_name="Антистрептолизин О",
    synonyms=["Антистрептолизин О", "АСЛ-О", "ASLO", "ASO", "Antistreptolysin O"],
    category="Маркеры воспаления",
    standard_unit="МЕ/мл",
    conversions={"МЕ/мл": 1.0, "IU/mL": 1.0}
)

# ============================================================================
# ОБЩИЙ АНАЛИЗ МОЧИ
# ============================================================================

_register_analyte(
    canonical_name="pH мочи",
    synonyms=["pH мочи", "pH", "PH мочи", "Кислотность мочи"],
    category="Общий анализ мочи",
    standard_unit="ед. pH",
    conversions={"ед. pH": 1.0, "pH": 1.0, "": 1.0}
)

_register_analyte(
    canonical_name="Плотность мочи",
    synonyms=["Плотность мочи", "Относительная плотность", "Relative Density", "SG", "Удельный вес"],
    category="Общий анализ мочи",
    standard_unit="г/мл",
    conversions={"г/мл": 1.0, "g/mL": 1.0, "г/л": 0.001}
)

_register_analyte(
    canonical_name="Белок в моче",
    synonyms=["Белок в моче", "Белок", "Protein (urine)", "PRO"],
    category="Общий анализ мочи",
    standard_unit="г/л",
    conversions={"г/л": 1.0, "g/L": 1.0, "мг/дл": 0.01, "mg/dL": 0.01}
)

_register_analyte(
    canonical_name="Глюкоза в моче",
    synonyms=["Глюкоза в моче", "Glucose (urine)", "GLU (urine)"],
    category="Общий анализ мочи",
    standard_unit="ммоль/л",
    conversions={"ммоль/л": 1.0, "mmol/L": 1.0, "мг/дл": 0.0555, "mg/dL": 0.0555}
)

_register_analyte(
    canonical_name="Кетоновые тела",
    synonyms=["Кетоновые тела", "Ketones", "Кетоны", "KET"],
    category="Общий анализ мочи",
    standard_unit="ммоль/л",
    conversions={"ммоль/л": 1.0, "mmol/L": 1.0}
)

_register_analyte(
    canonical_name="Уробилиноген",
    synonyms=["Уробилиноген", "Urobilinogen", "UBG"],
    category="Общий анализ мочи",
    standard_unit="мкмоль/л",
    conversions={"мкмоль/л": 1.0, "µmol/L": 1.0}
)

_register_analyte(
    canonical_name="Лейкоциты (моча)",
    synonyms=["Лейкоциты (моча)", "Лейкоциты в моче", "WBC (urine)"],
    category="Общий анализ мочи",
    standard_unit="в п/зр",
    conversions={"в п/зр": 1.0, "п/зр": 1.0, "п/зр.": 1.0, "кл/мкл": 1.0}
)

_register_analyte(
    canonical_name="Эритроциты (моча)",
    synonyms=["Эритроциты (моча)", "Эритроциты в моче", "RBC (urine)"],
    category="Общий анализ мочи",
    standard_unit="в п/зр",
    conversions={"в п/зр": 1.0, "п/зр": 1.0, "п/зр.": 1.0, "кл/мкл": 1.0}
)

_register_analyte(
    canonical_name="Эпителий плоский",
    synonyms=["Эпителий плоский", "Эпителий", "Squamous Epithelial Cells", "Клетки плоского эпителия"],
    category="Общий анализ мочи",
    standard_unit="в п/зр",
    conversions={"в п/зр": 1.0, "п/зр": 1.0, "п/зр.": 1.0, "кл/мкл": 1.0}
)

_register_analyte(
    canonical_name="Бактерии (моча)",
    synonyms=["Бактерии (моча)", "Бактерии", "Bacteria (urine)"],
    category="Общий анализ мочи",
    standard_unit="в п/зр",
    conversions={"в п/зр": 1.0, "п/зр": 1.0, "п/зр.": 1.0, "в 1 мкл": 1.0}
)

_register_analyte(
    canonical_name="Цилиндры гиалиновые",
    synonyms=["Цилиндры гиалиновые", "Гиалиновые цилиндры", "Hyaline Casts"],
    category="Общий анализ мочи",
    standard_unit="в п/зр",
    conversions={"в п/зр": 1.0, "п/зр": 1.0, "п/зр.": 1.0, "в 1 мкл": 1.0}
)

# ============================================================================
# ИНФЕКЦИИ
# ============================================================================

_register_analyte(
    canonical_name="HBsAg",
    synonyms=["HBsAg", "Антиген HBs", "Hepatitis B Surface Antigen", "Гепатит B (поверхностный антиген)"],
    category="Инфекции",
    standard_unit="",
    conversions={"": 1.0}
)

_register_analyte(
    canonical_name="Anti-HCV",
    synonyms=["Anti-HCV", "anti-HCV суммарные", "Антитела к HCV", "Hepatitis C Antibodies"],
    category="Инфекции",
    standard_unit="",
    conversions={"": 1.0}
)

_register_analyte(
    canonical_name="Anti-HIV",
    synonyms=["Anti-HIV", "anti-HIV 1/2", "ВИЧ", "HIV Antibodies"],
    category="Инфекции",
    standard_unit="",
    conversions={"": 1.0}
)

_register_analyte(
    canonical_name="Сифилис (антитела)",
    synonyms=["Сифилис (антитела)", "anti-Treponema pallidum суммарные", "Treponema pallidum", "RW", "RPR"],
    category="Инфекции",
    standard_unit="",
    conversions={"": 1.0}
)


class AnalyteNormalizationService:
    """Сервис для нормализации названий анализов и конвертации единиц измерения"""
    
    @classmethod
    def get_canonical_name(cls, test_name: str) -> Optional[str]:
        """
        Возвращает каноническое название анализа по любому из синонимов.
        
        Args:
            test_name: Название анализа из документа
            
        Returns:
            Каноническое название или None если не найдено
        """
        if not test_name:
            return None
        
        normalized = test_name.lower().strip()
        return _SYNONYM_INDEX.get(normalized)
    
    @classmethod
    def get_standard(cls, canonical_name: str) -> Optional[AnalyteStandard]:
        """Возвращает стандарт анализа по каноническому названию"""
        return ANALYTE_STANDARDS.get(canonical_name)
    
    @classmethod
    def get_standard_unit(cls, canonical_name: str) -> Optional[str]:
        """Возвращает стандартную единицу измерения для анализа"""
        standard = cls.get_standard(canonical_name)
        return standard.standard_unit if standard else None
    
    @classmethod
    def get_category(cls, canonical_name: str) -> Optional[str]:
        """Возвращает категорию анализа"""
        standard = cls.get_standard(canonical_name)
        return standard.category if standard else None
    
    @classmethod
    def convert_value(
        cls, 
        value: Any, 
        from_unit: Optional[str], 
        canonical_name: str
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Конвертирует значение в стандартную единицу измерения.
        
        Args:
            value: Значение анализа (строка или число)
            from_unit: Исходная единица измерения
            canonical_name: Каноническое название анализа
            
        Returns:
            Кортеж (конвертированное_значение, стандартная_единица)
        """
        standard = cls.get_standard(canonical_name)
        if not standard:
            return None, None
        
        # Парсим значение
        if value is None:
            return None, standard.standard_unit
        
        try:
            numeric_value = float(str(value).replace(',', '.').strip())
        except (ValueError, TypeError):
            return None, standard.standard_unit
        
        # Ищем коэффициент конвертации
        if from_unit:
            # Нормализуем единицу для поиска
            normalized_unit = from_unit.strip()
            
            if normalized_unit in standard.conversions:
                coefficient = standard.conversions[normalized_unit]
                return numeric_value * coefficient, standard.standard_unit
            
            # Попробуем найти близкое совпадение
            for unit_key, coefficient in standard.conversions.items():
                if unit_key.lower() == normalized_unit.lower():
                    return numeric_value * coefficient, standard.standard_unit
        
        # Если конвертация не найдена, возвращаем исходное значение
        return numeric_value, standard.standard_unit
    
    @classmethod
    def normalize_and_convert(
        cls,
        test_name: str,
        value: Any,
        unit: Optional[str]
    ) -> Tuple[Optional[str], Optional[float], Optional[str], Optional[str]]:
        """
        Полная нормализация: название + значение + единица + категория.
        
        Args:
            test_name: Название анализа из документа
            value: Значение
            unit: Единица измерения
            
        Returns:
            Кортеж (canonical_name, converted_value, standard_unit, category)
        """
        canonical_name = cls.get_canonical_name(test_name)
        
        if not canonical_name:
            # Анализ не найден в справочнике
            return None, None, None, None
        
        converted_value, standard_unit = cls.convert_value(value, unit, canonical_name)
        category = cls.get_category(canonical_name)
        
        return canonical_name, converted_value, standard_unit, category
    
    @classmethod
    def normalize_lab_result(cls, lab_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Нормализует результат анализа.
        
        Args:
            lab_result: Словарь с результатом анализа
                {
                    "test_name": str,
                    "value": str,
                    "unit": str | None,
                    "reference_range": str | None,
                    "flag": str | None
                }
            
        Returns:
            Нормализованный результат с дополнительными полями:
                {
                    ...original_fields,
                    "canonical_name": str | None,
                    "converted_value": float | None,
                    "standard_unit": str | None,
                    "category": str | None
                }
        """
        result = lab_result.copy()
        
        test_name = lab_result.get("test_name", "")
        value = lab_result.get("value")
        unit = lab_result.get("unit")
        
        canonical_name, converted_value, standard_unit, category = cls.normalize_and_convert(
            test_name, value, unit
        )
        
        result["canonical_name"] = canonical_name
        result["converted_value"] = converted_value
        result["standard_unit"] = standard_unit
        result["category"] = category
        
        return result
    
    @classmethod
    def get_all_categories(cls) -> List[str]:
        """Возвращает список всех категорий"""
        categories = set()
        for standard in ANALYTE_STANDARDS.values():
            categories.add(standard.category)
        return sorted(list(categories))
    
    @classmethod
    def get_analytes_by_category(cls, category: str) -> List[str]:
        """Возвращает список канонических названий анализов для категории"""
        analytes = []
        for name, standard in ANALYTE_STANDARDS.items():
            if standard.category == category:
                analytes.append(name)
        return sorted(analytes)
    
    @classmethod
    def is_known_analyte(cls, test_name: str) -> bool:
        """Проверяет, известен ли анализ в справочнике"""
        return cls.get_canonical_name(test_name) is not None
    
    @classmethod
    def get_all_synonyms(cls) -> Dict[str, List[str]]:
        """Возвращает словарь всех синонимов по каноническим названиям"""
        return {name: standard.synonyms for name, standard in ANALYTE_STANDARDS.items()}


# Глобальный экземпляр сервиса
analyte_normalization_service = AnalyteNormalizationService()

