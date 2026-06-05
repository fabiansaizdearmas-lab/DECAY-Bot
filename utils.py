import re
from datetime import datetime, timezone


def now_utc():
    return datetime.now(timezone.utc)


def parse_duration(duration_text):
    if not duration_text:
        return None
    match = re.fullmatch(r"(\d+)(h|d)", duration_text.lower())
    if not match:
        return None
    amount = int(match.group(1))
    if amount <= 0:
        return None
    from datetime import timedelta
    return timedelta(hours=amount) if match.group(2) == "h" else timedelta(days=amount)


def format_remaining(delta):
    seconds = max(1, int(delta.total_seconds()))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes or 1}m"


def target_name(target):
    import discord
    return target.mention if isinstance(target, discord.Member) else f"`{target}`"


def safe_channel_name(text):
    text = re.sub(r"[^a-z0-9-]", "-", text.lower())
    return re.sub(r"-+", "-", text).strip("-")[:40] or "user"


async def get_user_from_text(bot, guild, target_text):
    import discord
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
