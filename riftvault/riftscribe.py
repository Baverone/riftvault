"""Cliente da API pública da RiftScribe.

Validado a 2026-08-31 contra https://riftscribe.gg/api — ver CLAUDE.md.
Sem autenticação. `limit` máximo é 200 e o total vem no header X-Total-Count.
"""

from __future__ import annotations

import time
from typing import Iterator

import requests

BASE = "https://riftscribe.gg/api"
MAX_LIMIT = 200          # imposto pela spec (maximum: 200)
POLITE_DELAY = 1.0       # a API não documenta rate-limit; por educação, 1 pedido/s
TIMEOUT = 30

_session = requests.Session()
# SÓ ASCII no User-Agent: com acentos há servidores que respondem 403 (o
# CardTrader faz isso). A RiftScribe aceitava, mas não vale a pena arriscar.
_session.headers.update(
    {"User-Agent": "riftvault/0.1 (personal collection manager; non-commercial)"}
)


class RiftScribeError(RuntimeError):
    pass


def _get(path: str, params: dict | None = None) -> requests.Response:
    url = f"{BASE}{path}"
    try:
        resp = _session.get(url, params=params, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise RiftScribeError(f"falhou o pedido a {url}: {exc}") from exc
    if resp.status_code != 200:
        raise RiftScribeError(f"{url} devolveu HTTP {resp.status_code}")
    return resp


def filters() -> dict:
    """/api/cards/filters -> {sets, factions, rarities, types}."""
    return _get("/cards/filters").json()


def list_sets() -> list[str]:
    return list(filters().get("sets") or [])


def count_cards(set_id: str) -> int:
    resp = _get("/cards", {"set_id": set_id, "limit": 1, "offset": 0})
    return int(resp.headers.get("X-Total-Count", 0))


def iter_cards(set_id: str, delay: float = POLITE_DELAY) -> Iterator[dict]:
    """Todas as entradas de uma edição, na ordem `sort=default`.

    Essa ordem já coloca cada variante logo a seguir à carta base a que
    pertence — é a ordem que a grelha do site quer. Ver CLAUDE.md.
    """
    offset = 0
    total: int | None = None
    while True:
        resp = _get(
            "/cards",
            {"set_id": set_id, "limit": MAX_LIMIT, "offset": offset, "sort": "default"},
        )
        if total is None:
            total = int(resp.headers.get("X-Total-Count", 0))
        page = resp.json()
        if not page:
            return
        yield from page
        offset += len(page)
        if total and offset >= total:
            return
        if delay:
            time.sleep(delay)


def card(card_id: str) -> dict:
    """/api/cards/{card_id} — aceita OGN-7, OGN-007a, OGN-301-star, UNL-T03."""
    return _get(f"/cards/{card_id}").json()


def download(url: str) -> bytes:
    try:
        resp = _session.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise RiftScribeError(f"falhou a imagem {url}: {exc}") from exc
    if resp.status_code != 200:
        raise RiftScribeError(f"imagem {url} devolveu HTTP {resp.status_code}")
    return resp.content
