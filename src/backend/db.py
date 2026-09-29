import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from .config import DB_PATH


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY, filename TEXT NOT NULL, stored_name TEXT NOT NULL,
                file_type TEXT NOT NULL, size_bytes INTEGER NOT NULL, mime_type TEXT,
                sample_rate REAL, center_frequency REAL, iq_format TEXT,
                channels INTEGER, duration REAL, num_samples INTEGER,
                requires_metadata INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS analysis_jobs (
                id TEXT PRIMARY KEY, signal_id TEXT NOT NULL, status TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0, stage TEXT, message TEXT,
                error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS analysis_results (
                analysis_id TEXT PRIMARY KEY, signal_id TEXT NOT NULL,
                result_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reports (
                analysis_id TEXT PRIMARY KEY, report_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            """
        )


def get_signal(signal_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM signals WHERE id = ?", (signal_id,)).fetchone()
    return dict(row) if row else None


def list_signals() -> list[dict[str, Any]]:
    with connection() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM signals ORDER BY created_at DESC")]


def insert_signal(values: dict[str, Any]) -> None:
    fields = ["id", "filename", "stored_name", "file_type", "size_bytes", "mime_type", "sample_rate", "center_frequency", "iq_format", "channels", "duration", "num_samples", "requires_metadata", "created_at"]
    with connection() as conn:
        conn.execute(f"INSERT INTO signals ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})", [values.get(k) for k in fields])


def update_signal(signal_id: str, values: dict[str, Any]) -> None:
    with connection() as conn:
        assignments = ",".join(f"{key} = ?" for key in values)
        conn.execute(f"UPDATE signals SET {assignments} WHERE id = ?", [*values.values(), signal_id])


def delete_signal(signal_id: str) -> None:
    with connection() as conn:
        conn.execute("DELETE FROM signals WHERE id = ?", (signal_id,))


def insert_job(job_id: str, signal_id: str) -> None:
    now = _now()
    with connection() as conn:
        conn.execute("INSERT INTO analysis_jobs (id, signal_id, status, stage, message, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (job_id, signal_id, "QUEUED", "QUEUED", "Analysis queued", now, now))


def get_job(job_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM analysis_jobs WHERE id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def update_job(job_id: str, **values: Any) -> None:
    values["updated_at"] = _now()
    with connection() as conn:
        assignments = ",".join(f"{key} = ?" for key in values)
        conn.execute(f"UPDATE analysis_jobs SET {assignments} WHERE id = ?", [*values.values(), job_id])


def save_result(analysis_id: str, signal_id: str, result: dict[str, Any]) -> None:
    with connection() as conn:
        conn.execute("INSERT OR REPLACE INTO analysis_results VALUES (?, ?, ?, ?)", (analysis_id, signal_id, json.dumps(result), _now()))


def get_result(analysis_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT result_json FROM analysis_results WHERE analysis_id = ?", (analysis_id,)).fetchone()
    return json.loads(row[0]) if row else None


def latest_result_for_signal(signal_id: str) -> dict[str, Any] | None:
    # analysis_jobs keys its rows on `id`; there is no `analysis_id` column.
    with connection() as conn:
        row = conn.execute("SELECT id FROM analysis_jobs WHERE signal_id = ? AND status = 'COMPLETED' ORDER BY updated_at DESC LIMIT 1", (signal_id,)).fetchone()
    return get_result(row[0]) if row else None


def save_report(analysis_id: str, report: dict[str, Any]) -> None:
    with connection() as conn:
        conn.execute("INSERT OR REPLACE INTO reports VALUES (?, ?, ?)", (analysis_id, json.dumps(report), _now()))


def get_report(analysis_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT report_json FROM reports WHERE analysis_id = ?", (analysis_id,)).fetchone()
    return json.loads(row[0]) if row else None
