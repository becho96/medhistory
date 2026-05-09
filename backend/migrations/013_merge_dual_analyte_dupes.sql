-- Migration: 013_merge_dual_analyte_dupes
-- Description: Слить дубли DUAL-анализов "Абсолютное/Относительное количество X" → "X (абс)" / "X (%)".
-- Дубли создавал seed-скрипт, когда в исходных данных встречались длинные test_name без алиаса.
-- После расширения NAME_ALIASES (scripts/seed_analyte_mappings_from_csv.py) новые сидирования
-- таких дублей не создают — миграция чистит уже накопленные.
-- Идемпотентна: если src или tgt не существует, пара пропускается.
-- Date: 2026-05-09

DO $$
DECLARE
    pair RECORD;
    src_id UUID;
    tgt_id UUID;
BEGIN
    FOR pair IN SELECT * FROM (VALUES
        ('Абсолютное количество эозинофилов',   'Эозинофилы (абс)'),
        ('Относительное количество эозинофилов','Эозинофилы (%)'),
        ('Абсолютное количество лимфоцитов',    'Лимфоциты (абс)'),
        ('Относительное количество лимфоцитов', 'Лимфоциты (%)'),
        ('Абсолютное количество нейтрофилов',   'Нейтрофилы (абс)'),
        ('Относительное количество нейтрофилов','Нейтрофилы (%)'),
        ('Абсолютное количество моноцитов',     'Моноциты (абс)'),
        ('Относительное количество моноцитов',  'Моноциты (%)'),
        ('Абсолютное количество базофилов',     'Базофилы (абс)'),
        ('Относительное количество базофилов',  'Базофилы (%)')
    ) AS t(src_name, tgt_name)
    LOOP
        SELECT id INTO src_id FROM analyte_standards WHERE canonical_name = pair.src_name;
        SELECT id INTO tgt_id FROM analyte_standards WHERE canonical_name = pair.tgt_name;
        IF src_id IS NULL OR tgt_id IS NULL THEN
            CONTINUE;
        END IF;

        -- Удалить из источника синонимы, чьи (synonym_lower, unit_lower) уже есть в цели
        DELETE FROM analyte_synonyms s
        WHERE s.analyte_id = src_id
          AND EXISTS (
            SELECT 1 FROM analyte_synonyms t
            WHERE t.analyte_id = tgt_id
              AND t.synonym_lower = s.synonym_lower
              AND COALESCE(t.unit_lower, '') = COALESCE(s.unit_lower, '')
          );

        -- Перепривязать оставшиеся синонимы на цель
        UPDATE analyte_synonyms SET analyte_id = tgt_id WHERE analyte_id = src_id;

        -- Перепривязать пользовательские маппинги (если есть)
        UPDATE user_analyte_mappings SET analyte_id = tgt_id WHERE analyte_id = src_id;

        -- Удалить дубль-стандарт
        DELETE FROM analyte_standards WHERE id = src_id;
    END LOOP;
END $$;
