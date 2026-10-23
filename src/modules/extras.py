"""Funciones extra: voz, emojis, stickers, presencia, icono y spam."""
from __future__ import annotations

from pathlib import Path

import aiohttp
import discord

from .utils import human, pool

MAX_ICON_BYTES = 8 * 1024 * 1024


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


async def load_image(source: str) -> bytes:
    """Lee una imagen desde una URL o una ruta local de Termux."""
    source = source.strip().strip('"').strip("'")

    if source.startswith(("http://", "https://")):
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(source) as response:
                response.raise_for_status()
                data = await response.read()
    else:
        path = Path(source).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"No existe: {path}")
        data = path.read_bytes()

    if len(data) > MAX_ICON_BYTES:
        raise ValueError(f"La imagen pesa {len(data) / 1048576:.1f} MB (max 8 MB)")
    return data


async def set_icon(guild: discord.Guild, source: str) -> None:
    data = await load_image(source)
    await guild.edit(icon=data, reason="nuke")


async def spam_channel(channel, content: str, times: int, *,
                       concurrency: int = 3, log=print) -> int:
    """Envia el mismo mensaje N veces a un canal."""
    sent = 0

    async def send(_index):
        nonlocal sent
        try:
            await channel.send(content)
            sent += 1
        except Exception:
            pass

    await pool(range(times), lambda _item, i: send(i), concurrency)
    return sent


async def spam_channels_list(channels, content: str, times: int, *,
                             concurrency: int = 3, log=print) -> int:
    """Spam en varios canales: N mensajes en cada uno."""
    total = 0
    for channel in channels:
        total += await spam_channel(channel, content, times, concurrency=concurrency)
    return total


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
        activity=discord.Activity(
            type=ACTIVITY_TYPES.get(kind, discord.ActivityType.playing), name=text),
    )
