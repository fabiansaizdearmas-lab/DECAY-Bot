import os

import asyncpg

pool = None
_db_ready = False


def database_url():
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    # Fallback for Railway variable references if DATABASE_URL is not exposed directly.
    pg_host = os.getenv("PGHOST")
    pg_port = os.getenv("PGPORT", "5432")
    pg_user = os.getenv("PGUSER") or os.getenv("POSTGRES_USER")
    pg_password = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD")
    pg_database = os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB")

    if all([pg_host, pg_port, pg_user, pg_password, pg_database]):
        return f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"

    raise RuntimeError(
        "DATABASE_URL is not set in the bot service. Add a Railway variable reference like DATABASE_URL=${{Postgres.DATABASE_URL}}."
    )


async def get_pool():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(database_url(), min_size=1, max_size=5)
    return pool


async def init_db():
    global _db_ready
    db_pool = await get_pool()

    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS mod_logs (
                id BIGSERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                moderator_id BIGINT NOT NULL,
                action TEXT NOT NULL,
                duration TEXT,
                reason TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS active_punishments (
                id BIGSERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                action TEXT NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_xp (
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                xp INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS xp_disabled_channels (
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                PRIMARY KEY (guild_id, channel_id)
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_mod_logs_guild_user ON mod_logs (guild_id, user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_tempbans_expires ON active_punishments (expires_at)")
    _db_ready = True


async def ensure_db():
    if not _db_ready:
        await init_db()
    return await get_pool()


async def db_health_check():
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        value = await conn.fetchval("SELECT 1")
    return value == 1


async def add_mod_log(guild_id, user_id, moderator_id, action, duration=None, reason=None):
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        return await conn.fetchval(
            """
            INSERT INTO mod_logs (guild_id, user_id, moderator_id, action, duration, reason)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            guild_id,
            user_id,
            moderator_id,
            action,
            duration,
            reason or "No reason provided",
        )


async def add_active_tempban(guild_id, user_id, expires_at):
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO active_punishments (guild_id, user_id, action, expires_at) VALUES ($1, $2, 'TEMP_BAN', $3)",
            guild_id,
            user_id,
            expires_at,
        )


async def remove_active_tempban(guild_id, user_id):
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM active_punishments WHERE guild_id = $1 AND user_id = $2 AND action = 'TEMP_BAN'",
            guild_id,
            user_id,
        )


async def get_temp_bans():
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, guild_id, user_id, expires_at FROM active_punishments WHERE action = 'TEMP_BAN'")
    return [(row["id"], row["guild_id"], row["user_id"], row["expires_at"]) for row in rows]


async def delete_tempban_by_id(punishment_id):
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM active_punishments WHERE id = $1", punishment_id)


async def get_user_modlogs(guild_id, user_id, limit=10):
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, action, duration, reason, moderator_id, created_at
            FROM mod_logs
            WHERE guild_id = $1 AND user_id = $2
            ORDER BY id DESC
            LIMIT $3
            """,
            guild_id,
            user_id,
            limit,
        )
    return [(row["id"], row["action"], row["duration"], row["reason"], row["moderator_id"], row["created_at"]) for row in rows]


async def get_case(guild_id, case_id):
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT user_id, moderator_id, action, duration, reason, created_at
            FROM mod_logs
            WHERE guild_id = $1 AND id = $2
            """,
            guild_id,
            case_id,
        )
    if not row:
        return None
    return row["user_id"], row["moderator_id"], row["action"], row["duration"], row["reason"], row["created_at"]


async def update_case_reason(guild_id, case_id, new_reason):
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE mod_logs SET reason = $1 WHERE guild_id = $2 AND id = $3",
            new_reason,
            guild_id,
            case_id,
        )
    return not result.endswith(" 0")


async def delete_case(guild_id, case_id):
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        result = await conn.execute("DELETE FROM mod_logs WHERE guild_id = $1 AND id = $2", guild_id, case_id)
    return not result.endswith(" 0")


async def get_xp_data(guild_id, user_id):
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT xp, level FROM user_xp WHERE guild_id = $1 AND user_id = $2", guild_id, user_id)
        if not row:
            await conn.execute("INSERT INTO user_xp (guild_id, user_id, xp, level) VALUES ($1, $2, 0, 0)", guild_id, user_id)
            return 0, 0
    return row["xp"], row["level"]


async def set_xp_data(guild_id, user_id, xp, level):
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO user_xp (guild_id, user_id, xp, level)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, user_id)
            DO UPDATE SET xp = EXCLUDED.xp, level = EXCLUDED.level
            """,
            guild_id,
            user_id,
            xp,
            level,
        )


async def get_xp_leaderboard(guild_id, limit=10):
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, xp, level FROM user_xp WHERE guild_id = $1 ORDER BY level DESC, xp DESC LIMIT $2",
            guild_id,
            limit,
        )
    return [(row["user_id"], row["xp"], row["level"]) for row in rows]


async def is_xp_channel_disabled(guild_id, channel_id):
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT 1 FROM xp_disabled_channels WHERE guild_id = $1 AND channel_id = $2", guild_id, channel_id)
    return row is not None


async def set_xp_channel_disabled(guild_id, channel_id, disabled):
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        if disabled:
            await conn.execute(
                "INSERT INTO xp_disabled_channels (guild_id, channel_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                guild_id,
                channel_id,
            )
        else:
            await conn.execute("DELETE FROM xp_disabled_channels WHERE guild_id = $1 AND channel_id = $2", guild_id, channel_id)


async def get_disabled_xp_channels(guild_id):
    db_pool = await ensure_db()
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT channel_id FROM xp_disabled_channels WHERE guild_id = $1 ORDER BY channel_id", guild_id)
    return [row["channel_id"] for row in rows]
