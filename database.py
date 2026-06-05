import sqlite3
from datetime import datetime, timezone

from config import DB_PATH


def now_utc():
    return datetime.now(timezone.utc)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mod_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            duration TEXT,
            reason TEXT,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_punishments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_xp (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS xp_disabled_channels (
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            PRIMARY KEY (guild_id, channel_id)
        )
    """)
    conn.commit()
    conn.close()


def add_mod_log(guild_id, user_id, moderator_id, action, duration=None, reason=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO mod_logs (guild_id, user_id, moderator_id, action, duration, reason, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (guild_id, user_id, moderator_id, action, duration, reason or "No reason provided", now_utc().isoformat()),
    )
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id


def add_active_tempban(guild_id, user_id, expires_at):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO active_punishments (guild_id, user_id, action, expires_at) VALUES (?, ?, 'TEMP_BAN', ?)",
        (guild_id, user_id, expires_at.isoformat()),
    )
    conn.commit()
    conn.close()


def remove_active_tempban(guild_id, user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM active_punishments WHERE guild_id = ? AND user_id = ? AND action = 'TEMP_BAN'",
        (guild_id, user_id),
    )
    conn.commit()
    conn.close()


def get_temp_bans():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, guild_id, user_id, expires_at FROM active_punishments WHERE action = 'TEMP_BAN'")
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_tempban_by_id(punishment_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_punishments WHERE id = ?", (punishment_id,))
    conn.commit()
    conn.close()


def get_user_modlogs(guild_id, user_id, limit=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, action, duration, reason, moderator_id, created_at FROM mod_logs WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT ?",
        (guild_id, user_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_case(guild_id, case_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, moderator_id, action, duration, reason, created_at FROM mod_logs WHERE guild_id = ? AND id = ?",
        (guild_id, case_id),
    )
    row = cursor.fetchone()
    conn.close()
    return row


def update_case_reason(guild_id, case_id, new_reason):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM mod_logs WHERE guild_id = ? AND id = ?", (guild_id, case_id))
    exists = cursor.fetchone() is not None
    if exists:
        cursor.execute("UPDATE mod_logs SET reason = ? WHERE guild_id = ? AND id = ?", (new_reason, guild_id, case_id))
    conn.commit()
    conn.close()
    return exists


def delete_case(guild_id, case_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM mod_logs WHERE guild_id = ? AND id = ?", (guild_id, case_id))
    exists = cursor.fetchone() is not None
    if exists:
        cursor.execute("DELETE FROM mod_logs WHERE guild_id = ? AND id = ?", (guild_id, case_id))
    conn.commit()
    conn.close()
    return exists


def get_xp_data(guild_id, user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT xp, level FROM user_xp WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO user_xp (guild_id, user_id, xp, level) VALUES (?, ?, 0, 0)", (guild_id, user_id))
        conn.commit()
        conn.close()
        return 0, 0
    conn.close()
    return row[0], row[1]


def set_xp_data(guild_id, user_id, xp, level):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO user_xp (guild_id, user_id, xp, level) VALUES (?, ?, ?, ?) ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = excluded.xp, level = excluded.level",
        (guild_id, user_id, xp, level),
    )
    conn.commit()
    conn.close()


def get_xp_leaderboard(guild_id, limit=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, xp, level FROM user_xp WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT ?",
        (guild_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def is_xp_channel_disabled(guild_id, channel_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM xp_disabled_channels WHERE guild_id = ? AND channel_id = ?", (guild_id, channel_id))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def set_xp_channel_disabled(guild_id, channel_id, disabled):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if disabled:
        cursor.execute("INSERT OR IGNORE INTO xp_disabled_channels (guild_id, channel_id) VALUES (?, ?)", (guild_id, channel_id))
    else:
        cursor.execute("DELETE FROM xp_disabled_channels WHERE guild_id = ? AND channel_id = ?", (guild_id, channel_id))
    conn.commit()
    conn.close()


def get_disabled_xp_channels(guild_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id FROM xp_disabled_channels WHERE guild_id = ? ORDER BY channel_id", (guild_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]
