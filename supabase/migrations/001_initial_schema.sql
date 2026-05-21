-- EstateFlow initial schema (run in Supabase SQL Editor if not already applied)

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE properties (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    address         TEXT,
    city            TEXT,
    state           TEXT,
    zip             TEXT,
    total_units     INT DEFAULT 0,
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE units (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id     UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    unit_number     TEXT NOT NULL,
    floor           INT,
    bedrooms        INT,
    bathrooms       NUMERIC(3,1),
    is_occupied     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (property_id, unit_number)
);

CREATE TABLE vendors (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    specialty           TEXT NOT NULL,
    phone               TEXT,
    email               TEXT,
    available           BOOLEAN DEFAULT TRUE,
    rating              NUMERIC(3,1) DEFAULT 5.0 CHECK (rating >= 0 AND rating <= 5),
    total_assignments   INT DEFAULT 0,
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    city                TEXT,
    area                TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role            TEXT NOT NULL DEFAULT 'tenant' CHECK (role IN ('admin', 'manager', 'inspector', 'tenant')),
    full_name       TEXT,
    phone           TEXT,
    property_id     UUID REFERENCES properties(id) ON DELETE SET NULL,
    unit_id         UUID REFERENCES units(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE maintenance_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id       TEXT UNIQUE,
    tenant_name     TEXT NOT NULL,
    tenant_id       UUID REFERENCES profiles(id) ON DELETE SET NULL,
    unit            TEXT NOT NULL,
    property_id     UUID REFERENCES properties(id) ON DELETE SET NULL,
    property_name   TEXT NOT NULL,
    original_issue  TEXT NOT NULL,
    redacted_issue  TEXT,
    image_desc      TEXT,
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    status          TEXT NOT NULL DEFAULT 'Open'
                        CHECK (status IN ('Open', 'In Progress', 'Scheduled', 'Resolved', 'Pending Approval')),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE maintenance_request_media (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id      UUID NOT NULL REFERENCES maintenance_requests(id) ON DELETE CASCADE,
    storage_path    TEXT NOT NULL,
    mime_type       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE maintenance_pipeline_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id          UUID NOT NULL UNIQUE REFERENCES maintenance_requests(id) ON DELETE CASCADE,
    category            TEXT,
    urgency             TEXT,
    summary             TEXT,
    vendor_specialty    TEXT,
    estimated_time      TEXT,
    priority_reason     TEXT,
    duration_ms         INT,
    agents_run          JSONB DEFAULT '[]',
    pii_found           BOOLEAN DEFAULT FALSE,
    pii_log             TEXT,
    is_safe             BOOLEAN DEFAULT TRUE,
    security_notes      TEXT,
    threat_type         TEXT DEFAULT 'none',
    is_compliant        BOOLEAN DEFAULT TRUE,
    governance_notes    TEXT,
    compliance_flags    JSONB DEFAULT '[]',
    performance_score   INT,
    sla_target_hours    INT,
    performance_notes   TEXT,
    assigned_vendor     TEXT,
    vendor_phone        TEXT,
    assigned_vendor_id  UUID REFERENCES vendors(id) ON DELETE SET NULL,
    scheduled_time      TEXT,
    db_status           TEXT,
    human_approved      BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE inspections (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id         UUID REFERENCES properties(id) ON DELETE SET NULL,
    property_name       TEXT NOT NULL,
    unit                TEXT DEFAULT 'Common',
    inspection_type     TEXT NOT NULL,
    inspector_name      TEXT NOT NULL,
    inspector_id        UUID REFERENCES profiles(id) ON DELETE SET NULL,
    passed              INT DEFAULT 0,
    failed              INT DEFAULT 0,
    skipped             INT DEFAULT 0,
    notes               JSONB DEFAULT '{}',
    status              TEXT DEFAULT 'Completed',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE inspection_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id   UUID NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    item_name       TEXT NOT NULL,
    result          TEXT CHECK (result IN ('pass', 'fail', 'na')),
    note            TEXT,
    storage_path    TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE inspection_pipeline_results (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id           UUID NOT NULL UNIQUE REFERENCES inspections(id) ON DELETE CASCADE,
    overall_condition       TEXT,
    risk_level              TEXT,
    executive_summary       TEXT,
    top_issues              JSONB DEFAULT '[]',
    recommendations         JSONB DEFAULT '[]',
    next_inspection_due     TEXT,
    estimated_repair_cost   TEXT,
    compliance_flags        JSONB DEFAULT '[]',
    total_estimated_cost    NUMERIC(10,2) DEFAULT 0,
    work_order_count        INT DEFAULT 0,
    agents_run              JSONB DEFAULT '[]',
    duration_ms             INT,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE work_orders (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id               UUID REFERENCES inspections(id) ON DELETE CASCADE,
    maintenance_request_id      UUID REFERENCES maintenance_requests(id) ON DELETE CASCADE,
    item                        TEXT NOT NULL,
    priority                    TEXT CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
    assigned_specialty          TEXT,
    estimated_cost_usd          NUMERIC(10,2),
    note                        TEXT,
    vendor_id                   UUID REFERENCES vendors(id) ON DELETE SET NULL,
    status                      TEXT DEFAULT 'Pending'
                                    CHECK (status IN ('Pending', 'Assigned', 'In Progress', 'Completed', 'Cancelled')),
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agent_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_type   TEXT NOT NULL CHECK (pipeline_type IN ('maintenance', 'inspection')),
    reference_id    UUID NOT NULL,
    agent_name      TEXT NOT NULL,
    duration_ms     INT,
    success         BOOLEAN DEFAULT TRUE,
    output          JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type            TEXT NOT NULL CHECK (type IN ('sms', 'email', 'in_app')),
    recipient_id    UUID REFERENCES profiles(id) ON DELETE SET NULL,
    recipient_phone TEXT,
    recipient_email TEXT,
    subject         TEXT,
    message         TEXT NOT NULL,
    reference_type  TEXT,
    reference_id    UUID,
    status          TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    sent_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_units_property ON units(property_id);
CREATE INDEX idx_profiles_role ON profiles(role);
CREATE INDEX idx_profiles_property ON profiles(property_id);
CREATE INDEX idx_maintenance_requests_status ON maintenance_requests(status);
CREATE INDEX idx_maintenance_requests_property ON maintenance_requests(property_id);
CREATE INDEX idx_maintenance_requests_tenant ON maintenance_requests(tenant_id);
CREATE INDEX idx_maintenance_requests_created ON maintenance_requests(created_at DESC);
CREATE INDEX idx_inspections_property ON inspections(property_id);
CREATE INDEX idx_inspections_inspector ON inspections(inspector_id);
CREATE INDEX idx_inspections_created ON inspections(created_at DESC);
CREATE INDEX idx_inspection_items_inspection ON inspection_items(inspection_id);
CREATE INDEX idx_work_orders_inspection ON work_orders(inspection_id);
CREATE INDEX idx_work_orders_request ON work_orders(maintenance_request_id);
CREATE INDEX idx_work_orders_vendor ON work_orders(vendor_id);
CREATE INDEX idx_work_orders_status ON work_orders(status);
CREATE INDEX idx_agent_logs_reference ON agent_logs(reference_id);
CREATE INDEX idx_agent_logs_pipeline_type ON agent_logs(pipeline_type);
CREATE INDEX idx_notifications_recipient ON notifications(recipient_id);
CREATE INDEX idx_notifications_status ON notifications(status);

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_properties_updated_at BEFORE UPDATE ON properties FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_units_updated_at BEFORE UPDATE ON units FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_vendors_updated_at BEFORE UPDATE ON vendors FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_profiles_updated_at BEFORE UPDATE ON profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_maintenance_requests_upd BEFORE UPDATE ON maintenance_requests FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_inspections_updated_at BEFORE UPDATE ON inspections FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_work_orders_updated_at BEFORE UPDATE ON work_orders FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_role TEXT;
  v_name TEXT;
BEGIN
  v_name := COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1));
  v_role := COALESCE(NEW.raw_user_meta_data->>'role', 'tenant');
  IF v_role NOT IN ('admin', 'manager', 'inspector', 'tenant') THEN
    v_role := 'tenant';
  END IF;
  INSERT INTO public.profiles (id, full_name, role)
  VALUES (NEW.id, v_name, v_role)
  ON CONFLICT (id) DO UPDATE
    SET full_name = COALESCE(EXCLUDED.full_name, profiles.full_name),
        role = COALESCE(EXCLUDED.role, profiles.role),
        updated_at = NOW();
  RETURN NEW;
END;
$$;

GRANT USAGE ON SCHEMA public TO supabase_auth_admin;
GRANT ALL ON public.profiles TO supabase_auth_admin;
GRANT EXECUTE ON FUNCTION public.handle_new_user() TO supabase_auth_admin;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
