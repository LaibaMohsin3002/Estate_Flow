-- Seed 100 vendors across Pakistan (safe to re-run)

ALTER TABLE vendors ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS city TEXT;
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS area TEXT;

DELETE FROM vendors WHERE email ~ '^vendor[0-9]+@estateflow\.pk$';

WITH nums AS (
  SELECT generate_series(1, 100) AS n
),
specs AS (
  SELECT ARRAY['plumbing','hvac','electrical','structural','general','pest control','appliances'] AS list
),
cities AS (
  SELECT * FROM (VALUES
    ('Karachi', 24.8607::double precision, 67.0011::double precision),
    ('Lahore', 31.5204, 74.3587),
    ('Islamabad', 33.6844, 73.0479),
    ('Rawalpindi', 33.5651, 73.0169),
    ('Faisalabad', 31.4180, 73.0790),
    ('Multan', 30.1575, 71.5249)
  ) AS t(city, lat, lng)
),
areas AS (
  SELECT * FROM (VALUES
    ('Karachi', 'Clifton'),
    ('Karachi', 'DHA'),
    ('Karachi', 'Gulshan'),
    ('Lahore', 'Gulberg'),
    ('Lahore', 'DHA'),
    ('Lahore', 'Model Town'),
    ('Islamabad', 'F-10'),
    ('Islamabad', 'G-11'),
    ('Rawalpindi', 'Bahria'),
    ('Rawalpindi', 'Satellite Town'),
    ('Faisalabad', 'Susan Road'),
    ('Multan', 'Cantt')
  ) AS t(city, area)
)
INSERT INTO vendors (name, specialty, phone, email, available, rating, latitude, longitude, city, area)
SELECT
  format(
    '%s %s Services — %s',
    CASE (n.n % 10)
      WHEN 0 THEN 'Al-Madina' WHEN 1 THEN 'Pak' WHEN 2 THEN 'Quick' WHEN 3 THEN 'Pro'
      WHEN 4 THEN 'Expert' WHEN 5 THEN 'Reliable' WHEN 6 THEN 'Prime' WHEN 7 THEN 'Swift'
      WHEN 8 THEN 'Trust' ELSE 'Master'
    END,
    initcap(replace(s.specialty, ' ', '')),
    c.city
  ),
  s.specialty,
  '+92-3' || lpad((10 + (n.n % 90))::text, 2, '0') || '-' || lpad((1000000 + n.n)::text, 7, '0'),
  'vendor' || lpad(n.n::text, 3, '0') || '@estateflow.pk',
  (n.n % 8) <> 0,
  round((3.5 + (abs(hashtext(n.n::text)) % 15) / 10.0)::numeric, 1),
  c.lat + ((n.n % 30) - 15) * 0.004,
  c.lng + ((n.n % 25) - 12) * 0.004,
  c.city,
  a.area
FROM nums n
CROSS JOIN specs
CROSS JOIN LATERAL (
  SELECT (specs.list)[1 + ((n.n - 1) % array_length(specs.list, 1))] AS specialty
) s
CROSS JOIN LATERAL (
  SELECT city, lat, lng FROM cities
  ORDER BY city
  LIMIT 1 OFFSET ((n.n - 1) % (SELECT COUNT(*)::int FROM cities))
) c
CROSS JOIN LATERAL (
  SELECT area FROM areas WHERE areas.city = c.city
  ORDER BY area
  LIMIT 1 OFFSET ((n.n - 1) % GREATEST(1, (SELECT COUNT(*)::int FROM areas WHERE areas.city = c.city)))
) a;

-- Should return 100 rows. Check:
-- SELECT COUNT(*) FROM vendors WHERE email LIKE 'vendor%@estateflow.pk';
