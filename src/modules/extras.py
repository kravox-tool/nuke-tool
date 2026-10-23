"""Funciones extra: voz, emojis, stickers, presencia."""
from __future__ import annotations

import discord

from .utils import human, pool


async def disconnect_voice(guild: discord.Guild, *, concurrency: int = 3, log=print) -> int:
    from .members import fetch_all_members

    members = await fetch_all_members(guild)
    targets = [m for m in members if m.voice and m.voice.channel]

    log(f"Desconectando {human(len(targets))} usuarios de voz...")
    await pool(targets, lambda m, _i: m.move_to(None, reason="nuke"), concurrency)
    return len(targets)


async def delete_emojis(guild: discord.Guild, *, concurrency: int = 4, log=print) -> int:
    emojis = list(guild.emojis)
    log(f"Borrando {human(len(emojis))} emojis...")
    await pool(emojis, lambda e, _i: guild.delete_emoji(e, reason="nuke"), concurrency)
    return len(emojis)


async def delete_stickers(guild: discord.Guild, *, concurrency: int = 4, log=print) -> int:
    stickers = list(guild.stickers)
    log(f"Borrando {human(len(stickers))} stickers...")
    await pool(stickers, lambda s, _i: s.delete(reason="nuke"), concurrency)
    return len(stickers)


ACTIVITY_TYPES = {
    "playing": discord.ActivityType.playing,
    "watching": discord.ActivityType.watching,
    "listening": discord.ActivityType.listening,
    "competing": discord.ActivityType.competing,
    "custom": discord.ActivityType.custom,
}


async def set_status(client, text: str, kind: str = "playing") -> None:
    await client.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=ACTIVITY_TYPES.get(kind, discord.ActivityType.playing), name=text),
    )
