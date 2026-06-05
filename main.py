import os
import random
import re

import discord
from discord import app_commands
from discord.ext import commands, tasks

from checks import (
    basic_staff_only,
    can_punish,
    can_punish_slash,
    full_staff_only,
    interaction_has_any_role,
    is_oblivion,
    setup_only,
    ticket_staff_only,
)
from config import (
    ABUSE_LIMIT,
    ABUSE_WINDOW,
    ANNOUNCEMENTS_CHANNEL_ID,
    BASIC_STAFF_ROLE_IDS,
    BOT_COMMANDS_CHANNEL_ID,
    FULL_STAFF_ROLE_IDS,
    GENERAL_CHANNEL_ID,
    GUILD_APPLY_CHANNEL_ID,
    GUILD_TICKET_CATEGORY_ID,
    LOG_CHANNEL_ID,
    OBLIVION_ROLE_ID,
    RULES_CHANNEL_ID,
    SUGGESTIONS_CHANNEL_ID,
    TICKET_STAFF_ROLE_IDS,
    WELCOME_BANNER_URL,
    WELCOME_CHANNEL_ID,
    XP_COOLDOWN,
    XP_GAIN,
    MAX_LEVEL,
)
from database import (
    add_active_tempban,
    add_mod_log,
    delete_case,
    delete_tempban_by_id,
    get_case,
    get_disabled_xp_channels,
    get_temp_bans,
    get_user_modlogs,
    get_xp_data,
    init_db,
    is_xp_channel_disabled,
    remove_active_tempban,
    set_xp_channel_disabled,
    set_xp_data,
    update_case_reason,
)
from embeds import (
    create_apply_embed,
    create_commands_embed,
    create_contributions_embed,
    create_rules_embed,
    create_suggestions_embed,
    create_ticket_questions_embed,
    make_embed,
)
from phrases import PHRASES, pick, random_phrase
from utils import (
    format_remaining,
    get_user_from_text,
    now_utc,
    parse_duration,
    safe_channel_name,
    target_name,
)
from xp_system import calculate_new_xp, leaderboard_text, level_text, update_xp_role, xp_rank_name


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


async def send_log(guild, title, description, color=None):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if not channel:
        return
    embed = make_embed(title, description, color or 0xB30000)
    embed.timestamp = now_utc()
    try:
        await channel.send(embed=embed)
    except discord.DiscordException:
        pass


async def log_mod_action(guild, title, target, moderator, reason, log_id, duration=None):
    duration_line = f"**Duration:** `{duration}`\n" if duration else ""
    await send_log(
        guild,
        title,
        f"**User:** {target_name(target)} (`{target.id}`)\n"
        f"{duration_line}"
        f"**Moderator:** {moderator.mention}\n"
        f"**Reason:** {reason or 'No reason provided'}\n"
        f"**Case ID:** `#{log_id}`",
    )


async def check_abuse_limit(ctx, action):
    if is_oblivion(ctx.author):
        return True
    key = (ctx.guild.id, ctx.author.id, action)
    cutoff = now_utc() - ABUSE_WINDOW
    timestamps = [t for t in mod_action_history.get(key, []) if t > cutoff]
    if len(timestamps) >= ABUSE_LIMIT:
        remaining = ABUSE_WINDOW - (now_utc() - min(timestamps))
        await ctx.send(pick("cooldown", time=format_remaining(remaining), action=action))
        await send_log(
            ctx.guild,
            "Safety Limit Triggered",
            f"**Staff:** {ctx.author.mention}\n**Action:** `{action}`\n**Limit:** `{ABUSE_LIMIT}` per 6h\n**Remaining:** `{format_remaining(remaining)}`",
            discord.Color.orange(),
        )
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
        await interaction.response.send_message(
            pick("cooldown", time=format_remaining(remaining), action=action),
            ephemeral=True,
        )
        await send_log(
            interaction.guild,
            "Safety Limit Triggered",
            f"**Staff:** {interaction.user.mention}\n**Action:** `{action}`\n**Limit:** `{ABUSE_LIMIT}` per 6h\n**Remaining:** `{format_remaining(remaining)}`",
            discord.Color.orange(),
        )
        return False
    timestamps.append(now_utc())
    mod_action_history[key] = timestamps
    return True


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

    new_xp, new_level = calculate_new_xp(xp)
    set_xp_data(message.guild.id, message.author.id, new_xp, new_level)
    last_xp_times[key] = now_utc()

    if new_level > old_level:
        await update_xp_role(message.author, new_level)
        bot_channel = message.guild.get_channel(BOT_COMMANDS_CHANNEL_ID)
        if bot_channel:
            rank = xp_rank_name(new_level)
            rank_text = f" and became **{rank}**" if rank else ""
            await bot_channel.send(pick("levelup", user=message.author.mention, level=new_level) + rank_text)


