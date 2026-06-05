import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import re
import sqlite3
import random
from datetime import datetime, timedelta, timezone

DB_PATH = "modlogs_v2.db"
DECAY_RED = 0xB30000

# Staff / Guild role IDs
OBLIVION_ROLE_ID = 1509264947006279700
ENTROPY_ROLE_ID = 1509335654537105428
RUIN_ROLE_ID = 1509333457703141426
FRACTURE_ROLE_ID = 1509333436551401673
WITHER_ROLE_ID = 1509335734866411560
GUILD_CAPTAIN_ROLE_ID = 1509302357631041716

# XP role IDs
ASH_ROLE_ID = 1512584016740618291
EMBER_ROLE_ID = 1512584027708854423
SCORCH_ROLE_ID = 1512584031685050389
RUPTURE_ROLE_ID = 1512584036336533686
COLLAPSE_ROLE_ID = 1512584037695488110
CATACLYSM_ROLE_ID = 1512584039041728732

XP_ROLE_MILESTONES = {
    5: ASH_ROLE_ID,
    10: EMBER_ROLE_ID,
    15: SCORCH_ROLE_ID,
    20: RUPTURE_ROLE_ID,
    25: COLLAPSE_ROLE_ID,
    30: CATACLYSM_ROLE_ID,
}
XP_ROLE_NAMES = {
    5: "Ash",
    10: "Ember",
    15: "Scorch",
    20: "Rupture",
    25: "Collapse",
    30: "Cataclysm",
}

# Channel IDs
WELCOME_CHANNEL_ID = 1509285951816335411
GENERAL_CHANNEL_ID = 1509272809791029349
BOT_COMMANDS_CHANNEL_ID = 1509272900732059809
RULES_CHANNEL_ID = 1509281427689177220
ANNOUNCEMENTS_CHANNEL_ID = 1509273242580422777
GUILD_APPLY_CHANNEL_ID = 1509295180820381716
GUILD_TICKET_CATEGORY_ID = 1509302737399975966
SUGGESTIONS_CHANNEL_ID = 1509273303020343296
LOG_CHANNEL_ID = 1509323362344898652

WELCOME_BANNER_URL = "https://raw.githubusercontent.com/fabiansaizdearmas-lab/DECAY-Bot/main/DECAYBanner.png"
DECAY_LOGO_URL = "https://raw.githubusercontent.com/fabiansaizdearmas-lab/DECAY-Bot/main/DECAYLogo.png"

STAFF_ROLE_IDS = [OBLIVION_ROLE_ID, ENTROPY_ROLE_ID, RUIN_ROLE_ID, FRACTURE_ROLE_ID, WITHER_ROLE_ID]
TICKET_STAFF_ROLE_IDS = STAFF_ROLE_IDS + [GUILD_CAPTAIN_ROLE_ID]
FULL_STAFF_ROLE_IDS = [OBLIVION_ROLE_ID, ENTROPY_ROLE_ID, RUIN_ROLE_ID, FRACTURE_ROLE_ID]
BASIC_STAFF_ROLE_IDS = STAFF_ROLE_IDS

ABUSE_LIMIT = 3
ABUSE_WINDOW = timedelta(hours=6)
XP_GAIN = 10
XP_COOLDOWN = timedelta(seconds=60)
MAX_LEVEL = 30

mod_action_history = {}
last_xp_times = {}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.slash_synced = False

fun_group = app_commands.Group(name="fun", description="Fun commands")
xp_group = app_commands.Group(name="xp", description="XP system commands")
setup_group = app_commands.Group(name="setup", description="Setup embeds")
ticket_group = app_commands.Group(name="ticket", description="Ticket commands")
mod_group = app_commands.Group(name="mod", description="Moderation commands")

PHRASES = {
    "timeout": [
        "{user} got sent to the yapper containment unit for {duration}.",
        "{user} lost chat privileges for {duration}. tragic timeline.",
        "{user} got muted. peace has been restored for {duration}.",
        "{user} got put on airplane mode for {duration}.",
        "{user} has been temporarily silenced. chat can breathe for {duration}.",
    ],
    "untimeout": [
        "{user} got unmuted. character development check starts now.",
        "{user} escaped the yapper containment unit. do not sell the comeback.",
        "{user} can talk again. this may or may not be a mistake.",
        "{user} has been released back into chat. behave this time.",
        "{user} got their mic plugged back in. let's see how long it lasts.",
    ],
    "kick": [
        "{user} got kicked. bro failed the vibe check.",
        "{user} got launched out of DECAY. no fall damage, probably.",
        "{user} has left the server by force. speedrun complete.",
        "{user} got removed from the lobby. queue somewhere else.",
        "{user} got booted. skill issue detected.",
    ],
    "tempban": [
        "{user} got temporarily deleted for {duration}. respawn timer started.",
        "{user} got sent to exile for {duration}. comeback season pending.",
        "{user} got benched for {duration}. think about the gameplay.",
        "{user} got removed from the map for {duration}. patch notes needed.",
        "{user} got banished for {duration}. see you after the cooldown.",
    ],
    "permban": [
        "{user} got erased from DECAY. canon event.",
        "{user} got hard deleted. no autosave found.",
        "{user} got packed up permanently. gg go next.",
        "{user} is now server lore. not the good kind.",
        "{user} got sent to the shadow realm with no return ticket.",
    ],
    "unban": [
        "{user} respawned. don't waste the extra life.",
        "{user} got unbanned. redemption arc unlocked.",
        "{user} is back. season 2 better not flop.",
        "{user} got restored from the recycle bin.",
        "{user} returned from exile. behave or the sequel gets cancelled.",
    ],
    "clear": [
        "deleted {amount} messages. chat got a factory reset.",
        "{amount} messages evaporated. never happened.",
        "cleared {amount} messages. the allegations are gone.",
        "{amount} messages got wiped. clean slate moment.",
        "deleted {amount} messages. chat looks less cursed now.",
    ],
    "ticketclose": [
        "ticket closed. case archived, drama contained.",
        "ticket sealed. the council has spoken.",
        "ticket closed. another file thrown into the DECAY archives.",
        "application locked. judgment phase completed.",
        "ticket closed. no more yapping in this chamber.",
    ],
    "ticketdelete": [
        "ticket deleted. no screenshots, no evidence.",
        "ticket erased. clean work.",
        "ticket vaporized. it was never here.",
        "ticket deleted. DECAY archives have been cleansed.",
        "ticket removed from the timeline.",
    ],
    "cooldown": [
        "nahh you're doing too much. wait {time} before continuing the admin arc.",
        "bro is farming mod actions. wait {time} before doing allat again.",
        "chill, final boss. wait {time} before using more {action}s.",
        "mod rampage detected. wait {time} before continuing the chaos.",
        "you hit the safety limit. wait {time} before the next moderation episode.",
    ],
    "noperms": [
        "nice try, but you don't have the clearance for that.",
        "access denied. DECAY does not recognize your authority.",
        "bro tried to use forbidden magic.",
        "you are not high enough in the food chain for this.",
        "permission denied. the council is not impressed.",
    ],
    "missing": [
        "bro forgot half the command.",
        "command incomplete. the bot cannot read minds yet.",
        "missing arguments. try again, but with the actual info this time.",
        "you dropped some arguments on the way here.",
        "incomplete spell. add the missing pieces.",
    ],
    "mention": [
        "leave me alone dude",
        "bro summoned me for what",
        "what do you want now",
        "not now, i'm busy doing absolutely nothing",
        "bro thinks i'm customer support",
        "DECAY is watching, unfortunately",
        "say please next time",
        "you called?",
        "ping me again and i'll start charging rent",
        "i was mentally offline, try again",
    ],
    "8ball": [
        "yes, but don't get cooked.",
        "nah, terrible idea.",
        "DECAY approves this nonsense.",
        "ask again when your aura recovers.",
        "maybe, but the odds are looking homeless.",
        "absolutely. trust the process.",
        "no. even the void said pass.",
        "do it. worst case, it becomes server lore.",
        "signs point to yes, somehow.",
        "not now. the timeline is unstable.",
    ],
    "rate": [
        "{target} has {number}% DECAY aura. dangerous levels detected.",
        "{target} is {number}% cooked. recovery may be possible.",
        "{target} has {number}% leaderboard potential. maybe built different.",
        "{target} is {number}% useful and {rest}% side quest.",
        "{target} has {number}% luck. RNG is either blessing or bullying them.",
        "{target} has {number}% braincells active. server performance may vary.",
        "{target} is {number}% Guild material. the council is watching.",
        "{target} has {number}% chaos energy. keep an eye on this creature.",
        "{target} is {number}% carried. no further questions.",
        "{target} has {number}% villain arc progression.",
    ],
    "levelup": [
        "{user} hit level {level}. bro is farming chat XP like it's a full-time job.",
        "{user} reached level {level}. activity detected, grass untouched.",
        "{user} is now level {level}. chat XP economy is in shambles.",
        "{user} leveled up to {level}. yapping finally paid rent.",
        "{user} reached level {level}. DECAY has certified the grind.",
    ],
}


