-- Migration script to update email_preferences table
\c news_db;

-- Drop the old frequency column if it exists and add preferred_time
DO $$
BEGIN
    -- Check if frequency column exists and drop it
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='email_preferences' AND column_name='frequency'
    ) THEN
        ALTER TABLE email_preferences DROP COLUMN frequency;
    END IF;

    -- Add preferred_time column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='email_preferences' AND column_name='preferred_time'
    ) THEN
        ALTER TABLE email_preferences
        ADD COLUMN preferred_time VARCHAR(5) DEFAULT '07:00';
    END IF;
END $$;

-- Update existing records to have default time
UPDATE email_preferences
SET preferred_time = '07:00'
WHERE preferred_time IS NULL;
