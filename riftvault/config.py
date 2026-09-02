"""Caminhos do projeto e leitura do riftvault_config.json.

Tudo o que está no config é conhecimento do André ou palpite meu — nada disto
vem da API da RiftScribe. Ver CLAUDE.md, "Superfícies NÃO validadas".
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "riftvault"
WEB_DIR = PKG / "web"

# Dá para apontar as bases para outro sítio sem mexer no código (à mtgvault).
DATA_DIR = Path(os.environ.get("RIFTVAULT_DATA", ROOT / "data"))
VAULT_DB = Path(os.environ.get("RIFTVAULT_DB", DATA_DIR / "vault.db"))
CATALOG_DB = Path(os.environ.get("RIFTVAULT_CATALOG", DATA_DIR / "catalog.db"))
PRICES_DB = Path(os.environ.get("RIFTVAULT_PRICES", DATA_DIR / "prices.db"))
IMAGES_DIR = Path(os.environ.get("RIFTVAULT_IMAGES", DATA_DIR / "images"))
DECKS_DIR = Path(os.environ.get("RIFTVAULT_DECKS", ROOT / "decks"))
CONFIG_PATH = Path(os.environ.get("RIFTVAULT_CONFIG", ROOT / "riftvault_config.json"))

# Usados quando o ficheiro de config não existe ou não tem a chave.
DEFAULTS: dict = {
    "sets": {},
    "playset_targets_by_type": {
        "Unit": 3,
        "Spell": 3,
        "Gear": 3,
        "Battlefield": 1,
        "Legend": 1,
        "Rune": 12,
        "default": 3,
    },
    "master_targets_by_variant": {
        "base": 3,
        "alt_art": 1,
        "signature": 1,
        "rune_promo": 1,
        "special": 1,
    },
    "token_target": 1,
    "master_ignorar_variantes": ["alt_art"],
    "master_base_follows_type": True,
    "master_target_overrides": {},
    "token_card_keys": [],
    "faltas_ignorar_tipos": ["Rune"],
    "pimp_ignorar_tipos": ["signature", "rune_promo"],
    "price_badge_min_cents": 100,
    "image_size": "medium",
    "static_images": "remote",
}


@lru_cache(maxsize=1)
def load() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        # As chaves "_..." são notas para humanos; não são configuração.
        cfg.update({k: v for k, v in raw.items() if not k.startswith("_")})
    return cfg


def reload() -> dict:
    load.cache_clear()
    return load()


def set_name(set_id: str) -> str:
    return (load().get("sets", {}).get(set_id) or {}).get("name") or set_id


def set_order(set_id: str) -> int:
    # Edições que ainda não estão no config vão para o fim, por ordem alfabética.
    return (load().get("sets", {}).get(set_id) or {}).get("order") or 999


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    DECKS_DIR.mkdir(parents=True, exist_ok=True)
