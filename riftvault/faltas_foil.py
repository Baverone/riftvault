"""A metade das FOILS do separador «Faltas» (2026-09-27).

Palavras do André: *"quero as faltas separadas, as normais e as foils / as
foils nao sao faltas, sao apenas complemento e indicativo / mais tarde poderao
vir a ser compradas, entao preciso que tenham uma wantlist a parte"*. Sobre o
alvo: *"o alvo das foils e 3 de cada"* e, a precisar-se logo a seguir, *"no
caso, playset"*.

AS FOILS NÃO SÃO FALTAS — É A FRASE DELE, E É A REGRA
    Este bloco fica FORA de tudo o que já existe: fora da contagem de faltas
    (`faltas_edicao.totals`), fora da percentagem da Coleção e dos três níveis,
    fora das listas de compra que já existem (a wantlist do fim de cada edição,
    a «Wantlist — tudo», o «A subir») e fora dos quatro blocos. É
    «complemento e indicativo» — a palavra é dele.

    Isso não é uma promessa escrita num comentário: é ARQUITECTURA. O
    `faltas_edicao.py` não conhece este módulo nem a coluna `qty_foil`; as duas
    metades juntam-se aqui, no `payload_completo`, e a metade das normais vem de
    lá tal e qual. O `tests/test_faltas_foil.py` fotografa as normais com foils
    e sem foils e exige que fiquem iguais.

    A METADE DAS NORMAIS JÁ CONTA AS FOILS, e é outra coisa. Desde 2026-09-26
    (*"contabilizas tambem como parte do master set"*) o que uma impressão TEM,
    para os alvos da Coleção, é `qty + qty_foil` — uma foil tapa um buraco do
    master set. O que nasce hoje é a pergunta SIMÉTRICA e nova: «quantas foils
    me faltam para ter o playset EM FOIL». São duas contas diferentes sobre a
    mesma coluna, e nenhuma mexe na outra.

O ALVO É O PLAYSET DO TIPO — a função que já existe
    `metrics.playset_target` (`playset_targets_by_type`): Unit/Spell/Gear 3,
    Battlefield 1, Legend 1, **Rune 12**, token 1 (`token_target`). Não há alvo
    novo escrito em lado nenhum — reutiliza-se a tabela que já manda no playset
    jogável.

    A ORDEM DIZIA DUAS COISAS E ESCOLHEU-SE PELOS NÚMEROS. O texto dela nomeou
    o `metrics.alvo_do_tipo` (o alvo de COLEÇÃO do tipo, que dá **Rune 3** por
    causa do `master_targets_by_type`), mas a lista de alvos dela diz «Rune 12»,
    o `playset_targets_by_type` é a tabela do 12, e o total que ela mandou
    confirmar (1195 cópias, com 72 em runas = 6 runas × 12) só fecha com o 12.
    Fica o `playset_target`, e com ele uma diferença que se diz em voz alta:
    **numa runa o alvo em foil (12) não é o alvo da coleção normal (3)**. É a
    única divergência entre as duas metades, e é pergunta para ele.

O ÂMBITO É O DO CONTADOR DE FOIL — não há segundo âmbito
    `foil.no_ambito`: as impressões BASE, não sobrenumeradas, das raridades do
    `foil.raridades` (comuns e incomuns), fora as edições do
    `foil.edicoes_fora` (o OGS). É a mesma e única resposta à pergunta «esta
    impressão tem contagem de foil?» que o tile da grelha, o resumo, a rota e a
    CLI já fazem.

    DE RARA PARA CIMA NÃO SE LISTA NADA, e é a razão de fundo do âmbito ser
    este: em Riftbound as raridades acima de incomum só existem em foil — a
    carta normal É a foil. Listar «foils de raras» era duplicar a coleção
    inteira numa segunda lista.

    São **512 impressões** no `data/` de 2026-09-27, e nelas entram os **4
    tokens** que a API imprime como Unit (`OGN-271..274`, Recruit ×3 e Sprite):
    são base, comuns e não sobrenumerados, têm contador de foil na grelha desde
    2026-09-22, e por isso têm-no aqui — com o alvo deles, 1. A ordem media 508
    por os ter tirado à mão; preferiu-se não abrir um segundo âmbito por quatro
    impressões que o contador já conta (fica no relatório).

O PREÇO DE UMA FOIL É O PREÇO DA FOIL
    `metrics.precos_de_foil_map` (o `price_latest.price_foil_cents` de
    2026-09-26, à noite). Sem oferta foil no CardTrader a linha cai para o preço
    da NORMAL — e esse fallback conta-se e diz-se (`no_foil_price`), como no
    `prices.valor_dos_foils`: é ele que faz do total um PISO. Pôr o preço da
    normal em toda a lista sem dizer nada era subavaliá-la muito (a `OGN-045`
    Defy vale 1,25 € em normal e 5,02 € em foil).

O PENDENTE DE FOIL EXISTE DESDE 2026-09-27 — e é outro número
    Até esse dia não havia: a `pending` guardava a impressão e não o
    acabamento, e esta metade escrevia `pending = 0` em todas as linhas. Com os
    `+`/`−` a chegarem às Faltas (*"nas faltas, coloca o + e - para eu indicar
    que ja encomendei"*) a tabela ganhou a coluna `foil`, e uma foil
    encomendada é agora uma foil a caminho: `pending.open_qty(foil=True)`.

    SÃO DOIS PENDENTES DIFERENTES DA MESMA IMPRESSÃO, e não se somam. O da
    metade das normais é `open_qty()` (as normais) e não vê as foils; este é
    o das foils e não vê as normais. Uma foil a caminho não abate uma falta
    normal, nem o contrário — é a mesma separação das duas contagens do
    `copies` (2026-09-26).

    A linha continua VISÍVEL quando a encomenda cobre tudo o que falta (fica
    com `missing` 0 e marcada «a caminho»), como nas normais; o que sai é a
    wantlist, porque o que vem a caminho não se compra outra vez.

O AVISO QUE ELE PEDIU DE VOLTA
    As impressões em que ele TEM foil mas o playset das NORMAIS ainda está
    incompleto (`aviso_normais`). São as cartas em que a foil está a tapar um
    buraco: o tile da Coleção diz «3/3» porque a foil conta, e nas normais ele
    tem 2. **Não se decide nada sobre elas aqui** — mostram-se, contam-se, e a
    regra fica como está.
"""

