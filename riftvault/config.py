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
    # O alvo de COLEÇÃO por tipo, onde difere do playset jogável (o que não
    # estiver aqui segue o `playset_targets_by_type`). Só a runa: joga-se com
    # 12 no Rune Pool, coleciona-se a 3 (André, 2026-09-15: "as runas que estao
    # no masterset […] vamos ate 3 como as outras cartas"). Ver
    # `metrics.alvo_do_tipo`.
    "master_targets_by_type": {"Rune": 3},
    "token_target": 1,
    # As três categorias da Coleção (André, 2026-09-14, à noite: "só quero % de
    # completo para masterset! o que é Alt Art e Overnumbered, etc etc é
    # puramente coleção"), escritas como ele fala — pelo sufixo do código ou
    # pela palavra dele:
    #   `fora_da_percentagem` — a coleção extra: aparece, pede o playset, não
    #                           conta para a percentagem. As artes alternativas
    #                           (`a`), as sobrenumeradas (2026-09-10) e as
    #                           promos `VEN-SP` (2026-09-10).
    #   `escondidas`          — nem aparece: os tokens `-T`, as signatures `*`
    #                           (2026-09-11: "nunca vou colocar nenhuma, não
    #                           vale a pena estarem lá") e as runas SEM
    #                           numeração de master set, as promo `-R`
    #                           (2026-09-15: "Saiem as runas todas e deixam de
    #                           contar para masterset […] menos as que tem
    #                           numeração de masterset"). As runas numeradas —
    #                           a base e a arte alternativa do OGN — ficam onde
    #                           estavam, e desde essa tarde pedem 3 como o
    #                           resto (`master_targets_by_type`).
    #   `um_de_cada`          — o que pede 1 em vez do playset do tipo: as
    #                           sobrenumeradas e as promos (2026-09-15:
    #                           "overnumbered e promos (SP) voltamos a 1 de
    #                           cada / se eu tiver mais adiciono na mesma").
    #                           Só o ALVO; o bloco e a percentagem não mexem.
    #                           As artes alternativas ficam a playset.
    # `fora` é o nome antigo da primeira (2026-09-08 a 2026-09-14) e continua a
    # ser lido. Ver `metrics._fora`, `metrics.escondida`, `metrics.e_master` e
    # `metrics.e_um_de_cada`.
    "master_set": {"fora_da_percentagem": ["a", "overnumbered", "promo"],
                   "escondidas": ["-T", "*", "-R"],
                   "um_de_cada": ["overnumbered", "promo"]},
    # O bloco das runas especiais ("1 runa especial de cada para cada set",
    # 2026-09-08) — só o BLOCO. O `alvo` que aqui vivia (1, "runas 1 de cada")
    # deixou de ser lido a 2026-09-15: as runas pedem o alvo do tipo, como
    # tudo o resto. Ver `metrics.RUNA_ESPECIAL`.
    "runas_especiais": {"tipos": ["Rune"], "excepto": ["base"]},
    # `master_targets_by_variant`, `master_variantes_playset` e
    # `master_base_follows_type` deixaram de ser lidos a 2026-09-14: o alvo é
    # o do tipo em todos os blocos, menos o `um_de_cada` (`metrics.master_target`).
    "master_target_overrides": {},
    # As listas de compra («A subir», «Master set», as wantlists por edição e
    # por nível) são SÓ o master set (André, 2026-09-15: "sobrenumeradas não
    # entram na wantlist, nem na % de coleção completa; apenas pedi para ser
    # feito track de playset para eu saber exatamente quantas tenho"). A
    # coleção extra tem alvo para se VER, não para se comprar. Ver
    # `a_subir.so_master_set`.
    "listas_de_compra": {"so_master_set": True},
    # O separador «Quanto custa» (2026-09-15): um botão por edição do catálogo,
    # menos estas — o OGS (Proving Grounds) a pedido dele. Ver
    # `a_subir.edicoes_quanto_custa`.
    "quanto_custa": {"sem_edicoes": ["OGS"],
                     # Dentro de cada edição, quantas se mostram por raridade
                     # (2026-09-15: "o top5 de mais caras de comuns, e top5 de
                     # incomuns, e top5 de Raras"); as que não estão aqui — as
                     # épicas — mostram-se todas. Ver `a_subir.top_por_raridade`.
                     "top_por_raridade": 5,
                     "raridades_com_top": ["rare", "uncommon", "common"]},
    # As línguas cujas ofertas do CardTrader entram no preço (2026-09-15:
    # "apenas cartas versao ingles"). Era 'en' fixo no código desde o início.
    "precos": {"linguas": ["en"]},
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
    """Os nomes antigos da lista do que não conta para a percentagem.

    `master_ignorar_variantes` (até 2026-09-08) e `master_set.fora` (até
    2026-09-14) eram os nomes do que hoje é `master_set.fora_da_percentagem`.
    Um ficheiro escrito com um deles continua a mandar — a lista só se traduz
    para o nome novo, e vale o que valia: fora da percentagem, mas na página.
    Se o ficheiro trouxer o nome novo, é esse que ganha. A tradução vive aqui e
    não no `metrics` para haver uma leitura só do config.

    A partir do que o FICHEIRO diz, não dos defaults: um `master_set` escrito
    no ficheiro substitui o default inteiro (é o `cfg.update`), e o nome antigo
    não pode herdar o `escondidas` de omissão — esse ficheiro não escondia nada.
    """
    ms = raw.get("master_set") or {}
    if ms.get("fora_da_percentagem") is not None:
        return
    antigo = ms.get("fora")
    if antigo is None:
        antigo = raw.get("master_ignorar_variantes")
    if antigo is None:
        return
    cfg["master_set"] = {**ms, "fora_da_percentagem": list(antigo)}


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
