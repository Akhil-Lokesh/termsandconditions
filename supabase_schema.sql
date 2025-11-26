-- T&C Analysis System - Supabase Database Schema
-- Copy and paste this entire file into Supabase SQL Editor and run

-- ============================================================
-- SETUP: Enable Required Extensions
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABLE: users
-- Stores user account metadata (auth handled by Supabase Auth)
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE users IS 'User account metadata. Authentication is handled by Supabase Auth.';

-- ============================================================
-- TABLE: documents
-- Stores uploaded T&C documents and their metadata
-- ============================================================

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- File Information
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    
    -- Extracted Metadata
    company_name TEXT,
    jurisdiction TEXT,
    effective_date DATE,
    document_type TEXT,
    
    -- Processing Results
    total_sections INTEGER DEFAULT 0,
    total_clauses INTEGER DEFAULT 0,
    risk_score FLOAT CHECK (risk_score >= 0 AND risk_score <= 10),
    
    -- Vector Database Reference
    pinecone_namespace TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE documents IS 'Stores uploaded T&C documents and their analysis results';
COMMENT ON COLUMN documents.processing_status IS 'Status: pending, processing, completed, failed';
COMMENT ON COLUMN documents.risk_score IS 'Overall risk score from 1-10';
COMMENT ON COLUMN documents.pinecone_namespace IS 'Reference to Pinecone namespace for vector embeddings';

-- ============================================================
-- TABLE: clauses
-- Stores individual clauses extracted from documents
-- ============================================================

CREATE TABLE IF NOT EXISTS clauses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Clause Structure
    section TEXT NOT NULL,
    subsection TEXT,
    clause_number TEXT,
    text TEXT NOT NULL,
    level INTEGER DEFAULT 0 CHECK (level >= 0 AND level <= 5),
    chunk_index INTEGER DEFAULT 0,
    
    -- Vector Database Reference
    vector_id TEXT,
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE clauses IS 'Individual clauses extracted from T&C documents';
COMMENT ON COLUMN clauses.level IS 'Hierarchy level: 0=preamble, 1=section, 2=subsection, 3=clause';
COMMENT ON COLUMN clauses.chunk_index IS 'Index for clauses split into multiple chunks';
COMMENT ON COLUMN clauses.vector_id IS 'Reference to vector in Pinecone';

-- ============================================================
-- TABLE: anomalies
-- Stores detected anomalies and risky clauses
-- ============================================================

CREATE TABLE IF NOT EXISTS anomalies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    clause_id UUID REFERENCES clauses(id) ON DELETE CASCADE,
    
    -- Anomaly Classification
    anomaly_type TEXT NOT NULL CHECK (anomaly_type IN ('uncommon', 'risky', 'missing', 'unclear', 'one-sided')),
    severity TEXT NOT NULL CHECK (severity IN ('high', 'medium', 'low')),
    
    -- Details
    description TEXT NOT NULL,
    explanation TEXT,
    
    -- Scoring
    prevalence_score FLOAT CHECK (prevalence_score >= 0 AND prevalence_score <= 1),
    risk_flags TEXT[],
    
    -- Context
    section TEXT,
    clause_text TEXT,
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE anomalies IS 'Detected anomalies and risky clauses in T&C documents';
COMMENT ON COLUMN anomalies.anomaly_type IS 'Type: uncommon, risky, missing, unclear, one-sided';
COMMENT ON COLUMN anomalies.severity IS 'Severity: high, medium, low';
COMMENT ON COLUMN anomalies.prevalence_score IS 'How common this clause is (0=very rare, 1=universal)';
COMMENT ON COLUMN anomalies.risk_flags IS 'Array of risk keywords found';

-- ============================================================
-- TABLE: queries
-- Stores user Q&A queries and responses (optional - for analytics)
-- ============================================================

CREATE TABLE IF NOT EXISTS queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Query Details
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    sources JSONB,
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE queries IS 'User questions and AI-generated answers (for analytics)';
COMMENT ON COLUMN queries.confidence IS 'Confidence score of the answer (0-1)';
COMMENT ON COLUMN queries.sources IS 'JSON array of source clauses used for the answer';

