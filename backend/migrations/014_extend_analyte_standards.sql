-- Migration: 014_extend_analyte_standards
-- Description: Add LOINC code, UCUM unit and reference source columns to analyte_standards
-- Date: 2026-05-09
--
-- Цель: подготовить таблицу к хранению международных идентификаторов (LOINC),
-- стандартизованных единиц (UCUM) и метаинформации о происхождении референсных
-- диапазонов. Существующие столбцы reference_male/female_min/max не трогаем —
-- они заполняются миграцией 015.

ALTER TABLE analyte_standards
    ADD COLUMN IF NOT EXISTS loinc_code VARCHAR(20),
    ADD COLUMN IF NOT EXISTS loinc_long_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS ucum_unit VARCHAR(30),
    ADD COLUMN IF NOT EXISTS reference_source VARCHAR(50),
    ADD COLUMN IF NOT EXISTS reference_age_note VARCHAR(50) DEFAULT '18+ years';

CREATE INDEX IF NOT EXISTS ix_analyte_standards_loinc_code
    ON analyte_standards(loinc_code);

COMMENT ON COLUMN analyte_standards.loinc_code IS
    'LOINC identifier (e.g. 718-7 for Hemoglobin in Blood by Mass concentration)';
COMMENT ON COLUMN analyte_standards.loinc_long_name IS
    'Official LOINC long common name in English';
COMMENT ON COLUMN analyte_standards.ucum_unit IS
    'Unit of measure in UCUM notation (e.g. g/L, mmol/L, 10*9/L)';
COMMENT ON COLUMN analyte_standards.reference_source IS
    'Source of reference range values (Tietz / Минздрав РФ / IFCC / manufacturer)';
COMMENT ON COLUMN analyte_standards.reference_age_note IS
    'Age band the reference range applies to (default: 18+ years adult)';