async def send_modlog_message(send_func, guild, target):
    rows = get_user_modlogs(guild.id, target.id, 10)
    if not rows:
        await send_func("no moderation history found for this user.")
        return

    embed = make_embed(f"Modlog for {target}", "Latest **10 moderation cases** for this user.")
    for log_id, action, duration, reason, moderator_id, created_at in rows:
        date_text = created_at[:16].replace("T", " ") + " UTC"
        embed.add_field(
            name=f"Case #{log_id} — {action}",
            value=f"**Date:** {date_text}\n**Moderator:** <@{moderator_id}>\n**Duration:** {duration or 'N/A'}\n**Reason:** {reason}",
            inline=False,
        )
    await send_func(embed=embed)


async def send_case_message(send_func, guild, case_id):
    row = get_case(guild.id, case_id)
    if not row:
        await send_func("case not found. check the case ID and try again.")
        return

    user_id, moderator_id, action, duration, reason, created_at = row
    embed = make_embed(f"Case #{case_id}", "Moderation case details.")
    embed.add_field(name="User", value=f"<@{user_id}> (`{user_id}`)", inline=False)
    embed.add_field(name="Action", value=f"**{action}**", inline=True)
    embed.add_field(name="Duration", value=duration or "N/A", inline=True)
    embed.add_field(name="Moderator", value=f"<@{moderator_id}>", inline=False)
    embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
    await send_func(embed=embed)


async def update_reason_message(send_func, guild, moderator, case_id, new_reason):
    if not update_case_reason(guild.id, case_id, new_reason):
        await send_func("case not found. check the case ID and try again.")
        return
    await send_func(embed=make_embed("Case Reason Updated", f"**Case ID:** `#{case_id}`\n**New reason:** {new_reason}"))
    await send_log(
        guild,
        "Moderation: Reason Updated",
        f"**Moderator:** {moderator.mention}\n**Case ID:** `#{case_id}`\n**New reason:** {new_reason}",
    )


async def remove_log_message(send_func, guild, moderator, case_id):
    if not delete_case(guild.id, case_id):
        await send_func("case not found. check the case ID and try again.")
        return
    await send_func(embed=make_embed("Case Removed", f"**Case ID:** `#{case_id}` has been deleted from the modlog."))
    await send_log(
        guild,
        "Moderation: Case Removed",
        f"**Moderator:** {moderator.mention}\n**Removed Case ID:** `#{case_id}`",
    )


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
        await ticket_channel.send(
            content=f"{member.mention} " + " ".join(f"<@&{role_id}>" for role_id in TICKET_STAFF_ROLE_IDS),
            embed=create_ticket_questions_embed(member),
        )
        await send_log(
            guild,
            "Ticket Created",
            f"**User:** {member.mention} (`{member.id}`)\n**Ticket:** {ticket_channel.mention}\n**Type:** DECAY Guild application",
        )
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
            f"If you want to apply to a **DECAY Guild**, go to <#{GUILD_APPLY_CHANNEL_ID}> and create a ticket for the Guild you want to join.",
        )
        embed.set_image(url=WELCOME_BANNER_URL)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{member.guild.member_count} • DECAY")
        await welcome_channel.send(content=member.mention, embed=embed)

    general_channel = member.guild.get_channel(GENERAL_CHANNEL_ID)
    if general_channel:
        await general_channel.send(f"yo {member.mention} welcome to DECAY!")

    await send_log(
        member.guild,
        "Member Joined",
        f"**User:** {member.mention} (`{member.id}`)\n**Account created:** <t:{int(member.created_at.timestamp())}:R>\n**Member count:** {member.guild.member_count}",
    )


@bot.event
async def on_member_remove(member):
    joined_text = f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown"
    await send_log(
        member.guild,
        "Member Left",
        f"**User:** `{member}` (`{member.id}`)\n**Joined server:** {joined_text}\n**Member count:** {member.guild.member_count}",
        discord.Color.dark_red(),
    )


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
        await message.reply(random_phrase("mention"), mention_author=False)

    await handle_xp(message)
    await bot.process_commands(message)


