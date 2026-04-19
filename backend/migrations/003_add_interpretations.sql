-- Migration: Add interpretations tables
-- Description: Add support for AI interpretations of lab results

-- Create interpretations table
CREATE TABLE IF NOT EXISTS interpretations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    interpretation_text TEXT,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Create interpretation_documents association table
CREATE TABLE IF NOT EXISTS interpretation_documents (
    interpretation_id UUID NOT NULL REFERENCES interpretations(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    PRIMARY KEY (interpretation_id, document_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_interpretations_user_id ON interpretations(user_id);
CREATE INDEX IF NOT EXISTS idx_interpretations_status ON interpretations(status);
CREATE INDEX IF NOT EXISTS idx_interpretations_created_at ON interpretations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_interpretation_documents_interpretation_id ON interpretation_documents(interpretation_id);
CREATE INDEX IF NOT EXISTS idx_interpretation_documents_document_id ON interpretation_documents(document_id);

-- Add trigger to update updated_at automatically
CREATE OR REPLACE FUNCTION update_interpretations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_interpretations_updated_at
    BEFORE UPDATE ON interpretations
    FOR EACH ROW
    EXECUTE FUNCTION update_interpretations_updated_at();

