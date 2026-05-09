-- Migration: 016_align_prod_canonicals_with_dev
-- Description: Align prod-only variant canonical names with dev-canonical names so the
--   LOINC + reference seeds from migration 015 also apply on prod. Idempotent on dev
--   (target canonicals already exist there → variant rows are merged into them).
-- Date: 2026-05-09
--
-- Что делает:
--   1. Для каждой целевой канонической записи (target_name) ищет варианты на текущем контуре.
--      Если target_name уже существует — все варианты сливаются в неё (synonyms +
--      user_analyte_mappings переносятся, дубли удаляются). Если target_name отсутствует,
--      promotion: вариант с наибольшим числом synonyms переименовывается в target_name,
--      остальные варианты сливаются в него.
--   2. Для канонов, которых нет ни в каком виде ни на проде, ни на деве (Т3 свободный, ОЖСС),
--      выполняется INSERT.
--   3. В конце повторяется UPDATE LOINC + reference values из миграции 015 для тех 14 канонов,
--      которые иначе не получили бы их.
--
-- Безопасность: ON DELETE CASCADE на analyte_synonyms и unit_conversions сработает только
-- ПОСЛЕ переноса synonyms через UPDATE. analyte_id в user_analyte_mappings перепривязываем
-- явно (там SET NULL on delete, так что без переноса данные потерялись бы).

-- ============================================================================
-- Шаг 1. Слияние вариантов в целевые canonical_name
-- ============================================================================
DO $$
DECLARE
    rec                  RECORD;
    target_id            UUID;
    primary_id           UUID;
    variant_id           UUID;
    variant_name_iter    TEXT;
    has_unit_conversions BOOLEAN;
BEGIN
    -- Таблица unit_conversions есть только на dev (была добавлена скриптом seed_*),
    -- на проде её ещё нет — поэтому работаем с ней только если она существует.
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'unit_conversions'
    ) INTO has_unit_conversions;
    FOR rec IN SELECT * FROM (VALUES
        ('Лимфоциты',                  '%',       ARRAY['(LYM%) Лимфоциты','Лимфоциты (%)','Лимфоциты, %']),
        ('Нейтрофилы',                 '%',       ARRAY['(NEU%) Нейтрофилы','Нейтрофилы (%)','Нейтрофилы, %','Нейтрофилы (общ.число)','Нейтрофилы (общ.число), %']),
        ('Моноциты',                   '%',       ARRAY['(MONO%) Моноциты','Моноциты (%)','Моноциты, %']),
        ('Эозинофилы',                 '%',       ARRAY['(EOS%) Эозинофилы','Эозинофилы (%)','Эозинофилы, %']),
        ('Базофилы',                   '%',       ARRAY['(BAS%) Базофилы','Базофилы (%)','Базофилы, %']),
        ('Аланинаминотрансфераза',     'Ед/л',    ARRAY['Аланинаминотрансфераза (АЛТ)']),
        ('Аспартатаминотрансфераза',   'Ед/л',    ARRAY['Аспартатаминотрансфераза (АСТ)']),
        ('Холестерин-ЛПНП',            'ммоль/л', ARRAY['Холестерин-ЛПНП (липопротеины низкой плотности)','Холестерин-ЛПНП (по Фридвальду)','Холестерин липопротеинов низкой плотности (ЛПНП)','Определение липопротеинов низкой плотности (ЛПНП-бета)']),
        ('ТТГ',                        'мЕд/л',   ARRAY['Тиреотропный гормон (ТТГ)','Тиреотропный гормон: ТТГ','Определение тиреотропина, тиротропина, тиреоидного гормона (ТТГ)']),
        ('Т4 свободный',               'пмоль/л', ARRAY['Тироксин свободный: св.Т4','Тироксин свободный','Свободный тироксин']),
        ('Витамин D (25-OH)',          'нг/мл',   ARRAY['Витамин 25(ОН) D','Витамин D суммарный (25-OH D2 и D3, общий результат)','Витамин D, 25-гидрокси (кальциферол), ИХЛ']),
        ('Витамин B12',                'пг/мл',   ARRAY['Витамин В 12','Витамин В12'])  -- prod variants used Cyrillic В; target uses Latin B
    ) AS t(target_name, target_unit, variants)
    LOOP
        -- Шаг 1а: найти target по точному имени
        SELECT id INTO target_id FROM analyte_standards WHERE canonical_name = rec.target_name;

        -- Шаг 1б: если нет — promote вариант с наибольшим числом synonyms
        IF target_id IS NULL THEN
            SELECT a.id INTO primary_id
            FROM analyte_standards a
            LEFT JOIN analyte_synonyms s ON s.analyte_id = a.id
            WHERE a.canonical_name = ANY(rec.variants)
            GROUP BY a.id, a.canonical_name
            ORDER BY COUNT(s.id) DESC, a.canonical_name ASC
            LIMIT 1;

            IF primary_id IS NOT NULL THEN
                UPDATE analyte_standards
                SET canonical_name = rec.target_name,
                    standard_unit  = rec.target_unit,
                    updated_at     = NOW()
                WHERE id = primary_id;
                target_id := primary_id;
                RAISE NOTICE 'Promoted variant to canonical: %', rec.target_name;
            END IF;
        END IF;

        IF target_id IS NULL THEN
            RAISE NOTICE 'No variants found for: %  — skipping', rec.target_name;
            CONTINUE;
        END IF;

        -- Шаг 1в: смержить остальные варианты в target
        FOREACH variant_name_iter IN ARRAY rec.variants
        LOOP
            SELECT id INTO variant_id
            FROM analyte_standards
            WHERE canonical_name = variant_name_iter AND id <> target_id;

            CONTINUE WHEN variant_id IS NULL;

            -- Удалить из источника синонимы, чьи (synonym_lower, unit_lower) уже есть в target
            DELETE FROM analyte_synonyms s
            WHERE s.analyte_id = variant_id
              AND EXISTS (
                  SELECT 1 FROM analyte_synonyms t
                  WHERE t.analyte_id = target_id
                    AND t.synonym_lower = s.synonym_lower
                    AND COALESCE(t.unit_lower, '') = COALESCE(s.unit_lower, '')
              );

            -- Перенести оставшиеся синонимы
            UPDATE analyte_synonyms SET analyte_id = target_id WHERE analyte_id = variant_id;

            -- Перенести unit_conversions (только если таблица существует)
            IF has_unit_conversions THEN
                EXECUTE format($q$
                    DELETE FROM unit_conversions u
                    WHERE u.analyte_id = %L
                      AND EXISTS (
                          SELECT 1 FROM unit_conversions u2
                          WHERE u2.analyte_id = %L
                            AND u2.from_unit  = u.from_unit
                      )
                $q$, variant_id, target_id);
                EXECUTE format($q$
                    UPDATE unit_conversions SET analyte_id = %L WHERE analyte_id = %L
                $q$, target_id, variant_id);
            END IF;

            -- Перенести user_analyte_mappings
            UPDATE user_analyte_mappings SET analyte_id = target_id WHERE analyte_id = variant_id;

            -- Удалить вариант
            DELETE FROM analyte_standards WHERE id = variant_id;
            RAISE NOTICE 'Merged variant "%" into "%"', variant_name_iter, rec.target_name;
        END LOOP;

        -- Шаг 1г: убедиться, что target имеет правильную единицу
        UPDATE analyte_standards
        SET standard_unit = rec.target_unit, updated_at = NOW()
        WHERE id = target_id AND standard_unit <> rec.target_unit;
    END LOOP;