def pick(key, **kwargs):
    return random.choice(PHRASES[key]).format(**kwargs)


def now_utc():
    return datetime.now(timezone.utc)


def make_embed(title, description, color=DECAY_RED):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="DECAY Bot")
    return embed


def create_commands_embed():
    embed = make_embed(
        "DECAY Bot Commands",
        "Quick command list. Slash commands are organized by `/fun`, `/xp`, `/setup`, `/ticket`, and `/mod`."
    )
    embed.set_thumbnail(url=DECAY_LOGO_URL)
    embed.add_field(
        name="General / Fun",
        value="`!ping`\n`!commands` / `/commands`\n`!8ball question` / `/fun 8ball`\n`!rate target` / `/fun rate`",
        inline=False,
    )
    embed.add_field(
        name="XP",
        value="`!level` / `/xp level`\n`!level @user` / `/xp level user`\n`!leaderboard` / `/xp leaderboard`\n`!xpchanneloff` / `/xp channel_off`\n`!xpchannelon` / `/xp channel_on`\n`!xpexcluded` / `/xp excluded`",
        inline=False,
    )
    embed.add_field(
        name="Setup",
        value="`!guildapplysetup` / `/setup apply`\n`!rulesembed` / `/setup rules`\n`!suggestionsembed` / `/setup suggestions`\n`!contributionsembed` / `/setup contributions`",
        inline=False,
    )
    embed.add_field(
        name="Tickets",
        value="`!ticketclose` / `/ticket close`\n`!ticketdelete` / `/ticket delete`",
        inline=False,
    )
    embed.add_field(
        name="Moderation",
        value="`!timeout @user 1h reason` / `/mod timeout`\n`!untimeout @user reason` / `/mod untimeout`\n`!clear amount` / `/mod clear`\n`!kick @user reason` / `/mod kick`\n`!ban @user reason` / `/mod ban`\n`!ban @user 7d reason` / `/mod ban`\n`!unban userID reason` / `/mod unban`",
        inline=False,
    )
    embed.add_field(
        name="Modlogs",
        value="`!modlog @user` / `/mod modlog`\n`!case caseID` / `/mod case`\n`!reason caseID new reason` / `/mod reason`\n`!removelog caseID` / `/mod removelog`",
        inline=False,
    )
    return embed


def has_any_role(member, role_ids):
    return isinstance(member, discord.Member) and any(role.id in role_ids for role in member.roles)


def interaction_has_any_role(interaction, role_ids):
    return isinstance(interaction.user, discord.Member) and any(role.id in role_ids for role in interaction.user.roles)


def is_oblivion(member):
    return has_any_role(member, [OBLIVION_ROLE_ID])


def require_roles(role_ids):
    async def predicate(ctx):
        return has_any_role(ctx.author, role_ids)
    return commands.check(predicate)


def setup_only():
    return require_roles([OBLIVION_ROLE_ID])


def full_staff_only():
    return require_roles(FULL_STAFF_ROLE_IDS)


def basic_staff_only():
    return require_roles(BASIC_STAFF_ROLE_IDS)


def ticket_staff_only():
    return require_roles(TICKET_STAFF_ROLE_IDS)


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
    cursor.execute("INSERT INTO active_punishments (guild_id, user_id, action, expires_at) VALUES (?, ?, 'TEMP_BAN', ?)", (guild_id, user_id, expires_at.isoformat()))
    conn.commit()
    conn.close()


def remove_active_tempban(guild_id, user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM active_punishments WHERE guild_id = ? AND user_id = ? AND action = 'TEMP_BAN'", (guild_id, user_id))
    conn.commit()
    conn.close()


def xp_needed_for_level(level):
    return 50 + ((level - 1) * 25)


def total_xp_for_level(level):
    return sum(xp_needed_for_level(current_level) for current_level in range(1, level + 1))


def level_from_xp(xp):
    level = 0
    while level < MAX_LEVEL and xp >= total_xp_for_level(level + 1):
        level += 1
    return level


def xp_progress(xp, level):
    if level >= MAX_LEVEL:
        return 0, 0
    current_floor = total_xp_for_level(level)
    next_needed = xp_needed_for_level(level + 1)
    return max(0, xp - current_floor), next_needed


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


async def update_xp_role(member, level):
    role_to_add = None
    for milestone in sorted(XP_ROLE_MILESTONES):
        if level >= milestone:
            role_to_add = member.guild.get_role(XP_ROLE_MILESTONES[milestone])
    xp_role_ids = set(XP_ROLE_MILESTONES.values())
    roles_to_remove = [role for role in member.roles if role.id in xp_role_ids and role != role_to_add]
    try:
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason="XP role update")
        if role_to_add and role_to_add not in member.roles:
            await member.add_roles(role_to_add, reason="XP role update")
    except discord.DiscordException:
        pass


def xp_rank_name(level):
    rank = None
    for milestone in sorted(XP_ROLE_NAMES):
        if level >= milestone:
            rank = XP_ROLE_NAMES[milestone]
    return rank


async def send_log(guild, title, description, color=DECAY_RED):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if not channel:
        return
    embed = make_embed(title, description, color)
    embed.timestamp = now_utc()
    try:
        await channel.send(embed=embed)
    except discord.DiscordException:
        pass


async def handle_xp(message):
    if not message.guild or not isinstance(message.author, discord.Member):
        return
    if message.content.startswith("!"):
        return
    if is_xp_channel_disabled(message.guild.id, message.channel.id):
        return
    key = (message.guild.id, message.author.id)
    last_time = last_xp_times.get(key)
    if last_time and now_utc() - last_time < XP_COOLDOWN:
        return
    xp, old_level = get_xp_data(message.guild.id, message.author.id)
    if old_level >= MAX_LEVEL:
        return
    new_xp = xp + XP_GAIN
    new_level = min(level_from_xp(new_xp), MAX_LEVEL)
    set_xp_data(message.guild.id, message.author.id, new_xp, new_level)
    last_xp_times[key] = now_utc()
    if new_level > old_level:
        await update_xp_role(message.author, new_level)
        bot_channel = message.guild.get_channel(BOT_COMMANDS_CHANNEL_ID)
        if bot_channel:
            rank = xp_rank_name(new_level)
            rank_text = f" and became **{rank}**" if rank else ""
            await bot_channel.send(pick("levelup", user=message.author.mention, level=new_level) + rank_text)


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


def format_remaining(delta):
    seconds = max(1, int(delta.total_seconds()))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes or 1}m"


def target_name(target):
    return target.mention if isinstance(target, discord.Member) else f"`{target}`"


