"""
SQLite Database Module (aiosqlite)
Manages sessions and messages for the Agent Chat MVP.
"""

import sqlite3
import aiosqlite
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")


import asyncio
from contextlib import asynccontextmanager

# Global lock to serialize database writes
db_lock = asyncio.Lock()

@asynccontextmanager
async def get_connection():
    """Get a SQLite connection with row factory."""
    async with aiosqlite.connect(DB_PATH, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row
        # PRAGMA is set in init_db now
        yield conn


async def init_db():
    """Create tables if they don't exist."""
    async with get_connection() as conn:
        # Enable WAL mode for better concurrency
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA synchronous=NORMAL;")
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL DEFAULT 'New Chat',
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)

        await conn.execute("""
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

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id     TEXT PRIMARY KEY,
                profile_data TEXT NOT NULL DEFAULT '[]'
            );
        """)

        # --- Performance index ---
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id, timestamp);
        """)

        await conn.commit()


# --- Session CRUD ---

async def create_session(session_id: str, title: str = "New Chat") -> dict:
    async with db_lock:
        async with get_connection() as conn:
            await conn.execute(
                "INSERT INTO sessions (id, title) VALUES (?, ?)",
                (session_id, title),
            )
            await conn.commit()
            async with conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)) as cursor:
                row = await cursor.fetchone()
            return dict(row)


async def list_sessions() -> list[dict]:
    async with get_connection() as conn:
        async with conn.execute("SELECT * FROM sessions ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_session_title(session_id: str, title: str):
    async with db_lock:
        async with get_connection() as conn:
            await conn.execute(
                "UPDATE sessions SET title = ? WHERE id = ?",
                (title, session_id),
            )
            await conn.commit()


async def delete_session(session_id: str):
    async with db_lock:
        async with get_connection() as conn:
            await conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await conn.commit()

async def delete_all_sessions():
    async with db_lock:
        async with get_connection() as conn:
            await conn.execute("DELETE FROM sessions")
            await conn.commit()


# --- Message CRUD ---

async def add_message(session_id: str, role: str, content: str, msg_type: str = "text") -> dict:
    async with db_lock:
        async with get_connection() as conn:
            cursor = await conn.execute(
                "INSERT INTO messages (session_id, role, content, msg_type) VALUES (?, ?, ?, ?)",
                (session_id, role, content, msg_type),
            )
            await conn.commit()
            async with conn.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)) as fetch_cursor:
                row = await fetch_cursor.fetchone()
            return dict(row)


async def get_session_messages(session_id: str) -> list[dict]:
    async with get_connection() as conn:
        async with conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,)
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]

# --- User Profile ---

async def get_user_profile(user_id: str = "default_user") -> list:
    async with get_connection() as conn:
        async with conn.execute("SELECT profile_data FROM user_profiles WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
        if row:
            return json.loads(row["profile_data"])
        return []

async def append_user_profile(answer: str, user_id: str = "default_user"):
    profile = await get_user_profile(user_id)
    profile.append(answer)
    async with db_lock:
        async with get_connection() as conn:
            await conn.execute(
                "INSERT INTO user_profiles (user_id, profile_data) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET profile_data=excluded.profile_data",
                (user_id, json.dumps(profile, ensure_ascii=False))
            )
            await conn.commit()

async def clear_user_profile(user_id: str = "default_user"):
    async with db_lock:
        async with get_connection() as conn:
            await conn.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
            await conn.commit()
