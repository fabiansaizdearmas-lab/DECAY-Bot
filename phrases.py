import random

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


def random_phrase(key):
    return random.choice(PHRASES[key])