def safe_channel_name(text):
    text = re.sub(r"[^a-z0-9-]", "-", text.lower())
    return re.sub(r"-+", "-", text).strip("-")[:40] or "user"


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


def can_punish(ctx, target):
    if not isinstance(target, discord.Member):
        return True, None
    if target.id == ctx.author.id:
        return False, "you tried to moderate yourself. bro is fighting ghosts."
    if target.id == ctx.guild.owner_id:
        return False, "nice try, but the server owner has plot armor."
    if ctx.author.id != ctx.guild.owner_id and ctx.author.top_role <= target.top_role:
        return False, "target has equal or higher role. the food chain said no."
    if ctx.guild.me.top_role <= target.top_role:
        return False, "my role is too low to touch that user. give me more aura first."
    return True, None


def can_punish_slash(interaction, target):
    if not isinstance(target, discord.Member):
        return True, None
    actor = interaction.user
    if target.id == actor.id:
        return False, "you tried to moderate yourself. bro is fighting ghosts."
    if target.id == interaction.guild.owner_id:
        return False, "nice try, but the server owner has plot armor."
    if actor.id != interaction.guild.owner_id and actor.top_role <= target.top_role:
        return False, "target has equal or higher role. the food chain said no."
    if interaction.guild.me.top_role <= target.top_role:
        return False, "my role is too low to touch that user. give me more aura first."
    return True, None


async def check_abuse_limit(ctx, action):
    if is_oblivion(ctx.author):
        return True
    key = (ctx.guild.id, ctx.author.id, action)
    cutoff = now_utc() - ABUSE_WINDOW
    timestamps = [t for t in mod_action_history.get(key, []) if t > cutoff]
    if len(timestamps) >= ABUSE_LIMIT:
        remaining = ABUSE_WINDOW - (now_utc() - min(timestamps))
        await ctx.send(pick("cooldown", time=format_remaining(remaining), action=action))
        await send_log(ctx.guild, "Safety Limit Triggered", f"**Staff:** {ctx.author.mention}\n**Action:** `{action}`\n**Limit:** `{ABUSE_LIMIT}` per 6h\n**Remaining:** `{format_remaining(remaining)}`", discord.Color.orange())
        return False
    timestamps.append(now_utc())
    mod_action_history[key] = timestamps
    return True


async def check_abuse_limit_slash(interaction, action):
    if is_oblivion(interaction.user):
        return True
    key = (interaction.guild.id, interaction.user.id, action)
    cutoff = now_utc() - ABUSE_WINDOW
    timestamps = [t for t in mod_action_history.get(key, []) if t > cutoff]
    if len(timestamps) >= ABUSE_LIMIT:
        remaining = ABUSE_WINDOW - (now_utc() - min(timestamps))
        await interaction.response.send_message(pick("cooldown", time=format_remaining(remaining), action=action), ephemeral=True)
        await send_log(interaction.guild, "Safety Limit Triggered", f"**Staff:** {interaction.user.mention}\n**Action:** `{action}`\n**Limit:** `{ABUSE_LIMIT}` per 6h\n**Remaining:** `{format_remaining(remaining)}`", discord.Color.orange())
        return False
    timestamps.append(now_utc())
    mod_action_history[key] = timestamps
    return True


async def log_mod_action(guild, title, target, moderator, reason, log_id, duration=None):
    duration_line = f"**Duration:** `{duration}`\n" if duration else ""
    await send_log(guild, title, f"**User:** {target_name(target)} (`{target.id}`)\n{duration_line}**Moderator:** {moderator.mention}\n**Reason:** {reason or 'No reason provided'}\n**Case ID:** `#{log_id}`")


async def level_text(guild, target):
    xp, level_value = get_xp_data(guild.id, target.id)
    progress, needed = xp_progress(xp, level_value)
    rank = xp_rank_name(level_value)
    rank_text = f" | rank: {rank}" if rank else ""
    if level_value >= MAX_LEVEL:
        return f"{target.mention} is level {level_value}{rank_text}. max level reached, bro finished the current season."
    return f"{target.mention} is level {level_value}{rank_text}. XP: {progress}/{needed} until level {level_value + 1}."


def leaderboard_text(guild):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, xp, level FROM user_xp WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT 10", (guild.id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return "leaderboard is empty. chat XP economy has not started yet."
    lines = [f"{index}. <@{user_id}> — Level {level_value} | {xp} XP" for index, (user_id, xp, level_value) in enumerate(rows, start=1)]
    return "**DECAY XP Leaderboard**\n" + "\n".join(lines)


def create_apply_embed():
    embed = make_embed(
        "Apply for DECAY",
        "Do you want to join us?\n\n"
        "**DECAY** is our main Guild, built for top-level players who want to compete, improve, and represent one of the strongest communities in the game.\n\n"
        "We are looking for dedicated members with strong units, deep game knowledge, competitive mentality, and true loyalty to **DECAY**.\n\n"
        "**REQUIREMENTS:**\n"
        "- **Meta units** — Own strong units from the current **top meta**\n"
        "- **Game knowledge** — Have an **advanced understanding** of the game\n"
        "- **Competitive mindset** — Be competitive and motivated to improve\n"
        "- **Leaderboard runs** — Understand, or be willing to learn, **leaderboard strategies and team coordination**\n"
        "- **Guild investment** — Be willing to contribute a significant amount of resources into **Guild features** such as **Leveling Chambers**, **Mining Rooms**, and future Guild upgrades\n"
        "- **Loyalty** — Stay loyal and committed to **DECAY**\n"
        "- **Teamwork** — Be respectful, mature, and able to work with other Guild members\n\n"
        "**EXTRA INFORMATION:**\n"
        "Applying does **not** guarantee acceptance.\n\n"
        "Staff may ask for extra information about your units, progress, activity, experience, and availability.\n\n"
        "If you believe you are ready to represent **DECAY**, press the button below and start your application."
    )
    embed.set_thumbnail(url=DECAY_LOGO_URL)
    embed.set_footer(text="DECAY Guild Applications")
    return embed


def create_rules_embed():
    embed = make_embed(
        "Server Rules",
        "Welcome to **DECAY**.\n\n"
        "To keep the server organized, competitive, and respectful, every member must follow these rules.\n\n"
        "**RULES:**\n"
        "- **Respect everyone** — No harassment, hate speech, toxicity, threats, or personal attacks.\n"
        "- **No spam** — Avoid flooding chats, repeated messages, excessive mentions, or useless pings.\n"
        "- **Use channels properly** — Keep conversations in the correct channels.\n"
        "- **No drama** — Do not bring personal conflicts, Guild drama, or unnecessary arguments into the server.\n"
        "- **No NSFW or inappropriate content** — Keep all content safe and appropriate.\n"
        "- **No scams or suspicious links** — Do not post phishing links, fake giveaways, or unsafe websites.\n"
        "- **Follow owner decisions** — Owners have the final say in moderation and server management.\n"
        "- **Represent DECAY properly** — If you are part of the Guild, act with loyalty, maturity, and respect.\n\n"
        "**PUNISHMENTS:**\n"
        "Breaking the rules may result in timeouts, kicks, or bans depending on the severity.\n\n"
        "By staying in this server, you agree to follow these rules."
    )
    embed.set_thumbnail(url=DECAY_LOGO_URL)
    embed.set_footer(text="DECAY Server Rules")
    return embed


