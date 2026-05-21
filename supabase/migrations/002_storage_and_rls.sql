-- Run after 001. Adds storage bucket policies and RLS.

-- Storage bucket (create in Supabase Dashboard → Storage → New bucket: maintenance-media, public: false)
-- Or via API on first upload from backend using service role.

ALTER TABLE maintenance_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_pipeline_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_request_media ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE units ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendors ENABLE ROW LEVEL SECURITY;
ALTER TABLE inspections ENABLE ROW LEVEL SECURITY;
ALTER TABLE inspection_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_logs ENABLE ROW LEVEL SECURITY;

-- Profiles: users read/update/insert own row; auth trigger uses supabase_auth_admin
CREATE POLICY profiles_select_own ON profiles FOR SELECT TO authenticated USING (auth.uid() = id);
CREATE POLICY profiles_update_own ON profiles FOR UPDATE TO authenticated USING (auth.uid() = id) WITH CHECK (auth.uid() = id);
CREATE POLICY profiles_insert_own ON profiles FOR INSERT TO authenticated WITH CHECK (auth.uid() = id);
CREATE POLICY profiles_insert_service ON profiles FOR INSERT TO supabase_auth_admin WITH CHECK (true);

-- Properties & units: authenticated read
CREATE POLICY properties_read ON properties FOR SELECT TO authenticated USING (true);
CREATE POLICY units_read ON units FOR SELECT TO authenticated USING (true);

-- Vendors: authenticated read
CREATE POLICY vendors_read ON vendors FOR SELECT TO authenticated USING (true);

-- Maintenance requests: tenant sees own; manager/admin see all for their property
CREATE POLICY mr_tenant_insert ON maintenance_requests FOR INSERT TO authenticated
    WITH CHECK (tenant_id = auth.uid());
CREATE POLICY mr_tenant_select ON maintenance_requests FOR SELECT TO authenticated
    USING (
        tenant_id = auth.uid()
        OR EXISTS (
            SELECT 1 FROM profiles p
            WHERE p.id = auth.uid() AND p.role IN ('admin', 'manager')
        )
    );
CREATE POLICY mr_manager_update ON maintenance_requests FOR UPDATE TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM profiles p
            WHERE p.id = auth.uid() AND p.role IN ('admin', 'manager')
        )
    );

CREATE POLICY mpr_read ON maintenance_pipeline_results FOR SELECT TO authenticated USING (true);
CREATE POLICY mrm_read ON maintenance_request_media FOR SELECT TO authenticated USING (true);

-- Inspections: inspector + manager
CREATE POLICY insp_read ON inspections FOR SELECT TO authenticated USING (true);
CREATE POLICY insp_insert ON inspections FOR INSERT TO authenticated
    WITH CHECK (
        EXISTS (SELECT 1 FROM profiles p WHERE p.id = auth.uid() AND p.role IN ('admin', 'manager', 'inspector'))
    );

CREATE POLICY insp_items_read ON inspection_items FOR SELECT TO authenticated USING (true);

-- Notifications: recipient only
CREATE POLICY notif_own ON notifications FOR SELECT TO authenticated
    USING (recipient_id = auth.uid());

-- Agent logs: managers/admins
CREATE POLICY agent_logs_read ON agent_logs FOR SELECT TO authenticated
    USING (
        EXISTS (SELECT 1 FROM profiles p WHERE p.id = auth.uid() AND p.role IN ('admin', 'manager'))
    );
