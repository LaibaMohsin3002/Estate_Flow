-- RUN THIS FIRST if you see: column "latitude" of relation "properties" does not exist
-- Safe to run multiple times (IF NOT EXISTS)

ALTER TABLE properties ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;

ALTER TABLE vendors ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS city TEXT;
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS area TEXT;

ALTER TABLE maintenance_requests ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE maintenance_requests ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;

ALTER TABLE maintenance_pipeline_results ADD COLUMN IF NOT EXISTS human_approved BOOLEAN DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS maintenance_request_media (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id UUID NOT NULL REFERENCES maintenance_requests(id) ON DELETE CASCADE,
  storage_path TEXT NOT NULL,
  mime_type TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE inspection_items ADD COLUMN IF NOT EXISTS storage_path TEXT;