def create_suggestions_embed():
    embed = make_embed(
        "Suggestions",
        "Help us improve **DECAY**.\n\n"
        "This channel is for suggestions related to the server, Guild systems, events, channels, roles, bots, or community ideas.\n\n"
        "**HOW TO SUGGEST:**\n"
        "- Explain your idea clearly.\n"
        "- Keep it realistic and useful.\n"
        "- Give details if the suggestion affects the Guild or server structure.\n"
        "- Do not spam the same suggestion multiple times.\n"
        "- Respect other people's opinions.\n\n"
        "**EXAMPLES:**\n"
        "- New event ideas\n"
        "- Server channel improvements\n"
        "- Guild activity ideas\n"
        "- Role or reward suggestions\n"
        "- Bot feature suggestions\n\n"
        "Owners will review suggestions and decide what fits best for **DECAY**."
    )
    embed.set_thumbnail(url=DECAY_LOGO_URL)
    embed.set_footer(text="DECAY Suggestions")
    return embed


def create_contributions_embed():
    embed = make_embed(
        "Guild Contributions",
        "Use this channel to share the resources you contribute to the **DECAY Guild**.\n\n"
        "**WHAT TO POST:**\n"
        "- The resources you contributed\n"
        "- The amount contributed\n"
        "- A screenshot if possible\n\n"
        "**EXAMPLES:**\n"
        "- 200K GEMS\n"
        "- 500K GOLD\n"
        "- 25 STAT REROLLS\n"
        "- 100 TRAIT REROLLS\n\n"
        "**IMPORTANT:**\n"
        "Fake contributions may result in moderation action.\n\n"
        "Every contribution helps **DECAY** grow stronger."
    )
    embed.set_thumbnail(url=DECAY_LOGO_URL)
    embed.set_footer(text="DECAY Guild Contributions")
    return embed


def create_ticket_questions_embed(member):
    embed = make_embed(
        "DECAY Guild Application",
        f"Thanks for applying to **DECAY**, {member.mention}.\n\n"
        "Please answer the following questions:\n\n"
        "**1.** What is your **Roblox username**?\n"
        "**2.** Send a **screenshot of your best units**.\n"
        "**3.** How active are you in **Discord** and **Roblox** from **1 to 10**?\n"
        "**4.** Why do you want to join **DECAY**, and why should we accept you?\n\n"
        "A staff member will review your application soon. Please be patient."
    )
    embed.set_thumbnail(url=DECAY_LOGO_URL)
    embed.set_footer(text="DECAY Guild Applications")
    return embed


class GuildApplyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Apply for DECAY", style=discord.ButtonStyle.danger, custom_id="decay_apply_button")
    async def apply_for_decay(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        if not guild or not isinstance(member, discord.Member):
            await interaction.response.send_message("This button can only be used inside the server.", ephemeral=True)
            return
        category = guild.get_channel(GUILD_TICKET_CATEGORY_ID)
        if not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("The ticket category was not found. Please contact staff.", ephemeral=True)
            return
        topic_key = f"DECAY_APPLICATION_USER:{member.id}"
        for channel in category.text_channels:
            if channel.topic and topic_key in channel.topic:
                await interaction.response.send_message(f"You already have an open application ticket: {channel.mention}", ephemeral=True)
                return
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True),
        }
        for role_id in TICKET_STAFF_ROLE_IDS:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)
        ticket_channel = await guild.create_text_channel(
            name=f"decay-apply-{safe_channel_name(member.name)}",
            category=category,
            overwrites=overwrites,
            topic=f"DECAY Guild application ticket | {topic_key}",
            reason=f"DECAY application ticket created by {member}",
        )
        await ticket_channel.send(content=f"{member.mention} " + " ".join(f"<@&{role_id}>" for role_id in TICKET_STAFF_ROLE_IDS), embed=create_ticket_questions_embed(member))
        await send_log(guild, "Ticket Created", f"**User:** {member.mention} (`{member.id}`)\n**Ticket:** {ticket_channel.mention}\n**Type:** DECAY Guild application")
        await interaction.response.send_message(f"Your DECAY application ticket has been created: {ticket_channel.mention}", ephemeral=True)


@bot.event
async def on_ready():
    init_db()
    bot.add_view(GuildApplyView())
    if not check_temp_bans.is_running():
        check_temp_bans.start()
    if not bot.slash_synced:
        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
            except discord.DiscordException:
                pass
        bot.slash_synced = True
    print(f"Bot connected as {bot.user}")


@bot.event
async def on_member_join(member):
    welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if welcome_channel:
        embed = make_embed(
            f"Welcome to {member.guild.name}, {member.name}!",
            f"Hey {member.mention}, welcome to **DECAY**!\n\n"
            f"Please check <#{RULES_CHANNEL_ID}> before chatting.\n"
            f"Keep an eye on <#{ANNOUNCEMENTS_CHANNEL_ID}> for important updates.\n\n"
            f"If you want to apply to a **DECAY Guild**, go to <#{GUILD_APPLY_CHANNEL_ID}> and create a ticket for the Guild you want to join."
        )
        embed.set_image(url=WELCOME_BANNER_URL)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{member.guild.member_count} • DECAY")
        await welcome_channel.send(content=member.mention, embed=embed)
    general_channel = member.guild.get_channel(GENERAL_CHANNEL_ID)
    if general_channel:
        await general_channel.send(f"yo {member.mention} welcome to DECAY!")
    await send_log(member.guild, "Member Joined", f"**User:** {member.mention} (`{member.id}`)\n**Account created:** <t:{int(member.created_at.timestamp())}:R>\n**Member count:** {member.guild.member_count}")


@bot.event
async def on_member_remove(member):
    joined_text = f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown"
    await send_log(member.guild, "Member Left", f"**User:** `{member}` (`{member.id}`)\n**Joined server:** {joined_text}\n**Member count:** {member.guild.member_count}", discord.Color.dark_red())


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.guild and message.channel.id == SUGGESTIONS_CHANNEL_ID:
        try:
            await message.add_reaction("✅")
            await message.add_reaction("❌")
        except discord.DiscordException:
            pass
    if bot.user and bot.user in message.mentions and not message.content.strip().startswith("!"):
        await message.reply(random.choice(PHRASES["mention"]), mention_author=False)
    await handle_xp(message)
    await bot.process_commands(message)


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
                    await send_log(guild, "Temporary Ban Expired", f"**User:** `{user}` (`{user.id}`)\n**Action:** Auto unban")
                except discord.DiscordException:
                    pass
            cursor.execute("DELETE FROM active_punishments WHERE id = ?", (punishment_id,))
    conn.commit()
    conn.close()


# Prefix commands
@bot.command()
async def ping(ctx):
    await ctx.send("Pong 🏓")


@bot.command(name="commands")
async def commands_list(ctx):
    await ctx.send(embed=create_commands_embed())


@bot.command(name="8ball")
async def eight_ball(ctx, *, question=None):
    if not question:
        await ctx.send(pick("missing"))
        return
    await ctx.send(random.choice(PHRASES["8ball"]))


@bot.command()
async def rate(ctx, *, target=None):
    if not target:
        target = ctx.author.mention
    number = random.randint(0, 100)
    await ctx.send(pick("rate", target=target, number=number, rest=100 - number))


@bot.command()
async def level(ctx, target_text: str = None):
    target = ctx.author
    if target_text:
        found = await get_user_from_text(ctx.guild, target_text)
        if not found:
            await ctx.send("user not found. use a mention or valid user ID.")
            return
        target = found
    await ctx.send(await level_text(ctx.guild, target))


@bot.command()
async def leaderboard(ctx):
    await ctx.send(leaderboard_text(ctx.guild))


@bot.command()
@setup_only()
async def xpchanneloff(ctx):
    set_xp_channel_disabled(ctx.guild.id, ctx.channel.id, True)
    await ctx.send(f"XP disabled in {ctx.channel.mention}. no more chat farming here.")


@bot.command()
@setup_only()
async def xpchannelon(ctx):
    set_xp_channel_disabled(ctx.guild.id, ctx.channel.id, False)
    await ctx.send(f"XP enabled in {ctx.channel.mention}. the grind economy is back.")


