-- Run this if you already applied the original EstateFlow schema (without geolocation/media)

ALTER TABLE properties ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS city TEXT;
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS area TEXT;
ALTER TABLE maintenance_requests ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE maintenance_requests ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;

ALTER TABLE maintenance_requests DROP CONSTRAINT IF EXISTS maintenance_requests_status_check;
ALTER TABLE maintenance_requests ADD CONSTRAINT maintenance_requests_status_check
  CHECK (status IN ('Open', 'In Progress', 'Scheduled', 'Resolved', 'Pending Approval'));

CREATE TABLE IF NOT EXISTS maintenance_request_media (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id UUID NOT NULL REFERENCES maintenance_requests(id) ON DELETE CASCADE,
  storage_path TEXT NOT NULL,
  mime_type TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE maintenance_pipeline_results ADD COLUMN IF NOT EXISTS human_approved BOOLEAN DEFAULT FALSE;

ALTER TABLE inspection_items ADD COLUMN IF NOT EXISTS storage_path TEXT;