from __future__ import annotations

import sqlite3

from . import cardmarket, config, faltas_edicao, foil, locais, metrics, pending

# O id e o rótulo desta metade. O id NÃO está no `faltas_edicao.BLOCO_LABEL`,
# de propósito: se lá estivesse entrava na ordem dos blocos, nos `totals` e no
# `scope.printings` das normais — que é exactamente o que ele não quer.
BLOCO = "foil"
LABEL = "Foils"

# O que o cabeçalho escreve por baixo do rótulo, onde os outros blocos dizem
# «playset» ou «1 de cada» (`metrics.alvo_do_bloco`).
ALVO_LABEL = "playset do tipo, em foil"


def alvo(printing, cfg: dict | None = None) -> int:
    """O alvo de foils de uma impressão: o PLAYSET DO TIPO.

    **Mora no `foil.alvo` desde a noite de 2026-09-27**, quando o contador do
    TILE passou a mostrar `foil M/T` e precisou do mesmo número: a pergunta é da
    mesma casa que o `foil.no_ambito`, e ter duas respostas era ter duas
    tabelas. Esta função fica como o nome por onde esta metade lhe chama.

    Continua a ser o `metrics.playset_target` (`playset_targets_by_type`):
    Unit/Spell/Gear 3, Battlefield 1, Legend 1, Rune 12, e `token_target` (1)
    nos tokens. Não é o `metrics.alvo_do_tipo` (o alvo de COLEÇÃO do tipo), e a
    diferença é só na runa — 12 aqui, 3 na coleção normal. Ver o topo.
    """
    return foil.alvo(printing, cfg)


