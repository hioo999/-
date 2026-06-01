-- V4.1 MVP Agent local data-plane schema.
-- Business data is allowed only in the lawyer-side Agent local database.

CREATE TABLE IF NOT EXISTS local_users (
    id TEXT PRIMARY KEY,
    account TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    password_hash TEXT,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,
    permissions JSONB
);

CREATE TABLE IF NOT EXISTS case_spaces (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    cause_of_action TEXT,
    parties JSONB,
    court TEXT,
    stage TEXT,
    client_name TEXT,
    owner_id TEXT,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS case_members (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES case_spaces(id),
    user_id TEXT NOT NULL REFERENCES local_users(id),
    role_code TEXT NOT NULL,
    granted_by TEXT,
    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS local_data_sources (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    path TEXT NOT NULL,
    status TEXT NOT NULL,
    permission_status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS local_files (
    id TEXT PRIMARY KEY,
    data_source_id TEXT REFERENCES local_data_sources(id),
    case_id TEXT REFERENCES case_spaces(id),
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_ext TEXT,
    file_size BIGINT,
    file_hash TEXT,
    modified_at TIMESTAMP,
    process_status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS processing_tasks (
    id TEXT PRIMARY KEY,
    file_id TEXT REFERENCES local_files(id),
    case_id TEXT REFERENCES case_spaces(id),
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    error_code TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES case_spaces(id),
    file_id TEXT NOT NULL REFERENCES local_files(id),
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    page_number INTEGER,
    paragraph_ref TEXT,
    token_count INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vector_index_refs (
    id TEXT PRIMARY KEY,
    chunk_id TEXT NOT NULL REFERENCES document_chunks(id),
    vector_collection TEXT NOT NULL,
    vector_id TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES case_spaces(id),
    user_id TEXT REFERENCES local_users(id),
    title TEXT,
    save_mode TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES chat_sessions(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    has_citations BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS citations (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES chat_messages(id),
    file_id TEXT NOT NULL REFERENCES local_files(id),
    chunk_id TEXT NOT NULL REFERENCES document_chunks(id),
    page_number INTEGER,
    paragraph_ref TEXT,
    quote_text TEXT NOT NULL,
    relevance_score NUMERIC,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_configs (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    base_url TEXT NOT NULL,
    chat_model TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT,
    ip_address TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
