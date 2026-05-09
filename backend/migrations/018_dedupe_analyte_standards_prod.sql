-- Migration: 018_dedupe_analyte_standards_prod
-- Description: Доочистка дублей analyte_standards для prod-специфичных названий.
-- Миграция 017 не учла prod-стиль именования (`Foo (CODE)` суффикс vs `(CODE) Foo` префикс,
-- `Моноциты (абс)` без точки vs `Моноциты (абс.)` с точкой), и поэтому ~60 prod-дублей
-- сохранились. Эта миграция целится в актуальное состояние prod.
-- Алгоритм идентичен 017: insert src как синоним target, repoint, delete src.
-- Идемпотентна: пары с отсутствующими src/tgt пропускаются.
-- Date: 2026-05-09

DO $$
DECLARE
    pair RECORD;
    src_id UUID;
    tgt_id UUID;
    src_unit TEXT;
BEGIN
    FOR pair IN SELECT * FROM (VALUES
        -- ОАК: абсолютные количества (10*9/л) — prod-keeper "X (абс)" (без точки)
        ('(MONO#) Моноциты',                                 'Моноциты (абс)'),
        ('Моноциты (MON)',                                   'Моноциты (абс)'),
        ('Моноциты, абс.',                                   'Моноциты (абс)'),
        ('(LYM#) Лимфоциты',                                 'Лимфоциты (абс)'),
        ('Лимфоциты (LYM)',                                  'Лимфоциты (абс)'),
        ('Лимфоциты, абс.',                                  'Лимфоциты (абс)'),
        ('(NEU#) Нейтрофилы',                                'Нейтрофилы (абс)'),
        ('Нейтрофилы (NEU)',                                 'Нейтрофилы (абс)'),
        ('Нейтрофилы, абс.',                                 'Нейтрофилы (абс)'),
        ('(EOS#) Эозинофилы',                                'Эозинофилы (абс)'),
        ('Эозинофилы (EO)',                                  'Эозинофилы (абс)'),
        ('Эозинофилы, абс.',                                 'Эозинофилы (абс)'),
        ('(BAS#) Базофилы',                                  'Базофилы (абс)'),
        ('Базофилы (BA)',                                    'Базофилы (абс)'),
        ('Базофилы, абс.',                                   'Базофилы (абс)'),

        -- ОАК: нормобласты
        ('Абс количество нормобластов',                      'Абсолютное количество нормобластов'),
        ('Отн количество нормобластов',                      'Относительное количество нормобластов'),

        -- ОАК: индексы (Hb / RBC / HCT) — prod-стиль с суффиксом-кодом
        ('Гемоглобин (HGB)',                                 'Гемоглобин'),
        ('Эритроциты (RBC)',                                 'Эритроциты'),
        ('Гематокрит (HCT)',                                 'Гематокрит'),

        -- ОАК: тромбоциты (PCT / PDW)
        ('Общий объем тромбоцитов в крови (тромбокрит, PСT)','Общий объем тромбоцитов в крови (тромбоцитокрит)'),
        ('Тромбокрит (PCT)',                                 'Общий объем тромбоцитов в крови (тромбоцитокрит)'),
        ('Ширина распределения тромбоцитов по объему (PDW)', 'Ширина распределения тромбоцитов по объему'),

        -- ОАК: RDW (% — RDW-CV; фл — RDW-SD)
        ('(RDW-CV)Ширина распределения эритроцитов',         'Ширина распределения эритроцитов'),
        ('RDW (шир. распред. эритр)',                        'Ширина распределения эритроцитов'),
        ('Ширина распределения эритроцитов по объему',       'Ширина распределения эритроцитов'),
        ('(RDW-SD)Ширина распределения эритроцитов',         'Ширина распределения эритроцитов по объему (RDW-SD)'),

        -- Липиды (case-only-different unit мМоль/л ≡ ммоль/л; coefficient=1)
        ('Определение триглицеридов общих',                  'Триглицериды'),
        ('Определение холестерина общего',                   'Холестерин общий'),
        ('Холестерин липопротеинов высокой плотности (ЛПВП)','Холестерин-ЛПВП'),
        ('Определение липопротеинов высокой плотности (ЛПВП-альфа)','Холестерин-ЛПВП'),

        -- Витамины / микроэлементы
        ('Железо в сыворотке',                               'Железо'),
        ('Калий (К+)',                                       'Калий'),
        ('Натрий (Na+)',                                     'Натрий'),
        ('Кальций',                                          'Кальций общий'),

        -- Гликированный (cross-category)
        ('HbA1c (гликированный Hb)',                         'Гликированный гемоглобин'),

        -- Маркеры
        ('Скорость оседания эритроцитов (СОЭ)',              'СОЭ'),

        -- Прочие cross-category
        ('ЛДГ',                                              'Лактатдегидрогеназа (ЛДГ)'),
        ('Фосфатаза щелочная',                               'Щелочная фосфатаза (ЩФ)'),
        ('Мочевая кислота в сыворотке',                      'Мочевая кислота')
    ) AS t(src_name, tgt_name)
    LOOP
        SELECT id, standard_unit INTO src_id, src_unit FROM analyte_standards WHERE canonical_name = pair.src_name;
        SELECT id INTO tgt_id FROM analyte_standards WHERE canonical_name = pair.tgt_name;
        IF src_id IS NULL OR tgt_id IS NULL THEN
            CONTINUE;
        END IF;

        INSERT INTO analyte_synonyms (id, analyte_id, synonym, synonym_lower, unit, unit_lower, coefficient, source, is_primary)
        SELECT uuid_generate_v4(),
               tgt_id,
               pair.src_name,
               lower(pair.src_name),
               COALESCE(src_unit, ''),
               lower(COALESCE(src_unit, '')),
               1.0,
               'migration_018_dedupe_prod',
               false
        WHERE NOT EXISTS (
            SELECT 1 FROM analyte_synonyms s
            WHERE s.synonym_lower = lower(pair.src_name)
              AND COALESCE(s.unit_lower, '') = lower(COALESCE(src_unit, ''))
        );

        DELETE FROM analyte_synonyms s
        WHERE s.analyte_id = src_id
          AND EXISTS (
            SELECT 1 FROM analyte_synonyms t
            WHERE t.analyte_id = tgt_id
              AND t.synonym_lower = s.synonym_lower
              AND COALESCE(t.unit_lower, '') = COALESCE(s.unit_lower, '')
          );

        UPDATE analyte_synonyms SET analyte_id = tgt_id WHERE analyte_id = src_id;
        UPDATE user_analyte_mappings SET analyte_id = tgt_id WHERE analyte_id = src_id;
        DELETE FROM analyte_standards WHERE id = src_id;
    END LOOP;
END $$;
