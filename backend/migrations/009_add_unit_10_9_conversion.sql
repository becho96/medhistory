-- Migration: 009_add_unit_10_9_conversion
-- Description: Добавление варианта единицы "10^9/л" в unit_conversions для анализов ×10⁹/л
-- Причина: AI извлекает unit как "10^9/л", а в справочнике были только "10*9/л" и "х10^9/л"
-- Date: 2026-02-22

-- Добавляем "10^9/л" для всех анализов со стандартной единицей ×10⁹/л
INSERT INTO unit_conversions (id, analyte_id, from_unit, from_unit_lower, coefficient)
SELECT gen_random_uuid(), a.id, '10^9/л', '10^9/л', 1.0
FROM analyte_standards a
WHERE a.standard_unit = '×10⁹/л'
  AND a.is_active = TRUE
  AND NOT EXISTS (
    SELECT 1 FROM unit_conversions uc 
    WHERE uc.analyte_id = a.id AND uc.from_unit_lower = '10^9/л'
  );
