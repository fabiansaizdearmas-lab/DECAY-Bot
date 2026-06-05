import discord

from config import DECAY_RED, DECAY_LOGO_URL


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
