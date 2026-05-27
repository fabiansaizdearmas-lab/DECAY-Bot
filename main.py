import discord
from discord.ext import commands, tasks
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

DB_PATH = "modlogs_v2.db"
WELCOME_CHANNEL_ID = 1509285951816335411
RULES_CHANNEL_ID = 1509281427689177220
ANNOUNCEMENTS_CHANNEL_ID = 1509273242580422777
GUILD_TICKETS_CHANNEL_ID = 1509295180820381716
WELCOME_BANNER_URL = "https://raw.githubusercontent.com/fabiansaizdearmas-lab/DECAY-Bot/main/DECAYBanner.png"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


def now_utc():
    return datetime.now(timezone.utc)


def format_date(date_text):
    return datetime.fromisoformat(date_text).strftime("%Y-%m-%d %H:%M UTC")


def make_success_embed(title, description):
    return discord.Embed(title=title, description=description, color=discord.Color.green())


def make_error_embed(description):
    return discord.Embed(title="Command Error", description=description, color=discord.Color.red())


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


def parse_duration(duration_text):
    if not duration_text:
        return None
    match = re.fullmatch(r"(\d+)(h|d)", duration_text.lower())
    if not match:
        return None
    amount = int(match.group(1))
    if amount <= 0:
        return None
    return timedelta(hours=amount) if match.group(2) == "h" else timedelta(days=amount)


async def get_user_from_text(guild, target_text):
    if not target_text:
        return None
    target_id = target_text.strip().replace("<@", "").replace("!", "").replace(">", "")
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


def target_name(target):
    return target.mention if isinstance(target, discord.Member) else f"`{target}`"


def can_punish(ctx, target):
    if not isinstance(target, discord.Member):
        return True, None
    if target.id == ctx.author.id:
        return False, "❌ **Action blocked:** You cannot punish **yourself**."
    if target.id == ctx.guild.owner_id:
        return False, "❌ **Action blocked:** You cannot punish the **server owner**."
    if ctx.author.id != ctx.guild.owner_id and ctx.author.top_role <= target.top_role:
        return False, "❌ **Action blocked:** That member has an **equal or higher role** than you."
    if ctx.guild.me.top_role <= target.top_role:
        return False, "❌ **Action blocked:** My role is **not high enough** to punish that member."
    return True, None


@bot.event
async def on_ready():
    init_db()
    if not check_temp_bans.is_running():
        check_temp_bans.start()
    print(f"Bot connected as {bot.user}")


@bot.event
async def on_member_join(member):
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        return

    embed = discord.Embed(
        title=f"Welcome to {member.guild.name}, {member.name}!",
        description=(
            f"Hey {member.mention}, welcome to **DECAY**!\n\n"
            f"Please check <#{RULES_CHANNEL_ID}> before chatting.\n"
            f"Keep an eye on <#{ANNOUNCEMENTS_CHANNEL_ID}> for important updates.\n\n"
            f"If you want to apply to a **DECAY guild**, go to <#{GUILD_TICKETS_CHANNEL_ID}> "
            f"and create a ticket for the guild you want to join."
        ),
        color=discord.Color.red(),
    )
    embed.set_image(url=WELCOME_BANNER_URL)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Member #{member.guild.member_count}")
    await channel.send(content=member.mention, embed=embed)


@tasks.loop(minutes=1)
async def check_temp_bans():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, guild_id, user_id, expires_at FROM active_punishments WHERE action = 'TEMP_BAN'")
    rows = cursor.fetchall()

    for punishment_id, guild_id, user_id, expires_at_text in rows:
        if datetime.fromisoformat(expires_at_text) <= now_utc():
            guild = bot.get_guild(guild_id)
            if guild:
                try:
                    user = await bot.fetch_user(user_id)
                    await guild.unban(user, reason="Temporary ban expired")
                    add_mod_log(guild_id, user_id, bot.user.id, "AUTO_UNBAN", None, "Temporary ban expired")
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
async def warn(ctx, target_text: str = None, *, reason=None):
    if not target_text:
        await ctx.send(embed=make_error_embed("Missing **user**. Usage: `!warn @user reason`"))
        return
    target = await get_user_from_text(ctx.guild, target_text)
    if not target:
        await ctx.send(embed=make_error_embed("User not found. Use a **mention** or valid **user ID**."))
        return
    allowed, error = can_punish(ctx, target)
    if not allowed:
        await ctx.send(embed=make_error_embed(error))
        return
    log_id = add_mod_log(ctx.guild.id, target.id, ctx.author.id, "WARN", None, reason)
    await ctx.send(embed=make_success_embed("⚠️ User Warned", f"**User:** {target_name(target)}\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason or 'No reason provided'}\n**Case ID:** `#{log_id}`"))


