import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from backend.config import Settings


class ChatHistoryStore:

    def __init__(self, settings: Settings):
        self._db_path = settings.chat_history_db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    safety_flagged INTEGER NOT NULL DEFAULT 0
                )"""
            )
            # Migrate DBs created before safety_flagged existed.
            cols = {row[1] for row in conn.execute("PRAGMA table_info(chat_sessions)")}
            if "safety_flagged" not in cols:
                conn.execute(
                    "ALTER TABLE chat_sessions ADD COLUMN safety_flagged INTEGER NOT NULL DEFAULT 0"
                )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES chat_sessions(session_id),
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            # Migrate DBs created before sources_json existed.
            msg_cols = {row[1] for row in conn.execute("PRAGMA table_info(chat_messages)")}
            if "sources_json" not in msg_cols:
                conn.execute(
                    "ALTER TABLE chat_messages ADD COLUMN sources_json TEXT NOT NULL DEFAULT '[]'"
                )
            conn.commit()

    def create_session(self, session_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO chat_sessions (session_id, created_at) VALUES (?, ?)",
                (session_id, now),
            )
            conn.commit()

    def save_turn(
        self,
        session_id: str,
        user_msg: str,
        assistant_msg: str,
        sources: list[dict] | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO chat_messages (session_id, role, content, created_at, sources_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, "user", user_msg, now, "[]"),
            )
            conn.execute(
                "INSERT INTO chat_messages (session_id, role, content, created_at, sources_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, "assistant", assistant_msg, now, json.dumps(sources or [])),
            )
            conn.commit()

    def flag_session_safety(self, session_id: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE chat_sessions SET safety_flagged = 1 WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()

    def is_session_flagged(self, session_id: str) -> bool:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT safety_flagged FROM chat_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            return bool(row and row[0])

    def load_history(self, session_id: str) -> list[dict]:
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                "SELECT role, content, created_at, sources_json FROM chat_messages "
                "WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            )
            return [
                {
                    "role": role,
                    "content": content,
                    "created_at": created_at,
                    "sources": json.loads(sources_json) if sources_json else [],
                }
                for role, content, created_at, sources_json in cursor.fetchall()
            ]