@bot.command()
@setup_only()
async def xpexcluded(ctx):
    channels = get_disabled_xp_channels(ctx.guild.id)
    if not channels:
        await ctx.send("no channels excluded. XP is active everywhere by default.")
        return
    await ctx.send("XP is disabled in:\n" + "\n".join(f"<#{channel_id}>" for channel_id in channels))


@bot.command()
@setup_only()
async def guildapplysetup(ctx):
    await ctx.send(embed=create_apply_embed(), view=GuildApplyView())
    await send_log(ctx.guild, "Guild Apply Setup Sent", f"**Moderator:** {ctx.author.mention}\n**Channel:** {ctx.channel.mention}")


@bot.command()
@setup_only()
async def rulesembed(ctx):
    await ctx.send(embed=create_rules_embed())
    await send_log(ctx.guild, "Rules Embed Sent", f"**Moderator:** {ctx.author.mention}\n**Channel:** {ctx.channel.mention}")


@bot.command()
@setup_only()
async def suggestionsembed(ctx):
    await ctx.send(embed=create_suggestions_embed())
    await send_log(ctx.guild, "Suggestions Embed Sent", f"**Moderator:** {ctx.author.mention}\n**Channel:** {ctx.channel.mention}")


@bot.command()
@setup_only()
async def contributionsembed(ctx):
    await ctx.send(embed=create_contributions_embed())
    await send_log(ctx.guild, "Contributions Embed Sent", f"**Moderator:** {ctx.author.mention}\n**Channel:** {ctx.channel.mention}")


@bot.command()
@ticket_staff_only()
async def ticketclose(ctx):
    if not ctx.channel.topic or "DECAY_APPLICATION_USER:" not in ctx.channel.topic:
        await ctx.send("this command only works inside an application ticket.")
        return
    match = re.search(r"DECAY_APPLICATION_USER:(\d+)", ctx.channel.topic)
    user_id = int(match.group(1)) if match else None
    member = ctx.guild.get_member(user_id) if user_id else None
    if member:
        await ctx.channel.set_permissions(member, view_channel=False, send_messages=False)
    if not ctx.channel.name.startswith("closed-"):
        await ctx.channel.edit(name=f"closed-{ctx.channel.name[:80]}")
    await ctx.send(pick("ticketclose"))
    await send_log(ctx.guild, "Ticket Closed", f"**Closed by:** {ctx.author.mention}\n**Ticket:** {ctx.channel.mention}\n**Applicant ID:** `{user_id or 'Unknown'}`")


@bot.command()
@ticket_staff_only()
async def ticketdelete(ctx):
    if not ctx.channel.topic or "DECAY_APPLICATION_USER:" not in ctx.channel.topic:
        await ctx.send("this command only works inside an application ticket.")
        return
    ticket_name = ctx.channel.name
    ticket_id = ctx.channel.id
    match = re.search(r"DECAY_APPLICATION_USER:(\d+)", ctx.channel.topic)
    user_id = int(match.group(1)) if match else None
    await send_log(ctx.guild, "Ticket Deleted", f"**Deleted by:** {ctx.author.mention}\n**Ticket:** `#{ticket_name}` (`{ticket_id}`)\n**Applicant ID:** `{user_id or 'Unknown'}`")
    await ctx.send(pick("ticketdelete"))
    await ctx.channel.delete(reason=f"Application ticket deleted by {ctx.author}")


@bot.command()
@basic_staff_only()
async def timeout(ctx, target_text: str = None, duration_text: str = None, *, reason=None):
    if not target_text or not duration_text:
        await ctx.send("Usage: `!timeout @user 1h reason` or `!timeout @user 2d reason`")
        return
    if not await check_abuse_limit(ctx, "timeout"):
        return
    target = await get_user_from_text(ctx.guild, target_text)
    duration = parse_duration(duration_text)
    if not target or not isinstance(target, discord.Member):
        await ctx.send("member not found. timeouts only work on users currently in the server.")
        return
    if not duration:
        await ctx.send("invalid duration. use `1h`, `6h`, `1d`, or `7d`.")
        return
    allowed, error = can_punish(ctx, target)
    if not allowed:
        await ctx.send(error)
        return
    await target.timeout(now_utc() + duration, reason=reason or f"Timed out by {ctx.author}")
    log_id = add_mod_log(ctx.guild.id, target.id, ctx.author.id, "TIMEOUT", duration_text, reason)
    await ctx.send(f"{pick('timeout', user=target.mention, duration=duration_text)} case `#{log_id}`.")
    await log_mod_action(ctx.guild, "Moderation: Timeout", target, ctx.author, reason, log_id, duration_text)


@bot.command()
@basic_staff_only()
async def untimeout(ctx, target_text: str = None, *, reason=None):
    if not target_text:
        await ctx.send("Usage: `!untimeout @user reason`")
        return
    target = await get_user_from_text(ctx.guild, target_text)
    if not target or not isinstance(target, discord.Member):
        await ctx.send("member not found. untimeout only works on users currently in the server.")
        return
    allowed, error = can_punish(ctx, target)
    if not allowed:
        await ctx.send(error)
        return
    await target.timeout(None, reason=reason or f"Timeout removed by {ctx.author}")
    log_id = add_mod_log(ctx.guild.id, target.id, ctx.author.id, "UNTIMEOUT", None, reason)
    await ctx.send(f"{pick('untimeout', user=target.mention)} case `#{log_id}`.")
    await log_mod_action(ctx.guild, "Moderation: Untimeout", target, ctx.author, reason, log_id)


@bot.command()
@full_staff_only()
async def kick(ctx, target_text: str = None, *, reason=None):
    if not target_text:
        await ctx.send("Usage: `!kick @user reason`")
        return
    if not await check_abuse_limit(ctx, "kick"):
        return
    target = await get_user_from_text(ctx.guild, target_text)
    if not target or not isinstance(target, discord.Member):
        await ctx.send("member not found. kicks only work on users currently in the server.")
        return
    allowed, error = can_punish(ctx, target)
    if not allowed:
        await ctx.send(error)
        return
    await target.kick(reason=reason or f"Kicked by {ctx.author}")
    log_id = add_mod_log(ctx.guild.id, target.id, ctx.author.id, "KICK", None, reason)
    await ctx.send(f"{pick('kick', user=f'`{target}`')} case `#{log_id}`.")
    await log_mod_action(ctx.guild, "Moderation: Kick", target, ctx.author, reason, log_id)


@bot.command()
@full_staff_only()
async def ban(ctx, target_text: str = None, duration_text: str = None, *, reason=None):
    if not target_text:
        await ctx.send("Usage: `!ban @user reason` or `!ban @user 7d reason`")
        return
    if not await check_abuse_limit(ctx, "ban"):
        return
    target = await get_user_from_text(ctx.guild, target_text)
    if not target:
        await ctx.send("user not found. use a mention or valid user ID.")
        return
    duration = parse_duration(duration_text) if duration_text else None
    if duration_text and not duration:
        reason = f"{duration_text} {reason or ''}".strip()
        duration_text = None
    allowed, error = can_punish(ctx, target)
    if not allowed:
        await ctx.send(error)
        return
    await ctx.guild.ban(target, reason=reason or f"Banned by {ctx.author}")
    if duration:
        add_active_tempban(ctx.guild.id, target.id, now_utc() + duration)
        log_id = add_mod_log(ctx.guild.id, target.id, ctx.author.id, "TEMP_BAN", duration_text, reason)
        await ctx.send(f"{pick('tempban', user=f'`{target}`', duration=duration_text)} case `#{log_id}`.")
        await log_mod_action(ctx.guild, "Moderation: Temporary Ban", target, ctx.author, reason, log_id, duration_text)
    else:
        log_id = add_mod_log(ctx.guild.id, target.id, ctx.author.id, "PERMA_BAN", None, reason)
        await ctx.send(f"{pick('permban', user=f'`{target}`')} case `#{log_id}`.")
        await log_mod_action(ctx.guild, "Moderation: Permanent Ban", target, ctx.author, reason, log_id)


