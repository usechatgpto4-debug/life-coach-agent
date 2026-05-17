"""
SQLite Database Module
Manages sessions and messages for the Agent Chat MVP.
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")


def get_connection():
    """Get a SQLite connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL DEFAULT 'New Chat',
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            role        TEXT NOT NULL CHECK(role IN ('user', 'agent')),
            content     TEXT NOT NULL,
            msg_type    TEXT NOT NULL DEFAULT 'text' CHECK(msg_type IN ('text', 'mcq', 'file', 'survey')),
            timestamp   TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id     TEXT PRIMARY KEY,
            profile_data TEXT NOT NULL DEFAULT '[]'
        );
    """)

    # --- Performance index ---
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_session
        ON messages(session_id, timestamp);
    """)

    conn.commit()
    conn.close()


# --- Session CRUD ---

def create_session(session_id: str, title: str = "New Chat") -> dict:
    conn = get_connection()
    conn.execute(
        "INSERT INTO sessions (id, title) VALUES (?, ?)",
        (session_id, title),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return dict(row)


def list_sessions() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sessions ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_session_title(session_id: str, title: str):
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET title = ? WHERE id = ?",
        (title, session_id),
    )
    conn.commit()
    conn.close()


def delete_session(session_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

def delete_all_sessions():
    conn = get_connection()
    conn.execute("DELETE FROM sessions")
    conn.commit()
    conn.close()


# --- Message CRUD ---

def add_message(session_id: str, role: str, content: str, msg_type: str = "text") -> dict:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO messages (session_id, role, content, msg_type) VALUES (?, ?, ?, ?)",
        (session_id, role, content, msg_type),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return dict(row)


def get_session_messages(session_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- User Profile ---

def get_user_profile(user_id: str = "default_user") -> list:
    conn = get_connection()
    row = conn.execute("SELECT profile_data FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if row:
        return json.loads(row["profile_data"])
    return []

def append_user_profile(answer: str, user_id: str = "default_user"):
    profile = get_user_profile(user_id)
    profile.append(answer)
    conn = get_connection()
    conn.execute(
        "INSERT INTO user_profiles (user_id, profile_data) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET profile_data=excluded.profile_data",
        (user_id, json.dumps(profile, ensure_ascii=False))
    )
    conn.commit()
    conn.close()

def clear_user_profile(user_id: str = "default_user"):
    conn = get_connection()
    conn.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
