"""
📦 База данных — db.py
Используется ботом и веб-панелью
"""

import aiosqlite
import asyncio
import json
from datetime import datetime

DB_PATH = "grouphelp.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS groups (
                chat_id     INTEGER PRIMARY KEY,
                title       TEXT,
                username    TEXT DEFAULT '',
                joined_at   TEXT DEFAULT (datetime('now')),
                is_active   INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT DEFAULT '',
                full_name   TEXT DEFAULT '',
                first_seen  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS group_settings (
                chat_id             INTEGER PRIMARY KEY,
                welcome_enabled     INTEGER DEFAULT 1,
                goodbye_enabled     INTEGER DEFAULT 1,
                antiflood           INTEGER DEFAULT 1,
                antilinks           INTEGER DEFAULT 1,
                badwords            INTEGER DEFAULT 1,
                antispam_enabled    INTEGER DEFAULT 1,
                log_actions         INTEGER DEFAULT 1,
                antibot             INTEGER DEFAULT 0,
                max_warns           INTEGER DEFAULT 3,
                warn_action         TEXT DEFAULT 'ban',
                welcome_text        TEXT DEFAULT '',
                goodbye_text        TEXT DEFAULT '',
                rules               TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS warnings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER,
                user_id     INTEGER,
                mod_id      INTEGER,
                reason      TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS actions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER,
                mod_id      INTEGER,
                target_id   INTEGER,
                action_type TEXT,
                reason      TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS notes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER,
                name        TEXT,
                text        TEXT,
                created_by  INTEGER,
                created_at  TEXT DEFAULT (datetime('now')),
                UNIQUE(chat_id, name)
            );

            CREATE TABLE IF NOT EXISTS filters (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER,
                keyword     TEXT,
                response    TEXT,
                created_by  INTEGER,
                created_at  TEXT DEFAULT (datetime('now')),
                UNIQUE(chat_id, keyword)
            );

            CREATE TABLE IF NOT EXISTS bad_words (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER,
                word        TEXT,
                created_by  INTEGER,
                UNIQUE(chat_id, word)
            );

            CREATE TABLE IF NOT EXISTS antispam_requests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                username    TEXT DEFAULT '',
                full_name   TEXT DEFAULT '',
                reason      TEXT,
                status      TEXT DEFAULT 'pending',
                created_at  TEXT DEFAULT (datetime('now')),
                resolved_at TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS event_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     TEXT,
                chat_title  TEXT DEFAULT '',
                user_id     INTEGER,
                event_type  TEXT,
                details     TEXT DEFAULT '',
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS global_stats (
                key         TEXT PRIMARY KEY,
                value       INTEGER DEFAULT 0
            );

            INSERT OR IGNORE INTO global_stats VALUES ('messages', 0);
            INSERT OR IGNORE INTO global_stats VALUES ('bans', 0);
            INSERT OR IGNORE INTO global_stats VALUES ('mutes', 0);
            INSERT OR IGNORE INTO global_stats VALUES ('warns', 0);
            INSERT OR IGNORE INTO global_stats VALUES ('spam', 0);
            INSERT OR IGNORE INTO global_stats VALUES ('antispam_granted', 0);
        """)
        await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ГРУППЫ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def register_group(chat_id: int, title: str, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO groups (chat_id, title, username) VALUES (?, ?, ?)",
            (chat_id, title, username)
        )
        await db.execute(
            "INSERT OR IGNORE INTO group_settings (chat_id) VALUES (?)",
            (chat_id,)
        )
        await db.commit()


async def get_all_groups():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM groups ORDER BY joined_at DESC") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_group_settings(chat_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,)) as cur:
            row = await cur.fetchone()
            if row:
                return dict(row)
            # Создаём настройки по умолчанию
            await db.execute("INSERT OR IGNORE INTO group_settings (chat_id) VALUES (?)", (chat_id,))
            await db.commit()
            async with db.execute("SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,)) as cur2:
                row2 = await cur2.fetchone()
                return dict(row2) if row2 else {}


async def update_group_setting(chat_id: int, key: str, value):
    safe_keys = {
        "welcome_enabled", "goodbye_enabled", "antiflood", "antilinks",
        "badwords", "antispam_enabled", "log_actions", "antibot",
        "max_warns", "warn_action", "welcome_text", "goodbye_text", "rules"
    }
    if key not in safe_keys:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"INSERT INTO group_settings (chat_id, {key}) VALUES (?, ?) "
            f"ON CONFLICT(chat_id) DO UPDATE SET {key} = ?",
            (chat_id, value, value)
        )
        await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ПОЛЬЗОВАТЕЛИ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def register_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name)
        )
        await db.commit()


async def get_all_users(limit=100, offset=0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users ORDER BY first_seen DESC LIMIT ? OFFSET ?", (limit, offset)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def count_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ВАРНЫ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def add_warn(chat_id: int, user_id: int, mod_id: int, reason: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO warnings (chat_id, user_id, mod_id, reason) VALUES (?, ?, ?, ?)",
            (chat_id, user_id, mod_id, reason)
        )
        await db.commit()
        async with db.execute(
            "SELECT COUNT(*) FROM warnings WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def get_warn_count(chat_id: int, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM warnings WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def get_warns_list(chat_id: int, user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM warnings WHERE chat_id = ? AND user_id = ? ORDER BY created_at DESC",
            (chat_id, user_id)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def remove_warn(chat_id: int, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM warnings WHERE chat_id = ? AND user_id = ? ORDER BY created_at DESC LIMIT 1",
            (chat_id, user_id)
        ) as cur:
            row = await cur.fetchone()
        if row:
            await db.execute("DELETE FROM warnings WHERE id = ?", (row[0],))
            await db.commit()
        async with db.execute(
            "SELECT COUNT(*) FROM warnings WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ) as cur:
            cnt = await cur.fetchone()
            return cnt[0] if cnt else 0


async def clear_warns(chat_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM warnings WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        )
        await db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ДЕЙСТВИЯ (лог)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def add_action(chat_id: int, mod_id: int, target_id: int, action_type: str, reason: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO actions (chat_id, mod_id, target_id, action_type, reason) VALUES (?, ?, ?, ?, ?)",
            (chat_id, mod_id, target_id, action_type, reason)
        )
        await db.commit()


async def get_user_actions(chat_id: int, user_id: int, limit=10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM actions WHERE chat_id = ? AND target_id = ? ORDER BY created_at DESC LIMIT ?",
            (chat_id, user_id, limit)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_recent_actions(limit=50) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM actions ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ЗАМЕТКИ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def save_note(chat_id: int, name: str, text: str, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO notes (chat_id, name, text, created_by) VALUES (?, ?, ?, ?)",
            (chat_id, name, text, user_id)
        )
        await db.commit()


async def get_note(chat_id: int, name: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM notes WHERE chat_id = ? AND name = ?", (chat_id, name)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_all_notes(chat_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM notes WHERE chat_id = ? ORDER BY name", (chat_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def delete_note(chat_id: int, name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM notes WHERE chat_id = ? AND name = ?", (chat_id, name)
        )
        await db.commit()
        return cur.rowcount > 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ФИЛЬТРЫ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def add_filter(chat_id: int, keyword: str, response: str, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO filters (chat_id, keyword, response, created_by) VALUES (?, ?, ?, ?)",
            (chat_id, keyword, response, user_id)
        )
        await db.commit()


async def get_filters(chat_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM filters WHERE chat_id = ?", (chat_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def delete_filter(chat_id: int, keyword: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM filters WHERE chat_id = ? AND keyword = ?", (chat_id, keyword)
        )
        await db.commit()
        return cur.rowcount > 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ПЛОХИЕ СЛОВА
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def add_bad_word(chat_id: int, word: str, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO bad_words (chat_id, word, created_by) VALUES (?, ?, ?)",
            (chat_id, word, user_id)
        )
        await db.commit()


async def remove_bad_word(chat_id: int, word: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM bad_words WHERE chat_id = ? AND word = ?", (chat_id, word))
        await db.commit()


async def get_bad_words(chat_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT word FROM bad_words WHERE chat_id = ?", (chat_id,)) as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  АНТИ-СПАМ ЗАЯВКИ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def create_antispam_request(user_id: int, username: str, full_name: str, reason: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO antispam_requests (user_id, username, full_name, reason) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, reason)
        )
        await db.commit()
        return cur.lastrowid


async def get_antispam_requests(status="pending") -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM antispam_requests WHERE status = ? ORDER BY created_at DESC LIMIT 50",
            (status,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_antispam_request(req_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM antispam_requests WHERE id = ?", (req_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_antispam_status(req_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE antispam_requests SET status = ?, resolved_at = datetime('now') WHERE id = ?",
            (status, req_id)
        )
        await db.commit()


async def get_all_antispam_requests(limit=100) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM antispam_requests ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  СОБЫТИЯ ЛОГ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def log_event(chat_id, chat_title, user_id: int, event_type: str, details: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO event_log (chat_id, chat_title, user_id, event_type, details) VALUES (?, ?, ?, ?, ?)",
            (str(chat_id), chat_title or "", user_id, event_type, details)
        )
        await db.commit()


async def get_recent_events(limit=100) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM event_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ГЛОБАЛЬНАЯ СТАТИСТИКА
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def inc_global_stat(key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO global_stats (key, value) VALUES (?, 1) ON CONFLICT(key) DO UPDATE SET value = value + 1",
            (key,)
        )
        await db.commit()


async def get_global_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        stats = {}
        async with db.execute("SELECT * FROM global_stats") as cur:
            rows = await cur.fetchall()
            for r in rows:
                stats[r["key"]] = r["value"]
        # Считаем группы и юзеров
        async with db.execute("SELECT COUNT(*) FROM groups") as cur:
            row = await cur.fetchone()
            stats["groups"] = row[0] if row else 0
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
            stats["users"] = row[0] if row else 0
        return stats


async def get_stats_history(days=7) -> list:
    """Статистика событий по дням"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT date(created_at) as day, event_type, COUNT(*) as cnt
               FROM event_log
               WHERE created_at >= datetime('now', ?)
               GROUP BY day, event_type
               ORDER BY day""",
            (f"-{days} days",)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_top_groups(limit=10) -> list:
    """Топ групп по активности"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT g.chat_id, g.title, COUNT(e.id) as events
               FROM groups g
               LEFT JOIN event_log e ON CAST(e.chat_id AS TEXT) = CAST(g.chat_id AS TEXT)
               GROUP BY g.chat_id
               ORDER BY events DESC
               LIMIT ?""",
            (limit,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
