-- Migration 012: Add vendor role and multiple specialties support

-- 1. Drop existing role constraint if it exists and recreate it to support 'vendor'
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE public.profiles ADD CONSTRAINT profiles_role_check CHECK (role IN ('admin', 'manager', 'inspector', 'tenant', 'vendor'));

-- 2. Convert vendors specialty to text[]
-- First check if it is already text[] or needs conversion. If it's a string, convert it to array.
-- Using pg_typeof to determine if it is text and convert if so.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'vendors' 
          AND column_name = 'specialty' 
          AND data_type = 'text'
    ) THEN
        ALTER TABLE public.vendors ALTER COLUMN specialty TYPE text[] USING array[specialty];
    END IF;
END $$;

-- 3. Add vendor_replied column to maintenance_requests to track WhatsApp response status
ALTER TABLE public.maintenance_requests ADD COLUMN IF NOT EXISTS vendor_replied BOOLEAN DEFAULT FALSE;

-- 4. Recreate the handle_new_user trigger function to support vendor profiles automatically
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_role TEXT;
  v_name TEXT;
  v_phone TEXT;
BEGIN
  v_name := COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1));
  v_role := COALESCE(NEW.raw_user_meta_data->>'role', 'tenant');
  
  IF v_role NOT IN ('admin', 'manager', 'inspector', 'tenant', 'vendor') THEN
    v_role := 'tenant';
  END IF;

  INSERT INTO public.profiles (id, full_name, role)
  VALUES (NEW.id, v_name, v_role)
  ON CONFLICT (id) DO UPDATE
    SET full_name = COALESCE(EXCLUDED.full_name, profiles.full_name),
        role = COALESCE(EXCLUDED.role, profiles.role),
        updated_at = NOW();

  IF v_role = 'vendor' THEN
    IF NEW.email LIKE '%@estateflow.vendor' THEN
      v_phone := split_part(NEW.email, '@', 1);
    ELSE
      v_phone := COALESCE(NEW.raw_user_meta_data->>'phone', NEW.phone);
    END IF;

    INSERT INTO public.vendors (
      id,
      name,
      phone,
      email,
      available,
      rating,
      specialty,
      total_assignments,
      latitude,
      longitude,
      city,
      area
    )
    VALUES (
      NEW.id,
      v_name,
      v_phone,
      NEW.email,
      TRUE,
      5.0,
      ARRAY['general'],
      0,
      CASE
        WHEN NULLIF(NEW.raw_user_meta_data->>'latitude', '') ~ '^-?[0-9]+(\\.[0-9]+)?$'
          THEN NULLIF(NEW.raw_user_meta_data->>'latitude', '')::DOUBLE PRECISION
        ELSE NULL
      END,
      CASE
        WHEN NULLIF(NEW.raw_user_meta_data->>'longitude', '') ~ '^-?[0-9]+(\\.[0-9]+)?$'
          THEN NULLIF(NEW.raw_user_meta_data->>'longitude', '')::DOUBLE PRECISION
        ELSE NULL
      END,
      NULLIF(NEW.raw_user_meta_data->>'city', ''),
      NULLIF(NEW.raw_user_meta_data->>'area', '')
    )
    ON CONFLICT (id) DO UPDATE
    SET
      name = COALESCE(EXCLUDED.name, public.vendors.name),
      phone = COALESCE(EXCLUDED.phone, public.vendors.phone),
      email = COALESCE(EXCLUDED.email, public.vendors.email),
      available = COALESCE(EXCLUDED.available, public.vendors.available),
      rating = COALESCE(EXCLUDED.rating, public.vendors.rating),
      specialty = COALESCE(EXCLUDED.specialty, public.vendors.specialty),
      total_assignments = COALESCE(EXCLUDED.total_assignments, public.vendors.total_assignments),
      latitude = COALESCE(EXCLUDED.latitude, public.vendors.latitude),
      longitude = COALESCE(EXCLUDED.longitude, public.vendors.longitude),
      city = COALESCE(EXCLUDED.city, public.vendors.city),
      area = COALESCE(EXCLUDED.area, public.vendors.area);
  END IF;

  RETURN NEW;
END;
$$;

-- 5. Grant access
GRANT USAGE ON SCHEMA public TO supabase_auth_admin;
GRANT ALL ON public.profiles TO supabase_auth_admin;
GRANT ALL ON public.vendors TO supabase_auth_admin;
GRANT EXECUTE ON FUNCTION public.handle_new_user() TO supabase_auth_admin;


ALTER TABLE public.maintenance_pipeline_results 
ADD COLUMN follow_up_at TIMESTAMPTZ;

-- Highly recommended: Add an index since your code queries it with `.lt()`
CREATE INDEX IF NOT EXISTS idx_pipeline_results_follow_up 
ON public.maintenance_pipeline_results (follow_up_at);