@bot.command()
@full_staff_only()
async def unban(ctx, target_text: str = None, *, reason=None):
    if not target_text:
        await ctx.send("Usage: `!unban userID reason`")
        return
    target = await get_user_from_text(ctx.guild, target_text)
    if not target:
        await ctx.send("user not found. use a valid user ID.")
        return
    try:
        await ctx.guild.unban(target, reason=reason or f"Unbanned by {ctx.author}")
    except discord.NotFound:
        await ctx.send("that user is not banned in this server.")
        return
    remove_active_tempban(ctx.guild.id, target.id)
    log_id = add_mod_log(ctx.guild.id, target.id, ctx.author.id, "UNBAN", None, reason)
    await ctx.send(f"{pick('unban', user=f'`{target}`')} case `#{log_id}`.")
    await log_mod_action(ctx.guild, "Moderation: Unban", target, ctx.author, reason, log_id)


@bot.command()
@basic_staff_only()
async def clear(ctx, amount: int = None):
    if amount is None:
        await ctx.send("Usage: `!clear 10`")
        return
    if amount < 1 or amount > 100:
        await ctx.send("invalid amount. choose a number between 1 and 100.")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    confirmation = await ctx.send(pick("clear", amount=len(deleted) - 1))
    await send_log(ctx.guild, "Moderation: Clear", f"**Moderator:** {ctx.author.mention}\n**Channel:** {ctx.channel.mention}\n**Messages deleted:** `{len(deleted) - 1}`")
    try:
        await confirmation.delete(delay=5)
    except discord.DiscordException:
        pass


@bot.command()
@basic_staff_only()
async def modlog(ctx, target_text: str = None):
    if not target_text:
        await ctx.send("Usage: `!modlog @user`")
        return
    target = await get_user_from_text(ctx.guild, target_text)
    if not target:
        await ctx.send("user not found. use a mention or valid user ID.")
        return
    await send_modlog(ctx, target)


async def send_modlog(ctx, target):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, action, duration, reason, moderator_id, created_at FROM mod_logs WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT 10", (ctx.guild.id, target.id))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        await ctx.send("no moderation history found for this user.")
        return
    embed = make_embed(f"Modlog for {target}", "Latest **10 moderation cases** for this user.")
    for log_id, action, duration, reason, moderator_id, created_at in rows:
        date_text = datetime.fromisoformat(created_at).strftime("%Y-%m-%d %H:%M UTC")
        embed.add_field(name=f"Case #{log_id} — {action}", value=f"**Date:** {date_text}\n**Moderator:** <@{moderator_id}>\n**Duration:** {duration or 'N/A'}\n**Reason:** {reason}", inline=False)
    await ctx.send(embed=embed)


@bot.command(name="case")
@basic_staff_only()
async def view_case(ctx, log_id: int = None):
    if log_id is None:
        await ctx.send("Usage: `!case 12`")
        return
    await send_case_embed(ctx, log_id)


