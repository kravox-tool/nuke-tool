"""Interfaz de terminal: banner, colores y helpers de salida."""
from __future__ import annotations

import shutil
import sys
import threading
import time

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
CLEAR = "\x1b[2J\x1b[H"

PALETTE = ["#8B5CF6", "#A855F7", "#C084FC", "#D946EF", "#EC4899", "#F472B6", "#FB7185"]


def _rgb(hexcode: str):
    h = hexcode.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def fg(hexcode: str) -> str:
    """Devuelve el codigo ANSI truecolor para un hex."""
    r, g, b = _rgb(hexcode)
    return f"\x1b[38;2;{r};{g};{b}m"


class C:
    BRAND = fg("#A855F7")
    ACCENT = fg("#22D3EE")
    OK = fg("#34D399")
    WARN = fg("#FBBF24")
    ERROR = fg("#F87171")
    MUTED = fg("#6B7280")
    TEXT = fg("#E5E7EB")
    BOLD = BOLD


FALLBACK_ART = r"""
  _   _ _   _ _  __ _____   _____ ___  ___  _
 | \ | | | | | |/ /| ____| |_   _/ _ \|  _ \| |
 |  \| | | | | ' / |  _|     | || | | | | | | |
 | |\  | |_| | . \ | |___    | || |_| | |_| | |___
 |_| \_|\___/|_|\_\|_____|   |_| \___/|____/|_____|
"""


def paint(text: str, palette=None) -> str:
    palette = palette or PALETTE
    out = []
    for i, ch in enumerate(text):
        out.append(fg(palette[i % len(palette)]) + ch)
    return "".join(out) + RESET


def divider(width: int = 60) -> str:
    return C.MUTED + "\u2500" * width + RESET


def _build_art() -> str:
    try:
        import pyfiglet

        for font in ("ansi_shadow", "standard"):
            try:
                art = pyfiglet.figlet_format("NUKE", font=font)
                if art and art.strip():
                    return art
            except Exception:
                continue
    except ImportError:
        pass
    return FALLBACK_ART


def print_banner(version: str = "1.0.0") -> None:
    art = _build_art()
    sys.stdout.write(CLEAR)
    print()
    for i, line in enumerate(art.splitlines()):
        if not line.strip():
            continue
        palette = PALETTE[i % 2:] + PALETTE[: i % 2]
        print("  " + paint(line, palette))
    print("  " + C.ACCENT + "Discord Server Destroyer" + RESET + C.MUTED + f"  v{version}" + RESET)
    print("  " + divider(56))
    print("  " + C.MUTED + "escribe " + RESET + C.BRAND + "help" + RESET
          + C.MUTED + " para ver los comandos" + RESET + C.MUTED + " \u00b7 " + RESET
          + C.BRAND + "exit" + RESET + C.MUTED + " para salir" + RESET)
    print("  " + divider(56))
    print()


def ok(msg) -> None:
    print("  " + C.OK + "\u2714" + RESET + " " + C.TEXT + str(msg) + RESET)


def warn(msg) -> None:
    print("  " + C.WARN + "\u25b2" + RESET + " " + C.TEXT + str(msg) + RESET)


def error(msg) -> None:
    print("  " + C.ERROR + "\u2716" + RESET + " " + C.TEXT + str(msg) + RESET)


def info(msg) -> None:
    print("  " + C.ACCENT + "\u203a" + RESET + " " + C.TEXT + str(msg) + RESET)


def step(msg) -> None:
    print("  " + C.BRAND + "\u2192" + RESET + " " + C.MUTED + str(msg) + RESET)


def plain(msg) -> None:
    print("  " + C.TEXT + str(msg) + RESET)


def title(text: str) -> None:
    print()
    print("  " + C.BOLD + paint(text.upper()) + RESET)
    print("  " + divider(56))


def kv(key: str, value) -> None:
    print("  " + C.MUTED + str(key).ljust(14) + RESET + " " + C.TEXT + str(value) + RESET)


def table_row(index, name, extra="") -> None:
    print("  " + C.BRAND + str(index).rjust(2) + RESET + "  "
          + C.TEXT + str(name) + RESET + C.MUTED + str(extra) + RESET)


class Spinner:
    """Animacion de carga en hilo aparte."""

    FRAMES = "\u280b\u2819\u2839\u2838\u283c\u2834\u2826\u2827\u2807\u280f"

    def __init__(self, text: str):
        self.text = text
        self._stop = threading.Event()
        self._thread = None
        self._start = 0.0
        self._width = len(text) + 22

    def start(self) -> "Spinner":
        self._start = time.time()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def _loop(self) -> None:
        i = 0
        while not self._stop.is_set():
            elapsed = int(time.time() - self._start)
            frame = self.FRAMES[i % len(self.FRAMES)]
            sys.stdout.write("\r  " + C.BRAND + frame + RESET + " " + C.TEXT + self.text
                             + RESET + C.MUTED + f" {elapsed}s   " + RESET)
            sys.stdout.flush()
            i += 1
            self._stop.wait(0.08)

    def stop(self, final=None) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        sys.stdout.write("\r" + " " * self._width + "\r")
        if final:
            ok(final)

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc, tb):
        self.stop()
        return False


def terminal_width(default: int = 60) -> int:
    try:
        return min(shutil.get_terminal_size((default, 20)).columns, 100)
    except Exception:
        return default
