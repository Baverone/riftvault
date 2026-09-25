"""Os links de compra — Cardmarket e CardTrader —, num sítio só.

Nasceu a 2026-09-25, quando o André pediu links de compra no separador
«Produto Selado» (*"Se possivel, mete link para compra no cardmarket e no
cardtrader"*). Os dois templates do Cardmarket já existiam, mas viviam no
`venda.py` (2026-09-25, de tarde) — uma chave de config com nome de UMA aba a
responder a uma pergunta que agora é de duas. Mudaram-se para aqui, no bloco
`mercados` do config, e o `venda.py` passou a ler por esta porta.

    **Um config escrito antes de hoje continua a valer**: se `venda` trouxer
    `cardmarket_url` ou `cardmarket_busca` e o `mercados` não as escrever, são
    elas que mandam (`opcoes`). Com as duas escritas ganha a nova, que é a
    regra das outras migrações do config (ver `config._migrar_master_set`).

O CARDTRADER ESTÁ VALIDADO; O CARDMARKET NÃO — e é a diferença que interessa
    Medido a 2026-09-25, da máquina dele:

    | pedido | resposta |
    |---|---|
    | `cardtrader.com/robots.txt` | **200** — só proíbe `/uploads/` (e permite `/uploads/blueprints/`), e publica os sitemaps |
    | `sitemaps/en/blueprint_products*.xml.gz` | 7 ficheiros, 348 780 URLs, todos `…/en/cards/<blueprint_id>-<slug>` |
    | `www.cardtrader.com/en/cards/330791` | **200**, redirecciona para `…/330791-origins-booster-box-origins` |
    | `www.cardtrader.com/en/cards/999999999` | **404** (o formato é mesmo verificado) |
    | `www.cardtrader.com/en/search?q=Origins%20Booster%20Box` | **200**, com o produto na página |
    | `www.cardmarket.com/robots.txt` | **403** (Cloudflare, «Just a moment…») |

    Ou seja: o link do CardTrader **não é presunção** — o id sozinho chega, e
    é o próprio site que lhe acrescenta o slug. O `/en/` faz falta: sem ele
    (`cardtrader.com/cards/<id>`, que era o que o `a_subir` escrevia desde
    2026-09-08) a página abre em **italiano**.

    O do Cardmarket continua **NÃO VALIDADO** — o site responde 403 a
    qualquer pedido automático, nem sequer o `robots.txt` responde, e não há
    conta para experimentar. Não se contorna: é dado e segue. Por isso cada
    linha leva DOIS links, como na Venda — o directo por id e um de
    **pesquisa** pelo nome, que funciona mesmo que o primeiro abra em 404.

    O produto selado tem template próprio (`cardmarket_url_selado`): um
    display **não é um Single**, e escrever-lhe o caminho `Products/Singles`
    era dizer no URL uma coisa que se sabe falsa. O que identifica o produto
    é o `idProduct`; o caminho é a categoria deles, e é a parte que se
    presume. Se abrir em 404 muda-se esta linha e todos os links mudam com
    ela.

SEM ID NÃO SE INVENTA UM: PESQUISA-SE
    Um produto sem `cardmarket_id` (hoje 46 dos 98 do selado) ou sem
    `blueprint_id` (os 17 do `selado.extra`, que a API não tem) leva o link de
    **pesquisa pelo nome** nesse mercado, marcado como tal. Nunca se mostra um
    link directo montado com um id que não existe.
"""

from __future__ import annotations

from urllib.parse import quote

from . import config

DEFAULTS: dict = {
    # CARDMARKET — os dois primeiros vieram do `venda` (2026-09-25). `{id}` é
    # o `cardmarket_id`: no caso das cartas, o do `cardtrader_map` (1178 das
    # 1179 impressões têm um); no do selado, o `card_market_ids` do blueprint.
    # NÃO VALIDADOS (403 a pedidos automáticos) — ver o cabeçalho.
    "cardmarket_url": "https://www.cardmarket.com/en/Riftbound/Products/Singles?idProduct={id}",
    # O mesmo para PRODUTO SELADO, que não é um «Single» — ver o cabeçalho.
    "cardmarket_url_selado": "https://www.cardmarket.com/en/Riftbound/Products?idProduct={id}",
    # A pesquisa pelo nome: o segundo link de cada linha, e o único de quem
    # não tem id. `{q}` vai codificado para URL.
    "cardmarket_busca": "https://www.cardmarket.com/en/Riftbound/Products/Search?searchString={q}",
    # CARDTRADER — VALIDADOS a 2026-09-25 (ver o cabeçalho). `{id}` é o
    # `blueprint_id`; o site acrescenta-lhe o slug sozinho.
    "cardtrader_url": "https://www.cardtrader.com/en/cards/{id}",
    "cardtrader_busca": "https://www.cardtrader.com/en/search?q={q}",
}

