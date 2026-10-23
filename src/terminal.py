"""Lector unico de stdin compartido entre el menu y los asistentes."""
from __future__ import annotations

import asyncio
import sys
import threading


class Terminal:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._loop = None
        self._thread = None

    def start(self) -> None:
        if self._thread:
            return
        self._loop = asyncio.get_running_loop()

        def reader():
            while True:
                try:
                    line = input()
                except EOFError:
                    line = None
                except KeyboardInterrupt:
                    continue
                try:
                    self._loop.call_soon_threadsafe(self._queue.put_nowait, line)
                except RuntimeError:
                    return

        self._thread = threading.Thread(target=reader, daemon=True)
        self._thread.start()

    def write(self, text: str) -> None:
        sys.stdout.write(text)
        sys.stdout.flush()

    async def read(self, prompt: str = "") -> str:
        self.write(prompt)
        line = await self._queue.get()
        return "" if line is None else line

    async def read_until(self, prompt: str, should_yield, poll: float = 0.15):
        """Lee una linea, pero cede el turno si should_yield() es True y nadie escribio."""
        self.write(prompt)
        while True:
            if should_yield() and self._queue.empty():
                return None
            try:
                line = await asyncio.wait_for(self._queue.get(), timeout=poll)
                return "" if line is None else line
            except asyncio.TimeoutError:
                continue


term = Terminal()