@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, target_text: str = None, duration_text: str = None, *, reason=None):
    if not target_text or not duration_text:
        await ctx.send(embed=make_error_embed("Missing **arguments**. Usage: `!timeout @user 1h reason` or `!timeout @user 2d reason`"))
        return
    target = await get_user_from_text(ctx.guild, target_text)
    if not target or not isinstance(target, discord.Member):
        await ctx.send(embed=make_error_embed("Member not found. **Timeouts only work** on users currently in the server."))
        return
    duration = parse_duration(duration_text)
    if not duration:
        await ctx.send(embed=make_error_embed("Invalid **duration**. Use `1h`, `6h`, `1d`, or `7d`."))
        return
    allowed, error = can_punish(ctx, target)
    if not allowed:
        await ctx.send(embed=make_error_embed(error))
        return
    await target.timeout(now_utc() + duration, reason=reason or f"Timed out by {ctx.author}")
    log_id = add_mod_log(ctx.guild.id, target.id, ctx.author.id, "TIMEOUT", duration_text, reason)
    await ctx.send(embed=make_success_embed("⏳ User Timed Out", f"**User:** {target.mention}\n**Duration:** `{duration_text}`\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason or 'No reason provided'}\n**Case ID:** `#{log_id}`"))


@bot.command()
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, target_text: str = None, *, reason=None):
    if not target_text:
        await ctx.send(embed=make_error_embed("Missing **user**. Usage: `!untimeout @user reason`"))
        return
    target = await get_user_from_text(ctx.guild, target_text)
    if not target or not isinstance(target, discord.Member):
        await ctx.send(embed=make_error_embed("Member not found. **Untimeout only works** on users currently in the server."))
        return
    allowed, error = can_punish(ctx, target)
    if not allowed:
        await ctx.send(embed=make_error_embed(error))
        return
    await target.timeout(None, reason=reason or f"Timeout removed by {ctx.author}")
    log_id = add_mod_log(ctx.guild.id, target.id, ctx.author.id, "UNTIMEOUT", None, reason)
    await ctx.send(embed=make_success_embed("✅ Timeout Removed", f"**User:** {target.mention}\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason or 'No reason provided'}\n**Case ID:** `#{log_id}`"))


@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, target_text: str = None, *, reason=None):
    if not target_text:
        await ctx.send(embed=make_error_embed("Missing **user**. Usage: `!kick @user reason`"))
        return
    target = await get_user_from_text(ctx.guild, target_text)
    if not target or not isinstance(target, discord.Member):
        await ctx.send(embed=make_error_embed("Member not found. **Kicks only work** on users currently in the server."))
        return
    allowed, error = can_punish(ctx, target)
    if not allowed:
        await ctx.send(embed=make_error_embed(error))
        return
    await target.kick(reason=reason or f"Kicked by {ctx.author}")
    log_id = add_mod_log(ctx.guild.id, target.id, ctx.author.id, "KICK", None, reason)
    await ctx.send(embed=make_success_embed("👢 User Kicked", f"**User:** `{target}`\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason or 'No reason provided'}\n**Case ID:** `#{log_id}`"))


@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, target_text: str = None, duration_text: str = None, *, reason=None):
    if not target_text:
        await ctx.send(embed=make_error_embed("Missing **user**. Usage: `!ban @user reason` or `!ban @user 7d reason`"))
        return
    target = await get_user_from_text(ctx.guild, target_text)
    if not target:
        await ctx.send(embed=make_error_embed("User not found. Use a **mention** or valid **user ID**."))
        return

    duration = parse_duration(duration_text) if duration_text else None
    if duration_text and not duration:
        reason = f"{duration_text} {reason or ''}".strip()
        duration_text = None

    allowed, error = can_punish(ctx, target)
    if not allowed:
        await ctx.send(embed=make_error_embed(error))
        return

    await ctx.guild.ban(target, reason=reason or f"Banned by {ctx.author}")
    if duration:
        add_active_tempban(ctx.guild.id, target.id, now_utc() + duration)
        log_id = add_mod_log(ctx.guild.id, target.id, ctx.author.id, "TEMP_BAN", duration_text, reason)
        await ctx.send(embed=make_success_embed("🔨 User Temporarily Banned", f"**User:** `{target}`\n**Duration:** `{duration_text}`\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason or 'No reason provided'}\n**Case ID:** `#{log_id}`"))
    else:
        log_id = add_mod_log(ctx.guild.id, target.id, ctx.author.id, "PERMA_BAN", None, reason)
        await ctx.send(embed=make_success_embed("🔨 User Permanently Banned", f"**User:** `{target}`\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason or 'No reason provided'}\n**Case ID:** `#{log_id}`"))


@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, target_text: str = None, *, reason=None):
    if not target_text:
        await ctx.send(embed=make_error_embed("Missing **user ID**. Usage: `!unban userID reason`"))
        return
    target = await get_user_from_text(ctx.guild, target_text)
    if not target:
        await ctx.send(embed=make_error_embed("User not found. Use a valid **user ID**."))
        return
    try:
        await ctx.guild.unban(target, reason=reason or f"Unbanned by {ctx.author}")
    except discord.NotFound:
        await ctx.send(embed=make_error_embed("That user is **not banned** in this server."))
        return
    remove_active_tempban(ctx.guild.id, target.id)
    log_id = add_mod_log(ctx.guild.id, target.id, ctx.author.id, "UNBAN", None, reason)
    await ctx.send(embed=make_success_embed("✅ User Unbanned", f"**User:** `{target}`\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason or 'No reason provided'}\n**Case ID:** `#{log_id}`"))


