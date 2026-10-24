"""Lectura y escritura de config.json."""
from __future__ import annotations

import json
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "config.json"

DEFAULTS = {
    "token": "",
    "default_guild": "",
    "auto_nuke": False,
    "auto_target": "",
    "nuke": {
        "guild_name": "",
        "role_name": "nuked",
        "channel_name": "nuke",
        "category_name": "NUKE",
        "icon": "",
        "text_count": 15,
        "voice_count": 3,
        "delete_roles": True,
        "delete_channels": True,
        "delete_emojis": True,
        "delete_stickers": True,
        "ban_all": False,
        "spam_message": "Nuked.",
        "spam_times": 5,
        "spam_all_channels": False,
        "concurrency": 3,
    },
}


def load_config() -> dict:
    try:
        raw = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return json.loads(json.dumps(DEFAULTS))

    cfg = json.loads(json.dumps(DEFAULTS))
    cfg.update({k: v for k, v in raw.items() if k != "nuke"})
    cfg["nuke"].update(raw.get("nuke") or {})
    return cfg


def save_config(cfg: dict) -> None:
    FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
