"""
SQLite Operational State Store for Trust Analyst.
Manages operational state: approvals, watches, scheduled tasks, tool-call audit logs,
and investigation step states.
References FalkorDB entity/investigation node IDs as foreign keys.
"""

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from backend.app.config import settings

logger = logging.getLogger("trust_analyst.sqlite")

_local = threading.local()


def get_db_path() -> str:
    """Returns resolved path to the operational SQLite database."""
    return getattr(settings, "SQLITE_DB_PATH", "trust_operational.db")


def _get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Returns a thread-local SQLite connection with WAL mode and foreign keys enabled."""
    target_path = db_path or get_db_path()
    # Check thread-local cache
    conn = getattr(_local, "conn", None)
    cached_path = getattr(_local, "db_path", None)
    if conn is not None and cached_path == target_path:
        return conn

    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass

    parent_dir = Path(target_path).parent
    if parent_dir and not parent_dir.exists():
        parent_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(target_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    _local.conn = conn
    _local.db_path = target_path
    return conn


@contextmanager
def get_db(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager yielding an active SQLite connection with automatic commit."""
    conn = _get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_sqlite_db(db_path: str | None = None) -> None:
    """Creates operational tables and indexes if they do not exist."""
    with get_db(db_path) as conn:
        conn.executescript(
            """
            -- Approvals (Human-in-the-Loop Remediation queue)
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                investigation_id TEXT,
                action TEXT NOT NULL,
                target_id TEXT NOT NULL,
                rationale TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at INTEGER NOT NULL,
                approver TEXT,
                approved_at INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_approvals_status_created ON approvals(status, created_at);
            CREATE INDEX IF NOT EXISTS idx_approvals_investigation ON approvals(investigation_id);
            CREATE INDEX IF NOT EXISTS idx_approvals_action_target ON approvals(action, target_id, status);

            -- Watches (Condition & telemetry monitors)
            CREATE TABLE IF NOT EXISTS watches (
                id TEXT PRIMARY KEY,
                investigation_id TEXT,
                kind TEXT NOT NULL,
                spec TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                triggered_at INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_watches_status_expires ON watches(status, expires_at);
            CREATE INDEX IF NOT EXISTS idx_watches_investigation ON watches(investigation_id);

            -- Scheduled Tasks (Time-delayed verification & recheck follow-ups)
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                investigation_id TEXT,
                action TEXT NOT NULL,
                payload TEXT NOT NULL,
                due_at INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at INTEGER NOT NULL,
                executed_at INTEGER,
                result TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_status_due ON scheduled_tasks(status, due_at);
            CREATE INDEX IF NOT EXISTS idx_tasks_investigation ON scheduled_tasks(investigation_id);

            -- Tool Calls (Append-only operational audit log)
            CREATE TABLE IF NOT EXISTS tool_calls (
                id TEXT PRIMARY KEY,
                investigation_id TEXT,
                session_id TEXT,
                tool TEXT NOT NULL,
                arguments TEXT NOT NULL,
                allowed INTEGER NOT NULL,
                reason TEXT,
                evidence_ids TEXT,
                duration_ms INTEGER NOT NULL,
                at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tool_calls_investigation ON tool_calls(investigation_id);
            CREATE INDEX IF NOT EXISTS idx_tool_calls_tool_allowed ON tool_calls(tool, allowed);

            -- Step States (Investigation checkpoint snapshots)
            CREATE TABLE IF NOT EXISTS step_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                investigation_id TEXT NOT NULL,
                step_index INTEGER NOT NULL,
                status TEXT NOT NULL,
                state_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_step_states_inv_step ON step_states(investigation_id, step_index);
            """
        )
    logger.debug("Initialized operational SQLite schema.")


def reset_sqlite_db(db_path: str | None = None) -> None:
    """Truncates all operational tables and re-initializes schema."""
    init_sqlite_db(db_path)
    with get_db(db_path) as conn:
        conn.executescript(
            """
            DELETE FROM approvals;
            DELETE FROM watches;
            DELETE FROM scheduled_tasks;
            DELETE FROM tool_calls;
            DELETE FROM step_states;
            """
        )
    logger.debug("Reset operational SQLite database.")


# -----------------------------------------------------------------------------
# Approvals Operations
# -----------------------------------------------------------------------------