async def send_case_embed(ctx, log_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, moderator_id, action, duration, reason, created_at FROM mod_logs WHERE guild_id = ? AND id = ?", (ctx.guild.id, log_id))
    row = cursor.fetchone()
    conn.close()
    if not row:
        await ctx.send("case not found. check the case ID and try again.")
        return
    user_id, moderator_id, action, duration, reason, created_at = row
    embed = make_embed(f"Case #{log_id}", "Moderation case details.")
    embed.add_field(name="User", value=f"<@{user_id}> (`{user_id}`)", inline=False)
    embed.add_field(name="Action", value=f"**{action}**", inline=True)
    embed.add_field(name="Duration", value=duration or "N/A", inline=True)
    embed.add_field(name="Moderator", value=f"<@{moderator_id}>", inline=False)
    embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
    await ctx.send(embed=embed)


@bot.command()
@full_staff_only()
async def reason(ctx, log_id: int = None, *, new_reason=None):
    if log_id is None or not new_reason:
        await ctx.send("Usage: `!reason caseID new reason`")
        return
    await update_reason_common(ctx, log_id, new_reason)


async def update_reason_common(ctx, log_id, new_reason):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM mod_logs WHERE guild_id = ? AND id = ?", (ctx.guild.id, log_id))
    if not cursor.fetchone():
        conn.close()
        await ctx.send("case not found. check the case ID and try again.")
        return
    cursor.execute("UPDATE mod_logs SET reason = ? WHERE guild_id = ? AND id = ?", (new_reason, ctx.guild.id, log_id))
    conn.commit()
    conn.close()
    await ctx.send(embed=make_embed("Case Reason Updated", f"**Case ID:** `#{log_id}`\n**New reason:** {new_reason}"))
    await send_log(ctx.guild, "Moderation: Reason Updated", f"**Moderator:** {ctx.author.mention}\n**Case ID:** `#{log_id}`\n**New reason:** {new_reason}")


@bot.command()
@full_staff_only()
async def removelog(ctx, log_id: int = None):
    if log_id is None:
        await ctx.send("Usage: `!removelog 12`")
        return
    await remove_log_common(ctx, log_id)


async def remove_log_common(ctx, log_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM mod_logs WHERE guild_id = ? AND id = ?", (ctx.guild.id, log_id))
    if not cursor.fetchone():
        conn.close()
        await ctx.send("case not found. check the case ID and try again.")
        return
    cursor.execute("DELETE FROM mod_logs WHERE guild_id = ? AND id = ?", (ctx.guild.id, log_id))
    conn.commit()
    conn.close()
    await ctx.send(embed=make_embed("Case Removed", f"**Case ID:** `#{log_id}` has been deleted from the modlog."))
    await send_log(ctx.guild, "Moderation: Case Removed", f"**Moderator:** {ctx.author.mention}\n**Removed Case ID:** `#{log_id}`")


# Slash commands
@app_commands.command(name="commands", description="Show all DECAY bot commands")
async def slash_commands(interaction: discord.Interaction):
    await interaction.response.send_message(embed=create_commands_embed())


@fun_group.command(name="8ball", description="Ask the DECAY 8ball a question")
@app_commands.describe(question="Question to ask")
async def slash_fun_8ball(interaction: discord.Interaction, question: str):
    await interaction.response.send_message(random.choice(PHRASES["8ball"]))


@fun_group.command(name="rate", description="Rate anything or anyone")
@app_commands.describe(target="Target to rate")
async def slash_fun_rate(interaction: discord.Interaction, target: str = None):
    target = target or interaction.user.mention
    number = random.randint(0, 100)
    await interaction.response.send_message(pick("rate", target=target, number=number, rest=100 - number))


@xp_group.command(name="level", description="Show your level or another member's level")
@app_commands.describe(user="Member to check")
async def slash_xp_level(interaction: discord.Interaction, user: discord.Member = None):
    await interaction.response.send_message(await level_text(interaction.guild, user or interaction.user))


@xp_group.command(name="leaderboard", description="Show the DECAY XP leaderboard")
async def slash_xp_leaderboard(interaction: discord.Interaction):
    await interaction.response.send_message(leaderboard_text(interaction.guild))


@xp_group.command(name="channel_off", description="Disable XP in this channel")
async def slash_xp_channel_off(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, [OBLIVION_ROLE_ID]):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    set_xp_channel_disabled(interaction.guild.id, interaction.channel.id, True)
    await interaction.response.send_message(f"XP disabled in {interaction.channel.mention}. no more chat farming here.")


@xp_group.command(name="channel_on", description="Enable XP in this channel")
async def slash_xp_channel_on(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, [OBLIVION_ROLE_ID]):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    set_xp_channel_disabled(interaction.guild.id, interaction.channel.id, False)
    await interaction.response.send_message(f"XP enabled in {interaction.channel.mention}. the grind economy is back.")


@xp_group.command(name="excluded", description="Show channels where XP is disabled")
async def slash_xp_excluded(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, [OBLIVION_ROLE_ID]):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    channels = get_disabled_xp_channels(interaction.guild.id)
    if not channels:
        await interaction.response.send_message("no channels excluded. XP is active everywhere by default.")
        return
    await interaction.response.send_message("XP is disabled in:\n" + "\n".join(f"<#{channel_id}>" for channel_id in channels))


@setup_group.command(name="apply", description="Send the Apply for DECAY embed")
async def slash_setup_apply(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, [OBLIVION_ROLE_ID]):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    await interaction.response.send_message(embed=create_apply_embed(), view=GuildApplyView())
    await send_log(interaction.guild, "Guild Apply Setup Sent", f"**Moderator:** {interaction.user.mention}\n**Channel:** {interaction.channel.mention}")


@setup_group.command(name="rules", description="Send the rules embed")
async def slash_setup_rules(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, [OBLIVION_ROLE_ID]):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    await interaction.response.send_message(embed=create_rules_embed())
    await send_log(interaction.guild, "Rules Embed Sent", f"**Moderator:** {interaction.user.mention}\n**Channel:** {interaction.channel.mention}")


@setup_group.command(name="suggestions", description="Send the suggestions embed")
async def slash_setup_suggestions(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, [OBLIVION_ROLE_ID]):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    await interaction.response.send_message(embed=create_suggestions_embed())
    await send_log(interaction.guild, "Suggestions Embed Sent", f"**Moderator:** {interaction.user.mention}\n**Channel:** {interaction.channel.mention}")


@setup_group.command(name="contributions", description="Send the contributions embed")
async def slash_setup_contributions(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, [OBLIVION_ROLE_ID]):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    await interaction.response.send_message(embed=create_contributions_embed())
    await send_log(interaction.guild, "Contributions Embed Sent", f"**Moderator:** {interaction.user.mention}\n**Channel:** {interaction.channel.mention}")


@ticket_group.command(name="close", description="Close an application ticket")
async def slash_ticket_close(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, TICKET_STAFF_ROLE_IDS):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    channel = interaction.channel
    if not channel.topic or "DECAY_APPLICATION_USER:" not in channel.topic:
        await interaction.response.send_message("this command only works inside an application ticket.", ephemeral=True)
        return
    match = re.search(r"DECAY_APPLICATION_USER:(\d+)", channel.topic)
    user_id = int(match.group(1)) if match else None
    member = interaction.guild.get_member(user_id) if user_id else None
    if member:
        await channel.set_permissions(member, view_channel=False, send_messages=False)
    if not channel.name.startswith("closed-"):
        await channel.edit(name=f"closed-{channel.name[:80]}")
    await interaction.response.send_message(pick("ticketclose"))
    await send_log(interaction.guild, "Ticket Closed", f"**Closed by:** {interaction.user.mention}\n**Ticket:** {channel.mention}\n**Applicant ID:** `{user_id or 'Unknown'}`")


@ticket_group.command(name="delete", description="Delete an application ticket")
async def slash_ticket_delete(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, TICKET_STAFF_ROLE_IDS):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    channel = interaction.channel
    if not channel.topic or "DECAY_APPLICATION_USER:" not in channel.topic:
        await interaction.response.send_message("this command only works inside an application ticket.", ephemeral=True)
        return
    ticket_name = channel.name
    ticket_id = channel.id
    match = re.search(r"DECAY_APPLICATION_USER:(\d+)", channel.topic)
    user_id = int(match.group(1)) if match else None
    await send_log(interaction.guild, "Ticket Deleted", f"**Deleted by:** {interaction.user.mention}\n**Ticket:** `#{ticket_name}` (`{ticket_id}`)\n**Applicant ID:** `{user_id or 'Unknown'}`")
    await interaction.response.send_message(pick("ticketdelete"))
    await channel.delete(reason=f"Application ticket deleted by {interaction.user}")


@mod_group.command(name="timeout", description="Timeout a member")
@app_commands.describe(user="Member to timeout", duration="Duration like 1h or 2d", reason="Reason")
async def slash_mod_timeout(interaction: discord.Interaction, user: discord.Member, duration: str, reason: str = None):
    if not interaction_has_any_role(interaction, BASIC_STAFF_ROLE_IDS):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    if not await check_abuse_limit_slash(interaction, "timeout"):
        return
    parsed_duration = parse_duration(duration)
    if not parsed_duration:
        await interaction.response.send_message("invalid duration. use `1h`, `6h`, `1d`, or `7d`.", ephemeral=True)
        return
    allowed, error = can_punish_slash(interaction, user)
    if not allowed:
        await interaction.response.send_message(error, ephemeral=True)
        return
    await user.timeout(now_utc() + parsed_duration, reason=reason or f"Timed out by {interaction.user}")
    log_id = add_mod_log(interaction.guild.id, user.id, interaction.user.id, "TIMEOUT", duration, reason)
    await interaction.response.send_message(f"{pick('timeout', user=user.mention, duration=duration)} case `#{log_id}`.")
    await log_mod_action(interaction.guild, "Moderation: Timeout", user, interaction.user, reason, log_id, duration)


@mod_group.command(name="untimeout", description="Remove a member timeout")
@app_commands.describe(user="Member to untimeout", reason="Reason")
async def slash_mod_untimeout(interaction: discord.Interaction, user: discord.Member, reason: str = None):
    if not interaction_has_any_role(interaction, BASIC_STAFF_ROLE_IDS):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    allowed, error = can_punish_slash(interaction, user)
    if not allowed:
        await interaction.response.send_message(error, ephemeral=True)
        return
    await user.timeout(None, reason=reason or f"Timeout removed by {interaction.user}")
    log_id = add_mod_log(interaction.guild.id, user.id, interaction.user.id, "UNTIMEOUT", None, reason)
    await interaction.response.send_message(f"{pick('untimeout', user=user.mention)} case `#{log_id}`.")
    await log_mod_action(interaction.guild, "Moderation: Untimeout", user, interaction.user, reason, log_id)


@mod_group.command(name="clear", description="Clear messages")
@app_commands.describe(amount="Number of messages to delete")
async def slash_mod_clear(interaction: discord.Interaction, amount: int):
    if not interaction_has_any_role(interaction, BASIC_STAFF_ROLE_IDS):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    if amount < 1 or amount > 100:
        await interaction.response.send_message("invalid amount. choose a number between 1 and 100.", ephemeral=True)
        return
    await interaction.response.defer()
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(pick("clear", amount=len(deleted)), wait=True)
    await send_log(interaction.guild, "Moderation: Clear", f"**Moderator:** {interaction.user.mention}\n**Channel:** {interaction.channel.mention}\n**Messages deleted:** `{len(deleted)}`")


@mod_group.command(name="kick", description="Kick a member")
@app_commands.describe(user="Member to kick", reason="Reason")
async def slash_mod_kick(interaction: discord.Interaction, user: discord.Member, reason: str = None):
    if not interaction_has_any_role(interaction, FULL_STAFF_ROLE_IDS):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    if not await check_abuse_limit_slash(interaction, "kick"):
        return
    allowed, error = can_punish_slash(interaction, user)
    if not allowed:
        await interaction.response.send_message(error, ephemeral=True)
        return
    await user.kick(reason=reason or f"Kicked by {interaction.user}")
    log_id = add_mod_log(interaction.guild.id, user.id, interaction.user.id, "KICK", None, reason)
    await interaction.response.send_message(f"{pick('kick', user=f'`{user}`')} case `#{log_id}`.")
    await log_mod_action(interaction.guild, "Moderation: Kick", user, interaction.user, reason, log_id)


@mod_group.command(name="ban", description="Ban a user")
@app_commands.describe(user="User to ban", duration="Optional duration like 7d or 12h", reason="Reason")
async def slash_mod_ban(interaction: discord.Interaction, user: discord.User, duration: str = None, reason: str = None):
    if not interaction_has_any_role(interaction, FULL_STAFF_ROLE_IDS):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    if not await check_abuse_limit_slash(interaction, "ban"):
        return
    parsed_duration = parse_duration(duration) if duration else None
    if duration and not parsed_duration:
        reason = f"{duration} {reason or ''}".strip()
        duration = None
    member_target = interaction.guild.get_member(user.id)
    allowed, error = can_punish_slash(interaction, member_target or user)
    if not allowed:
        await interaction.response.send_message(error, ephemeral=True)
        return
    await interaction.guild.ban(user, reason=reason or f"Banned by {interaction.user}")
    if parsed_duration:
        add_active_tempban(interaction.guild.id, user.id, now_utc() + parsed_duration)
        log_id = add_mod_log(interaction.guild.id, user.id, interaction.user.id, "TEMP_BAN", duration, reason)
        await interaction.response.send_message(f"{pick('tempban', user=f'`{user}`', duration=duration)} case `#{log_id}`.")
        await log_mod_action(interaction.guild, "Moderation: Temporary Ban", user, interaction.user, reason, log_id, duration)
    else:
        log_id = add_mod_log(interaction.guild.id, user.id, interaction.user.id, "PERMA_BAN", None, reason)
        await interaction.response.send_message(f"{pick('permban', user=f'`{user}`')} case `#{log_id}`.")
        await log_mod_action(interaction.guild, "Moderation: Permanent Ban", user, interaction.user, reason, log_id)


@mod_group.command(name="unban", description="Unban a user by ID")
@app_commands.describe(user_id="User ID to unban", reason="Reason")
async def slash_mod_unban(interaction: discord.Interaction, user_id: str, reason: str = None):
    if not interaction_has_any_role(interaction, FULL_STAFF_ROLE_IDS):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    if not user_id.isdigit():
        await interaction.response.send_message("user ID must be a number.", ephemeral=True)
        return
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user, reason=reason or f"Unbanned by {interaction.user}")
    except discord.NotFound:
        await interaction.response.send_message("that user is not banned in this server.", ephemeral=True)
        return
    remove_active_tempban(interaction.guild.id, user.id)
    log_id = add_mod_log(interaction.guild.id, user.id, interaction.user.id, "UNBAN", None, reason)
    await interaction.response.send_message(f"{pick('unban', user=f'`{user}`')} case `#{log_id}`.")
    await log_mod_action(interaction.guild, "Moderation: Unban", user, interaction.user, reason, log_id)


@mod_group.command(name="modlog", description="Show a user's modlog")
@app_commands.describe(user="User to check")
async def slash_mod_modlog(interaction: discord.Interaction, user: discord.User):
    if not interaction_has_any_role(interaction, BASIC_STAFF_ROLE_IDS):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, action, duration, reason, moderator_id, created_at FROM mod_logs WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT 10", (interaction.guild.id, user.id))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        await interaction.response.send_message("no moderation history found for this user.", ephemeral=True)
        return
    embed = make_embed(f"Modlog for {user}", "Latest **10 moderation cases** for this user.")
    for log_id, action, duration, reason, moderator_id, created_at in rows:
        date_text = datetime.fromisoformat(created_at).strftime("%Y-%m-%d %H:%M UTC")
        embed.add_field(name=f"Case #{log_id} — {action}", value=f"**Date:** {date_text}\n**Moderator:** <@{moderator_id}>\n**Duration:** {duration or 'N/A'}\n**Reason:** {reason}", inline=False)
    await interaction.response.send_message(embed=embed)


@mod_group.command(name="case", description="Show a moderation case")
@app_commands.describe(case_id="Case ID")
async def slash_mod_case(interaction: discord.Interaction, case_id: int):
    if not interaction_has_any_role(interaction, BASIC_STAFF_ROLE_IDS):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, moderator_id, action, duration, reason, created_at FROM mod_logs WHERE guild_id = ? AND id = ?", (interaction.guild.id, case_id))
    row = cursor.fetchone()
    conn.close()
    if not row:
        await interaction.response.send_message("case not found. check the case ID and try again.", ephemeral=True)
        return
    user_id, moderator_id, action, duration, reason, created_at = row
    embed = make_embed(f"Case #{case_id}", "Moderation case details.")
    embed.add_field(name="User", value=f"<@{user_id}> (`{user_id}`)", inline=False)
    embed.add_field(name="Action", value=f"**{action}**", inline=True)
    embed.add_field(name="Duration", value=duration or "N/A", inline=True)
    embed.add_field(name="Moderator", value=f"<@{moderator_id}>", inline=False)
    embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
    await interaction.response.send_message(embed=embed)


@mod_group.command(name="reason", description="Update a moderation case reason")
@app_commands.describe(case_id="Case ID", new_reason="New reason")
async def slash_mod_reason(interaction: discord.Interaction, case_id: int, new_reason: str):
    if not interaction_has_any_role(interaction, FULL_STAFF_ROLE_IDS):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM mod_logs WHERE guild_id = ? AND id = ?", (interaction.guild.id, case_id))
    if not cursor.fetchone():
        conn.close()
        await interaction.response.send_message("case not found. check the case ID and try again.", ephemeral=True)
        return
    cursor.execute("UPDATE mod_logs SET reason = ? WHERE guild_id = ? AND id = ?", (new_reason, interaction.guild.id, case_id))
    conn.commit()
    conn.close()
    await interaction.response.send_message(embed=make_embed("Case Reason Updated", f"**Case ID:** `#{case_id}`\n**New reason:** {new_reason}"))
    await send_log(interaction.guild, "Moderation: Reason Updated", f"**Moderator:** {interaction.user.mention}\n**Case ID:** `#{case_id}`\n**New reason:** {new_reason}")


@mod_group.command(name="removelog", description="Remove a moderation case")
@app_commands.describe(case_id="Case ID")
async def slash_mod_removelog(interaction: discord.Interaction, case_id: int):
    if not interaction_has_any_role(interaction, FULL_STAFF_ROLE_IDS):
        await interaction.response.send_message(random.choice(PHRASES["noperms"]), ephemeral=True)
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM mod_logs WHERE guild_id = ? AND id = ?", (interaction.guild.id, case_id))
    if not cursor.fetchone():
        conn.close()
        await interaction.response.send_message("case not found. check the case ID and try again.", ephemeral=True)
        return
    cursor.execute("DELETE FROM mod_logs WHERE guild_id = ? AND id = ?", (interaction.guild.id, case_id))
    conn.commit()
    conn.close()
    await interaction.response.send_message(embed=make_embed("Case Removed", f"**Case ID:** `#{case_id}` has been deleted from the modlog."))
    await send_log(interaction.guild, "Moderation: Case Removed", f"**Moderator:** {interaction.user.mention}\n**Removed Case ID:** `#{case_id}`")


bot.tree.add_command(slash_commands)
bot.tree.add_command(fun_group)
bot.tree.add_command(xp_group)
bot.tree.add_command(setup_group)
bot.tree.add_command(ticket_group)
bot.tree.add_command(mod_group)


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
@guildapplysetup.error
@rulesembed.error
@suggestionsembed.error
@contributionsembed.error
@ticketclose.error
@ticketdelete.error
@xpchanneloff.error
@xpchannelon.error
@xpexcluded.error
async def command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(random.choice(PHRASES["noperms"]))
    elif isinstance(error, commands.BadArgument):
        await ctx.send("invalid argument type. check the command format and try again.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(random.choice(PHRASES["missing"]))
    else:
        await ctx.send("unexpected error. the bot tripped over a cable or something.")
        raise error


key_name = "DISCORD" + "_" + "T0KEN".replace("0", "O")
bot.run(os.getenv(key_name))
