-- Migration: Add family relations support
-- Date: 2026-01-03
-- Description: Adds support for multiple family profiles per account

-- Add birth_date to users
ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date DATE;

-- Make email nullable for family members created without email
ALTER TABLE users ALTER COLUMN email DROP NOT NULL;

-- Make password_hash nullable for family members without credentials
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

-- Create enum for relation types
DO $$ BEGIN
    CREATE TYPE relation_type_enum AS ENUM (
        'parent',
        'child', 
        'spouse',
        'grandparent',
        'grandchild',
        'sibling',
        'other'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create family_relations table
CREATE TABLE IF NOT EXISTS family_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    member_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    relation_type relation_type_enum NOT NULL,
    custom_relation VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Prevent duplicate relations
    CONSTRAINT unique_family_relation UNIQUE (owner_id, member_id)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_family_relations_owner ON family_relations(owner_id);
CREATE INDEX IF NOT EXISTS idx_family_relations_member ON family_relations(member_id);

-- Add trigger to update updated_at
CREATE OR REPLACE FUNCTION update_family_relations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_family_relations_updated_at ON family_relations;
CREATE TRIGGER trigger_family_relations_updated_at
    BEFORE UPDATE ON family_relations
    FOR EACH ROW
    EXECUTE FUNCTION update_family_relations_updated_at();

-- Add comment for documentation
COMMENT ON TABLE family_relations IS 'Family relations between users. Owner can manage member profile.';
COMMENT ON COLUMN family_relations.owner_id IS 'User who added the family member and can manage their profile';
COMMENT ON COLUMN family_relations.member_id IS 'The family member being managed';
COMMENT ON COLUMN family_relations.relation_type IS 'How member relates to owner (e.g., child = member is owner child)';