def create_approval(
    approval_id: str,
    investigation_id: str,
    action: str,
    target_id: str,
    rationale: str,
    created_at: int,
    status: str = "pending",
    db_path: str | None = None,
) -> dict[str, Any]:
    """Records a new ApprovalRequest in the operational database."""
    init_sqlite_db(db_path)
    with get_db(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO approvals (id, investigation_id, action, target_id, rationale, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (approval_id, investigation_id, action, target_id, rationale, status, created_at),
        )
    return {
        "id": approval_id,
        "investigation_id": investigation_id,
        "action": action,
        "target_id": target_id,
        "rationale": rationale,
        "status": status,
        "created_at": created_at,
    }


def get_approval(approval_id: str, db_path: str | None = None) -> dict[str, Any] | None:
    """Retrieves an approval record by ID."""
    init_sqlite_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_approvals(
    investigation_id: str | None = None,
    status: str | None = None,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    """Lists approvals filtered by investigation_id and/or status."""
    init_sqlite_db(db_path)
    query = "SELECT * FROM approvals WHERE 1=1"
    params: list[Any] = []
    if investigation_id:
        query += " AND investigation_id = ?"
        params.append(investigation_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"

    with get_db(db_path) as conn:
        cursor = conn.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]


def update_approval_status(
    approval_id: str,
    status: str,
    approver: str | None = None,
    approved_at: int | None = None,
    db_path: str | None = None,
) -> bool:
    """Updates approval status (approved, rejected) and recording metadata."""
    init_sqlite_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE approvals
            SET status = ?, approver = COALESCE(?, approver), approved_at = COALESCE(?, approved_at)
            WHERE id = ?
            """,
            (status, approver, approved_at, approval_id),
        )
        return cursor.rowcount > 0


def get_approved_action(action: str, target_id: str | None = None, db_path: str | None = None) -> dict[str, Any] | None:
    """Checks if an approved approval exists for the given action and optional target."""
    init_sqlite_db(db_path)
    with get_db(db_path) as conn:
        if target_id:
            cursor = conn.execute(
                """
                SELECT * FROM approvals
                WHERE action = ? AND status = 'approved' AND (target_id = ? OR target_id = '')
                ORDER BY approved_at DESC LIMIT 1
                """,
                (action, target_id),
            )
        else:
            cursor = conn.execute(
                """
                SELECT * FROM approvals
                WHERE action = ? AND status = 'approved'
                ORDER BY approved_at DESC LIMIT 1
                """,
                (action,),
            )
        row = cursor.fetchone()
        return dict(row) if row else None


# -----------------------------------------------------------------------------
# Watches Operations
# -----------------------------------------------------------------------------


def create_watch(
    watch_id: str,
    investigation_id: str,
    kind: str,
    spec: dict[str, Any] | str,
    created_at: int,
    expires_at: int,
    status: str = "active",
    db_path: str | None = None,
) -> dict[str, Any]:
    """Registers an active condition watch in SQLite."""
    init_sqlite_db(db_path)
    spec_str = json.dumps(spec) if isinstance(spec, dict) else spec
    with get_db(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO watches (id, investigation_id, kind, spec, status, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (watch_id, investigation_id, kind, spec_str, status, created_at, expires_at),
        )
    return {
        "id": watch_id,
        "investigation_id": investigation_id,
        "kind": kind,
        "spec": spec_str,
        "status": status,
        "created_at": created_at,
        "expires_at": expires_at,
    }


def list_active_watches(db_path: str | None = None) -> list[dict[str, Any]]:
    """Fetches all currently active watches."""
    init_sqlite_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.execute("SELECT * FROM watches WHERE status = 'active' ORDER BY created_at ASC")
        return [dict(row) for row in cursor.fetchall()]


def list_watches(investigation_id: str | None = None, db_path: str | None = None) -> list[dict[str, Any]]:
    """Lists all watches, optionally filtered by investigation_id."""
    init_sqlite_db(db_path)
    with get_db(db_path) as conn:
        if investigation_id:
            cursor = conn.execute(
                "SELECT * FROM watches WHERE investigation_id = ? ORDER BY created_at DESC",
                (investigation_id,),
            )
        else:
            cursor = conn.execute("SELECT * FROM watches ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def update_watch_status(
    watch_id: str,
    status: str,
    triggered_at: int | None = None,
    db_path: str | None = None,
) -> bool:
    """Updates watch status (triggered, expired)."""
    init_sqlite_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE watches
            SET status = ?, triggered_at = COALESCE(?, triggered_at)
            WHERE id = ?
            """,
            (status, triggered_at, watch_id),
        )
        return cursor.rowcount > 0


# -----------------------------------------------------------------------------
# Scheduled Tasks Operations
# -----------------------------------------------------------------------------


def create_task(
    task_id: str,
    investigation_id: str,
    action: str,
    payload: dict[str, Any] | str,
    due_at: int,
    created_at: int,
    status: str = "pending",
    db_path: str | None = None,
) -> dict[str, Any]:
    """Enqueues a new scheduled task."""
    init_sqlite_db(db_path)
    payload_str = json.dumps(payload) if isinstance(payload, dict) else payload
    with get_db(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO scheduled_tasks (id, investigation_id, action, payload, due_at, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, investigation_id, action, payload_str, due_at, status, created_at),
        )
    return {
        "id": task_id,
        "investigation_id": investigation_id,
        "action": action,
        "payload": payload_str,
        "due_at": due_at,
        "status": status,
        "created_at": created_at,
    }


def list_due_tasks(now: int, db_path: str | None = None) -> list[dict[str, Any]]:
    """Retrieves all pending scheduled tasks whose due_at <= now."""
    init_sqlite_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT * FROM scheduled_tasks
            WHERE status = 'pending' AND due_at <= ?
            ORDER BY due_at ASC
            """,
            (now,),
        )
        return [dict(row) for row in cursor.fetchall()]


def list_tasks(investigation_id: str | None = None, db_path: str | None = None) -> list[dict[str, Any]]:
    """Lists all scheduled tasks, optionally filtered by investigation_id."""
    init_sqlite_db(db_path)
    with get_db(db_path) as conn:
        if investigation_id:
            cursor = conn.execute(
                "SELECT * FROM scheduled_tasks WHERE investigation_id = ? ORDER BY due_at ASC",
                (investigation_id,),
            )
        else:
            cursor = conn.execute("SELECT * FROM scheduled_tasks ORDER BY due_at ASC")
        return [dict(row) for row in cursor.fetchall()]


def update_task_status(
    task_id: str,
    status: str,
    executed_at: int | None = None,
    result: str | None = None,
    db_path: str | None = None,
) -> bool:
    """Updates scheduled task status (completed, failed)."""
    init_sqlite_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE scheduled_tasks
            SET status = ?, executed_at = COALESCE(?, executed_at), result = COALESCE(?, result)
            WHERE id = ?
            """,
            (status, executed_at, result, task_id),
        )
        return cursor.rowcount > 0