# Que campo é que cada template pede. Um template sem ele rebenta — um link
# montado com o placeholder por substituir abria sempre na mesma página.
_PEDE = {
    "cardmarket_url": "{id}",
    "cardmarket_url_selado": "{id}",
    "cardmarket_busca": "{q}",
    "cardtrader_url": "{id}",
    "cardtrader_busca": "{q}",
}

# As duas chaves que viviam no bloco `venda` até 2026-09-25.
_DO_VENDA = ("cardmarket_url", "cardmarket_busca")


def opcoes(cfg: dict | None = None) -> dict:
    cfg = cfg if cfg is not None else config.load()
    bruto = cfg.get("mercados") or {}
    if not isinstance(bruto, dict):
        raise ValueError("mercados: tem de ser um objecto")
    bruto = {k: v for k, v in bruto.items() if not k.startswith("_")}
    out = {**DEFAULTS, **bruto}
    # Compatibilidade: um config escrito antes de hoje tem estas duas no
    # bloco `venda`. Ficam a valer o que valiam; com as duas escritas ganha a
    # nova, como nas outras migrações do config.
    #
    # Compara-se com o DEFAULT e não com «está escrita no ficheiro»: o
    # `config.load` funde por chave de topo, por isso `cfg["mercados"]` traz
    # sempre o bloco inteiro dos defaults, esteja ou não no ficheiro dele.
    velho = cfg.get("venda") or {}
    if isinstance(velho, dict):
        for k in _DO_VENDA:
            if k in velho and out.get(k) == DEFAULTS[k]:
                out[k] = velho[k]
    for k, marca in _PEDE.items():
        v = out.get(k)
        if not isinstance(v, str) or marca not in v:
            raise ValueError(f"mercados.{k}: tem de ser um endereço com {marca} "
                             f"lá dentro (está {v!r})")
    return out


def _busca(template: str, nome: str) -> str:
    return template.format(q=quote(nome or "", safe=""))


def cardmarket(nome: str, id_cm=None, *, selado: bool = False,
               op: dict | None = None, cfg: dict | None = None) -> dict:
    """O link do Cardmarket: directo se houver id, pesquisa se não houver."""
    op = op or opcoes(cfg)
    chave = "cardmarket_url_selado" if selado else "cardmarket_url"
    if id_cm:
        return {"url": op[chave].format(id=id_cm), "pesquisa": False}
    return {"url": _busca(op["cardmarket_busca"], nome), "pesquisa": True}


def cardmarket_busca(nome: str, op: dict | None = None,
                     cfg: dict | None = None) -> str:
    return _busca((op or opcoes(cfg))["cardmarket_busca"], nome)


def cardtrader(nome: str, blueprint_id=None, *, op: dict | None = None,
               cfg: dict | None = None) -> dict:
    """O link do CardTrader: o `blueprint_id` sozinho chega (validado)."""
    op = op or opcoes(cfg)
    if blueprint_id:
        return {"url": op["cardtrader_url"].format(id=blueprint_id), "pesquisa": False}
    return {"url": _busca(op["cardtrader_busca"], nome), "pesquisa": True}


def cardtrader_busca(nome: str, op: dict | None = None,
                     cfg: dict | None = None) -> str:
    return _busca((op or opcoes(cfg))["cardtrader_busca"], nome)


def links(nome: str, *, cardmarket_id=None, blueprint_id=None,
          selado: bool = False, op: dict | None = None,
          cfg: dict | None = None) -> dict:
    """Os dois links de uma linha, para o frontend não ter de os montar.

    Cada um diz se é `pesquisa` — a página escreve-o, em vez de fingir que um
    link de pesquisa é a página do produto.
    """
    op = op or opcoes(cfg)
    return {
        "cardmarket": cardmarket(nome, cardmarket_id, selado=selado, op=op),
        "cardtrader": cardtrader(nome, blueprint_id, op=op),
    }
