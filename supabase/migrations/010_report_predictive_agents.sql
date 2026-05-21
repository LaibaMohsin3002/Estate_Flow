-- Report Agent (Node I) + Predictive Maintenance snapshots

ALTER TABLE maintenance_pipeline_results
    ADD COLUMN IF NOT EXISTS report_summary TEXT,
    ADD COLUMN IF NOT EXISTS report_pdf_path TEXT,
    ADD COLUMN IF NOT EXISTS report_signed BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS report_pending_signature BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS audit_ledger JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS token_usage_estimate INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS performance_alerts JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS recommended_model TEXT;

ALTER TABLE agent_logs DROP CONSTRAINT IF EXISTS agent_logs_pipeline_type_check;
ALTER TABLE agent_logs ADD CONSTRAINT agent_logs_pipeline_type_check
    CHECK (pipeline_type IN ('maintenance', 'inspection', 'predictive'));

CREATE TABLE IF NOT EXISTS predictive_maintenance_snapshots (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id         UUID REFERENCES properties(id) ON DELETE CASCADE,
    property_name       TEXT,
    forecast_period     TEXT NOT NULL DEFAULT 'weekly',
    recurring_issues    JSONB DEFAULT '[]',
    failure_forecasts   JSONB DEFAULT '[]',
    risk_score          INT DEFAULT 0,
    estimated_savings_pkr NUMERIC(12,2),
    agent_notes         TEXT,
    agents_run          JSONB DEFAULT '[]',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_predictive_property ON predictive_maintenance_snapshots(property_id);
CREATE INDEX IF NOT EXISTS idx_predictive_created ON predictive_maintenance_snapshots(created_at DESC);