# -----------------------------------------------------------------------------
# Tool Calls Audit Log Operations
# -----------------------------------------------------------------------------


def log_tool_call(
    call_id: str,
    tool: str,
    arguments: dict[str, Any] | str,
    allowed: bool,
    reason: str,
    evidence_ids: list[str],
    duration_ms: int,
    at: int,
    session_id: str | None = None,
    investigation_id: str | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Appends a tool execution record to the audit log."""
    init_sqlite_db(db_path)
    args_str = json.dumps(arguments) if isinstance(arguments, dict) else str(arguments)
    evidence_str = json.dumps(evidence_ids)
    with get_db(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO tool_calls (
                id, investigation_id, session_id, tool, arguments, allowed, reason, evidence_ids, duration_ms, at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                call_id,
                investigation_id,
                session_id,
                tool,
                args_str,
                1 if allowed else 0,
                reason,
                evidence_str,
                duration_ms,
                at,
            ),
        )
    return {
        "id": call_id,
        "tool": tool,
        "allowed": allowed,
        "reason": reason,
        "investigation_id": investigation_id,
        "session_id": session_id,
        "at": at,
    }


def list_tool_calls(
    investigation_id: str | None = None,
    tool: str | None = None,
    limit: int = 100,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    """Fetches recent tool calls from the audit log."""
    init_sqlite_db(db_path)
    query = "SELECT * FROM tool_calls WHERE 1=1"
    params: list[Any] = []
    if investigation_id:
        query += " AND investigation_id = ?"
        params.append(investigation_id)
    if tool:
        query += " AND tool = ?"
        params.append(tool)
    query += " ORDER BY at DESC LIMIT ?"
    params.append(limit)

    with get_db(db_path) as conn:
        cursor = conn.execute(query, tuple(params))
        rows = []
        for r in cursor.fetchall():
            d = dict(r)
            d["allowed"] = bool(d["allowed"])
            if d.get("arguments"):
                try:
                    d["arguments"] = json.loads(d["arguments"])
                except Exception:
                    pass
            if d.get("evidence_ids"):
                try:
                    d["evidence_ids"] = json.loads(d["evidence_ids"])
                except Exception:
                    pass
            rows.append(d)
        return rows


def count_tool_calls_for_investigation(investigation_id: str, db_path: str | None = None) -> int:
    """Counts total tool calls recorded for an investigation."""
    init_sqlite_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.execute(
            "SELECT count(*) FROM tool_calls WHERE investigation_id = ?",
            (investigation_id,),
        )
        return cursor.fetchone()[0]


# -----------------------------------------------------------------------------
# Step States Checkpoints
# -----------------------------------------------------------------------------


def save_step_state(
    investigation_id: str,
    step_index: int,
    status: str,
    state_json: str,
    created_at: int,
    db_path: str | None = None,
) -> int:
    """Saves an investigation execution step checkpoint."""
    init_sqlite_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO step_states (investigation_id, step_index, status, state_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (investigation_id, step_index, status, state_json, created_at),
        )
        return cursor.lastrowid or 0


def get_latest_step_state(investigation_id: str, db_path: str | None = None) -> dict[str, Any] | None:
    """Fetches the latest checkpoint state for an investigation."""
    init_sqlite_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT * FROM step_states
            WHERE investigation_id = ?
            ORDER BY step_index DESC, id DESC LIMIT 1
            """,
            (investigation_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_step_states(investigation_id: str, db_path: str | None = None) -> list[dict[str, Any]]:
    """Lists all historical step checkpoints for an investigation in chronological order."""
    init_sqlite_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM step_states WHERE investigation_id = ? ORDER BY step_index ASC, id ASC",
            (investigation_id,),
        )
        return [dict(row) for row in cursor.fetchall()]
