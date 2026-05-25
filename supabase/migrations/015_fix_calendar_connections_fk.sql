-- Migration 015: Fix calendar_connections foreign key constraint to support both profiles and vendors.
--
-- The calendar_connections.profile_id column was previously constrained to public.profiles(id).
-- Since vendors are stored in public.vendors and not in public.profiles, this constraint caused a 
-- foreign key violation (23503) when vendors attempted to connect their Google Calendar.
-- Both public.profiles and public.vendors use the UUID from auth.users, so redirecting the 
-- foreign key to reference auth.users(id) directly allows both roles to sync their calendars.

ALTER TABLE public.calendar_connections 
  DROP CONSTRAINT IF EXISTS calendar_connections_profile_id_fkey;

ALTER TABLE public.calendar_connections 
  ADD CONSTRAINT calendar_connections_profile_id_fkey 
  FOREIGN KEY (profile_id) 
  REFERENCES auth.users(id) 
  ON DELETE CASCADE;