@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = None):
    if amount is None:
        await ctx.send(embed=make_error_embed("Missing **amount**. Usage: `!clear 10`"))
        return
    if amount < 1 or amount > 100:
        await ctx.send(embed=make_error_embed("Invalid **amount**. Choose a number between **1 and 100**."))
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    confirmation = await ctx.send(embed=make_success_embed("🧹 Messages Cleared", f"Deleted **{len(deleted) - 1}** messages."))
    try:
        await confirmation.delete(delay=5)
    except discord.DiscordException:
        pass


@bot.command()
@commands.has_permissions(moderate_members=True)
async def modlog(ctx, target_text: str = None):
    if not target_text:
        await ctx.send(embed=make_error_embed("Missing **user**. Usage: `!modlog @user`"))
        return
    target = await get_user_from_text(ctx.guild, target_text)
    if not target:
        await ctx.send(embed=make_error_embed("User not found. Use a **mention** or valid **user ID**."))
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, action, duration, reason, moderator_id, created_at FROM mod_logs WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT 10",
        (ctx.guild.id, target.id),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await ctx.send(embed=make_error_embed("No **moderation history** found for this user."))
        return

    embed = discord.Embed(title=f"📜 Modlog for {target}", color=discord.Color.orange())
    for log_id, action, duration, reason, moderator_id, created_at in rows:
        embed.add_field(
            name=f"Case #{log_id} — {action}",
            value=f"**Date:** {format_date(created_at)}\n**Moderator:** <@{moderator_id}>\n**Duration:** {duration or 'N/A'}\n**Reason:** {reason}",
            inline=False,
        )
    await ctx.send(embed=embed)


@bot.command(name="case")
@commands.has_permissions(moderate_members=True)
async def view_case(ctx, log_id: int = None):
    if log_id is None:
        await ctx.send(embed=make_error_embed("Missing **case ID**. Usage: `!case 12`"))
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, moderator_id, action, duration, reason, created_at FROM mod_logs WHERE guild_id = ? AND id = ?",
        (ctx.guild.id, log_id),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        await ctx.send(embed=make_error_embed("Case not found. Check the **case ID** and try again."))
        return
    user_id, moderator_id, action, duration, reason, created_at = row
    embed = discord.Embed(title=f"📁 Case #{log_id}", color=discord.Color.blue())
    embed.add_field(name="User", value=f"<@{user_id}> (`{user_id}`)", inline=False)
    embed.add_field(name="Action", value=f"**{action}**", inline=True)
    embed.add_field(name="Duration", value=duration or "N/A", inline=True)
    embed.add_field(name="Moderator", value=f"<@{moderator_id}>", inline=False)
    embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
    embed.set_footer(text=format_date(created_at))
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(moderate_members=True)
async def reason(ctx, log_id: int = None, *, new_reason=None):
    if log_id is None or not new_reason:
        await ctx.send(embed=make_error_embed("Missing **arguments**. Usage: `!reason caseID new reason`"))
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM mod_logs WHERE guild_id = ? AND id = ?", (ctx.guild.id, log_id))
    if not cursor.fetchone():
        conn.close()
        await ctx.send(embed=make_error_embed("Case not found. Check the **case ID** and try again."))
        return
    cursor.execute("UPDATE mod_logs SET reason = ? WHERE guild_id = ? AND id = ?", (new_reason, ctx.guild.id, log_id))
    conn.commit()
    conn.close()
    await ctx.send(embed=make_success_embed("✏️ Case Reason Updated", f"**Case ID:** `#{log_id}`\n**New reason:** {new_reason}"))


@bot.command()
@commands.has_permissions(moderate_members=True)
async def removelog(ctx, log_id: int = None):
    if log_id is None:
        await ctx.send(embed=make_error_embed("Missing **case ID**. Usage: `!removelog 12`"))
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM mod_logs WHERE guild_id = ? AND id = ?", (ctx.guild.id, log_id))
    if not cursor.fetchone():
        conn.close()
        await ctx.send(embed=make_error_embed("Case not found. Check the **case ID** and try again."))
        return
    cursor.execute("DELETE FROM mod_logs WHERE guild_id = ? AND id = ?", (ctx.guild.id, log_id))
    conn.commit()
    conn.close()
    await ctx.send(embed=make_success_embed("🗑️ Case Removed", f"**Case ID:** `#{log_id}` has been deleted from the modlog."))


@warn.error
@timeout.error
@untimeout.error
@kick.error
@ban.error
@unban.error
@clear.error
@modlog.error
@view_case.error
@reason.error
@removelog.error
async def command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=make_error_embed("You do not have the **required permissions** to use this command."))
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(embed=make_error_embed("I do not have the **required permissions** to do that."))
    elif isinstance(error, commands.BadArgument):
        await ctx.send(embed=make_error_embed("Invalid **argument type**. Check the command format and try again."))
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=make_error_embed("Missing **arguments**. Check the command usage and try again."))
    else:
        await ctx.send(embed=make_error_embed("An **unexpected error** occurred while running this command."))
        raise error


TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
