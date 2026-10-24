"""Asistentes paso a paso para las acciones destructivas."""
from __future__ import annotations

from src import menu, ui

MAX_CHANNELS = 50


async def nuke_wizard(client, guild) -> dict | None:
    ui.title("Asistente de NUKE")
    ui.kv("Servidor", f"{guild.name}  ({guild.id})")
    ui.plain("Enter acepta el valor por defecto.")
    print()

    options = {}

    options["guild_name"] = await menu.ask(
        "1/9  Nombre del servidor", default=f"nuked by {client.user.name}")

    options["channel_name"] = await menu.ask(
        "2/9  Nombre base de los canales", default="nuke")

    icon = await menu.ask(
        "3/9  Foto del servidor (ruta o URL)", optional=True)
    options["icon"] = icon or ""

    options["spam_message"] = await menu.ask(
        "4/9  Mensaje de spam", default="Nuked.")

    options["spam_times"] = await menu.ask_int(
        "5/9  Veces que repetir el mensaje", default=5, minimum=0, maximum=100)

    options["spam_all_channels"] = await menu.ask_bool(
        "6/9  Spam en TODOS los canales nuevos", default=False)

    channels_count = await menu.ask_int(
        f"7/9  Numero de canales (max {MAX_CHANNELS})", default=15,
        minimum=1, maximum=MAX_CHANNELS)
    options["text_count"] = channels_count

    options["voice_count"] = await menu.ask_int(
        "8/9  Canales de voz", default=3, minimum=0,
        maximum=max(0, MAX_CHANNELS - channels_count))

    options["ban_all"] = await menu.ask_bool(
        "9/9  Banear a todos los miembros", default=False)

    print()
    ui.title("Resumen")
    ui.kv("Servidor", options["guild_name"])
    ui.kv("Canales", options["channel_name"] + "-1 ... " + options["channel_name"]
                        + f"-{channels_count}")
    ui.kv("Voz", options["voice_count"])
    ui.kv("Foto", icon or "sin cambios")
    ui.kv("Spam", f'"{options["spam_message"]}" x{options["spam_times"]}'
                  + (" (todos los canales)" if options["spam_all_channels"] else " (1er canal)"))
    ui.kv("Banear", "si" if options["ban_all"] else "no")
    print()

    if not await menu.ask_bool("Ejecutar el nuke", default=True):
        return None
    return options


async def spam_wizard(guild) -> dict | None:
    ui.title("Asistente de SPAM")
    ui.kv("Servidor", guild.name)
    print()

    channel = await menu.choose_channel(guild, "text")
    if not channel:
        return None

    message = await menu.ask("Mensaje a enviar", default="Spam")
    times = await menu.ask_int("Cuantas veces", default=10, minimum=1, maximum=200)

    print()
    ui.kv("Canal", "#" + channel.name)
    ui.kv("Mensaje", message)
    ui.kv("Veces", times)
    print()

    if not await menu.ask_bool("Enviar", default=True):
        return None
    return {"channel": channel, "message": message, "times": times}


async def dm_wizard(guild) -> dict | None:
    """Asistente del DM masivo: mensaje, repeticiones y limite de miembros."""
    ui.title("Asistente de DM masivo")
    ui.kv("Servidor", guild.name)
    print()

    message = await menu.ask("Mensaje a enviar", default="Nuked.")

    times = await menu.ask_int(
        "Cuantas veces se envia a cada miembro", default=1, minimum=1, maximum=20)

    limit = await menu.ask_int(
        "Limite de miembros (0 = todos)", default=0, minimum=0, maximum=10000)

    print()
    ui.kv("Mensaje", message)
    ui.kv("Por miembro", times)
    ui.kv("Miembros", limit or "todos")
    print()

    if not await menu.ask_bool("Enviar los DMs", default=True):
        return None
    return {"message": message, "times": times, "limit": limit}
