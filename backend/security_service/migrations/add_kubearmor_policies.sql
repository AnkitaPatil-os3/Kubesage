-- Migration: Add new categories and user edited policies table

-- Add new policy categories
INSERT INTO policy_categories (name, display_name, description, icon) VALUES
('file_based', '📁 File-Based Security Policies', 'Protect against unauthorized file changes and access', 'file-lock'),
('process_based', '⚙️ Process-Based Security Policies', 'Control process execution and behavior', 'cpu'),
('network_based', '🌐 Network-Based Security Policies', 'Control network access and communications', 'network'),
('capabilities_permissions', '🔑 Capabilities & Permissions', 'Manage service account tokens and permissions', 'key')
ON CONFLICT (name) DO NOTHING;

-- Create user_edited_policies table
CREATE TABLE IF NOT EXISTS user_edited_policies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    original_policy_id INTEGER NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
    edited_yaml_content TEXT NOT NULL,
    edited_name VARCHAR(300),
    edited_description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Create unique constraint to prevent duplicate edited policies per user
    UNIQUE(user_id, original_policy_id, is_active)
);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_edited_policies_user_id ON user_edited_policies(user_id);
CREATE INDEX IF NOT EXISTS idx_user_edited_policies_original_policy_id ON user_edited_policies(original_policy_id);
CREATE INDEX IF NOT EXISTS idx_user_edited_policies_active ON user_edited_policies(is_active);

-- Add new columns to policy_applications table
ALTER TABLE policy_applications 
ADD COLUMN IF NOT EXISTS user_edited_policy_id INTEGER REFERENCES user_edited_policies(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS is_edited_policy BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS original_yaml TEXT;

-- Create index for the new foreign key
CREATE INDEX IF NOT EXISTS idx_policy_applications_user_edited_policy_id ON policy_applications(user_edited_policy_id);

-- Update trigger for user_edited_policies
CREATE OR REPLACE FUNCTION update_user_edited_policies_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_edited_policies_updated_at
    BEFORE UPDATE ON user_edited_policies
    FOR EACH ROW
    EXECUTE FUNCTION update_user_edited_policies_updated_at();