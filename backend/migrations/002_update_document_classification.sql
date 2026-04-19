-- Migration: Update document classification structure
-- Remove specialty, document_language, ai_confidence_score fields
-- These are now stored in MongoDB as part of classification object

-- Drop columns that are moving to MongoDB
ALTER TABLE documents DROP COLUMN IF EXISTS specialty;
ALTER TABLE documents DROP COLUMN IF EXISTS document_language;
ALTER TABLE documents DROP COLUMN IF EXISTS ai_confidence_score;

-- Add comment to document_type column to clarify allowed values
COMMENT ON COLUMN documents.document_type IS 'One of 5 fixed types: Прием врача, Результаты анализа, Инструментальное исследование, Функциональная диагностика, Другое';

