"""Prompts interactivos: lectura validada, seleccion de servidor y menus."""
from __future__ import annotations

from src import ui
from src.modules.utils import human
from src.terminal import term


async def _read(prompt: str) -> str:
    return await term.read(prompt)


def _label(prompt: str, default=None, optional: bool = False, suffix: str = "") -> str:
    hint = ""
    if default not in (None, ""):
        hint += f" [{default}]"
    if optional:
        hint += " (Enter = omitir)"
    return ("  " + ui.C.ACCENT + prompt + ui.RESET
            + ui.C.MUTED + hint + suffix + ui.RESET + " " + ui.C.BRAND + "\u276f " + ui.RESET)


async def ask(prompt: str, default=None, optional: bool = False):
    while True:
        raw = (await _read(_label(prompt, default, optional))).strip()
        if raw in ("", "-"):
            if optional:
                return None
            if default is not None:
                return default
        if raw and raw != "-":
            return raw
        ui.warn("Escribe un valor.")


async def ask_int(prompt: str, default: int, minimum: int, maximum: int,
                  optional: bool = False):
    while True:
        raw = (await _read(_label(f"{prompt} ({minimum}-{maximum})", default, optional))).strip()
        if raw in ("", "-"):
            if optional:
                return None
            if raw == "":
                return default
        if raw.lstrip("-").isdigit():
            value = int(raw)
            if minimum <= value <= maximum:
                return value
            ui.warn(f"Fuera de rango: {minimum}-{maximum}.")
            continue
        ui.warn("Numero invalido.")


async def ask_bool(prompt: str, default: bool = False) -> bool:
    default_text = "s" if default else "n"
    while True:
        raw = (await _read(_label(prompt + " (s/n)", default_text))).strip().lower()
        if raw == "":
            return default
        if raw in ("s", "si", "sí", "y", "yes", "1"):
            return True
        if raw in ("n", "no", "0"):
            return False
        ui.warn("Responde s o n.")


async def read_line(prompt: str, default=None) -> str:
    return (await _read(_label(prompt, default))).strip()


async def choose_guild(client, current_id=None, title: str = "Selecciona un servidor"):
    guilds = list(client.guilds)
    if not guilds:
        ui.error("El bot no esta en ningun servidor.")
        return None

    current_index = None
    print()
    ui.title(title)
    for i, guild in enumerate(guilds, start=1):
        if str(guild.id) == str(current_id):
            current_index = i
        mark = ui.C.OK + "   \u25c0 actual" + ui.RESET if str(guild.id) == str(current_id) else ""
        ui.table_row(i, guild.name, f"   ({human(guild.member_count or 0)} miembros)" + mark)
    print()

    while True:
        raw = (await _read(_label("Numero de servidor", current_index))).strip()
        if raw == "" and current_index:
            return guilds[current_index - 1]
        if raw.isdigit() and 1 <= int(raw) <= len(guilds):
            return guilds[int(raw) - 1]
        ui.warn(f"Escribe un numero entre 1 y {len(guilds)}.")


async def choose_channel(guild, kind: str = "text", limit: int = 25):
    import discord

    channels = [c for c in guild.channels if c.type == (
        discord.ChannelType.voice if kind == "voice" else discord.ChannelType.text)]
    if not channels:
        ui.error(f"No hay canales de {kind}.")
        return None
    channels = channels[:limit]

    print()
    ui.title(f"Canales de {kind}")
    for i, channel in enumerate(channels, start=1):
        ui.table_row(i, "#" + channel.name)
    print()

    while True:
        raw = (await _read(_label("Numero de canal", 1))).strip() or "1"
        if raw.isdigit() and 1 <= int(raw) <= len(channels):
            return channels[int(raw) - 1]
        ui.warn(f"Escribe un numero entre 1 y {len(channels)}.")


async def pause(text: str = "Enter para volver al menu") -> None:
    await _read("  " + ui.C.MUTED + text + ui.RESET + " ")
