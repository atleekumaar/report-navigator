"""
Database Integration Layer for Report Navigator.

Supports Neon Serverless PostgreSQL with pgvector (or relational storage),
with automatic graceful fallback to the local file-based index store.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import config

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Schema DDL for Neon Serverless PostgreSQL
POSTGRES_SCHEMA_SQL = """
-- Neon Serverless PostgreSQL Schema for Report Navigator
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Uncomment if pgvector is enabled on Neon:
-- CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(64) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    title VARCHAR(512),
    page_count INT DEFAULT 0,
    table_count INT DEFAULT 0,
    file_size_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    chunk_type VARCHAR(32) NOT NULL, -- 'text' or 'table'
    content TEXT NOT NULL,
    page_number INT NOT NULL,
    section VARCHAR(255),
    rects_json JSONB,
    table_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS query_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id VARCHAR(64),
    query TEXT NOT NULL,
    answer TEXT NOT NULL,
    confidence FLOAT,
    citations_json JSONB,
    latency_ms INT,
    user_rating VARCHAR(16), -- 'positive', 'negative'
    user_comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc_page ON document_chunks(document_id, page_number);
CREATE INDEX IF NOT EXISTS idx_query_logs_created ON query_logs(created_at DESC);
"""


def is_database_connected() -> bool:
    """Check if a remote PostgreSQL / Neon database is configured."""
    return bool(DATABASE_URL and DATABASE_URL.startswith("postgres"))


def init_database() -> Dict[str, Any]:
    """
    Initialize database schema if DATABASE_URL is provided,
    otherwise confirm local file storage is active.
    """
    if not is_database_connected():
        return {
            "mode": "local_file_store",
            "index_dir": str(config.INDEX_DIR),
            "status": "ready"
        }

    try:
        import psycopg
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(POSTGRES_SCHEMA_SQL)
            conn.commit()
        return {
            "mode": "neon_postgresql",
            "database_url": DATABASE_URL.split("@")[-1],  # sanitized without password
            "status": "ready"
        }
    except ImportError:
        # Fallback to local file store if psycopg is not installed locally
        return {
            "mode": "local_file_store_psycopg_missing",
            "message": "DATABASE_URL detected. Install psycopg to enable Neon synchronization: pip install psycopg[binary]",
            "status": "local_fallback"
        }
    except Exception as e:
        return {
            "mode": "local_fallback",
            "error": str(e),
            "status": "local_fallback"
        }
