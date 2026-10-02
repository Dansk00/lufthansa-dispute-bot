import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "database.sqlite")
EVIDENCE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "evidence")
ATTACHMENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "attachments")


def init_db(db_path: str = DB_PATH) -> None:
    """Initializes the database schema and required evidence directories."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    os.makedirs(ATTACHMENTS_DIR, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                protocol_number TEXT,
                generated_text TEXT NOT NULL,
                attachment_filename TEXT,
                screenshot_path TEXT,
                error_message TEXT,
                execution_time_seconds REAL,
                mode TEXT DEFAULT 'AUTO'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Default schedule if not set
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('scheduled_time', '09:00')")
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('is_active', '1')")
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_retry_on_fail', '1')")
        conn.commit()


class DatabaseManager:
    """Handles all SQLite persistence operations for Lufthansa feedback bot."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def record_submission(
        self,
        status: str,
        generated_text: str,
        protocol_number: Optional[str] = None,
        attachment_filename: Optional[str] = None,
        screenshot_path: Optional[str] = None,
        error_message: Optional[str] = None,
        execution_time_seconds: float = 0.0,
        mode: str = "AUTO"
    ) -> int:
        """Records a new submission attempt with full evidence."""
        now = datetime.now().isoformat()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO submissions (
                    timestamp, status, protocol_number, generated_text,
                    attachment_filename, screenshot_path, error_message,
                    execution_time_seconds, mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    status,
                    protocol_number,
                    generated_text,
                    attachment_filename,
                    screenshot_path,
                    error_message,
                    execution_time_seconds,
                    mode,
                )
            )
            conn.commit()
            return int(cursor.lastrowid or 0)

    def get_recent_submissions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent submission records."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM submissions ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_submission_by_id(self, sub_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single submission by ID."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM submissions WHERE id = ?", (sub_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_summary_stats(self) -> Dict[str, Any]:
        """Calculates operational stats for the dashboard."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM submissions")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM submissions WHERE status = 'SUCCESS'")
            success_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM submissions WHERE status != 'SUCCESS'")
            fail_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT protocol_number, timestamp FROM submissions WHERE status = 'SUCCESS' ORDER BY id DESC LIMIT 1"
            )
            last_success_row = cursor.fetchone()

            cursor.execute("SELECT * FROM submissions ORDER BY id DESC LIMIT 1")
            last_run_row = cursor.fetchone()

            cursor.execute("SELECT key, value FROM settings")
            settings = dict(cursor.fetchall())

            return {
                "total_runs": total,
                "success_count": success_count,
                "fail_count": fail_count,
                "success_rate": round((success_count / total * 100), 1) if total > 0 else 0,
                "last_success_protocol": last_success_row["protocol_number"] if last_success_row else None,
                "last_success_time": last_success_row["timestamp"] if last_success_row else None,
                "last_run": dict(last_run_row) if last_run_row else None,
                "settings": settings
            }

    def update_setting(self, key: str, value: str) -> None:
        """Updates a configuration setting."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value))
            )
            conn.commit()


if __name__ == "__main__":
    db = DatabaseManager()
    stats = db.get_summary_stats()
    print("Database initialized successfully. Current stats:", stats)
