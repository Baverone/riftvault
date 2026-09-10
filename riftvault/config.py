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
    # Fora da coleção (André, 2026-09-08): escreve-se pelo sufixo do código, que
    # é como ele fala. Hoje o `-T` dos tokens, o `*` das signatures e as
    # `overnumbered` — as artes alternativas voltaram para dentro com alvo 1
    # ("no fim 1 alt art de cada"), as signatures saíram a 2026-09-09 ("das
    # coleções tira as signatures, fazemos 1 Alt Art de cada mas as signature
    # não") e as sobrenumeradas a 2026-09-10 ("também não quero para a coleção
    # as overnumbered"). Ver `metrics._fora` e `metrics.e_master`.
    "master_set": {"fora": ["-T", "*", "overnumbered"]},
    # O bloco 2 da Coleção: "1 runa especial de cada para cada set".
    "runas_especiais": {"tipos": ["Rune"], "excepto": ["base"], "alvo": 1},
    # Vazio desde 2026-09-08: as artes alternativas pedem 1, não o playset.
    "master_variantes_playset": [],
    "master_base_follows_type": True,
    "master_target_overrides": {},
    "token_card_keys": [],
    "faltas_ignorar_tipos": ["Rune"],
    "pimp_ignorar_tipos": ["signature", "rune_promo"],
    "pimp_ignorar_impressoes": ["unl-238-219"],
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
        _migrar_master_set(raw, cfg)
        _migrar_a_subir(raw, cfg)
    return cfg


def _migrar_master_set(raw: dict, cfg: dict) -> None:
    """`master_ignorar_variantes` era o nome antigo do `master_set.fora`.

    Um ficheiro escrito antes de 2026-09-08 continua a mandar — a lista só se
    traduz para o nome novo. Se o ficheiro trouxer os dois, o novo ganha: é o
    que lá está escrito por último. A tradução vive aqui e não no `metrics`
    para haver uma leitura só do config.
    """
    antigo = raw.get("master_ignorar_variantes")
    if antigo is None or (raw.get("master_set") or {}).get("fora") is not None:
        return
    cfg["master_set"] = {**(cfg.get("master_set") or {}), "fora": list(antigo)}


def _migrar_a_subir(raw: dict, cfg: dict) -> None:
    """`a_subir.excluir_tipos` era o nome antigo do `a_subir.excluir.tipos`.

    Passou a haver dois critérios a 2026-09-08, quando o André mandou tirar
    também os showcases: a signature é uma VARIANTE e o showcase é uma
    RARIDADE, e uma lista só não dizia as duas coisas.

    Um ficheiro escrito antes disso continua a mandar, **e a valer exatamente o
    que valia**: `raridades` fica vazia de propósito, porque o ficheiro antigo
    não excluía raridade nenhuma. Quem quiser os showcases fora escreve a chave
    nova. Se o ficheiro trouxer as duas, a nova ganha.
    """
    bruto = raw.get("a_subir") or {}
    antigo = bruto.get("excluir_tipos")
    if antigo is None or bruto.get("excluir") is not None:
        return
    cfg["a_subir"] = {**bruto, "excluir": {"tipos": list(antigo), "raridades": []}}


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
