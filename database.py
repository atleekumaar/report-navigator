"""
Database Integration Layer for Report Navigator.

Supports Neon Serverless PostgreSQL with graceful fallback
to local file-based storage when DATABASE_URL is not set.
Background execution ensures database operations never block user request latency.
"""

import os
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional
from pathlib import Path
import config

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Background executor for non-blocking logging
_db_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="neon_db_worker")

# Cached health check to prevent high-latency cross-region roundtrips on every ping
_last_health_check_time = 0.0
_cached_health_status: Dict[str, Any] = {"status": "uninitialized", "mode": "neon_postgresql"}
_health_lock = threading.Lock()

# Schema DDL for Neon Serverless PostgreSQL
POSTGRES_SCHEMA_SQL = """
-- Neon Serverless PostgreSQL Schema for Report Navigator
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
    chunk_type VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    page_number INT NOT NULL,
    section VARCHAR(255),
    rects_json JSONB,
    table_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS query_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(64),
    query TEXT NOT NULL,
    answer TEXT NOT NULL,
    confidence FLOAT,
    citations_json JSONB,
    latency_ms INT,
    user_rating VARCHAR(16),
    user_comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc_page ON document_chunks(document_id, page_number);
CREATE INDEX IF NOT EXISTS idx_query_logs_created ON query_logs(created_at DESC);
"""


def is_database_connected() -> bool:
    """Check if a remote PostgreSQL / Neon database is configured."""
    return bool(DATABASE_URL and DATABASE_URL.startswith("postgres"))


def _get_connection():
    """Return a psycopg connection to Neon, or None if unavailable."""
    if not is_database_connected():
        return None
    try:
        import psycopg
        url = DATABASE_URL
        sep = "&" if "?" in url else "?"
        if "connect_timeout" not in url:
            url = url + sep + "connect_timeout=10"
        return psycopg.connect(url, autocommit=True)
    except Exception as e:
        print(f"[DB] Connection failed: {e}")
        return None


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
        url = DATABASE_URL
        sep = "&" if "?" in url else "?"
        if "connect_timeout" not in url:
            url = url + sep + "connect_timeout=10"
        with psycopg.connect(url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(POSTGRES_SCHEMA_SQL)
        return {
            "mode": "neon_postgresql",
            "database_url": DATABASE_URL.split("@")[-1],  # sanitized
            "status": "ready"
        }
    except ImportError:
        return {
            "mode": "local_file_store_psycopg_missing",
            "message": "DATABASE_URL detected. Install psycopg to enable Neon: pip install psycopg[binary]",
            "status": "local_fallback"
        }
    except Exception as e:
        return {
            "mode": "local_fallback",
            "error": str(e),
            "status": "local_fallback"
        }


def check_health() -> Dict[str, Any]:
    """Check database connectivity for health endpoint with 60s caching."""
    global _last_health_check_time, _cached_health_status
    if not is_database_connected():
        return {"status": "not_configured", "mode": "local_file_store"}

    now = time.time()
    with _health_lock:
        if now - _last_health_check_time < 60.0 and _cached_health_status.get("status") in ("connected", "error"):
            return _cached_health_status

    conn = _get_connection()
    if conn is None:
        result = {"status": "error", "mode": "neon_postgresql", "detail": "connection_failed"}
    else:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
            result = {"status": "connected", "mode": "neon_postgresql"}
        except Exception as e:
            result = {"status": "error", "mode": "neon_postgresql", "detail": str(e)}

    with _health_lock:
        _last_health_check_time = now
        _cached_health_status = result

    return result


def _sync_log_query(document_id, query, answer, confidence, citations, latency_ms):
    """Worker task: insert query log row into Neon."""
    conn = _get_connection()
    if conn is None:
        return False
    # Safely normalize confidence to numeric float if string (e.g. "high" -> 0.95)
    conf_val = None
    if isinstance(confidence, (int, float)):
        conf_val = float(confidence)
    elif isinstance(confidence, str):
        cmap = {"high": 0.95, "medium": 0.70, "low": 0.40}
        conf_val = cmap.get(confidence.lower().strip())
        if conf_val is None:
            try:
                conf_val = float(confidence)
            except ValueError:
                pass

    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO query_logs (document_id, query, answer, confidence, citations_json, latency_ms)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    document_id,
                    query[:2000],
                    answer[:8000],
                    conf_val,
                    json.dumps(citations) if citations else None,
                    latency_ms,
                ),
            )
        conn.close()
        return True
    except Exception as e:
        print(f"[DB] async log_query failed: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return False


def log_query(
    document_id: Optional[str],
    query: str,
    answer: str,
    confidence: Optional[float] = None,
    citations: Optional[List[Dict]] = None,
    latency_ms: Optional[int] = None,
) -> bool:
    """Non-blocking fire-and-forget query logging into Neon."""
    if not is_database_connected():
        return False
    _db_pool.submit(
        _sync_log_query,
        document_id,
        query,
        answer,
        confidence,
        citations,
        latency_ms
    )
    return True


def _sync_log_feedback(query, answer, rating, comment):
    """Worker task: record user feedback into Neon."""
    conn = _get_connection()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE query_logs
                   SET user_rating = %s, user_comment = %s
                   WHERE id = (
                       SELECT id FROM query_logs
                       WHERE query = %s AND answer = %s
                       ORDER BY created_at DESC LIMIT 1
                   )""",
                (rating, comment, query[:2000], answer[:8000]),
            )
            if cur.rowcount == 0:
                cur.execute(
                    """INSERT INTO query_logs (document_id, query, answer, user_rating, user_comment)
                       VALUES (NULL, %s, %s, %s, %s)""",
                    (query[:2000], answer[:8000], rating, comment),
                )
        conn.close()
        return True
    except Exception as e:
        print(f"[DB] async log_feedback failed: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return False


def log_feedback(
    query: str,
    answer: str,
    rating: str,
    comment: Optional[str] = None,
) -> bool:
    """Non-blocking fire-and-forget feedback logging into Neon."""
    if not is_database_connected():
        return False
    _db_pool.submit(_sync_log_feedback, query, answer, rating, comment)
    return True


def _sync_register_document(doc_id, filename, title, page_count, table_count, file_size):
    """Worker task: upsert document in Neon."""
    conn = _get_connection()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO documents (id, filename, title, page_count, table_count, file_size_bytes, is_active)
                   VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                   ON CONFLICT (id) DO UPDATE SET
                       filename = EXCLUDED.filename,
                       title = EXCLUDED.title,
                       page_count = EXCLUDED.page_count,
                       table_count = EXCLUDED.table_count,
                       file_size_bytes = EXCLUDED.file_size_bytes,
                       is_active = TRUE""",
                (doc_id, filename, title, page_count, table_count, file_size),
            )
            cur.execute(
                "UPDATE documents SET is_active = FALSE WHERE id != %s",
                (doc_id,),
            )
        conn.close()
        return True
    except Exception as e:
        print(f"[DB] async register_document failed: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return False


def register_document(
    doc_id: str,
    filename: str,
    title: Optional[str] = None,
    page_count: int = 0,
    table_count: int = 0,
    file_size: int = 0,
) -> bool:
    """Non-blocking fire-and-forget document registration in Neon."""
    if not is_database_connected():
        return False
    _db_pool.submit(
        _sync_register_document,
        doc_id,
        filename,
        title,
        page_count,
        table_count,
        file_size
    )
    return True
