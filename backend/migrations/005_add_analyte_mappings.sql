-- Migration: 005_add_analyte_mappings
-- Description: Создание таблиц для справочника анализов и маппинга единиц измерения
-- Date: 2026-01-03

-- ============================================================================
-- Таблица категорий анализов
-- ============================================================================
CREATE TABLE IF NOT EXISTS analyte_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    icon VARCHAR(10) DEFAULT '📋',
    sort_order INTEGER DEFAULT 0,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_analyte_categories_sort_order ON analyte_categories(sort_order);
CREATE INDEX IF NOT EXISTS ix_analyte_categories_is_active ON analyte_categories(is_active);

COMMENT ON TABLE analyte_categories IS 'Категории анализов (Общий анализ крови, Биохимия и т.д.)';

-- ============================================================================
-- Таблица канонических названий анализов
-- ============================================================================
CREATE TABLE IF NOT EXISTS analyte_standards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL REFERENCES analyte_categories(id) ON DELETE CASCADE,
    canonical_name VARCHAR(150) NOT NULL UNIQUE,
    standard_unit VARCHAR(30) NOT NULL,
    description TEXT,
    reference_male_min NUMERIC(15, 4),
    reference_male_max NUMERIC(15, 4),
    reference_female_min NUMERIC(15, 4),
    reference_female_max NUMERIC(15, 4),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_analyte_standards_category_id ON analyte_standards(category_id);
CREATE INDEX IF NOT EXISTS ix_analyte_standards_canonical_name ON analyte_standards(canonical_name);
CREATE INDEX IF NOT EXISTS ix_analyte_standards_is_active ON analyte_standards(is_active);

COMMENT ON TABLE analyte_standards IS 'Канонические названия анализов со стандартными единицами измерения';

-- ============================================================================
-- Таблица синонимов названий анализов
-- ============================================================================
CREATE TABLE IF NOT EXISTS analyte_synonyms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analyte_id UUID NOT NULL REFERENCES analyte_standards(id) ON DELETE CASCADE,
    synonym VARCHAR(200) NOT NULL,
    synonym_lower VARCHAR(200) NOT NULL,
    source VARCHAR(100),
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_analyte_synonyms_analyte_id ON analyte_synonyms(analyte_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_analyte_synonyms_synonym_lower_unique ON analyte_synonyms(synonym_lower);

COMMENT ON TABLE analyte_synonyms IS 'Синонимы названий анализов для маппинга разных лабораторий';

-- ============================================================================
-- Таблица коэффициентов конвертации единиц
-- ============================================================================
CREATE TABLE IF NOT EXISTS unit_conversions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analyte_id UUID NOT NULL REFERENCES analyte_standards(id) ON DELETE CASCADE,
    from_unit VARCHAR(30) NOT NULL,
    from_unit_lower VARCHAR(30) NOT NULL,
    coefficient NUMERIC(15, 6) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_unit_conversions_analyte_id ON unit_conversions(analyte_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_unit_conversions_analyte_unit ON unit_conversions(analyte_id, from_unit_lower);

COMMENT ON TABLE unit_conversions IS 'Коэффициенты конвертации единиц измерения (value * coefficient = standard_value)';

-- ============================================================================
-- Таблица пользовательских маппингов (для будущего)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_analyte_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_name VARCHAR(200) NOT NULL,
    original_name_lower VARCHAR(200) NOT NULL,
    analyte_id UUID REFERENCES analyte_standards(id) ON DELETE SET NULL,
    is_ignored BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_analyte_mappings_user_id ON user_analyte_mappings(user_id);
CREATE INDEX IF NOT EXISTS ix_user_analyte_mappings_original_name_lower ON user_analyte_mappings(original_name_lower);
CREATE UNIQUE INDEX IF NOT EXISTS ix_user_analyte_mappings_user_name ON user_analyte_mappings(user_id, original_name_lower);

COMMENT ON TABLE user_analyte_mappings IS 'Пользовательские маппинги названий анализов';

-- ============================================================================
-- Триггер для автоматического обновления updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_analyte_categories_updated_at ON analyte_categories;
CREATE TRIGGER update_analyte_categories_updated_at
    BEFORE UPDATE ON analyte_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_analyte_standards_updated_at ON analyte_standards;
CREATE TRIGGER update_analyte_standards_updated_at
    BEFORE UPDATE ON analyte_standards
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