def escopo(con: sqlite3.Connection, cfg: dict | None = None) -> dict[str, dict]:
    """printing_id -> a linha do catálogo com o `target`, das que têm foil.

    O âmbito é o do contador (`foil.no_ambito`); a linha vem inteira porque o
    item do separador precisa da imagem, da orientação e do rótulo da variante.
    """
    cfg = cfg or config.load()
    out: dict[str, dict] = {}
    for r in con.execute("SELECT * FROM catalog.printings ORDER BY set_id, api_sort"):
        if not foil.no_ambito(r, cfg):
            continue
        out[r["printing_id"]] = {**dict(r), "target": alvo(r, cfg)}
    return out


def _foils(con: sqlite3.Connection) -> dict[str, int]:
    """printing_id -> cópias FOIL. A única leitura da coluna nesta metade.

    Não passa pelo `locais`: os locais (`copy_locations`) contam normais, e onde
    está cada foil é pergunta que ele nunca fez. Aqui a pergunta é quantas tem.
    """
    return foil.qty_foil(con)


def em_falta(con: sqlite3.Connection, esc: dict[str, dict]) -> dict[str, dict]:
    """Do âmbito, quantas foils lhe faltam para o playset de cada impressão.

    O gémeo do `faltas_edicao.em_falta`, com uma diferença: o que ele TEM são
    as cópias foil, não a Coleção. O pendente é o das FOILS
    (`pending.open_qty(foil=True)`, 2026-09-27) — uma foil encomendada não é
    uma normal encomendada —, e trata-se como nas normais: fica à parte do
    `missing`, por isso a linha não desaparece quando ele carrega no `+`.

    Uma impressão com foils acima do alvo não aparece; uma com zero aparece a
    pedir o playset inteiro.
    """
    tem = _foils(con)
    a_caminho = pending.open_qty(con, foil=True)
    out: dict[str, dict] = {}
    for pid, info in esc.items():
        have = tem.get(pid, 0)
        curto = info["target"] - have
        if curto <= 0:
            continue
        pend = min(a_caminho.get(pid, 0), curto)
        out[pid] = {**info, "have": have, "pending": pend,
                    "missing": curto - pend, "short": curto}
    return out


def _item(pid: str, info: dict, preco: int | None, de_foil: bool, mkt: dict) -> dict:
    """Uma linha desta metade — a MESMA forma das normais (`faltas_edicao.item`).

    Só se acrescentam dois campos: `foil` (esta linha é de uma cópia foil, e por
    isso o filtro Foil do Cardmarket tem de ser ligado nela) e `price_is_foil` (o
    preço é o da foil, ou o da normal por não haver oferta foil — o PISO).

    O `foil_only` do gerador do Cardmarket vai a `True` em todas: nas normais
    quer dizer «o CardTrader só a lista em foil», e aqui quer dizer «esta
    entrada é foil». O efeito é o mesmo e é o que interessa — a página e a CLI
    dizem em que linhas ligar o filtro à mão, porque o foil NÃO se marca no
    texto da wantlist.
    """
    x = faltas_edicao.item(pid, info, preco, mkt)
    return {**x, "foil": True, "price_is_foil": de_foil, "foil_only": True}


