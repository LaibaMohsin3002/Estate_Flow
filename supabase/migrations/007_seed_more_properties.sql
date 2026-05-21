-- Additional properties + units for tenant dropdowns (managers can also add via app /properties)

ALTER TABLE properties ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;

INSERT INTO properties (id, name, address, city, state, zip, total_units, latitude, longitude)
VALUES
  ('11111111-1111-1111-1111-111111111104', 'Gulberg Heights', 'Main Blvd, Gulberg', 'Lahore', 'Punjab', '54000', 20, 31.5150, 74.3450),
  ('11111111-1111-1111-1111-111111111105', 'F-10 Residency', 'F-10 Markaz', 'Islamabad', 'ICT', '44000', 8, 33.6910, 73.0370),
  ('11111111-1111-1111-1111-111111111106', 'PECHS Block 2 Flats', 'PECHS Block 2', 'Karachi', 'Sindh', '75400', 16, 24.8710, 67.0650),
  ('11111111-1111-1111-1111-111111111107', 'Model Town Residency', 'Model Town', 'Lahore', 'Punjab', '54700', 14, 31.4850, 74.3250),
  ('11111111-1111-1111-1111-111111111108', 'Bahria Enclave', 'Bahria Enclave', 'Islamabad', 'ICT', '44000', 22, 33.7200, 73.1500)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  city = EXCLUDED.city,
  latitude = EXCLUDED.latitude,
  longitude = EXCLUDED.longitude;

INSERT INTO units (property_id, unit_number, floor, bedrooms, bathrooms, is_occupied)
SELECT p.id, u.unit_number, u.floor, u.bedrooms, u.bathrooms, u.is_occupied
FROM (VALUES
  ('11111111-1111-1111-1111-111111111104', 'G-101', 1, 2, 2.0, true),
  ('11111111-1111-1111-1111-111111111104', 'G-102', 1, 2, 2.0, false),
  ('11111111-1111-1111-1111-111111111104', 'G-201', 2, 3, 2.5, true),
  ('11111111-1111-1111-1111-111111111105', 'F10-1', 0, 3, 3.0, true),
  ('11111111-1111-1111-1111-111111111105', 'F10-2', 0, 2, 2.0, true),
  ('11111111-1111-1111-1111-111111111106', 'P2-301', 3, 2, 2.0, true),
  ('11111111-1111-1111-1111-111111111106', 'P2-302', 3, 2, 2.0, false),
  ('11111111-1111-1111-1111-111111111107', 'MT-12', 1, 3, 2.5, true),
  ('11111111-1111-1111-1111-111111111108', 'BE-5A', 5, 2, 2.0, true)
) AS u(pid, unit_number, floor, bedrooms, bathrooms, is_occupied)
JOIN properties p ON p.id::text = u.pid
ON CONFLICT (property_id, unit_number) DO NOTHING;