@tasks.loop(minutes=1)
async def check_temp_bans():
    for punishment_id, guild_id, user_id, expires_at_text in get_temp_bans():
        if now_utc().fromisoformat(expires_at_text) <= now_utc():
            guild = bot.get_guild(guild_id)
            if guild:
                try:
                    user = await bot.fetch_user(user_id)
                    await guild.unban(user, reason="Temporary ban expired")
                    add_mod_log(guild_id, user_id, bot.user.id, "AUTO_UNBAN", None, "Temporary ban expired")
                    await send_log(guild, "Temporary Ban Expired", f"**User:** `{user}` (`{user.id}`)\n**Action:** Auto unban")
                except discord.DiscordException:
                    pass
            delete_tempban_by_id(punishment_id)


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
    await ctx.send(random_phrase("8ball"))


@bot.command()
async def rate(ctx, *, target=None):
    target = target or ctx.author.mention
    number = random.randint(0, 100)
    await ctx.send(pick("rate", target=target, number=number, rest=100 - number))


@bot.command()
async def level(ctx, target_text: str = None):
    target = ctx.author
    if target_text:
        found = await get_user_from_text(bot, ctx.guild, target_text)
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
    target = await get_user_from_text(bot, ctx.guild, target_text)
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
    target = await get_user_from_text(bot, ctx.guild, target_text)
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
    target = await get_user_from_text(bot, ctx.guild, target_text)
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
    target = await get_user_from_text(bot, ctx.guild, target_text)
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
    target = await get_user_from_text(bot, ctx.guild, target_text)
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
    target = await get_user_from_text(bot, ctx.guild, target_text)
    if not target:
        await ctx.send("user not found. use a mention or valid user ID.")
        return
    await send_modlog_message(ctx.send, ctx.guild, target)


@bot.command(name="case")
@basic_staff_only()
async def view_case(ctx, log_id: int = None):
    if log_id is None:
        await ctx.send("Usage: `!case 12`")
        return
    await send_case_message(ctx.send, ctx.guild, log_id)


@bot.command()
@full_staff_only()
async def reason(ctx, log_id: int = None, *, new_reason=None):
    if log_id is None or not new_reason:
        await ctx.send("Usage: `!reason caseID new reason`")
        return
    await update_reason_message(ctx.send, ctx.guild, ctx.author, log_id, new_reason)


@bot.command()
@full_staff_only()
async def removelog(ctx, log_id: int = None):
    if log_id is None:
        await ctx.send("Usage: `!removelog 12`")
        return
    await remove_log_message(ctx.send, ctx.guild, ctx.author, log_id)


# Slash commands
@app_commands.command(name="commands", description="Show all DECAY bot commands")
async def slash_commands(interaction: discord.Interaction):
    await interaction.response.send_message(embed=create_commands_embed())


@fun_group.command(name="8ball", description="Ask the DECAY 8ball a question")
@app_commands.describe(question="Question to ask")
async def slash_fun_8ball(interaction: discord.Interaction, question: str):
    await interaction.response.send_message(random_phrase("8ball"))


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
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
        return
    set_xp_channel_disabled(interaction.guild.id, interaction.channel.id, True)
    await interaction.response.send_message(f"XP disabled in {interaction.channel.mention}. no more chat farming here.")


@xp_group.command(name="channel_on", description="Enable XP in this channel")
async def slash_xp_channel_on(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, [OBLIVION_ROLE_ID]):
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
        return
    set_xp_channel_disabled(interaction.guild.id, interaction.channel.id, False)
    await interaction.response.send_message(f"XP enabled in {interaction.channel.mention}. the grind economy is back.")


@xp_group.command(name="excluded", description="Show channels where XP is disabled")
async def slash_xp_excluded(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, [OBLIVION_ROLE_ID]):
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
        return
    channels = get_disabled_xp_channels(interaction.guild.id)
    if not channels:
        await interaction.response.send_message("no channels excluded. XP is active everywhere by default.")
        return
    await interaction.response.send_message("XP is disabled in:\n" + "\n".join(f"<#{channel_id}>" for channel_id in channels))


