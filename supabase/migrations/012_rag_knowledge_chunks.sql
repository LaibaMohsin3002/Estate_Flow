-- RAG knowledge store (pgvector) + similarity search RPC

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type     TEXT NOT NULL CHECK (source_type IN (
                        'maintenance_ticket', 'inspection', 'property_doc', 'policy'
                    )),
    source_id       UUID,
    property_id     UUID REFERENCES properties(id) ON DELETE SET NULL,
    chunk_index     INT NOT NULL DEFAULT 0,
    content         TEXT NOT NULL,
    metadata        JSONB NOT NULL DEFAULT '{}',
    embedding       vector(1536),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_type, source_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_property ON knowledge_chunks(property_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_source ON knowledge_chunks(source_type, source_id);

-- IVFFlat index (build after seeding chunks in production)
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding
    ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- Seed global policy / playbook chunks (no embedding until backfill runs)
INSERT INTO knowledge_chunks (source_type, source_id, property_id, chunk_index, content, metadata)
VALUES
    ('policy', NULL, NULL, 0,
     'Critical maintenance (gas leak, flooding, electrical fire risk, no water, elevator trapped) must be escalated to High or Critical urgency and require manager approval before dispatch.',
     '{"title": "Critical escalation policy"}'),
    ('policy', NULL, NULL, 1,
     'Recurring plumbing issues at the same property within 90 days should trigger preventive inspection and may increase urgency.',
     '{"title": "Plumbing recurrence policy"}'),
    ('policy', NULL, NULL, 2,
     'Tenant communications may be in English, Urdu, or Roman Urdu. Classify trade and category from issue description; use property history when available.',
     '{"title": "Language and classification policy"}')
ON CONFLICT (source_type, source_id, chunk_index) DO NOTHING;

CREATE OR REPLACE FUNCTION match_knowledge_chunks(
    query_embedding vector(1536),
    match_count INT DEFAULT 5,
    match_property_id UUID DEFAULT NULL,
    match_tenant_id UUID DEFAULT NULL,
    include_global BOOLEAN DEFAULT TRUE
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    source_type TEXT,
    source_id UUID,
    property_id UUID,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        kc.id,
        kc.content,
        kc.source_type,
        kc.source_id,
        kc.property_id,
        kc.metadata,
        (1 - (kc.embedding <=> query_embedding))::FLOAT AS similarity
    FROM knowledge_chunks kc
    WHERE kc.embedding IS NOT NULL
      AND (
          (match_property_id IS NOT NULL AND kc.property_id = match_property_id)
          OR (match_tenant_id IS NOT NULL AND (kc.metadata->>'tenant_id') = match_tenant_id::TEXT)
          OR (include_global AND kc.source_type = 'policy')
          OR (match_property_id IS NULL AND match_tenant_id IS NULL)
      )
    ORDER BY kc.embedding <=> query_embedding
    LIMIT GREATEST(match_count, 1);
$$;