def bloco(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """A metade das foils, por edição: `{block, sets, totals, scope, aviso_*}`.

    Cada entrada de `sets` tem a forma de um bloco do separador (id, rótulo,
    somas, `items`, `wantlist`), para o ecrã e a CLI desenharem as duas metades
    com o mesmo código. `in_lists` é **sempre False**: as foils não entram em
    lista de compra nenhuma que já exista.
    """
    cfg = cfg or config.load()
    esc = escopo(con, cfg)
    falta = em_falta(con, esc)
    mercado = cardmarket.versoes(con)
    precos = metrics.prices_map(con)
    precos_foil = metrics.precos_de_foil_map(con)

    por_set: dict[str, list[dict]] = {}
    ambito: dict[str, int] = {}
    for pid, info in esc.items():
        sid = info["set_id"]
        ambito[sid] = ambito.get(sid, 0) + 1
        if pid in falta:
            pf = precos_foil.get(pid)
            preco = pf if pf is not None else precos.get(pid)
            por_set.setdefault(sid, []).append(
                _item(pid, falta[pid], preco, pf is not None, mercado.get(pid) or {}))

    sets: dict[str, dict] = {}
    for sid in ambito:
        itens = sorted(por_set.get(sid, []), key=lambda x: (x["cn"], x["code"]))
        sets[sid] = {
            "id": BLOCO, "label": LABEL, "target_label": ALVO_LABEL,
            # As foils NUNCA entram nas listas de compra gerais. Não é um
            # botão de config: é a frase dele («não são faltas»).
            "in_lists": False,
            "scope": ambito[sid],
            **faltas_edicao.soma(itens),
            # Quantas linhas contam ao preço da NORMAL por não haver oferta
            # foil — o fallback que faz do total um PISO.
            "no_foil_price": sum(1 for x in itens
                                 if x["missing"] > 0 and x["price"] is not None
                                 and not x["price_is_foil"]),
            "items": itens,
            "wantlist": _wantlist_do_bloco(itens),
        }

    todos = [x for d in sets.values() for x in d["items"]]
    tem = _foils(con)
    rars, fora = foil.opcoes(cfg)
    return {
        "block": {"id": BLOCO, "label": LABEL, "target_label": ALVO_LABEL,
                  "in_lists": False},
        "sets": sets,
        "totals": {**faltas_edicao.soma(todos),
                   "no_foil_price": sum(d["no_foil_price"] for d in sets.values())},
        "scope": {
            "printings": sum(ambito.values()),
            # As foils que ele já tem, dentro do âmbito — para o cabeçalho
            # poder dizer «tens N de M» sem uma segunda conta.
            "owned": sum(n for pid, n in tem.items() if pid in esc),
            "owned_printings": sum(1 for pid in tem if pid in esc),
            "target": sum(info["target"] for info in esc.values()),
            "rarities": foil.raridades(cfg),
            "rarity_labels": {r: foil.RARIDADE_LABEL.get(r, r.capitalize())
                              for r in foil.raridades(cfg)},
            "sem_edicoes": sorted(fora),
        },
        "aviso_normais": aviso_normais(con, esc, cfg),
    }


def aviso_normais(con: sqlite3.Connection, esc: dict[str, dict] | None = None,
                  cfg: dict | None = None) -> list[dict]:
    """As impressões em que ele TEM foil e o playset das NORMAIS está incompleto.

    O aviso que ele pediu de volta. As normais são as da Coleção **sem as
    foils** (`locais.na_colecao(com_foil=False)`) — é o mesmo funil que a metade
    das normais usa, menos a parte que as foils lá metem desde 2026-09-26 — e o
    alvo é o da COLEÇÃO (`metrics.alvo`), o que o tile mostra.

    É a leitura de uma foil a tapar um buraco: o tile diz «3/3» porque a foil
    conta, e em normais ele tem 2. **Não se decide nada aqui** — só se mostra.
    """
    cfg = cfg or config.load()
    esc = esc if esc is not None else escopo(con, cfg)
    normais = locais.na_colecao(con, cfg, com_foil=False)
    tem = _foils(con)
    out = []
    for pid, info in esc.items():
        f = tem.get(pid, 0)
        if f <= 0:
            continue
        alvo_n = metrics.alvo(info, cfg)
        n = normais.get(pid, 0)
        if n >= alvo_n:
            continue
        out.append({"printing_id": pid, "name": info["name"],
                    "code": info["public_code"], "set": info["set_id"],
                    "cn": info["collector_number"],
                    "normais": n, "target": alvo_n, "foil": f})
    out.sort(key=lambda x: (config.set_order(x["set"]), x["set"], x["cn"]))
    return out


def _wantlist_do_bloco(itens: list[dict]) -> dict:
    """O resumo da wantlist desta metade — a QUINTA (2026-09-27).

    A mesma gramática das quatro por bloco de 2026-09-19: só o que há a
    comprar, o texto sai do `cardmarket.gerar` (o gerador único) e o cliente
    escreve o mesmo a partir dos `items`. `foil` são as linhas que precisam do
    filtro Foil ligado à mão — aqui, todas.
    """
    w = cardmarket.gerar([x for x in itens if x["missing"] > 0])
    return {"lines": w["lines"], "copies": w["copies"], "cents": w["cents"],
            "foil": len(w["foil"])}


def wantlist(con: sqlite3.Connection, set_id: str, cfg: dict | None = None,
             com_codigo: bool = False) -> dict:
    """A wantlist das foils de UMA edição — a quinta, «a parte» como ele pediu.

    Mesma forma da `faltas_edicao.wantlist`, para a CLI e o site não terem de
    saber qual das metades estão a pedir. **O texto não leva marca de foil**: no
    Cardmarket o foil é um filtro por entrada, posto na interface deles (é a
    regra de 2026-09-01, e não se inventa sintaxe) — por isso todas as linhas
    vêm em `foil`, para se dizer onde o ligar.
    """
    cfg = cfg or config.load()
    b = bloco(con, cfg)
    d = b["sets"].get(set_id)
    if d is None:
        raise ValueError(
            f"não há foils a listar em {set_id!r}. O âmbito do foil é "
            f"{', '.join(foil.raridades(cfg))} nas edições fora de "
            f"{', '.join(b['scope']['sem_edicoes']) or 'nenhuma'}")
    itens = [x for x in d["items"] if x["missing"] > 0]
    return {"set": set_id, "name": config.set_name(set_id), "block": BLOCO,
            "label": LABEL, "in_lists": False,
            **cardmarket.gerar(itens, com_codigo), "items": itens}


def payload_completo(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """O separador inteiro: as NORMAIS como sempre, e as FOILS ao lado.

    É aqui — e só aqui — que as duas metades se juntam. A metade das normais vem
    do `faltas_edicao.payload` **tal e qual**: `blocks`, `totals`,
    `totals_lists` e os quatro blocos de cada edição não sabem que esta existe,
    e é isso que garante que nenhum número deles mexe. As foils entram em duas
    chaves novas — `foil` no topo e `foil` em cada edição — que quem só quer as
    normais pode ignorar.
    """
    cfg = cfg or config.load()
    p = faltas_edicao.payload(con, cfg)
    b = bloco(con, cfg)
    for d in p["sets"]:
        d["foil"] = b["sets"].get(d["set"])
    p["foil"] = {k: v for k, v in b.items() if k != "sets"}
    return p


def texto(b: dict, sets: list[dict] | None = None) -> str:
    """O resumo desta metade em consola, para o `riftvault faltas`."""
    t, s = b["totals"], b["scope"]
    linhas = [
        f"FOILS — {ALVO_LABEL} — complemento, NÃO são faltas: "
        f"faltam {t['copies']} cópias de {t['cards']} impressões · "
        f"{t['cents'] / 100:.2f} €",
        f"  tens {s['owned']} foils em {s['owned_printings']} de {s['printings']} "
        f"impressões possíveis (alvo {s['target']}); "
        f"{', '.join(s['rarities'])}, fora {', '.join(s['sem_edicoes']) or 'nenhuma edição'}.",
        "  não entram na contagem de faltas, na percentagem da Coleção nem nas "
        "listas de compra: têm wantlist própria (--edicao X --bloco foil "
        "--cardmarket).",
    ]
    if t.get("pending_copies"):
        linhas.append(f"  {t['pending_copies']} foils já encomendadas e por chegar: "
                      f"continuam na lista, marcadas, e saem da wantlist "
                      f"(`riftvault encomendas --mais REF --foil`).")
    if t.get("no_foil_price"):
        linhas.append(f"  {t['no_foil_price']} linhas contam ao preço da NORMAL, por não "
                      f"haver oferta foil no CardTrader — o total é um PISO.")
    if b["aviso_normais"]:
        linhas.append(f"  AVISO: {len(b['aviso_normais'])} impressões têm foil mas o "
                      f"playset das NORMAIS está incompleto:")
        for x in b["aviso_normais"]:
            linhas.append(f"    {cardmarket.codigo(x['code']):<12} {x['name'][:34]:<34} "
                          f"normais {x['normais']}/{x['target']} · foil {x['foil']}")
    return "\n".join(linhas)
