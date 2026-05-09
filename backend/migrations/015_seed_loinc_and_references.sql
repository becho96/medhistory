-- Migration: 015_seed_loinc_and_references
-- Description: Seed LOINC codes, UCUM units and adult (18+) reference ranges for top-50 analytes
-- Date: 2026-05-09
--
-- Источники референсных значений:
--   * Tietz Textbook of Clinical Chemistry, 6th ed. (2019) — основной источник;
--   * Клинические рекомендации Минздрава РФ — для специфики российской практики.
--
-- Конвенция:
--   * Только взрослые (18+ лет). Педиатрические нормы — отдельная задача.
--   * Если анализ гендер-нейтрален, заполняется только пара male_min/max,
--     female_*_min/max остаются NULL. API в documents.py использует fallback:
--     если у пользователя female и female-значения = NULL → используются male.
--   * Если анализ гендер-зависимый (Hgb, RBC, Hct, СОЭ, Креатинин, Мочевая
--     кислота, АЛТ, АСТ, ГГТ, Железо, Ферритин), заполнены обе пары.
--   * Качественные/мочевые показатели (pH мочи, бактерии, эпителий, белок мочи)
--     в этот список не вошли — для них референс не оформляется числовым диапазоном.

-- ============================================================================
-- Шаг 1. Добавить недостающие канонические записи (6 шт.)
-- ============================================================================
INSERT INTO analyte_standards (id, category_id, canonical_name, standard_unit, sort_order, is_active)
SELECT gen_random_uuid(), c.id, n.canonical_name, n.standard_unit, 0, true
FROM (VALUES
    ('Альбумин',                  'г/л',     'Биохимия крови'),
    ('Гликированный гемоглобин',  '%',       'Биохимия крови'),
    ('Кальций общий',             'ммоль/л', 'Биохимия крови'),
    ('Трансферрин',               'г/л',     'Биохимия крови'),
    ('Фосфор',                    'ммоль/л', 'Биохимия крови'),
    ('ПСА общий',                 'нг/мл',   'Другие анализы')
) AS n(canonical_name, standard_unit, category_name)
JOIN analyte_categories c ON c.name = n.category_name
ON CONFLICT (canonical_name) DO NOTHING;

