-- Seed properties, units, and vendors for Pakistan (Karachi / Lahore)
-- Safe to re-run: uses ON CONFLICT or deletes only seed-named rows
-- Requires geo columns — runs 008 patch inline if missing

ALTER TABLE properties ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS city TEXT;
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS area TEXT;

-- Properties
INSERT INTO properties (id, name, address, city, state, zip, total_units, latitude, longitude)
VALUES
  ('11111111-1111-1111-1111-111111111101', 'Sunset Residency Clifton', 'Block 5, Clifton', 'Karachi', 'Sindh', '75600', 12, 24.8138, 67.0299),
  ('11111111-1111-1111-1111-111111111102', 'Bahria Town Phase 8', 'Phase 8, Bahria Town', 'Rawalpindi', 'Punjab', '46000', 24, 33.5198, 73.1180),
  ('11111111-1111-1111-1111-111111111103', 'DHA Phase 6 Lahore', 'Phase 6, DHA', 'Lahore', 'Punjab', '54000', 18, 31.4707, 74.4081)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  address = EXCLUDED.address,
  city = EXCLUDED.city,
  latitude = EXCLUDED.latitude,
  longitude = EXCLUDED.longitude;

-- Units
INSERT INTO units (property_id, unit_number, floor, bedrooms, bathrooms, is_occupied)
VALUES
  ('11111111-1111-1111-1111-111111111101', '101', 1, 2, 2.0, true),
  ('11111111-1111-1111-1111-111111111101', '102', 1, 2, 2.0, true),
  ('11111111-1111-1111-1111-111111111101', '201', 2, 3, 2.5, false),
  ('11111111-1111-1111-1111-111111111102', 'A-12', 0, 3, 3.0, true),
  ('11111111-1111-1111-1111-111111111102', 'B-04', 0, 2, 2.0, true),
  ('11111111-1111-1111-1111-111111111103', '5-A', 5, 2, 2.0, true),
  ('11111111-1111-1111-1111-111111111103', '7-C', 7, 3, 3.0, false)
ON CONFLICT (property_id, unit_number) DO NOTHING;

-- Vendors (Pakistan phone format, geo for nearest-match)
DELETE FROM vendors WHERE email LIKE '%@estateflow.pk';

INSERT INTO vendors (id, name, specialty, phone, email, available, rating, latitude, longitude, city, area)
VALUES
  ('22222222-2222-2222-2222-222222222201', 'Karachi Quick Plumbing', 'plumbing', '+92-300-1110001', 'plumbing@estateflow.pk', true, 4.8, 24.8607, 67.0011, 'Karachi', 'Clifton'),
  ('22222222-2222-2222-2222-222222222202', 'CoolBreeze HVAC Karachi', 'hvac', '+92-300-1110002', 'hvac@estateflow.pk', true, 4.7, 24.8700, 67.0300, 'Karachi', 'DHA'),
  ('22222222-2222-2222-2222-222222222203', 'Spark Electric Lahore', 'electrical', '+92-300-2220001', 'electric@estateflow.pk', true, 4.9, 31.5204, 74.3587, 'Lahore', 'Gulberg'),
  ('22222222-2222-2222-2222-222222222204', 'StructureFix Rawalpindi', 'structural', '+92-300-3330001', 'structural@estateflow.pk', true, 4.6, 33.5651, 73.0169, 'Rawalpindi', 'Bahria'),
  ('22222222-2222-2222-2222-222222222205', 'HandyPro General Karachi', 'general', '+92-300-4440001', 'general@estateflow.pk', true, 4.5, 24.8500, 67.0100, 'Karachi', 'Saddar'),
  ('22222222-2222-2222-2222-222222222206', 'PestAway Solutions', 'pest control', '+92-300-5550001', 'pest@estateflow.pk', true, 4.7, 24.9000, 67.0500, 'Karachi', 'PECHS'),
  ('22222222-2222-2222-2222-222222222207', 'ApplianceCare Lahore', 'appliances', '+92-300-6660001', 'appliances@estateflow.pk', true, 4.6, 31.4800, 74.3500, 'Lahore', 'DHA'),
  ('22222222-2222-2222-2222-222222222208', 'Generator Experts PK', 'electrical', '+92-300-7770001', 'gen@estateflow.pk', true, 4.4, 24.9200, 67.0800, 'Karachi', 'Malir'),
  ('22222222-2222-2222-2222-222222222209', 'Tile & Leak Masters', 'plumbing', '+92-300-8880001', 'tiles@estateflow.pk', true, 4.8, 31.4900, 74.4000, 'Lahore', 'Model Town'),
  ('22222222-2222-2222-2222-222222222210', 'AC Doctor Islamabad', 'hvac', '+92-300-9990001', 'ac@estateflow.pk', true, 4.7, 33.6844, 73.0479, 'Islamabad', 'F-10')
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  specialty = EXCLUDED.specialty,
  latitude = EXCLUDED.latitude,
  longitude = EXCLUDED.longitude,
  city = EXCLUDED.city,
  area = EXCLUDED.area,
  rating = EXCLUDED.rating;
