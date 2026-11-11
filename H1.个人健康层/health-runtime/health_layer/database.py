from __future__ import annotations

import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA_VERSION = "health-db-v0.1"


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_versions (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS health_profiles (
    profile_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS health_sources (
    source_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_device TEXT,
    source_app TEXT,
    authorization_status TEXT NOT NULL DEFAULT 'unknown',
    priority INTEGER NOT NULL DEFAULT 100,
    first_sample_at TEXT,
    last_sample_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS health_import_batches (
    import_batch_id TEXT PRIMARY KEY,
    source_filename TEXT NOT NULL,
    source_file_hash TEXT NOT NULL,
    source_file_size INTEGER NOT NULL,
    importer_version TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    total_records INTEGER NOT NULL DEFAULT 0,
    inserted_records INTEGER NOT NULL DEFAULT 0,
    duplicate_records INTEGER NOT NULL DEFAULT 0,
    skipped_records INTEGER NOT NULL DEFAULT 0,
    error_records INTEGER NOT NULL DEFAULT 0,
    error_log_json TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_import_batches_hash
    ON health_import_batches(source_file_hash);

CREATE TABLE IF NOT EXISTS health_raw_samples (
    sample_id TEXT PRIMARY KEY,
    record_kind TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    start_time TEXT,
    end_time TEXT,
    value_text TEXT,
    value_num REAL,
    unit TEXT,
    source_device TEXT,
    source_app TEXT,
    source_record_id TEXT,
    timezone TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    raw_payload_json TEXT NOT NULL,
    first_import_batch_id TEXT NOT NULL REFERENCES health_import_batches(import_batch_id),
    source_file_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_raw_metric_start
    ON health_raw_samples(metric_type, start_time);
CREATE INDEX IF NOT EXISTS idx_raw_source
    ON health_raw_samples(source_app, source_device);

CREATE TABLE IF NOT EXISTS health_import_memberships (
    import_batch_id TEXT NOT NULL REFERENCES health_import_batches(import_batch_id),
    sample_id TEXT NOT NULL REFERENCES health_raw_samples(sample_id),
    outcome TEXT NOT NULL CHECK(outcome IN ('inserted', 'duplicate')),
    PRIMARY KEY (import_batch_id, sample_id)
);

CREATE TABLE IF NOT EXISTS health_normalized_samples (
    sample_id TEXT PRIMARY KEY REFERENCES health_raw_samples(sample_id),
    canonical_metric TEXT NOT NULL,
    numeric_value REAL,
    text_value TEXT,
    canonical_unit TEXT,
    local_start_time TEXT,
    local_end_time TEXT,
    timezone TEXT,
    quality_status TEXT NOT NULL DEFAULT 'accepted',
    quality_notes_json TEXT NOT NULL DEFAULT '[]',
    normalization_version TEXT NOT NULL,
    normalized_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_normalized_metric_start
    ON health_normalized_samples(canonical_metric, local_start_time);
CREATE INDEX IF NOT EXISTS idx_normalized_start
    ON health_normalized_samples(local_start_time);
CREATE INDEX IF NOT EXISTS idx_normalized_end
    ON health_normalized_samples(local_end_time);

CREATE TABLE IF NOT EXISTS health_daily_summaries (
    date TEXT PRIMARY KEY,
    timezone TEXT NOT NULL,
    status TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    calculation_version TEXT NOT NULL,
    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS health_daily_reports (
    report_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    status TEXT NOT NULL,
    report_json TEXT NOT NULL,
    markdown TEXT NOT NULL,
    related_daily_report_id TEXT,
    report_version TEXT NOT NULL,
    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, report_version)
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    return connection


def initialize(db_path: str | Path) -> None:
    with closing(connect(db_path)) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.execute(
            "INSERT OR IGNORE INTO schema_versions(version) VALUES (?)",
            (SCHEMA_VERSION,),
        )
        connection.commit()


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    try:
        connection.execute("BEGIN")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

