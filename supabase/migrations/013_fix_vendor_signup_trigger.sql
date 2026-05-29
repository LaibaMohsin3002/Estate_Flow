-- Fix vendor signup trigger issues on existing databases
-- Ensures vendor role is allowed, vendor row inserts are granted, and specialty stays compatible.

ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE public.profiles ADD CONSTRAINT profiles_role_check
CHECK (role IN ('admin', 'manager', 'inspector', 'tenant', 'vendor'));

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'vendors'
      AND column_name = 'specialty'
      AND data_type = 'text'
  ) THEN
    ALTER TABLE public.vendors
      ALTER COLUMN specialty TYPE text[] USING array[specialty];
  END IF;
END $$;

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
  v_specialties TEXT[];
BEGIN
  v_name := COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1));
  v_role := COALESCE(NEW.raw_user_meta_data->>'role', 'tenant');

  IF v_role NOT IN ('admin', 'manager', 'inspector', 'tenant', 'vendor') THEN
    v_role := 'tenant';
  END IF;

  IF v_role <> 'vendor' THEN
    INSERT INTO public.profiles (id, full_name, role)
    VALUES (NEW.id, v_name, v_role)
    ON CONFLICT (id) DO UPDATE
      SET
        full_name = COALESCE(EXCLUDED.full_name, profiles.full_name),
        role = COALESCE(EXCLUDED.role, profiles.role),
        updated_at = NOW();
  END IF;

  IF v_role = 'vendor' THEN
    v_phone := CASE
      WHEN NEW.email LIKE '%@estateflow.vendor' THEN split_part(NEW.email, '@', 1)
      WHEN NULLIF(NEW.raw_user_meta_data->>'phone', '') IS NOT NULL THEN NEW.raw_user_meta_data->>'phone'
      WHEN NULLIF(NEW.phone, '') IS NOT NULL THEN NEW.phone
      ELSE NULL
    END;

    v_specialties := COALESCE(
      (
        SELECT array_agg(value::text)
        FROM jsonb_array_elements_text(
          CASE
            WHEN jsonb_typeof(NEW.raw_user_meta_data->'specialties') = 'array' THEN NEW.raw_user_meta_data->'specialties'
            WHEN jsonb_typeof(NEW.raw_user_meta_data->'specialty') = 'array' THEN NEW.raw_user_meta_data->'specialty'
            WHEN NULLIF(NEW.raw_user_meta_data->>'specialties', '') IS NOT NULL THEN to_jsonb(string_to_array(NEW.raw_user_meta_data->>'specialties', ','))
            WHEN NULLIF(NEW.raw_user_meta_data->>'specialty', '') IS NOT NULL THEN to_jsonb(string_to_array(NEW.raw_user_meta_data->>'specialty', ','))
            ELSE '[]'::jsonb
          END
        )
      ),
      ARRAY['general']
    );

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
      v_specialties,
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

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

GRANT USAGE ON SCHEMA public TO supabase_auth_admin;
GRANT ALL ON public.profiles TO supabase_auth_admin;
GRANT ALL ON public.vendors TO supabase_auth_admin;
GRANT EXECUTE ON FUNCTION public.handle_new_user() TO supabase_auth_admin;

DROP POLICY IF EXISTS profiles_insert_own ON public.profiles;
DROP POLICY IF EXISTS profiles_insert_service ON public.profiles;
DROP POLICY IF EXISTS profiles_select_own ON public.profiles;
DROP POLICY IF EXISTS profiles_update_own ON public.profiles;

CREATE POLICY profiles_select_own ON public.profiles
  FOR SELECT TO authenticated
  USING (auth.uid() = id);

CREATE POLICY profiles_update_own ON public.profiles
  FOR UPDATE TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

CREATE POLICY profiles_insert_own ON public.profiles
  FOR INSERT TO authenticated
  WITH CHECK (auth.uid() = id);

CREATE POLICY profiles_insert_service ON public.profiles
  FOR INSERT TO supabase_auth_admin
  WITH CHECK (true);
