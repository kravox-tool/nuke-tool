"""Operaciones masivas sobre miembros."""
from __future__ import annotations

import discord

from .utils import human, pool


async def fetch_all_members(guild: discord.Guild) -> list:
    try:
        total = guild.member_count or 0
        if total and len(guild.members) >= total:
            return list(guild.members)
        return [m async for m in guild.fetch_members(limit=None)]
    except Exception:
        return list(guild.members)


async def ban_all(guild, client, *, reason: str = "nuke", ban_self: bool = False,
                  unban_self: bool = True, concurrency: int = 3, log=print) -> int:
    members = await fetch_all_members(guild)
    me = client.user.id
    targets = [m for m in members if ban_self or m.id != me]

    log(f"Baneando {human(len(targets))} miembros...")
    counter = {"n": 0}

    async def ban(member):
        try:
            await guild.ban(member, reason=reason)
            counter["n"] += 1
        except Exception:
            pass

    await pool(targets, lambda m, _i: ban(m), concurrency)

    if ban_self and unban_self:
        try:
            await guild.unban(discord.Object(id=me), reason=reason)
        except Exception:
            pass

    return counter["n"]


async def kick_all(guild, client, *, reason: str = "nuke", kick_self: bool = False,
                   concurrency: int = 3, log=print) -> int:
    members = await fetch_all_members(guild)
    me = client.user.id
    targets = [m for m in members if kick_self or m.id != me]

    log(f"Expulsando {human(len(targets))} miembros...")
    counter = {"n": 0}

    async def kick(member):
        try:
            await guild.kick(member, reason=reason)
            counter["n"] += 1
        except Exception:
            pass

    await pool(targets, lambda m, _i: kick(m), concurrency)
    return counter["n"]


async def nick_all(guild, nick: str, *, concurrency: int = 3, log=print) -> int:
    members = await fetch_all_members(guild)
    targets = [m for m in members if not m.bot]

    log(f"Cambiando el nick de {human(len(targets))} miembros...")
    counter = {"n": 0}

    async def rename(member):
        try:
            await member.edit(nick=nick, reason="nuke")
            counter["n"] += 1
        except Exception:
            pass

    await pool(targets, lambda m, _i: rename(m), concurrency)
    return counter["n"]


async def dm_all(guild, content: str, *, times: int = 1, limit: int = 0,
                 concurrency: int = 5, log=print) -> int:
    """Envia `content` `times` veces a cada miembro (limit 0 = todos)."""
    members = await fetch_all_members(guild)
    targets = [m for m in members if not m.bot]

    if limit and limit > 0:
        targets = targets[:limit]

    total = len(targets) * max(1, times)
    log(f"Enviando {human(total)} DMs a {human(len(targets))} miembros...")

    counter = {"n": 0}

    async def send(member):
        for _ in range(max(1, times)):
            try:
                await member.send(content)
                counter["n"] += 1
            except Exception:
                pass

    await pool(targets, lambda m, _i: send(m), concurrency)
    return counter["n"]
