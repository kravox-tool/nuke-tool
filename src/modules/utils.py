"""Utilidades comunes."""
from __future__ import annotations

import asyncio


async def pool(items, worker, limit: int = 3):
    """Ejecuta worker(item, index) con concurrencia limitada.

    Nunca lanza excepciones: los fallos se devuelven como None.
    """
    items = list(items)
    if not items:
        return []

    results = [None] * len(items)
    sem = asyncio.Semaphore(max(1, limit))

    async def run(index, item):
        async with sem:
            try:
                results[index] = await worker(item, index)
            except Exception:
                results[index] = None

    await asyncio.gather(*(run(i, item) for i, item in enumerate(items)))
    return results


def human(n) -> str:
    try:
        return f"{int(n):,}".replace(",", ".")
    except Exception:
        return str(n)
