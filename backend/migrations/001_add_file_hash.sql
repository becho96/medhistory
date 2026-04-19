-- Migration: Add file_hash column to documents table
-- Purpose: Enable duplicate file detection

-- Add file_hash column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'documents' 
        AND column_name = 'file_hash'
    ) THEN
        ALTER TABLE documents 
        ADD COLUMN file_hash VARCHAR(64);
        
        -- Create index for faster duplicate lookups
        CREATE INDEX idx_documents_file_hash ON documents(file_hash);
        
        RAISE NOTICE 'Column file_hash added to documents table';
    ELSE
        RAISE NOTICE 'Column file_hash already exists in documents table';
    END IF;
END $$;

