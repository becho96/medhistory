-- 026_backfill_thyroid_unit_conversions.sql
-- Phase 0 backfill (part A2): free T4 / free T3 name-variants reported in a unit
-- that needs CONVERSION to the canonical standard unit (пмоль/л).
-- Standard literature molar-conversion factors:
--   free T4:  нг/дл × 12.87  = пмоль/л   (MW 776.87)
--   free T3:  пг/мл × 1.536  = пмоль/л   (MW 650.98)
-- Idempotent: ON CONFLICT (synonym_lower, unit_lower) DO NOTHING.
-- After applying on prod: POST /api/v1/internal/analytes/reload (or wait 1h cache TTL).

INSERT INTO analyte_synonyms (id, analyte_id, synonym, synonym_lower, unit, unit_lower, coefficient, source, is_primary)
SELECT gen_random_uuid(), a.id, v.synonym, lower(v.synonym), v.unit, lower(v.unit), v.coefficient, 'backfill_026', FALSE
FROM (VALUES
    ('Свободный тироксин (Т4)', 'нг/дл', 'Т4 свободный', 12.87),
    ('Т4 свободный', 'нг/дл', 'Т4 свободный', 12.87),
    ('Т3 свободный', 'пг/мл', 'Т3 свободный', 1.536),
    ('Трийодтиронин свободный (Т3 свободный)', 'пг/мл', 'Т3 свободный', 1.536)
) AS v(synonym, unit, canonical_name, coefficient)
JOIN analyte_standards a ON a.canonical_name = v.canonical_name
ON CONFLICT (synonym_lower, unit_lower) DO NOTHING;
