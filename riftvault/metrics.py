"""As duas métricas de completude e os payloads que o frontend come.

  1) PLAYSET JOGÁVEL — alvo por CARTA LÓGICA (o nome). Qualquer impressão de
     qualquer edição conta. É a métrica de "consigo montar decks com isto".
  2) MASTER SET — alvo por IMPRESSÃO. É a métrica de colecionador, e desde
     2026-09-08 a Coleção são TRÊS BLOCOS por esta ordem (ver `BLOCOS`):

       1. a sequência do master set, em PLAYSET (o alvo do tipo da carta),
          **exceto as runas, que são 1 de cada** — ver `e_runa`;
       2. as runas especiais, **1 de cada** e por edição;
       3. no fim, as artes alternativas, **1 de cada**.

     Os três contam para a percentagem; o que fica de fora (`master_set.fora`,
     hoje os tokens `-T`, as signatures `*`, as sobrenumeradas e as promos
     `VEN-SP`) vai para blocos informativos no fim. Ver `fora_da_colecao`,
     `e_master`, `bloco` e `conta_bloco`.

São sempre calculadas e mostradas em paralelo. Nenhuma substitui a outra.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from . import config

# Ordem em que as variantes aparecem dentro do grupo, na grelha.
KIND_ORDER = {"base": 0, "alt_art": 1, "signature": 2,
              "rune_promo": 3, "special": 4, "token": 5, "unknown": 9}

RARITY_ORDER = ["common", "uncommon", "rare", "epic", "showcase"]

# Os blocos da grelha, por esta ordem (André, 2026-09-08): *"master set playset
# todo seguido; 1 runa especial de cada para cada set; no fim 1 alt art de
# cada"*. Os três primeiros são a COLEÇÃO — contam para a percentagem; os
# outros são o que ficou fora dela (`master_set.fora`, hoje os tokens, as
# signatures — *"das coleções tira as signatures, fazemos 1 Alt Art de cada mas
# as signature não"*, André, 2026-09-09 —, as sobrenumeradas — *"também não
# quero para a coleção as overnumbered"*, André, 2026-09-10 — e as promos —
# *"deparei-me com as VEN-SP (promos). Quero que as promos fiquem também à
# parte, tal como as signature e as overnumbered"*, André, 2026-09-10).
#
# Há um bloco por variante, e não só para as que ele nomeou: assim quem
# acrescentar uma variante ao `master_set.fora` recebe um cabeçalho a dizer o
# que é, em vez do «outras». Os blocos vazios não aparecem.
BLOCO_MASTER = "master"
BLOCO_RUNA = "rune_special"
# As sobrenumeradas (André, 2026-09-10: *"também não quero para a coleção as
# overnumbered"*) — as «300/298». Não são uma variante: é o NÚMERO que passa o
# tamanho da edição, por isso têm bloco próprio em vez de caírem no da variante
# delas. Ver `e_overnumbered`.
BLOCO_OVER = "overnumbered"
BLOCOS = [
    (BLOCO_MASTER, None),
    (BLOCO_RUNA, "Runas especiais — 1 de cada"),
    ("alt_art", "Artes alternativas — 1 de cada"),
    ("token", "Fora da coleção — tokens"),
    ("signature", "Fora da coleção — signatures"),
    (BLOCO_OVER, "Fora da coleção — sobrenumeradas"),
    ("rune_promo", "Fora da coleção — runas promo"),
    # As `VEN-SP` (André, 2026-09-10). Chamam-se «promos» porque é o nome que
    # ele lhes deu e o que o catálogo lhes chama (`variant_label: "Promo"`); as
    # runas promo do VEN são outra coisa e têm bloco próprio, acima.
    ("special", "Fora da coleção — promos"),
    ("base", "Fora da coleção — impressões base"),
    ("outras", "Fora da coleção — outras"),
]
BLOCO_LABEL = dict(BLOCOS)

# O mesmo bloco muda de rótulo quando o `master_set.fora` o põe fora da coleção:
# a cauda das artes alternativas é «1 de cada» enquanto conta, e «fora» quando
# não conta. É o mesmo id nos dois casos — o que muda é o que se lê. Ver
# `rotulo()`.
BLOCO_LABEL_FORA = {"alt_art": "Fora da coleção — artes alternativas"}

# O nome curto de cada bloco, para os chips da percentagem por bloco. É o mesmo
# nos dois rótulos, por isso não se tira do `label` a golpes de expressão
# regular.
BLOCO_CURTO = {
    BLOCO_MASTER: "master set",
    BLOCO_RUNA: "runas especiais",
    "alt_art": "artes alternativas",
    "token": "tokens",
    "signature": "signatures",
    BLOCO_OVER: "sobrenumeradas",
    "rune_promo": "runas promo",
    "special": "promos",
    "base": "impressões base",
    "outras": "outras",
}

# As runas. Três campos, e cada um responde a uma pergunta diferente:
#
#   `tipos`   — o que É uma runa. Decide o ALVO de TODAS elas (`e_runa`), desde
#               que ele disse *"as runas normais, quando têm número de set,
#               apenas 1 de cada também"* (2026-09-08, à noite).
#   `alvo`    — esse alvo: 1 por impressão, base ou especial.
#   `excepto` — quais é que ficam na SEQUÊNCIA (só a base). O resto vai para o
#               bloco 2, «runas especiais» (`e_runa_especial`) — hoje as artes
#               alternativas do OGN e as promo do VEN (a RiftScribe não tem
#               runas no SFD nem no UNL — ver "BURACO NO CATÁLOGO" no CLAUDE.md).
#
# Muda-se em `runas_especiais` no config. `tipos: []` desliga as três coisas e
# as runas voltam a seguir o playset, como qualquer outra carta.
RUNA_ESPECIAL: dict = {"tipos": ["Rune"], "excepto": ["base"], "alvo": 1}

# O sufixo do CÓDIGO IMPRESSO -> o `variant_kind` que ele dá no catálogo. É a
# escrita do André ("sigla-T", "a no fim"), e o `master_set.fora` aceita-a a par
# do nome da variante — as duas dizem a mesma coisa. Ver `kinds_fora`.
SUFIXO_KIND = {
    "-t": "token",          # UNL-T03
    "a": "alt_art",         # UNL-228a
    "*": "signature",       # OGN-299*
    "-r": "rune_promo",     # VEN-R01
    "-sp": "special",       # VEN-SP4
}

# A PALAVRA dele para uma variante, a par do sufixo e do nome interno. Ele
# nomeou as `VEN-SP` pelo nome que o catálogo lhes dá (`variant_label: "Promo"`)
# e não pelo sufixo: *"deparei-me com as VEN-SP (promos). Quero que as promos
# fiquem também à parte"* (2026-09-10). As três escritas dão o mesmo kind.
#
# «Promo» aqui é SÓ a `special`. As runas promo do VEN (`VEN-R01..R06`) são
# outra categoria — escrevem-se `-R`/`rune_promo` — e ficam dentro da Coleção,
# no bloco das runas especiais, por decisão dele de 2026-09-08 (*"1 runa
# especial de cada para cada set"*). Ver o `fora_da_colecao`.
PALAVRA_KIND = {
    "promo": "special",     # VEN-SP4
}

# O valor do `master_set.fora` que NÃO é uma variante. As sobrenumeradas são um
# critério de NÚMERO — como o `showcase` do `a_subir.excluir` é um critério de
# raridade —, mas escrevem-se na mesma lista de propósito: a pergunta é uma só
# ("o que é que não é a Coleção") e tem de ter uma resposta só.
FORA_OVERNUMBERED = "overnumbered"

# Memo do `_fora`: a lista do config não muda dentro de uma corrida, e a
# pergunta é feita uma vez por impressão (1180) por payload.
_FORA_MEMO: dict[tuple, tuple] = {}

# Alvo das sobrenumeradas depois de saírem: **1 de cada**, como as signatures e
# os tokens que já estavam fora. Elas continuam na grelha e o tile continua a
# dizer quantas ele tem — mas pedir o playset de uma carta que já não se
# coleciona era ler o número ao contrário. ALVO e CONTA são campos diferentes
# desde 2026-09-02; isto é o alvo.
ALVO_OVERNUMBERED = 1


# --------------------------------------------------------------------------
# Alvos
# --------------------------------------------------------------------------


def campo(printing, nome: str, omissao=None):
    """Um campo da impressão, aceitando linha do SQLite, dicionário ou nem isso.

    O `bloco()` e o `e_master()` são chamados com linhas da `catalog.printings`
    mas também com dicionários mínimos (`{"variant_kind": ..., "is_token": 0}`).
    A `sqlite3.Row` levanta `IndexError` no que não existe e o `dict` levanta
    `KeyError`; aqui a falta de um campo é uma resposta, não um erro.
    """
    try:
        valor = printing[nome]
    except (KeyError, IndexError):
        return omissao
    return omissao if valor is None else valor


def opcoes_runa(cfg: dict | None = None) -> dict:
    """`runas_especiais` do config, por cima dos defaults do `RUNA_ESPECIAL`."""
    cfg = cfg or config.load()
    out = dict(RUNA_ESPECIAL)
    out.update({k: v for k, v in (cfg.get("runas_especiais") or {}).items()
                if not k.startswith("_")})
    return out


def e_runa(printing, cfg: dict | None = None) -> bool:
    """Esta impressão é de uma RUNA — a pergunta do ALVO do master set.

    André, 2026-09-08, à noite: *"as runas normais, quando têm número de set,
    apenas 1 de cada também, em vez de 12 (playset)"*. Passou a haver **uma
    regra só** para as runas todas: base ou especial, o alvo do master é 1
    (`runas_especiais.alvo`). Ver `master_target`.

    O que continua a distinguir a base da especial é só o BLOCO da grelha —
    a base fica na sequência, o resto vai para o bloco 2. Ver `e_runa_especial`.
    """
    return campo(printing, "type") in (opcoes_runa(cfg).get("tipos") or ())


def e_runa_especial(printing, cfg: dict | None = None) -> bool:
    """Esta impressão é uma «runa especial» — o bloco 2 da Coleção?

    André, 2026-09-08: *"1 runa especial de cada para cada set"*. A runa base
    fica no bloco 1 (a sequência) e as outras impressões da runa — a arte
    alternativa e a promo — vão para um bloco próprio, por edição, antes da
    cauda das artes alternativas.

    **É só sobre o bloco, já não sobre o alvo.** O alvo das duas é o mesmo (1)
    desde a segunda frase dele nesse dia — ver `e_runa`.
    """
    if not e_runa(printing, cfg):
        return False
    excepto = opcoes_runa(cfg).get("excepto") or ()
    return campo(printing, "variant_kind") not in excepto


def playset_target(card_type: str | None, is_token: bool, cfg: dict | None = None) -> int:
    cfg = cfg or config.load()
    # Tokens: 1 de cada (decisão do André). É o ALVO — desde 2026-09-08 os que
    # têm código `-T` já não entram na percentagem de master set (`e_master`),
    # mas o tile continua a dizer-lhe quantos lhe faltam.
    if is_token:
        return int(cfg.get("token_target", 1))
    targets = cfg.get("playset_targets_by_type", {})
    return int(targets.get(card_type or "", targets.get("default", 3)))


def master_target(printing_id: str, kind: str, card_type: str | None, is_token: bool,
                  cfg: dict | None = None, printing=None) -> int:
    """O alvo do master set de uma impressão.

    Quem tem a LINHA do catálogo na mão deve chamar o `alvo()`, não isto: o alvo
    das sobrenumeradas depende do código impresso, e daqui só se vê a variante.
    Os quatro escalares ficam para quem não tem a linha (e para os testes).
    """
    cfg = cfg or config.load()
    override = cfg.get("master_target_overrides", {}).get(printing_id)
    if override is not None:
        return int(override)
    if printing is not None and fora_da_colecao(printing, cfg) == BLOCO_OVER:
        # Saiu da Coleção por ser sobrenumerada (André, 2026-09-10): fica na
        # grelha com 1 de cada, como as signatures e os tokens que já lá estão.
        return ALVO_OVERNUMBERED
    if is_token:
        return int(cfg.get("token_target", 1))
    by_variant = cfg.get("master_targets_by_variant", {})
    if e_runa({"type": card_type}, cfg):
        # *"As runas normais, quando têm número de set, apenas 1 de cada também,
        # em vez de 12 (playset)"* (André, 2026-09-08, à noite). UMA regra para
        # as runas todas — base ou especial, o alvo do MASTER é 1 —, e antes do
        # `master_base_follows_type`, que é quem lhes dava o playset.
        #
        # O playset JOGÁVEL da runa continua 12 (`playset_targets_by_type`): é o
        # Rune Pool de cada deck, e quem responde a isso é a métrica 1. São duas
        # perguntas diferentes — colecionar e jogar.
        return int(opcoes_runa(cfg).get("alvo", 1))
    if kind == "base" and cfg.get("master_base_follows_type", True):
        # Senão uma Rune base pediria 3 em vez de 12, e um Legend pediria 3
        # em vez de 1. O alvo do master da base segue o alvo de jogo.
        return playset_target(card_type, is_token, cfg)
    if kind in set(cfg.get("master_variantes_playset", [])):
        # O André quer contagem de playset nas artes alternativas (2026-09-05):
        # se decide colecionar a alt art, quer as 3 na mesma, não uma. Isto é
        # só o alvo do tile — continuam fora da percentagem (`e_master`).
        return playset_target(card_type, is_token, cfg)
    return int(by_variant.get(kind, 1))


def alvo(printing, cfg: dict | None = None) -> int:
    """O alvo do master set de uma LINHA do catálogo — a porta de entrada.

    É o `master_target` com o contexto que o número de coleccionador precisa.
    Toda a produção passa por aqui (a grelha, os níveis, as listas de compra e a
    Venda) para não haver duas contas do mesmo alvo.
    """
    return master_target(printing["printing_id"], printing["variant_kind"],
                         campo(printing, "type"), bool(campo(printing, "is_token")),
                         cfg, printing=printing)


def _fora(cfg: dict | None = None) -> tuple[frozenset[str], bool]:
    """O `master_set.fora` lido: (variantes que saem, as sobrenumeradas saem?).

    A lista escreve-se como o André fala — pelo sufixo do código impresso
    (`["-T", "*"]`), pela palavra dele para a variante (`"promo"`), pelo nome
    interno dela (`["token", "signature"]`) ou pela palavra do que não é
    variante nenhuma (`"overnumbered"`). Uma leitura só, para os dois critérios
    não se separarem.

    Um valor que não se reconheça REBENTA, e de propósito: uma variante nova
    (um `b`? um `sp7`?) tem de aparecer, não de ser ignorada em silêncio —
    ver CLAUDE.md, "Superfícies NÃO validadas".
    """
    cfg = cfg or config.load()
    bruto = tuple((cfg.get("master_set") or {}).get("fora") or ())
    memo = _FORA_MEMO.get(bruto)
    if memo is not None:
        return memo
    kinds, over = set(), False
    for valor in bruto:
        chave = str(valor).strip().lower()
        if chave == FORA_OVERNUMBERED:
            over = True
        elif chave in SUFIXO_KIND:
            kinds.add(SUFIXO_KIND[chave])
        elif chave in PALAVRA_KIND:
            kinds.add(PALAVRA_KIND[chave])
        elif chave in KIND_ORDER:
            kinds.add(chave)
        else:
            aceites = ", ".join(sorted(set(SUFIXO_KIND) | set(PALAVRA_KIND)
                                       | set(KIND_ORDER) | {FORA_OVERNUMBERED}))
            raise ValueError(
                f"master_set.fora: nao reconheco {valor!r}. Aceita: {aceites}")
    _FORA_MEMO[bruto] = out = (frozenset(kinds), over)
    return out


def kinds_fora(cfg: dict | None = None) -> frozenset[str]:
    """Os `variant_kind` que ficam FORA da Coleção — metade do `master_set.fora`.

    As signatures saíram a 2026-09-09 (*"das coleções tira as signatures,
    fazemos 1 Alt Art de cada mas as signature não"*): o `"*"` da lista tira-as
    da sequência **e** do denominador da percentagem — é a mesma pergunta. Não
    saem da grelha: ficam num bloco próprio no fim, com alvo, para as que ele
    tenha continuarem visíveis. Tira-se o `"*"` para as pôr de volta.

    As promos `VEN-SP` saíram a 2026-09-10, pela mesma lista e pelo mesmo
    mecanismo (*"quero que as promos fiquem também à parte, tal como as
    signature e as overnumbered"*): é o `"promo"` do config, que o
    `PALAVRA_KIND` traduz para `variant_kind = "special"`.

    A outra metade da lista é o `fora_overnumbered`, que não é por variante.
    """
    return _fora(cfg)[0]


def fora_overnumbered(cfg: dict | None = None) -> bool:
    """As sobrenumeradas ficam fora da Coleção? — a outra metade da lista.

    André, 2026-09-10: *"no riftvault, também não quero para a coleção as
    overnumbered"*. Escreve-se `"overnumbered"` no `master_set.fora`, a par dos
    sufixos; tira-se de lá para as pôr de volta. Ver `e_overnumbered`.
    """
    return _fora(cfg)[1]


def tamanho_do_set(printing) -> int | None:
    """O tamanho nominal da edição, lido do CÓDIGO IMPRESSO desta impressão.

    O `public_code` traz os dois números — `OGN-299*/298` é a 299 de um set de
    298 —, por isso o tamanho não é um número escrito à mão nem uma segunda
    consulta: vem da mesma linha do catálogo, do mesmo sítio de onde vem o
    número da carta. Confirmado no catálogo real: o denominador é o mesmo em
    todas as impressões da lane principal de cada edição (OGN 298, OGS 24,
    SFD 221, UNL 219, VEN 166).

    `None` quando o código não traz denominador nenhum. São 16 no catálogo de
    hoje — os tokens `-T` e as runas promo `VEN-R01..R06` —, e é a resposta
    certa: essas são numeradas numa série própria, fora da numeração da edição,
    e por isso nunca a podem passar.
    """
    code = campo(printing, "public_code", "")
    if "/" not in code:
        return None
    try:
        return int(code.rsplit("/", 1)[1])
    except ValueError:
        return None


def e_overnumbered(printing) -> bool:
    """O número desta impressão passa o tamanho da edição — é uma «300/298»?

    São as reimpressões showcase de topo de set e as signatures que se lhes
    agarram (ARMADILHA 2 do CLAUDE.md): a mesma carta lógica reaparece na mesma
    edição com número de coleção PRÓPRIO, acima do tamanho nominal.

    O critério é o CÓDIGO IMPRESSO, como todas as decisões dele sobre a Coleção:
    `collector_number > tamanho_do_set`. O `VEN-SP4/006` é a 4 de uma série de
    6 e por isso não é sobrenumerada — a série dela é outra, e o código diz isso.
    """
    tamanho = tamanho_do_set(printing)
    cn = campo(printing, "collector_number")
    return tamanho is not None and cn is not None and int(cn) > tamanho


def fora_da_colecao(printing, cfg: dict | None = None) -> str | None:
    """PORQUE é que esta impressão está fora da Coleção — o bloco, ou `None`.

    Uma pergunta, uma função: quem quer saber se conta chama o `e_master`, quem
    quer saber onde é que ela vai parar na grelha chama o `bloco`, e os dois
    saem daqui. O motivo é o bloco porque é isso que ele lê no cabeçalho —
    «Fora da coleção — signatures» é diferente de «— sobrenumeradas».

    A ordem é a das decisões dele: primeiro a VARIANTE que ele nomeou (o sufixo
    do código), depois o NÚMERO. É por isso que as 36 signatures continuam no
    bloco das signatures — são todas sobrenumeradas, mas o que as tirou foi a
    frase de 2026-09-09, e mudá-las de bloco agora era apagar essa decisão do
    ecrã.

    **As runas promo do VEN (`VEN-R01..R06`) NÃO saem por aqui.** São
    `rune_promo`, não `special`, e continuam dentro da Coleção, no bloco das
    runas especiais: é a decisão dele de 2026-09-08 (*"1 runa especial de cada
    para cada set"*) e são elas que enchem esse bloco no VEN. Ele nomeou as
    `VEN-SP`; tirar as `VEN-R` com elas era apagar a outra decisão.
    """
    cfg = cfg or config.load()
    kinds, over = _fora(cfg)
    kind = campo(printing, "variant_kind", "unknown")
    if kind in kinds:
        # Uma variante nova (um `b`? um `sp7`?) tem de cair num sítio visível em
        # vez de desaparecer — ver CLAUDE.md, "Superfícies não validadas".
        return kind if kind in BLOCO_LABEL else "outras"
    if over and e_overnumbered(printing):
        return BLOCO_OVER
    # Os tokens com número de coleção próprio (`OGN-271/298`, o Recruit) não têm
    # sufixo nenhum e por isso ficam: estão numerados dentro da edição.
    if campo(printing, "is_token") and int(cfg.get("token_target", 1)) <= 0:
        return "token"
    return None


def e_master(printing, cfg: dict | None = None) -> bool:
    """Esta impressão faz parte da COLEÇÃO — isto é, conta para a percentagem?

    É a única resposta a esta pergunta em todo o riftvault: usam-na a métrica
    (o denominador da percentagem), a grelha da Coleção (a ordem dos blocos), a
    aba «A subir», a lista completa do master set e a lista de venda. Havia duas
    leituras a divergir — a percentagem ignorava as artes alternativas mas a
    grelha punha-as na sequência — e passou a haver uma.

    A REGRA É O CÓDIGO IMPRESSO (André, 2026-09-08): o que ele mandou tirar
    escreve-se pelo sufixo, e no catálogo lê-se pelo `variant_kind`, que é
    derivado do mesmo sufixo:

      `UNL-T03`   -> variant `t03` -> kind `token`
      `UNL-228a`  -> variant `a`   -> kind `alt_art`

    Muda-se em `master_set.fora`, hoje `["-T", "*", "overnumbered", "promo"]` —
    os tokens, as signatures, as sobrenumeradas e as promos `VEN-SP`. **As
    artes alternativas voltaram
    para dentro a 2026-09-08**, na segunda frase dele (*"no fim 1 alt art de
    cada"*): continuam a ser a cauda da grelha, num bloco próprio, mas agora
    contam com alvo 1. **As signatures saíram a 2026-09-09**: *"das coleções
    tira as signatures, fazemos 1 Alt Art de cada mas as signature não"* — as
    duas coisas na mesma frase, e é esta função que as separa. **As
    sobrenumeradas saíram a 2026-09-10**: *"também não quero para a coleção as
    overnumbered"* — e essas não são uma variante, são um número (ver
    `e_overnumbered`). **As promos `VEN-SP` saíram no mesmo dia**: *"quero que
    as promos fiquem também à parte, tal como as signature e as overnumbered"* —
    essas são outra vez uma variante (`special`), e por isso só precisaram de
    uma palavra na lista. Ver `fora_da_colecao`, `bloco` e `conta_bloco`.

    Não confundir com o ALVO (`master_target`): o alvo é o que o tile mostra
    ("6/12"), isto é o que entra no denominador. São duas perguntas diferentes
    e têm dois campos desde 2026-09-02.

    Aceita uma linha do `catalog.printings` ou qualquer dicionário com
    `variant_kind` e `is_token` — as sobrenumeradas precisam também do
    `public_code` e do `collector_number`, e sem eles a resposta é "não é".
    """
    return fora_da_colecao(printing, cfg) is None


def bloco(printing, cfg: dict | None = None) -> str:
    """Em que bloco da grelha é que esta impressão cai.

    A Coleção são três blocos seguidos (André, 2026-09-08): a sequência do
    master set em playset, depois as runas especiais a 1, depois as artes
    alternativas a 1. O que está fora da coleção vai para um bloco próprio a
    seguir a tudo — nunca intercalado. Ver `BLOCOS` para a ordem.
    """
    fora = fora_da_colecao(printing, cfg)
    if fora is not None:
        return fora
    # A runa especial ganha à arte alternativa: a arte alternativa de uma runa é
    # das duas coisas, e ele pediu-a no bloco das runas ("1 runa especial de
    # cada para cada set"), antes da cauda das alt arts.
    if e_runa_especial(printing, cfg):
        return BLOCO_RUNA
    if printing["variant_kind"] == "alt_art":
        return "alt_art"
    return BLOCO_MASTER


def conta_bloco(bloco_id: str, cfg: dict | None = None) -> bool:
    """Este bloco entra na percentagem da Coleção?

    Os três blocos da coleção contam; os outros são o que o `master_set.fora`
    deixou de fora e existem só para ele ver que não desapareceram. O `alt_art`
    é o único id que aparece dos dois lados — é a cauda da coleção enquanto
    contar, e um bloco de fora quando o `master_set.fora` o levar.
    """
    if bloco_id in (BLOCO_MASTER, BLOCO_RUNA):
        return True
    return bloco_id == "alt_art" and "alt_art" not in kinds_fora(cfg)


def rotulo(bloco_id: str, cfg: dict | None = None) -> str | None:
    """O cabeçalho do bloco. `None` no primeiro: a sequência não leva título."""
    if not conta_bloco(bloco_id, cfg) and bloco_id in BLOCO_LABEL_FORA:
        return BLOCO_LABEL_FORA[bloco_id]
    return BLOCO_LABEL.get(bloco_id)


# --------------------------------------------------------------------------
# Contagem por NÍVEIS: 1 de cada, 2 de cada, o playset
# --------------------------------------------------------------------------
#
# André, 2026-09-08: *"Para a coleção de master set, gostava que fizesses também
# uma contagem: quantas cartas faltam para ter 1 de cada, quantas faltam para
# ter 2 de cada, quantas faltam para ter o playset de cada — do género 1/3 Z % ·
# 2/3 X % · 3/3 Y %."*
#
# A barra do master set responde a "quanto falta para estar tudo completo"; isto
# parte a mesma pergunta em degraus, que é como se compra: primeiro uma de cada,
# depois a segunda, e só no fim a terceira.
#
# O ÂMBITO É O MESMO DA BARRA — as impressões que `conta_bloco` deixa contar
# (os três blocos da Coleção), pelo alvo do `master_target`. Não é um âmbito
# novo: se fosse, a percentagem do último nível não batia certo com a barra por
# cima da qual ela aparece. As impressões de alvo 1 — as runas, os Legends, os
# Battlefields, as runas especiais e as artes alternativas — só podem faltar no
# nível 1; do nível 2 em diante contam como feitas, porque `min(k, alvo)` nunca
# lhes pede mais do que 1. É por isso que a percentagem do nível mais alto é
# EXACTAMENTE a da barra do master set.
#
# CONTA CÓPIAS, NÃO O QUE VEM A CAMINHO. É a regra da Coleção — o `pending` fica
# fora do `copies` de propósito, e as barras não mexem enquanto a encomenda vem
# (ver CLAUDE.md, "Encomendas a caminho"). As wantlists por nível descontam o
# pendente, porque aí a pergunta é o que ainda há a COMPRAR; aqui é o que está
# na caixa.


def niveis(itens, n: int | None = None) -> list[dict]:
    """A contagem por níveis de uma lista de `(alvo, tem, preço|None)`.

    Para cada nível k, o alvo é `min(k, alvo)`:

      `missing` = Σ max(0, min(k, alvo) − tem)   — cópias que faltam
      `done`    = quantas impressões já lá chegaram
      `cents`   = o que custam essas cópias ao preço de hoje

    `n` é quantos níveis se fazem; por omissão, o maior alvo que lá está. O
    denominador é o mesmo em todos os níveis (as impressões todas do âmbito),
    senão as percentagens não eram comparáveis entre si.
    """
    itens = [(a, t, p) for a, t, p in itens if a > 0]
    if n is None:
        n = max((a for a, _, _ in itens), default=0)
    saida = []
    for k in range(1, int(n) + 1):
        done = total = missing = cents = 0
        for alvo, tem, preco in itens:
            total += 1
            falta = max(0, min(k, alvo) - tem)
            missing += falta
            cents += falta * (preco or 0)
            if not falta:
                done += 1
        saida.append({"k": k, "done": done, "total": total,
                      "missing": missing, "cents": cents,
                      "pct": round(done / total * 100, 1) if total else 0.0})
    return saida


def itens_da_colecao(con: sqlite3.Connection, cfg: dict | None = None) -> list[tuple]:
    """`(set_id, alvo, cópias, preço)` das impressões que contam para a barra."""
    from . import locais

    cfg = cfg or config.load()
    # SÓ as cópias que estão nos binders de COLEÇÃO (André, 2026-09-10): *"vou
    # querer ter as cartas da coleção apenas alocadas à coleção e as cartas dos
    # decks apenas alocadas a Decks"*. Uma cópia que esteja num deck ou no
    # binder Decks/Venda deixou de contar aqui, mesmo sendo a mesma impressão.
    qty = locais.na_colecao(con)
    price = prices_map(con)
    out = []
    for r in con.execute(
        # O `public_code` e o `collector_number` são o que o `e_overnumbered`
        # precisa — sem eles as sobrenumeradas entravam por aqui na contagem.
        "SELECT printing_id, set_id, collector_number, public_code, "
        "       variant_kind, type, is_token "
        "FROM catalog.printings"
    ):
        pid = r["printing_id"]
        n = alvo(r, cfg)
        if n <= 0 or not conta_bloco(bloco(r, cfg), cfg):
            continue
        out.append((r["set_id"], n, qty.get(pid, 0), price.get(pid)))
    return out


def niveis_max(con: sqlite3.Connection, cfg: dict | None = None) -> int:
    """Quantos níveis há: o maior alvo do master set em TODO o catálogo.

    Vem do catálogo inteiro e não de cada edição para as cinco mostrarem os
    mesmos degraus — uma edição só de Legends daria um nível só, e o `1/3` de
    uma deixava de ser comparável com o `1/1` da outra.

    Hoje são **3** (o playset das Units/Spells/Gears). Se as runas voltarem ao
    playset — `runas_especiais.tipos: []` — passam a ser 12, e é isso que se vê:
    o número de degraus é o maior alvo, não um valor escrito à mão.
    """
    return max((a for _, a, _, _ in itens_da_colecao(con, cfg)), default=0)


def niveis_payload(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """A contagem por níveis GLOBAL e por edição, com os mesmos degraus.

    O `by_set` vai para o cliente para ele poder trocar a edição aberta pelos
    números locais (otimistas) sem perder as outras quatro: os campos são todos
    somas, por isso o global é a soma das edições.
    """
    cfg = cfg or config.load()
    itens = itens_da_colecao(con, cfg)
    n = max((a for _, a, _, _ in itens), default=0)
    por_set: dict[str, list] = {}
    for s, alvo, tem, preco in itens:
        por_set.setdefault(s, []).append((alvo, tem, preco))
    return {
        "max": n,
        "levels": niveis([(a, t, p) for _, a, t, p in itens], n),
        "by_set": {s: niveis(v, n) for s, v in por_set.items()},
    }


# --------------------------------------------------------------------------
# Payloads
# --------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sets_payload(con: sqlite3.Connection) -> list[dict]:
    rows = con.execute(
        "SELECT set_id, COUNT(*) AS n FROM catalog.printings GROUP BY set_id"
    ).fetchall()
    out = [
        {"id": r["set_id"], "name": config.set_name(r["set_id"]),
         "order": config.set_order(r["set_id"]), "n_printings": r["n"]}
        for r in rows
    ]
    out.sort(key=lambda s: (s["order"], s["id"]))
    return out


def owned_by_card(con: sqlite3.Connection) -> dict[str, int]:
    """Cópias por carta lógica, somando TODAS as impressões de TODAS as edições."""
    rows = con.execute(
        "SELECT p.card_key AS k, SUM(c.qty) AS n FROM copies c "
        "JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 GROUP BY p.card_key"
    ).fetchall()
    return {r["k"]: r["n"] for r in rows}


def prices_map(con: sqlite3.Connection) -> dict[str, int]:
    """printing_id -> preço em cêntimos. Vazio enquanto não houver `riftvault prices`."""
    try:
        rows = con.execute(
            "SELECT printing_id, price_cents FROM catalog.price_latest "
            "WHERE price_cents IS NOT NULL"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}               # catálogo antigo, sem a tabela ainda
    return {r["printing_id"]: r["price_cents"] for r in rows}


def set_payload(con: sqlite3.Connection, set_id: str, editable: bool = True,
                image_mode: str = "local") -> dict:
    from . import decks, locais

    cfg = config.load()
    # `qty` é o que a COLEÇÃO tem — é ele que manda nas barras, no filtro
    # "Faltas" e na contagem por níveis. O total físico vai à parte em
    # `qty_total`, e o `locations` diz onde estão as outras.
    qty = locais.na_colecao(con)
    totais = locais.totais(con)
    locais_por_pid = locais.por_local(con)
    nomes_decks = locais.nomes_dos_decks(con)
    owned_cards = owned_by_card(con)
    price = prices_map(con)
    # Onde estão as cópias que não estão no binder de coleção: nos decks.
    # E que decks USAM cada carta lógica (André, 2026-09-11: *"na coleção
    # indica onde as cartas estão a ser usadas"*) — é por carta, não por
    # impressão, porque a alocação é por carta.
    try:
        nos_decks = decks.printing_allocation(con)
        uso = decks.uso_por_carta(con)
    except sqlite3.OperationalError:
        nos_decks, uso = {}, {}

    rows = con.execute(
        "SELECT * FROM catalog.printings WHERE set_id = ? ORDER BY api_sort", (set_id,)
    ).fetchall()

    groups: dict[str, dict] = {}
    for r in rows:
        g = groups.get(r["group_key"])
        if g is None:
            g = groups[r["group_key"]] = {
                "key": r["group_key"],
                "cn": r["collector_number"],
                "lane": r["lane"],
                "sort": r["api_sort"],
                "card_key": r["card_key"],
                "name": r["name"],
                "type": r["type"],
                "rarity": r["base_rarity"],
                # Custo de energia da impressão base — é por aqui que a grelha
                # ordena quando se escolhe "Custo".
                "energy": r["energy"],
                "faction": r["faction"],
                "is_token": bool(r["is_token"]),
                # Os decks que pedem esta carta, por prioridade, com o que
                # cada um leva e o que lhe falta: «Azir 3 · Kennen 2 (faltam 2)».
                "decks": uso.get(r["card_key"], []),
                "printings": [],
            }
        g["printings"].append({
            "id": r["printing_id"],
            "code": r["public_code"],
            "kind": r["variant_kind"],
            "label": r["variant_label"],
            "name": r["name"],
            "rarity": r["rarity"],
            # Battlefields vêm 'landscape' — o tile tem de mudar de proporção.
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "price": price.get(r["printing_id"]),   # cêntimos, ou None
            "in_decks": nos_decks.get(r["printing_id"], []),
            "qty": qty.get(r["printing_id"], 0),
            # Cópias FÍSICAS (todos os locais) e onde estão. A barra mede o
            # `qty`; isto é o que a linha do tile lê para dizer «2 na Coleção ·
            # 1 no deck Azir». São dois números diferentes de propósito.
            "qty_total": totais.get(r["printing_id"], 0),
            "locations": [
                {"loc": loc, "label": locais.rotulo(loc, nomes_decks), "qty": n}
                for loc, n in sorted(
                    (locais_por_pid.get(r["printing_id"]) or {}).items(),
                    key=lambda kv: (kv[0] != locais.COLECAO, kv[0]))],
            "target": alvo(r, cfg),
            # O bloco da grelha: `master`, `rune_special` ou `alt_art` dentro da
            # coleção, e um bloco próprio para o que ficou de fora. É o mesmo
            # campo que diz se entra na percentagem (ver `conta_bloco`).
            "block": bloco(r, cfg),
            "img": f"img/{r['printing_id']}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "banned": bool(r["is_banned"]),
            "sort": r["api_sort"],
        })

    ordered = sorted(groups.values(), key=lambda g: g["sort"])
    for g in ordered:
        g["printings"].sort(key=lambda p: (KIND_ORDER.get(p["kind"], 9), p["sort"]))
        for i, p in enumerate(g["printings"]):
            p["head"] = i == 0   # o tile que fica visível em "Só artes base"
        target = playset_target(g["type"], g["is_token"], cfg)
        g["playset"] = {"owned": owned_cards.get(g["card_key"], 0), "target": target}

    # ----- barras de progresso e contadores -----
    seen_cards: set[str] = set()
    play_done = play_total = 0
    for g in ordered:
        if g["playset"]["target"] <= 0 or g["card_key"] in seen_cards:
            continue
        seen_cards.add(g["card_key"])
        play_total += 1
        if g["playset"]["owned"] >= g["playset"]["target"]:
            play_done += 1

    master_done = master_total = 0
    by_rarity: dict[str, list[int]] = {}
    # `(alvo, cópias, preço)` do que conta para a barra — a matéria-prima da
    # contagem por níveis (1 de cada, 2 de cada, playset). Sai do mesmo ciclo
    # da barra de propósito: é o mesmo âmbito, e a percentagem do último nível
    # tem de dar exactamente a da barra.
    para_niveis: list[tuple] = []
    # TODOS os blocos têm contador próprio ("tens N de M"); os três da coleção
    # somam-se ainda na percentagem global, e os de fora não — é o ponto todo
    # de estarem fora.
    by_block: dict[str, list[int]] = {}
    for g in ordered:
        for p in g["printings"]:
            if p["target"] <= 0:
                continue
            complete = p["qty"] >= p["target"]
            slot = by_block.setdefault(p["block"], [0, 0])
            slot[1] += 1
            slot[0] += 1 if complete else 0
            if not conta_bloco(p["block"], cfg):
                continue
            master_total += 1
            master_done += 1 if complete else 0
            para_niveis.append((p["target"], p["qty"], p["price"]))
            # Pela raridade da BASE do grupo, como sempre: a `showcase` não é
            # raridade de jogo. A soma dos chips é o denominador da barra.
            slot = by_rarity.setdefault(g["rarity"] or "?", [0, 0])
            slot[1] += 1
            slot[0] += 1 if complete else 0

    rarities = [
        {"rarity": k, "done": v[0], "total": v[1]}
        for k, v in sorted(by_rarity.items(),
                           key=lambda kv: (RARITY_ORDER.index(kv[0])
                                           if kv[0] in RARITY_ORDER else 99, kv[0]))
    ]

    # Valor do que tenho DESTA edição, e o que a edição inteira valeria se
    # estivesse completa segundo a métrica de master set.
    value_owned = value_full = 0
    for g in ordered:
        for p in g["printings"]:
            if p["price"] is None:
                continue
            # O valor é do que ele TEM, esteja onde estiver: uma carta num deck
            # não vale menos por estar sleevada. Por isso o total físico, e não
            # o `qty` da Coleção.
            value_owned += p["qty_total"] * p["price"]
            # "se estivesse completa" é sobre a COLEÇÃO: o que não entra na
            # percentagem também não entra no preço de a fechar. Desde
            # 2026-09-08 isso inclui 1 de cada runa especial e 1 de cada alt art.
            if conta_bloco(p["block"], cfg):
                value_full += p["target"] * p["price"]

    # Cada bloco leva o seu "tens N de M"; o `counts` diz quais é que se somam
    # na barra do master set. A percentagem global é a soma dos que contam.
    blocks = [
        {"id": bid, "label": rotulo(bid, cfg), "short": BLOCO_CURTO.get(bid, bid),
         "counts": conta_bloco(bid, cfg),
         "done": by_block[bid][0], "total": by_block[bid][1]}
        for bid, _ in BLOCOS if bid in by_block
    ]

    return {
        "editable": editable,
        "image_mode": image_mode,
        "generated_at": _now(),
        "set": {"id": set_id, "name": config.set_name(set_id)},
        # A partir de que preço é que o valor aparece por cima da carta.
        "price_badge_min": int(cfg.get("price_badge_min_cents", 100)),
        "progress": {
            "playset": {"done": play_done, "total": play_total},
            "master": {"done": master_done, "total": master_total},
            "value": {"owned": value_owned, "full": value_full,
                      "currency": "EUR", "has_prices": bool(price)},
            "rarities": rarities,
            # 1 de cada, 2 de cada, o playset — DESTA edição. Os degraus são os
            # do catálogo inteiro (`niveis_max`) para as cinco edições se
            # poderem comparar; o cliente recalcula os números a partir do
            # estado local, como faz com as barras, mas o número de degraus vem
            # daqui para não haver duas regras.
            "levels": niveis(para_niveis, niveis_max(con, cfg)),
        },
        # A ordem dos blocos da grelha, e o rótulo de cada um. Vem do servidor
        # para o cliente não ter uma segunda cópia da regra.
        "blocks": blocks,
        "groups": ordered,
    }


def ordem_da_grelha(payload: dict) -> list[tuple[str, str]]:
    """(bloco, printing_id) pela ordem em que a grelha desenha os tiles.

    O `groups` do payload continua a vir por número de coleção — é a ordem da
    API e é a que a sequência do master set precisa. O que a grelha faz é
    percorrê-lo uma vez POR BLOCO: primeiro o master set inteiro, depois as
    runas especiais, depois as artes alternativas, e só no fim o que está fora
    da coleção (André, 2026-09-08). O `render()` do `app.js` faz exatamente
    estes dois ciclos; isto é a mesma ordem em Python, para dar para testar sem
    browser.
    """
    fora = []
    for b in payload.get("blocks") or [{"id": BLOCO_MASTER}]:
        for g in payload["groups"]:
            for p in g["printings"]:
                if p["block"] == b["id"]:
                    fora.append((b["id"], p["id"]))
    return fora


def index_payload(con: sqlite3.Connection, editable: bool = True,
                  image_mode: str = "local") -> dict:
    from . import collection, prices

    try:
        value = prices.collection_value(con)
    except sqlite3.OperationalError:
        value = None            # ainda não correu `riftvault prices`

    return {
        "editable": editable,
        "image_mode": image_mode,
        "generated_at": _now(),
        "sets": sets_payload(con),
        "totals": collection.totals(con),
        "value": value,
        # A contagem por níveis das cinco edições juntas, e a de cada uma. A
        # Coleção mostra a global por baixo da barra e troca a edição aberta
        # pelos números locais — ver `renderNiveis` no app.js.
        "levels": niveis_payload(con),
    }