-- ============================================================
-- INDEXES: For Performance Optimization
-- ============================================================

-- Documents indexes
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);

-- Clauses indexes
CREATE INDEX IF NOT EXISTS idx_clauses_document_id ON clauses(document_id);
CREATE INDEX IF NOT EXISTS idx_clauses_section ON clauses(section);

-- Anomalies indexes
CREATE INDEX IF NOT EXISTS idx_anomalies_document_id ON anomalies(document_id);
CREATE INDEX IF NOT EXISTS idx_anomalies_severity ON anomalies(severity);
CREATE INDEX IF NOT EXISTS idx_anomalies_type ON anomalies(anomaly_type);

-- Queries indexes
CREATE INDEX IF NOT EXISTS idx_queries_document_id ON queries(document_id);
CREATE INDEX IF NOT EXISTS idx_queries_user_id ON queries(user_id);
CREATE INDEX IF NOT EXISTS idx_queries_created_at ON queries(created_at DESC);

-- ============================================================
-- TRIGGERS: Auto-update timestamps
-- ============================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to documents table
DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON documents
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE clauses ENABLE ROW LEVEL SECURITY;
ALTER TABLE anomalies ENABLE ROW LEVEL SECURITY;
ALTER TABLE queries ENABLE ROW LEVEL SECURITY;

-- Users: Users can view and update their own profile
CREATE POLICY "Users can view own profile"
    ON users FOR SELECT
    USING (auth.uid()::text = id::text);

CREATE POLICY "Users can update own profile"
    ON users FOR UPDATE
    USING (auth.uid()::text = id::text);

-- Documents: Users can manage their own documents
CREATE POLICY "Users can view own documents"
    ON documents FOR SELECT
    USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own documents"
    ON documents FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own documents"
    ON documents FOR UPDATE
    USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can delete own documents"
    ON documents FOR DELETE
    USING (auth.uid()::text = user_id::text);

-- Clauses: Users can view clauses of their documents
CREATE POLICY "Users can view clauses of own documents"
    ON clauses FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM documents 
            WHERE documents.id = clauses.document_id 
            AND documents.user_id::text = auth.uid()::text
        )
    );

-- Anomalies: Users can view anomalies of their documents
CREATE POLICY "Users can view anomalies of own documents"
    ON anomalies FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM documents 
            WHERE documents.id = anomalies.document_id 
            AND documents.user_id::text = auth.uid()::text
        )
    );

-- Queries: Users can view their own queries
CREATE POLICY "Users can view own queries"
    ON queries FOR SELECT
    USING (auth.uid()::text = user_id::text);

-- ============================================================
-- SEED DATA (Optional - for testing)
-- ============================================================

-- Uncomment to insert test user (remove in production)
-- INSERT INTO users (id, email, full_name) 
-- VALUES (
--     '00000000-0000-0000-0000-000000000000',
--     'test@example.com',
--     'Test User'
-- ) ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================

-- Run these to verify schema was created successfully

-- Check all tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('users', 'documents', 'clauses', 'anomalies', 'queries')
ORDER BY table_name;

-- Check all indexes exist
SELECT indexname 
FROM pg_indexes 
WHERE schemaname = 'public' 
AND tablename IN ('users', 'documents', 'clauses', 'anomalies', 'queries')
ORDER BY indexname;

-- Check RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('users', 'documents', 'clauses', 'anomalies', 'queries');

-- ============================================================
-- SUCCESS!
-- ============================================================

-- If you see this message, your schema was created successfully
DO $$ 
BEGIN 
    RAISE NOTICE '✅ T&C Analysis System database schema created successfully!';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Go to Storage and create "documents" bucket';
    RAISE NOTICE '  2. Add storage policies (see SUPABASE_DEPLOYMENT_GUIDE.md)';
    RAISE NOTICE '  3. Deploy your backend to Railway';
    RAISE NOTICE '  4. Deploy your frontend to Vercel';
END $$;
