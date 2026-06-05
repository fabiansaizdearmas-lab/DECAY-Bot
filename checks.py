import discord
from discord.ext import commands

from config import (
    BASIC_STAFF_ROLE_IDS,
    FULL_STAFF_ROLE_IDS,
    OBLIVION_ROLE_ID,
    TICKET_STAFF_ROLE_IDS,
)


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
