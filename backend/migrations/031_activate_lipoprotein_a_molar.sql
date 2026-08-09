-- 031_activate_lipoprotein_a_molar.sql
-- Follow-up to 030: the canonical inserted there left is_active NULL, and the
-- dictionary loader selects `WHERE a.is_active = TRUE`, so the molar Lp(a)
-- never reached the cache and its нмоль/л synonym resolved to nothing.
-- Idempotent.

UPDATE analyte_standards
SET is_active = TRUE, updated_at = now()
WHERE canonical_name = 'Липопротеин (а), молярный'
  AND is_active IS DISTINCT FROM TRUE;