-- ============================================================================
-- Шаг 2. UPDATE LOINC + UCUM + reference values для топ-50 анализов
-- ============================================================================
WITH refs(canonical_name, loinc_code, loinc_long_name, ucum_unit,
          ref_m_min, ref_m_max, ref_f_min, ref_f_max,
          source) AS (VALUES
    -- ОАК (15 показателей)
    ('Гемоглобин',                                       '718-7',   'Hemoglobin [Mass/volume] in Blood',                        'g/L',     130::numeric, 160::numeric, 120::numeric, 150::numeric, 'Tietz 6th ed.'),
    ('Эритроциты',                                       '789-8',   'Erythrocytes [#/volume] in Blood by Automated count',       '10*12/L', 4.0,          5.5,          3.7,          4.7,          'Tietz 6th ed.'),
    ('Лейкоциты',                                        '6690-2',  'Leukocytes [#/volume] in Blood by Automated count',         '10*9/L',  4.0,          9.0,          NULL,         NULL,         'Tietz 6th ed.'),
    ('Тромбоциты',                                       '777-3',   'Platelets [#/volume] in Blood by Automated count',          '10*9/L',  150,          400,          NULL,         NULL,         'Tietz 6th ed.'),
    ('Гематокрит',                                       '4544-3',  'Hematocrit [Volume Fraction] of Blood by Automated count',  '%',       40,           48,           36,           46,           'Tietz 6th ed.'),
    ('Лимфоциты',                                        '736-9',   'Lymphocytes/100 leukocytes in Blood by Automated count',    '%',       19,           37,           NULL,         NULL,         'Tietz 6th ed.'),
    ('Нейтрофилы',                                       '770-8',   'Neutrophils/100 leukocytes in Blood by Automated count',    '%',       47,           72,           NULL,         NULL,         'Tietz 6th ed.'),
    ('Моноциты',                                         '5905-5',  'Monocytes/100 leukocytes in Blood by Automated count',      '%',       3,            11,           NULL,         NULL,         'Tietz 6th ed.'),
    ('Эозинофилы',                                       '713-8',   'Eosinophils/100 leukocytes in Blood by Automated count',    '%',       0.5,          5,            NULL,         NULL,         'Tietz 6th ed.'),
    ('Базофилы',                                         '706-2',   'Basophils/100 leukocytes in Blood by Automated count',      '%',       0,            1,            NULL,         NULL,         'Tietz 6th ed.'),
    ('СОЭ',                                              '4537-7',  'Erythrocyte sedimentation rate by Westergren method',       'mm/h',    0,            15,           0,            20,           'Tietz 6th ed.'),
    ('Среднее содержание гемоглобина в эритроците',      '785-6',   'MCH [Entitic mass] by Automated count',                     'pg',      27,           33,           NULL,         NULL,         'Tietz 6th ed.'),
    ('Средний объем эритроцита',                         '787-2',   'MCV [Entitic volume] by Automated count',                   'fL',      80,           100,          NULL,         NULL,         'Tietz 6th ed.'),
    ('Ширина распределения эритроцитов',                 '788-0',   'Erythrocyte distribution width [Ratio] by Automated count', '%',       11.5,         14.5,         NULL,         NULL,         'Tietz 6th ed.'),
    ('Средний объем тромбоцитов',                        '32623-1', 'Platelet mean volume [Entitic volume] in Blood',            'fL',      7.5,          11.5,         NULL,         NULL,         'Tietz 6th ed.'),

    -- Биохимия (12)
    ('Глюкоза',                                          '14749-6', 'Glucose [Moles/volume] in Serum or Plasma',                 'mmol/L',  3.9,          5.6,          NULL,         NULL,         'Tietz 6th ed.'),
    ('Креатинин',                                        '2160-0',  'Creatinine [Mass/volume] in Serum or Plasma',               'umol/L',  62,           115,          53,           97,           'Tietz 6th ed.'),
    ('Мочевина',                                         '3094-0',  'Urea nitrogen [Mass/volume] in Serum or Plasma',            'mmol/L',  2.5,          8.3,          NULL,         NULL,         'Tietz 6th ed.'),
    ('Мочевая кислота',                                  '3084-1',  'Urate [Mass/volume] in Serum or Plasma',                    'umol/L',  200,          420,          140,          340,          'Tietz 6th ed.'),
    ('Общий белок',                                      '2885-2',  'Protein [Mass/volume] in Serum or Plasma',                  'g/L',     64,           83,           NULL,         NULL,         'Tietz 6th ed.'),
    ('Альбумин',                                         '1751-7',  'Albumin [Mass/volume] in Serum or Plasma',                  'g/L',     35,           52,           NULL,         NULL,         'Tietz 6th ed.'),
    ('Билирубин общий',                                  '1975-2',  'Bilirubin.total [Mass/volume] in Serum or Plasma',          'umol/L',  5,            21,           NULL,         NULL,         'Tietz 6th ed.'),
    ('Билирубин прямой',                                 '1968-7',  'Bilirubin.direct [Mass/volume] in Serum or Plasma',         'umol/L',  0,            5,            NULL,         NULL,         'Tietz 6th ed.'),
    ('Аланинаминотрансфераза',                           '1742-6',  'Alanine aminotransferase [Enzymatic activity/volume]',      'U/L',     0,            41,           0,            33,           'Tietz 6th ed.'),
    ('Аспартатаминотрансфераза',                         '1920-8',  'Aspartate aminotransferase [Enzymatic activity/volume]',    'U/L',     0,            40,           0,            32,           'Tietz 6th ed.'),
    ('Гамма-глутамилтрансфераза (ГГТ)',                  '2324-2',  'Gamma glutamyl transferase [Enzymatic activity/volume]',    'U/L',     0,            55,           0,            38,           'Tietz 6th ed.'),
    ('С-реактивный белок',                               '1988-5',  'C reactive protein [Mass/volume] in Serum or Plasma',       'mg/L',    0,            5,            NULL,         NULL,         'Tietz 6th ed.'),

    -- Липидный профиль (4)
    ('Холестерин общий',                                 '2093-3',  'Cholesterol [Moles/volume] in Serum or Plasma',             'mmol/L',  0,            5.2,          NULL,         NULL,         'Tietz 6th ed.'),
    ('Холестерин-ЛПВП',                                  '2085-9',  'Cholesterol in HDL [Moles/volume] in Serum or Plasma',      'mmol/L',  1.0,          2.5,          1.2,          2.5,          'Tietz 6th ed.'),
    ('Холестерин-ЛПНП',                                  '13457-7', 'Cholesterol in LDL [Moles/volume] calculated',              'mmol/L',  0,            3.0,          NULL,         NULL,         'Tietz 6th ed.'),
    ('Триглицериды',                                     '2571-8',  'Triglyceride [Moles/volume] in Serum or Plasma',            'mmol/L',  0,            1.7,          NULL,         NULL,         'Tietz 6th ed.'),

    -- Тиреоидная панель (3)
    ('ТТГ',                                              '3016-3',  'Thyrotropin [Units/volume] in Serum or Plasma',             'mIU/L',   0.4,          4.0,          NULL,         NULL,         'Tietz 6th ed.'),
    ('Т4 свободный',                                     '3024-7',  'Thyroxine free [Moles/volume] in Serum or Plasma',          'pmol/L',  9.0,          22.0,         NULL,         NULL,         'Tietz 6th ed.'),
    ('Т3 свободный',                                     '3051-0',  'Triiodothyronine free [Moles/volume] in Serum or Plasma',   'pmol/L',  2.6,          5.7,          NULL,         NULL,         'Tietz 6th ed.'),

    -- Железо/обмен железа + витамины (6)
    ('Железо',                                           '2498-4',  'Iron [Moles/volume] in Serum or Plasma',                    'umol/L',  11.0,         30.0,         9.0,          30.0,         'Tietz 6th ed.'),
    ('Ферритин',                                         '2276-4',  'Ferritin [Mass/volume] in Serum or Plasma',                 'ug/L',    30,           400,          13,           150,          'Tietz 6th ed.'),
    ('Трансферрин',                                      '3034-6',  'Transferrin [Mass/volume] in Serum or Plasma',              'g/L',     2.0,          3.6,          NULL,         NULL,         'Tietz 6th ed.'),
    ('ОЖСС',                                             '2502-3',  'Iron binding capacity [Moles/volume] in Serum or Plasma',   'umol/L',  45,           72,           NULL,         NULL,         'Tietz 6th ed.'),
    ('Витамин D (25-OH)',                                '14635-7', '25-Hydroxyvitamin D3 [Mass/volume] in Serum or Plasma',     'ng/mL',   30,           100,          NULL,         NULL,         'Минздрав РФ КР'),
    ('Витамин B12',                                      '2132-9',  'Cobalamin (Vitamin B12) [Mass/volume] in Serum or Plasma',  'pg/mL',   200,          900,          NULL,         NULL,         'Tietz 6th ed.'),
    ('Фолаты',                                           '2284-8',  'Folate [Mass/volume] in Serum or Plasma',                   'ng/mL',   3.0,          17.0,         NULL,         NULL,         'Tietz 6th ed.'),

    -- Электролиты (5)
    ('Калий',                                            '2823-3',  'Potassium [Moles/volume] in Serum or Plasma',               'mmol/L',  3.5,          5.1,          NULL,         NULL,         'Tietz 6th ed.'),
    ('Натрий',                                           '2951-2',  'Sodium [Moles/volume] in Serum or Plasma',                  'mmol/L',  136,          145,          NULL,         NULL,         'Tietz 6th ed.'),
    ('Хлор',                                             '2075-0',  'Chloride [Moles/volume] in Serum or Plasma',                'mmol/L',  98,           107,          NULL,         NULL,         'Tietz 6th ed.'),
    ('Кальций общий',                                    '17861-6', 'Calcium [Moles/volume] in Serum or Plasma',                 'mmol/L',  2.15,         2.55,         NULL,         NULL,         'Tietz 6th ed.'),
    ('Магний',                                           '19123-9', 'Magnesium [Moles/volume] in Serum or Plasma',               'mmol/L',  0.66,         1.07,         NULL,         NULL,         'Tietz 6th ed.'),
    ('Фосфор',                                           '14879-1', 'Phosphate [Moles/volume] in Serum or Plasma',               'mmol/L',  0.81,         1.45,         NULL,         NULL,         'Tietz 6th ed.'),

    -- Диабет / онкомаркер / поджелудочная (3)
    ('Гликированный гемоглобин',                         '4548-4',  'Hemoglobin A1c/Hemoglobin.total in Blood',                  '%',       4.0,          5.6,          NULL,         NULL,         'ADA / Минздрав РФ КР'),
    ('ПСА общий',                                        '2857-1',  'Prostate specific Ag [Mass/volume] in Serum or Plasma',     'ng/mL',   0,            4.0,          NULL,         NULL,         'Tietz 6th ed.'),
    ('Альфа-амилаза',                                    '1798-8',  'Amylase [Enzymatic activity/volume] in Serum or Plasma',    'U/L',     28,           100,          NULL,         NULL,         'Tietz 6th ed.')
)
UPDATE analyte_standards a SET
    loinc_code           = r.loinc_code,
    loinc_long_name      = r.loinc_long_name,
    ucum_unit            = r.ucum_unit,
    reference_male_min   = r.ref_m_min,
    reference_male_max   = r.ref_m_max,
    reference_female_min = r.ref_f_min,
    reference_female_max = r.ref_f_max,
    reference_source     = r.source,
    updated_at           = NOW()
FROM refs r
WHERE a.canonical_name = r.canonical_name;

-- ============================================================================
-- Шаг 3. Sanity-check (не падаем, просто отчёт)
-- ============================================================================
DO $$
DECLARE
    total_seeded INT;
BEGIN
    SELECT COUNT(*) INTO total_seeded
    FROM analyte_standards
    WHERE loinc_code IS NOT NULL;
    RAISE NOTICE 'analyte_standards: % rows now have loinc_code', total_seeded;
END $$;