END $$;

-- ============================================================================
-- Шаг 2. Добавить полностью отсутствующие каноны (Т3 свободный, ОЖСС)
-- ============================================================================
INSERT INTO analyte_standards (id, category_id, canonical_name, standard_unit, sort_order, is_active)
SELECT gen_random_uuid(), c.id, n.canonical_name, n.standard_unit, 0, true
FROM (VALUES
    ('Т3 свободный', 'пмоль/л', 'Гормоны'),
    ('ОЖСС',         'мкмоль/л', 'Биохимия крови')
) AS n(canonical_name, standard_unit, category_name)
JOIN analyte_categories c ON c.name = n.category_name
ON CONFLICT (canonical_name) DO NOTHING;

-- ============================================================================
-- Шаг 3. Применить LOINC + reference values для 14 канонов из миграции 015,
--        которые могли остаться без значений из-за расхождения имён.
--        UPDATE идемпотентен — на dev переписывает теми же значениями.
-- ============================================================================
WITH refs(canonical_name, loinc_code, loinc_long_name, ucum_unit,
          ref_m_min, ref_m_max, ref_f_min, ref_f_max,
          source) AS (VALUES
    ('Лимфоциты',                '736-9',  'Lymphocytes/100 leukocytes in Blood by Automated count',  '%',       19::numeric, 37::numeric, NULL::numeric, NULL::numeric, 'Tietz 6th ed.'),
    ('Нейтрофилы',               '770-8',  'Neutrophils/100 leukocytes in Blood by Automated count',  '%',       47,          72,          NULL,          NULL,          'Tietz 6th ed.'),
    ('Моноциты',                 '5905-5', 'Monocytes/100 leukocytes in Blood by Automated count',    '%',       3,           11,          NULL,          NULL,          'Tietz 6th ed.'),
    ('Эозинофилы',               '713-8',  'Eosinophils/100 leukocytes in Blood by Automated count',  '%',       0.5,         5,           NULL,          NULL,          'Tietz 6th ed.'),
    ('Базофилы',                 '706-2',  'Basophils/100 leukocytes in Blood by Automated count',    '%',       0,           1,           NULL,          NULL,          'Tietz 6th ed.'),
    ('Аланинаминотрансфераза',   '1742-6', 'Alanine aminotransferase [Enzymatic activity/volume]',    'U/L',     0,           41,          0,             33,            'Tietz 6th ed.'),
    ('Аспартатаминотрансфераза', '1920-8', 'Aspartate aminotransferase [Enzymatic activity/volume]',  'U/L',     0,           40,          0,             32,            'Tietz 6th ed.'),
    ('Холестерин-ЛПНП',          '13457-7','Cholesterol in LDL [Moles/volume] calculated',            'mmol/L',  0,           3.0,         NULL,          NULL,          'Tietz 6th ed.'),
    ('ТТГ',                      '3016-3', 'Thyrotropin [Units/volume] in Serum or Plasma',           'mIU/L',   0.4,         4.0,         NULL,          NULL,          'Tietz 6th ed.'),
    ('Т4 свободный',             '3024-7', 'Thyroxine free [Moles/volume] in Serum or Plasma',        'pmol/L',  9.0,         22.0,        NULL,          NULL,          'Tietz 6th ed.'),
    ('Т3 свободный',             '3051-0', 'Triiodothyronine free [Moles/volume] in Serum or Plasma', 'pmol/L',  2.6,         5.7,         NULL,          NULL,          'Tietz 6th ed.'),
    ('ОЖСС',                     '2502-3', 'Iron binding capacity [Moles/volume] in Serum or Plasma', 'umol/L',  45,          72,          NULL,          NULL,          'Tietz 6th ed.'),
    ('Витамин D (25-OH)',        '14635-7','25-Hydroxyvitamin D3 [Mass/volume] in Serum or Plasma',   'ng/mL',   30,          100,         NULL,          NULL,          'Минздрав РФ КР'),
    ('Витамин B12',              '2132-9', 'Cobalamin (Vitamin B12) [Mass/volume] in Serum or Plasma','pg/mL',   200,         900,         NULL,          NULL,          'Tietz 6th ed.')
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
-- Шаг 4. Нормализация standard_unit для всех 50 канонов (фикс для прода:
--        у "Гемоглобин" исторически пустая единица, нужна для UI/конвертации).
-- ============================================================================
WITH units(canonical_name, standard_unit) AS (VALUES
    ('Гемоглобин','г/л'),                                     ('Эритроциты','10*12/л'),                ('Лейкоциты','10*9/л'),
    ('Тромбоциты','10*9/л'),                                  ('Гематокрит','%'),                      ('Лимфоциты','%'),
    ('Нейтрофилы','%'),                                       ('Моноциты','%'),                        ('Эозинофилы','%'),
    ('Базофилы','%'),                                         ('СОЭ','мм/час'),                        ('Среднее содержание гемоглобина в эритроците','пг'),
    ('Средний объем эритроцита','фл'),                        ('Ширина распределения эритроцитов','%'),('Средний объем тромбоцитов','фл'),
    ('Глюкоза','ммоль/л'),                                    ('Креатинин','мкмоль/л'),                ('Мочевина','ммоль/л'),
    ('Мочевая кислота','мкмоль/л'),                           ('Общий белок','г/л'),                   ('Альбумин','г/л'),
    ('Билирубин общий','мкмоль/л'),                           ('Билирубин прямой','мкмоль/л'),         ('Аланинаминотрансфераза','Ед/л'),
    ('Аспартатаминотрансфераза','Ед/л'),                      ('Гамма-глутамилтрансфераза (ГГТ)','МЕ/л'),
    ('С-реактивный белок','мг/л'),                            ('Холестерин общий','ммоль/л'),          ('Холестерин-ЛПВП','ммоль/л'),
    ('Холестерин-ЛПНП','ммоль/л'),                            ('Триглицериды','ммоль/л'),              ('ТТГ','мЕд/л'),
    ('Т4 свободный','пмоль/л'),                               ('Т3 свободный','пмоль/л'),              ('Железо','мкмоль/л'),
    ('Ферритин','нг/мл'),                                     ('Трансферрин','г/л'),                   ('ОЖСС','мкмоль/л'),
    ('Витамин D (25-OH)','нг/мл'),                            ('Витамин B12','пг/мл'),                 ('Фолаты','нг/мл'),
    ('Калий','ммоль/л'),                                      ('Натрий','ммоль/л'),                    ('Хлор','ммоль/л'),
    ('Кальций общий','ммоль/л'),                              ('Магний','ммоль/л'),                    ('Фосфор','ммоль/л'),
    ('Гликированный гемоглобин','%'),                         ('ПСА общий','нг/мл'),                   ('Альфа-амилаза','МЕ/л')
)
UPDATE analyte_standards a SET
    standard_unit = u.standard_unit,
    updated_at    = NOW()
FROM units u
WHERE a.canonical_name = u.canonical_name
  AND COALESCE(a.standard_unit, '') <> u.standard_unit;

-- ============================================================================
-- Sanity check
-- ============================================================================
DO $$
DECLARE total_seeded INT;
BEGIN
    SELECT COUNT(*) INTO total_seeded
    FROM analyte_standards
    WHERE loinc_code IS NOT NULL;
    RAISE NOTICE 'analyte_standards: % rows now have loinc_code', total_seeded;
END $$;
