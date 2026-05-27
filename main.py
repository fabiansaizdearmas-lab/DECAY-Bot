import discord
from discord.ext import commands, tasks
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

DB_PATH = "modlogs.db"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
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
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS active_punishments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def add_mod_log(guild_id, user_id, moderator_id, action, duration=None, reason=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO mod_logs (guild_id, user_id, moderator_id, action, duration, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            guild_id,
            user_id,
            moderator_id,
            action,
            duration,
            reason or "No reason provided",
            datetime.now(timezone.utc).isoformat(),
        ),
    )

    conn.commit()
    conn.close()


def add_active_punishment(guild_id, user_id, action, expires_at):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO active_punishments (guild_id, user_id, action, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (guild_id, user_id, action, expires_at.isoformat()),
    )

    conn.commit()
    conn.close()


def parse_duration(duration_text):
    if not duration_text:
        return None

    match = re.fullmatch(r"(\d+)(h|d)", duration_text.lower())
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    if unit == "h":
        return timedelta(hours=amount)

    if unit == "d":
        return timedelta(days=amount)

    return None


async def get_user_from_text(guild, target_text):
    target_id = target_text.replace("<@", "").replace("!", "").replace(">", "")

    if not target_id.isdigit():
        return None

    user_id = int(target_id)

    member = guild.get_member(user_id)
    if member:
        return member

    try:
        return await bot.fetch_user(user_id)
    except discord.NotFound:
        return None


@bot.event
async def on_ready():
    init_db()

    if not check_temp_bans.is_running():
        check_temp_bans.start()

    print(f"Bot connected as {bot.user}")


@tasks.loop(minutes=1)
async def check_temp_bans():
    now = datetime.now(timezone.utc)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, guild_id, user_id, expires_at FROM active_punishments WHERE action = 'TEMP_BAN'")
    rows = cursor.fetchall()

    for punishment_id, guild_id, user_id, expires_at_text in rows:
        expires_at = datetime.fromisoformat(expires_at_text)

        if expires_at <= now:
            guild = bot.get_guild(guild_id)

            if guild:
                try:
                    user = await bot.fetch_user(user_id)
                    await guild.unban(user, reason="Temporary ban expired")
                except discord.DiscordException:
                    pass

            cursor.execute("DELETE FROM active_punishments WHERE id = ?", (punishment_id,))

    conn.commit()
    conn.close()


@bot.command()
async def ping(ctx):
    await ctx.send("Pong 🏓")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def warn(ctx, target_text: str, *, reason=None):
    target = await get_user_from_text(ctx.guild, target_text)

    if not target:
        await ctx.send("User not found.")
        return

    add_mod_log(ctx.guild.id, target.id, ctx.author.id, "WARN", None, reason)

    await ctx.send(f"⚠️ User warned. Reason: {reason or 'No reason provided'}")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, target_text: str, duration_text: str, *, reason=None):
    target = await get_user_from_text(ctx.guild, target_text)

    if not target or not isinstance(target, discord.Member):
        await ctx.send("Member not found.")
        return

    duration = parse_duration(duration_text)

    if not duration:
        await ctx.send("Invalid duration. Use 1h or 1d format.")
        return

    until = datetime.now(timezone.utc) + duration

    await target.timeout(until, reason=reason)

    add_mod_log(ctx.guild.id, target.id, ctx.author.id, "TIMEOUT", duration_text, reason)

    await ctx.send(f"⏳ User timed out for {duration_text}.")


@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, target_text: str, *, reason=None):
    target = await get_user_from_text(ctx.guild, target_text)

    if not target or not isinstance(target, discord.Member):
        await ctx.send("Member not found.")
        return

    await target.kick(reason=reason)

    add_mod_log(ctx.guild.id, target.id, ctx.author.id, "KICK", None, reason)

    await ctx.send("👢 User kicked.")


@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, target_text: str, duration_text=None, *, reason=None):
    target = await get_user_from_text(ctx.guild, target_text)

    if not target:
        await ctx.send("User not found.")
        return

    duration = parse_duration(duration_text) if duration_text else None

    await ctx.guild.ban(target, reason=reason)

    if duration:
        expires_at = datetime.now(timezone.utc) + duration

        add_active_punishment(ctx.guild.id, target.id, "TEMP_BAN", expires_at)
        add_mod_log(ctx.guild.id, target.id, ctx.author.id, "TEMP_BAN", duration_text, reason)

        await ctx.send(f"🔨 User banned for {duration_text}.")
    else:
        add_mod_log(ctx.guild.id, target.id, ctx.author.id, "PERMA_BAN", None, reason)

        await ctx.send("🔨 User permanently banned.")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def modlog(ctx, target_text: str):
    target = await get_user_from_text(ctx.guild, target_text)

    if not target:
        await ctx.send("User not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT action, duration, reason, moderator_id, created_at
        FROM mod_logs
        WHERE guild_id = ? AND user_id = ?
        ORDER BY id DESC
        LIMIT 10
        """,
        (ctx.guild.id, target.id),
    )

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await ctx.send("No moderation history found.")
        return

    embed = discord.Embed(
        title=f"Modlog for {target}",
        color=discord.Color.orange()
    )

    for action, duration, reason, moderator_id, created_at in rows:
        embed.add_field(
            name=f"{action} | {created_at[:19]}",
            value=f"Moderator: <@{moderator_id}>\nDuration: {duration or 'N/A'}\nReason: {reason or 'No reason provided'}",
            inline=False
        )

    await ctx.send(embed=embed)


TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
