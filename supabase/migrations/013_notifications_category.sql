-- Optional category for filtering in-app notifications
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS category TEXT;

CREATE INDEX IF NOT EXISTS idx_notifications_recipient_unread
    ON notifications (recipient_id, created_at DESC)
    WHERE read_at IS NULL;
