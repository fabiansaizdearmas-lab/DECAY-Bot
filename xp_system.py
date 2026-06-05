from config import MAX_LEVEL, XP_GAIN, XP_ROLE_MILESTONES, XP_ROLE_NAMES
from database import get_xp_data, set_xp_data, get_xp_leaderboard


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


def xp_rank_name(level):
    rank = None
    for milestone in sorted(XP_ROLE_NAMES):
        if level >= milestone:
            rank = XP_ROLE_NAMES[milestone]
    return rank


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
    except Exception:
        pass


async def level_text(guild, target):
    xp, level_value = await get_xp_data(guild.id, target.id)
    progress, needed = xp_progress(xp, level_value)
    rank = xp_rank_name(level_value)
    rank_text = f" | rank: {rank}" if rank else ""
    if level_value >= MAX_LEVEL:
        return f"{target.mention} is level {level_value}{rank_text}. max level reached, bro finished the current season."
    return f"{target.mention} is level {level_value}{rank_text}. XP: {progress}/{needed} until level {level_value + 1}."


async def leaderboard_text(guild):
    rows = await get_xp_leaderboard(guild.id, 10)
    if not rows:
        return "leaderboard is empty. chat XP economy has not started yet."
    lines = [f"{index}. <@{user_id}> — Level {level_value} | {xp} XP" for index, (user_id, xp, level_value) in enumerate(rows, start=1)]
    return "**DECAY XP Leaderboard**\n" + "\n".join(lines)


def calculate_new_xp(current_xp):
    new_xp = current_xp + XP_GAIN
    new_level = min(level_from_xp(new_xp), MAX_LEVEL)
    return new_xp, new_level


async def save_xp(guild_id, user_id, xp, level):
    await set_xp_data(guild_id, user_id, xp, level)
