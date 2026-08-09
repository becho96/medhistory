-- 030_fix_lipoprotein_a_mass_units.sql
-- Lp(a) results reported in mass units were silently dropped from the chart:
-- the canonical analyte stored нмоль/л, and strict unit conversion has no
-- mass↔molar coefficient, so /labs/timeseries discarded every point.
-- Mass becomes the canonical scale (1 г/л = 100 мг/дл); molar results move to
-- their own canonical, because mass↔molar conversion for Lp(a) depends on the
-- apo(a) isoform and is not clinically recommended.
-- Idempotent. After applying on prod: POST /api/v1/internal/analytes/reload
-- (or wait for the 1h cache TTL).

BEGIN;

-- 1. Canonical Lp(a) switches to the mass unit.
UPDATE analyte_standards
SET standard_unit = 'г/л', updated_at = now()
WHERE canonical_name = 'Липопротеин (а)';

-- 2. Separate canonical for molar results, same category.
INSERT INTO analyte_standards (id, category_id, canonical_name, standard_unit)
SELECT gen_random_uuid(), a.category_id, 'Липопротеин (а), молярный', 'нмоль/л'
FROM analyte_standards a
WHERE a.canonical_name = 'Липопротеин (а)'
ON CONFLICT (canonical_name) DO NOTHING;

-- 3. Existing нмоль/л synonym points at the molar canonical.
--    (A second row with the same (synonym_lower, unit_lower) is impossible —
--     the pair is unique — so the row is moved, not duplicated.)
UPDATE analyte_synonyms s
SET analyte_id = m.id
FROM analyte_standards m
WHERE m.canonical_name = 'Липопротеин (а), молярный'
  AND s.synonym_lower = 'липопротеин (а)'
  AND s.unit_lower = 'нмоль/л';

-- 4. Mass-unit synonyms: г/л 1:1, мг/дл × 0.01 → г/л.
INSERT INTO analyte_synonyms (id, analyte_id, synonym, synonym_lower, unit, unit_lower, coefficient, source, is_primary)
SELECT gen_random_uuid(), a.id, v.synonym, lower(v.synonym), v.unit, lower(v.unit), v.coefficient, 'backfill_030', FALSE
FROM (VALUES
    ('Липопротеин (а)', 'г/л', 1.0),
    ('Липопротеин (а)', 'мг/дл', 0.01)
) AS v(synonym, unit, coefficient)
JOIN analyte_standards a ON a.canonical_name = 'Липопротеин (а)'
ON CONFLICT (synonym_lower, unit_lower) DO NOTHING;

-- 5. Close the queue items this migration resolves.
UPDATE analyte_mapping_queue
SET status = 'approved', resolved_at = now(), resolved_by = 'migration_030', updated_at = now()
WHERE status = 'pending'
  AND lower(original_name) = 'липопротеин (а)'
  AND lower(COALESCE(unit, '')) IN ('г/л', 'мг/дл');

COMMIT;