@setup_group.command(name="apply", description="Send the Apply for DECAY embed")
async def slash_setup_apply(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, [OBLIVION_ROLE_ID]):
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
        return
    await interaction.response.send_message(embed=create_apply_embed(), view=GuildApplyView())
    await send_log(interaction.guild, "Guild Apply Setup Sent", f"**Moderator:** {interaction.user.mention}\n**Channel:** {interaction.channel.mention}")


@setup_group.command(name="rules", description="Send the rules embed")
async def slash_setup_rules(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, [OBLIVION_ROLE_ID]):
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
        return
    await interaction.response.send_message(embed=create_rules_embed())
    await send_log(interaction.guild, "Rules Embed Sent", f"**Moderator:** {interaction.user.mention}\n**Channel:** {interaction.channel.mention}")


@setup_group.command(name="suggestions", description="Send the suggestions embed")
async def slash_setup_suggestions(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, [OBLIVION_ROLE_ID]):
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
        return
    await interaction.response.send_message(embed=create_suggestions_embed())
    await send_log(interaction.guild, "Suggestions Embed Sent", f"**Moderator:** {interaction.user.mention}\n**Channel:** {interaction.channel.mention}")


@setup_group.command(name="contributions", description="Send the contributions embed")
async def slash_setup_contributions(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, [OBLIVION_ROLE_ID]):
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
        return
    await interaction.response.send_message(embed=create_contributions_embed())
    await send_log(interaction.guild, "Contributions Embed Sent", f"**Moderator:** {interaction.user.mention}\n**Channel:** {interaction.channel.mention}")


@ticket_group.command(name="close", description="Close an application ticket")
async def slash_ticket_close(interaction: discord.Interaction):
    if not interaction_has_any_role(interaction, TICKET_STAFF_ROLE_IDS):
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
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
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
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
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
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
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
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
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
        return
    if amount < 1 or amount > 100:
        await interaction.response.send_message("invalid amount. choose a number between 1 and 100.", ephemeral=True)
        return
    await interaction.response.defer()
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(pick("clear", amount=len(deleted)))
    await send_log(interaction.guild, "Moderation: Clear", f"**Moderator:** {interaction.user.mention}\n**Channel:** {interaction.channel.mention}\n**Messages deleted:** `{len(deleted)}`")


@mod_group.command(name="kick", description="Kick a member")
@app_commands.describe(user="Member to kick", reason="Reason")
async def slash_mod_kick(interaction: discord.Interaction, user: discord.Member, reason: str = None):
    if not interaction_has_any_role(interaction, FULL_STAFF_ROLE_IDS):
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
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
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
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
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
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
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
        return
    await send_modlog_message(interaction.response.send_message, interaction.guild, user)


@mod_group.command(name="case", description="Show a moderation case")
@app_commands.describe(case_id="Case ID")
async def slash_mod_case(interaction: discord.Interaction, case_id: int):
    if not interaction_has_any_role(interaction, BASIC_STAFF_ROLE_IDS):
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
        return
    await send_case_message(interaction.response.send_message, interaction.guild, case_id)


@mod_group.command(name="reason", description="Update a moderation case reason")
@app_commands.describe(case_id="Case ID", new_reason="New reason")
async def slash_mod_reason(interaction: discord.Interaction, case_id: int, new_reason: str):
    if not interaction_has_any_role(interaction, FULL_STAFF_ROLE_IDS):
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
        return
    await update_reason_message(interaction.response.send_message, interaction.guild, interaction.user, case_id, new_reason)


@mod_group.command(name="removelog", description="Remove a moderation case")
@app_commands.describe(case_id="Case ID")
async def slash_mod_removelog(interaction: discord.Interaction, case_id: int):
    if not interaction_has_any_role(interaction, FULL_STAFF_ROLE_IDS):
        await interaction.response.send_message(random_phrase("noperms"), ephemeral=True)
        return
    await remove_log_message(interaction.response.send_message, interaction.guild, interaction.user, case_id)


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
        await ctx.send(random_phrase("noperms"))
    elif isinstance(error, commands.BadArgument):
        await ctx.send("invalid argument type. check the command format and try again.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(random_phrase("missing"))
    else:
        await ctx.send("unexpected error. the bot tripped over a cable or something.")
        raise error


key_name = "DISCORD" + "_" + "T0KEN".replace("0", "O")
bot.run(os.getenv(key_name))
