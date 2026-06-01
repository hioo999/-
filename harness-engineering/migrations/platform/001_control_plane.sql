-- V4.1 MVP platform control-plane schema.
-- Platform tables must not contain case, file, document, chunk, vector, chat, prompt, answer, or credential business data.

CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS platform_users (
    id TEXT PRIMARY KEY,
    organization_id TEXT REFERENCES organizations(id),
    account TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS licenses (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    license_key_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    expired_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_instances (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    license_id TEXT REFERENCES licenses(id),
    version TEXT NOT NULL,
    status TEXT NOT NULL,
    last_heartbeat_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_heartbeats (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agent_instances(id),
    status TEXT NOT NULL,
    task_pending_count INTEGER NOT NULL DEFAULT 0,
    task_running_count INTEGER NOT NULL DEFAULT 0,
    task_failed_count INTEGER NOT NULL DEFAULT 0,
    error_code TEXT,
    cpu_usage NUMERIC,
    memory_usage NUMERIC,
    disk_usage NUMERIC,
    reported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS platform_audit_logs (
    id TEXT PRIMARY KEY,
    operator_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
