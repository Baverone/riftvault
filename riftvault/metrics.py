"""As duas métricas de completude e os payloads que o frontend come.

  1) PLAYSET JOGÁVEL — alvo por CARTA LÓGICA (o nome). Qualquer impressão de
     qualquer edição conta. É a métrica de "consigo montar decks com isto".
  2) MASTER SET — alvo por IMPRESSÃO. É a métrica de colecionador, e desde a
     noite de 2026-09-14 a página da Coleção são TRÊS CATEGORIAS (André:
     *"quero masterset com playset / runas 1 de cada / Alt Art, overnumbered,
     etc etc mete Playset na contagem / mas só quero % de completo para
     masterset! / o que é Alt Art e Overnumbered, etc etc é puramente
     coleção"*):

       1. o MASTER SET — a sequência da edição, por número de coleção. É o
          ÚNICO bloco que entra na percentagem de completo e nos níveis.
       2. a COLEÇÃO EXTRA («puramente coleção») — as runas especiais, as
          artes alternativas, as sobrenumeradas, as promos `VEN-SP`. Aparecem
          na grelha com contagem própria, entram nas listas de compra e na
          Venda como qualquer carta, mas NÃO contam para a percentagem.
          Escreve-se em `master_set.fora_da_percentagem`.
       3. as ESCONDIDAS — os tokens `-T` e as signatures `*`. Não aparecem na
          página (André, 2026-09-11: *"nunca vou colocar nenhuma, não vale a
          pena estarem lá"*). Escreve-se em `master_set.escondidas`.

     O ALVO é o mesmo nas duas primeiras: o playset do tipo da carta
     (Unit/Spell/Gear 3, Legend e Battlefield 1) — **excepto as runas, que
     são 1 de cada**, base ou especial. Até 2026-09-14 de manhã as variantes
     de dentro pediam 1 (decisões de 2026-09-08) e nessa tarde tudo pediu o
     playset, runas a 12 incluídas (*"muda tudo para playset"*); a frase da
     noite é a que vale. Ver `master_target`, `escondida`, `fora_do_master`,
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

# Os blocos da grelha, por esta ordem: primeiro o master set inteiro (André,
# 2026-09-08: *"master set playset todo seguido"*), depois a coleção extra —
# as runas especiais (*"1 runa especial de cada para cada set"*), as artes
# alternativas, as sobrenumeradas (*"também não quero para a coleção as
# overnumbered"*, 2026-09-10) e as promos (*"deparei-me com as VEN-SP (promos).
# Quero que as promos fiquem também à parte"*, 2026-09-10). Desde a noite de
# 2026-09-14 só o primeiro conta para a percentagem; os outros são «puramente
# coleção» (ver o cabeçalho do módulo). Os tokens e as signatures não aparecem
# (`master_set.escondidas`) — os blocos deles ficam na lista para o caso de
# alguém os tirar de lá.
#
# Há um bloco por variante, e não só para as que ele nomeou: assim uma
# variante nova recebe um cabeçalho a dizer o que é, em vez do «outras». Os
# blocos vazios não aparecem.
BLOCO_MASTER = "master"
BLOCO_RUNA = "rune_special"
# As sobrenumeradas (André, 2026-09-10) — as «300/298». Não são uma variante:
# é o NÚMERO que passa o tamanho da edição, por isso têm bloco próprio em vez
# de caírem no da variante delas. Ver `e_overnumbered`.
BLOCO_OVER = "overnumbered"
BLOCOS = [
    (BLOCO_MASTER, None),
    # O sufixo do alvo («— 1 de cada», «— playset») vem do alvo em vigor, não
    # está escrito aqui — ver `rotulo`.
    (BLOCO_RUNA, "Runas especiais"),
    ("alt_art", "Artes alternativas"),
    (BLOCO_OVER, "Sobrenumeradas"),
    # As `VEN-SP` (André, 2026-09-10). Chamam-se «promos» porque é o nome que
    # ele lhes deu e o que o catálogo lhes chama (`variant_label: "Promo"`); as
    # runas promo do VEN são outra coisa e caem nas runas especiais, acima.
    ("special", "Promos"),
    ("rune_promo", "Runas promo"),
    ("token", "Tokens"),
    ("signature", "Signatures"),
    ("base", "Impressões base"),
    ("outras", "Outras"),
]
BLOCO_LABEL = dict(BLOCOS)

# O prefixo do cabeçalho de um bloco que NÃO conta para a percentagem: é a
# palavra dele (*"é puramente coleção"*). Um bloco que conte — só o master set,
# hoje — não leva prefixo. Ver `rotulo()`.
PREFIXO_COLECAO = "Coleção — "

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
#   `tipos`   — o que É uma runa. Decide o ALVO de TODAS elas (`e_runa`), base
#               ou especial, dentro ou fora do master set.
#   `alvo`    — esse alvo: **1 por impressão** (André, 2026-09-14, à noite:
#               *"runas 1 de cada"*, dito como frase solta a seguir a *"quero
#               masterset com playset"* — vale para todas). Foi 1 de 2026-09-08
#               (*"apenas 1 de cada também, em vez de 12"*) até à tarde de
#               2026-09-14 (*"muda tudo para playset"*, 12), e voltou a 1 nessa
#               noite. `"playset"` continua a ser aceite e dá as 12.
#   `excepto` — quais é que ficam na SEQUÊNCIA do master set (só a base). O
#               resto vai para o bloco «runas especiais» (`e_runa_especial`) —
#               hoje as artes alternativas do OGN e as promo do VEN (a
#               RiftScribe não tem runas no SFD nem no UNL — ver "BURACO NO
#               CATÁLOGO" no CLAUDE.md).
#
# Muda-se em `runas_especiais` no config. `tipos: []` desliga as três coisas e
# as runas voltam a seguir o playset, como qualquer outra carta.
RUNA_ESPECIAL: dict = {"tipos": ["Rune"], "excepto": ["base"], "alvo": 1}

# O valor do `runas_especiais.alvo` que quer dizer «o playset do tipo», em vez
# de um número fixo. É a escrita dele de 2026-09-14 à tarde (*"muda tudo para
# playset"*); à noite voltou ao 1, mas a escrita fica aceite.
ALVO_PLAYSET = "playset"

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

# O valor das listas do `master_set` que NÃO é uma variante. As sobrenumeradas
# são um critério de NÚMERO — como o `showcase` do `a_subir.excluir` é um
# critério de raridade —, mas escrevem-se na mesma lista de propósito: a
# pergunta é uma só ("o que é que não é o master set") e tem de ter uma
# resposta só.
FORA_OVERNUMBERED = "overnumbered"

# As duas listas do `master_set`, com a MESMA gramática (ver `_ler_lista`):
#
#   `fora_da_percentagem` — a coleção extra (bloco 2): aparece, tem alvo de
#                           playset, não conta para a percentagem.
#   `escondidas`          — o que nem aparece (bloco 3).
#
# `fora` é o nome antigo (2026-09-08 a 2026-09-14) e continua a ser lido — ver
# `config._migrar_master_set`.
LISTA_FORA = "fora_da_percentagem"
LISTA_ESCONDIDAS = "escondidas"

# Memo do `_ler_lista`: as listas do config não mudam dentro de uma corrida, e
# a pergunta é feita uma vez por impressão (1180) por payload.
_FORA_MEMO: dict[tuple, tuple] = {}


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
    """Esta impressão é de uma RUNA — a pergunta do ALVO.

    André, 2026-09-14, à noite: *"runas 1 de cada"*. É **uma regra só** para
    as runas todas: base ou especial, dentro ou fora do master set, o alvo é o
    `runas_especiais.alvo` (1). Ver `master_target`.

    O que distingue a base da especial é só o BLOCO da grelha — a base fica na
    sequência, o resto vai para as runas especiais. Ver `e_runa_especial`.
    """
    return campo(printing, "type") in (opcoes_runa(cfg).get("tipos") or ())


def e_runa_especial(printing, cfg: dict | None = None) -> bool:
    """Esta impressão é uma «runa especial» — o bloco a seguir ao master set?

    André, 2026-09-08: *"1 runa especial de cada para cada set"*. A runa base
    fica na sequência e as outras impressões da runa — a arte alternativa e a
    promo — vão para um bloco próprio, por edição, antes da cauda das artes
    alternativas. Desde 2026-09-14 à noite esse bloco é coleção extra: não
    conta para a percentagem, como as artes alternativas de que é feito.

    **É só sobre o bloco, não sobre o alvo.** O alvo das duas é o mesmo (1) —
    ver `e_runa`.
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
    """O alvo de uma impressão — o que o tile mostra («2/3»).

    UMA regra (André, 2026-09-14, à noite): **se for runa, 1; senão, o playset
    do tipo** (`playset_targets_by_type`: Unit/Spell/Gear 3, Legend e
    Battlefield 1). Vale igual no master set e na coleção extra — *"Alt Art,
    overnumbered, etc etc mete Playset na contagem"* —, e é o mesmo número da
    métrica jogável, de propósito: colecionar 3 é ter as 3 que se jogam. Os
    tokens ficam com o `token_target` (1), como sempre.

    Até aqui havia três botões a dizer coisas diferentes
    (`master_targets_by_variant`, `master_variantes_playset`,
    `master_base_follows_type`) e as variantes de fora pediam 1 enquanto as de
    dentro pediam o playset. Os três deixaram de ser lidos; se ainda estiverem
    num config, não fazem nada.

    Quem tem a LINHA do catálogo na mão deve chamar o `alvo()`, não isto; os
    quatro escalares ficam para quem não a tem (e para os testes).
    """
    cfg = cfg or config.load()
    override = cfg.get("master_target_overrides", {}).get(printing_id)
    if override is not None:
        return int(override)
    if is_token:
        return int(cfg.get("token_target", 1))
    if e_runa({"type": card_type}, cfg):
        # *"runas 1 de cada"*, base ou especial. `"playset"` no `alvo` é a
        # escrita da tarde de 2026-09-14 e continua a dar as 12.
        alvo_runa = opcoes_runa(cfg).get("alvo", 1)
        if alvo_runa == ALVO_PLAYSET:
            return playset_target(card_type, is_token, cfg)
        return int(alvo_runa)
    return playset_target(card_type, is_token, cfg)


def alvo(printing, cfg: dict | None = None) -> int:
    """O alvo de uma LINHA do catálogo — a porta de entrada.

    É o `master_target` com o que a linha traz. Toda a produção passa por aqui
    (a grelha, os níveis, as listas de compra e a Venda) para não haver duas
    contas do mesmo alvo. `printing` pode ser um dicionário mínimo com
    `printing_id`, `variant_kind`, `type` e `is_token`.
    """
    return master_target(printing["printing_id"], printing["variant_kind"],
                         campo(printing, "type"), bool(campo(printing, "is_token")),
                         cfg, printing=printing)


def _ler_lista(nome: str, bruto: tuple) -> tuple[frozenset[str], bool]:
    """Uma lista do `master_set` lida: (variantes, as sobrenumeradas também?).

    A lista escreve-se como o André fala — pelo sufixo do código impresso
    (`["-T", "*"]`), pela palavra dele para a variante (`"promo"`), pelo nome
    interno dela (`["token", "signature"]`) ou pela palavra do que não é
    variante nenhuma (`"overnumbered"`). É a MESMA gramática para o
    `fora_da_percentagem` e para o `escondidas`, para não haver duas maneiras
    de dizer «signature».

    Um valor que não se reconheça REBENTA, e de propósito: uma variante nova
    (um `b`? um `sp7`?) tem de aparecer, não de ser ignorada em silêncio —
    ver CLAUDE.md, "Superfícies NÃO validadas".
    """
    memo = _FORA_MEMO.get((nome, bruto))
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
                f"master_set.{nome}: nao reconheco {valor!r}. Aceita: {aceites}")
    _FORA_MEMO[(nome, bruto)] = out = (frozenset(kinds), over)
    return out


def _lista(cfg: dict, nome: str) -> tuple:
    return tuple((cfg.get("master_set") or {}).get(nome) or ())


def _fora(cfg: dict | None = None) -> tuple[frozenset[str], bool]:
    """O que NÃO conta para a percentagem: `fora_da_percentagem` MAIS `escondidas`.

    O que está escondido não conta por construção — não há maneira de esconder
    uma variante da página e deixá-la a contar. Ver `_escondidas`.
    """
    cfg = cfg or config.load()
    fora = _ler_lista(LISTA_FORA, _lista(cfg, LISTA_FORA))
    esc = _escondidas(cfg)
    return (fora[0] | esc[0], fora[1] or esc[1])


def _escondidas(cfg: dict | None = None) -> tuple[frozenset[str], bool]:
    """O `master_set.escondidas` lido: (variantes, as sobrenumeradas também?).

    André, 2026-09-11 (à noite): *"podes tirar as signatures da coleção, nunca
    vou colocar nenhuma, não vale a pena estarem lá"*. Hoje é `["-T", "*"]`:
    os tokens e as signatures não aparecem na página — nem num bloco de fora.
    """
    cfg = cfg or config.load()
    return _ler_lista(LISTA_ESCONDIDAS, _lista(cfg, LISTA_ESCONDIDAS))


def kinds_fora(cfg: dict | None = None) -> frozenset[str]:
    """Os `variant_kind` que NÃO contam para a percentagem (blocos 2 e 3).

    Hoje as artes alternativas e as runas promo (`fora_da_percentagem`, André
    2026-09-14: *"o que é Alt Art e Overnumbered, etc etc é puramente
    coleção"*), as promos `VEN-SP` (2026-09-10) e, por estarem escondidas, os
    tokens e as signatures. A outra metade das listas é o `fora_overnumbered`,
    que não é por variante.
    """
    return _fora(cfg)[0]


def fora_overnumbered(cfg: dict | None = None) -> bool:
    """As sobrenumeradas ficam fora da percentagem? — a outra metade da lista.

    André, 2026-09-10: *"também não quero para a coleção as overnumbered"* e,
    2026-09-14: *"overnumbered […] mete Playset na contagem"* — fora da
    percentagem, dentro da coleção extra. Escreve-se `"overnumbered"` no
    `master_set.fora_da_percentagem`. Ver `e_overnumbered`.
    """
    return _fora(cfg)[1]


def kinds_escondidas(cfg: dict | None = None) -> frozenset[str]:
    """Os `variant_kind` que não aparecem na página da Coleção — `escondidas`."""
    return _escondidas(cfg)[0]


def escondida(printing, cfg: dict | None = None) -> bool:
    """Esta impressão fica FORA DA PÁGINA da Coleção — o bloco 3?

    É a única resposta a esta pergunta: o `set_payload` (a grelha), o
    `sets_payload` (o «N impressões» do separador), as listas de compra
    (`a_subir.masterset`) e a Venda (`venda.excedente`, que lhe dá alvo 0)
    perguntam aqui. O que sai daqui não desaparece do vault: as cópias
    continuam no `copies`, contam para o valor, e a Venda — que lê o `copies`
    directamente — continua a listá-las como excedente inteiro.
    """
    cfg = cfg or config.load()
    kinds, over = _escondidas(cfg)
    if campo(printing, "variant_kind", "unknown") in kinds:
        return True
    return bool(over and e_overnumbered(printing))


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


def fora_do_master(printing, cfg: dict | None = None) -> str | None:
    """PORQUE é que esta impressão não conta para a percentagem — o bloco, ou `None`.

    Uma pergunta, uma função: quem quer saber se conta chama o `e_master`, quem
    quer saber onde é que ela vai parar na grelha chama o `bloco`, e os dois
    saem daqui. O motivo é o bloco porque é isso que ele lê no cabeçalho —
    «Coleção — sobrenumeradas» é diferente de «Coleção — promos». As
    escondidas também saem daqui (o `_fora` junta as duas listas): quem quer
    saber se APARECE pergunta ao `escondida`.

    A ordem é a das decisões dele: primeiro a VARIANTE que ele nomeou (o sufixo
    do código), depois o NÚMERO. É por isso que as 36 signatures continuam a
    ser «signature» — são todas sobrenumeradas, mas o que as tirou foi a frase
    de 2026-09-09, e mudá-las de motivo agora era apagar essa decisão.

    Chamava-se `fora_da_colecao` até 2026-09-14: desde essa noite a coleção
    extra É coleção (*"puramente coleção"*), o que ela não é é master set.
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
    """Esta impressão é MASTER SET — isto é, conta para a percentagem?

    É a única resposta a esta pergunta em todo o riftvault: usam-na a métrica
    (o denominador da percentagem e os níveis), a grelha da Coleção (o bloco
    que conta) e a Venda (o âmbito estreito, «a sequência nunca se vende»).

    A REGRA É O CÓDIGO IMPRESSO (André, 2026-09-08): o que ele mandou tirar
    escreve-se pelo sufixo, e no catálogo lê-se pelo `variant_kind`, que é
    derivado do mesmo sufixo:

      `UNL-T03`   -> variant `t03` -> kind `token`
      `UNL-228a`  -> variant `a`   -> kind `alt_art`

    Muda-se em `master_set.fora_da_percentagem` (hoje `["a", "-R",
    "overnumbered", "promo"]`) e `master_set.escondidas` (`["-T", "*"]`). A
    história das decisões está no cabeçalho do módulo e no CLAUDE.md; a última
    é de 2026-09-14 à noite — *"só quero % de completo para masterset!"* —, e
    é a que tirou as artes alternativas e as runas especiais da percentagem.

    Não confundir com o ALVO (`master_target`): o alvo é o que o tile mostra
    ("2/3"), isto é o que entra no denominador. São duas perguntas diferentes
    e têm dois campos desde 2026-09-02. Nem com o `e_colecao`, que diz se está
    na PÁGINA e nas listas de compra.

    Aceita uma linha do `catalog.printings` ou qualquer dicionário com
    `variant_kind` e `is_token` — as sobrenumeradas precisam também do
    `public_code` e do `collector_number`, e sem eles a resposta é "não é".

    É `conta_bloco(bloco(...))`, e não o `fora_do_master` directamente, para a
    barra (que soma por bloco) e os níveis (que somam por impressão) não
    poderem discordar: uma runa especial conta se e só se o bloco dela conta.
    """
    return conta_bloco(bloco(printing, cfg), cfg)


def e_colecao(printing, cfg: dict | None = None) -> bool:
    """Esta impressão é COLEÇÃO — está na página, tem alvo, compra-se?

    O master set (bloco 1) e a coleção extra (bloco 2), que é tudo o que não
    está escondido. É o âmbito das listas de compra (`a_subir.masterset`) e o
    que a Venda protege até ao alvo. O que conta para a PERCENTAGEM é menos do
    que isto — só o bloco 1, ver `e_master`.
    """
    return not escondida(printing, cfg)


def bloco(printing, cfg: dict | None = None) -> str:
    """Em que bloco da grelha é que esta impressão cai.

    Primeiro o master set inteiro, depois a coleção extra em blocos próprios —
    as runas especiais, as artes alternativas, as sobrenumeradas, as promos —,
    nunca intercalados. Ver `BLOCOS` para a ordem. Uma impressão escondida
    devolve o bloco da variante dela na mesma (`token`, `signature`); é o
    `set_payload` que a deixa de fora da grelha.
    """
    # A runa especial ganha à arte alternativa: a arte alternativa de uma runa é
    # das duas coisas, e ele pediu-a no bloco das runas ("1 runa especial de
    # cada para cada set"), antes da cauda das alt arts. Mas não ganha ao
    # escondido: uma signature de runa, se um dia existir, não aparece.
    if not escondida(printing, cfg) and e_runa_especial(printing, cfg):
        return BLOCO_RUNA
    fora = fora_do_master(printing, cfg)
    if fora is not None:
        return fora
    if printing["variant_kind"] == "alt_art":
        return "alt_art"
    return BLOCO_MASTER


def conta_bloco(bloco_id: str, cfg: dict | None = None) -> bool:
    """Este bloco entra na percentagem de completo?

    Só o master set (André, 2026-09-14: *"só quero % de completo para
    masterset!"*). Os outros são coleção extra ou escondidos, e existem para
    ele ver o que tem — não para a barra.

    A excepção é de config, não de hoje: se alguém tirar uma variante do
    `fora_da_percentagem`, o bloco dela volta a contar (é o «1 alt art de cada»
    de 2026-09-08, a uma linha de distância). O bloco das runas especiais é
    feito de variantes (artes alternativas e runas promo) e conta só quando
    nenhuma delas está fora.
    """
    if bloco_id == BLOCO_MASTER:
        return True
    kinds = kinds_fora(cfg)
    if bloco_id == BLOCO_RUNA:
        # As variantes que podem cair neste bloco: tudo o que não é a base (o
        # `excepto`) nem um token — um token nunca é runa especial.
        variantes = (set(KIND_ORDER) - {"token", "unknown"}
                     - set(opcoes_runa(cfg).get("excepto") or ()))
        return not (variantes & kinds)
    if bloco_id in KIND_ORDER:
        return bloco_id not in kinds
    return False


def _sufixo_alvo(bloco_id: str, cfg: dict) -> str:
    """«— playset» ou «— N de cada», conforme o alvo que o bloco pede hoje.

    Lê-se do mesmo config que o `master_target` lê, para o título e o badge do
    tile não divergirem: as runas especiais dizem o `runas_especiais.alvo`, os
    tokens o `token_target`, e todos os outros o playset do tipo.
    """
    if bloco_id == BLOCO_RUNA:
        alvo_bloco = opcoes_runa(cfg).get("alvo", 1)
    elif bloco_id == "token":
        alvo_bloco = int(cfg.get("token_target", 1))
    else:
        alvo_bloco = ALVO_PLAYSET
    if alvo_bloco == ALVO_PLAYSET:
        return " — playset"
    return f" — {int(alvo_bloco)} de cada"


def rotulo(bloco_id: str, cfg: dict | None = None) -> str | None:
    """O cabeçalho do bloco. `None` no primeiro: a sequência não leva título.

    Os blocos que não contam levam «Coleção — » à frente — é a palavra dele
    (*"é puramente coleção"*) — e o alvo que pedem atrás.
    """
    cfg = cfg or config.load()
    base = BLOCO_LABEL.get(bloco_id)
    if not base:
        return base
    if conta_bloco(bloco_id, cfg):
        return base + _sufixo_alvo(bloco_id, cfg)
    return PREFIXO_COLECAO + base[0].lower() + base[1:] + _sufixo_alvo(bloco_id, cfg)


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
# O ÂMBITO É O MESMO DA BARRA — as impressões que `e_master` deixa contar (só
# o master set, desde 2026-09-14 à noite), pelo alvo do `master_target`. Não é
# um âmbito novo: se fosse, a percentagem do último nível não batia certo com a
# barra por cima da qual ela aparece. As impressões de alvo 1 — as runas, os
# Legends, os Battlefields — só podem faltar no nível 1; do nível 2 em diante
# contam como feitas, porque `min(k, alvo)` nunca lhes pede mais do que 1. É
# por isso que a percentagem do nível mais alto é EXACTAMENTE a da barra do
# master set. A coleção extra (artes alternativas, sobrenumeradas, promos) não
# entra aqui, como não entra na barra.
#
# CONTA CÓPIAS, NÃO O QUE VEM A CAMINHO. É a regra da Coleção — o `pending` fica
# fora do `copies` de propósito, e as barras não mexem enquanto a encomenda vem
# (ver CLAUDE.md, "Encomendas a caminho"). As wantlists por nível descontam o
# pendente, porque aí a pergunta é o que ainda há a COMPRAR; aqui é o que está
# na caixa.


def alvo_do_nivel(k: int, n: int, alvo: int) -> int:
    """O alvo da impressão no degrau k de n: `min(k, alvo)`, e no ÚLTIMO degrau
    o alvo inteiro.

    É a frase dele — *"1 de cada, 2 de cada, o playset de cada"*: o último
    degrau é o playset, seja ele 3 ou 12. Enquanto o maior alvo da Coleção era
    3 as duas leituras davam o mesmo; desde *"muda tudo para playset"*
    (2026-09-14) as runas pedem 12, e `min(3, 12)` deixava o «3/3» a 3 cópias
    da runa — a barra do master set, que pede as 12, já não batia com ele.
    Ver `degraus`.
    """
    return alvo if k >= n else min(k, alvo)


def degraus(itens, cfg: dict | None = None) -> int:
    """Quantos níveis há: 1 de cada, 2 de cada, …, e o playset no fim.

    São `min(maior alvo do âmbito, playset comum)`, com o playset comum a ser o
    `playset_targets_by_type.default` (3). Não é um número escrito à mão para
    os níveis: é o playset de uma carta qualquer, que é o que ele descreveu
    (*"do género 1/3 Z % · 2/3 X % · 3/3 Y %"*).

    Era «o maior alvo do âmbito», e dava o mesmo (3) enquanto as runas pediam 1.
    Com as runas a 12 (2026-09-14) davam 12 degraus, e do 4.º ao 12.º só as 24
    runas mexiam — nove colunas iguais para uma leitura de relance. O último
    degrau pede o playset INTEIRO de cada impressão (`alvo_do_nivel`), por isso
    a runa continua a pedir as 12 no «3/3» e a percentagem desse degrau continua
    a ser EXACTAMENTE a da barra.
    """
    cfg = cfg or config.load()
    maior = max((a for a, _, _ in itens), default=0)
    comum = int(cfg.get("playset_targets_by_type", {}).get("default", 3))
    return min(maior, comum) if maior else 0


def niveis(itens, n: int | None = None, cfg: dict | None = None) -> list[dict]:
    """A contagem por níveis de uma lista de `(alvo, tem, preço|None)`.

    Para cada nível k, o alvo é o do `alvo_do_nivel` — `min(k, alvo)`, e o
    alvo inteiro no último degrau:

      `missing` = Σ max(0, alvo_k − tem)   — cópias que faltam
      `done`    = quantas impressões já lá chegaram
      `cents`   = o que custam essas cópias ao preço de hoje

    `n` é quantos níveis se fazem; por omissão, os `degraus`. O denominador é
    o mesmo em todos os níveis (as impressões todas do âmbito), senão as
    percentagens não eram comparáveis entre si.
    """
    itens = [(a, t, p) for a, t, p in itens if a > 0]
    if n is None:
        n = degraus(itens, cfg)
    saida = []
    for k in range(1, int(n) + 1):
        done = total = missing = cents = 0
        for alvo, tem, preco in itens:
            total += 1
            falta = max(0, alvo_do_nivel(k, int(n), alvo) - tem)
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
        if n <= 0 or not e_master(r, cfg):
            continue
        out.append((r["set_id"], n, qty.get(pid, 0), price.get(pid)))
    return out


def niveis_max(con: sqlite3.Connection, cfg: dict | None = None) -> int:
    """Quantos níveis há, medido em TODO o catálogo — ver `degraus`.

    Vem do catálogo inteiro e não de cada edição para as cinco mostrarem os
    mesmos degraus — uma edição só de Legends daria um nível só, e o `1/3` de
    uma deixava de ser comparável com o `1/1` da outra.

    Hoje são **3**: 1 de cada, 2 de cada, e o playset — que nas runas são 12
    desde 2026-09-14. Até aí era «o maior alvo do catálogo», que dava os mesmos
    3 porque as runas pediam 1.
    """
    return degraus([(a, t, p) for _, a, t, p in itens_da_colecao(con, cfg)], cfg)


def niveis_payload(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """A contagem por níveis GLOBAL e por edição, com os mesmos degraus.

    O `by_set` vai para o cliente para ele poder trocar a edição aberta pelos
    números locais (otimistas) sem perder as outras quatro: os campos são todos
    somas, por isso o global é a soma das edições.
    """
    cfg = cfg or config.load()
    itens = itens_da_colecao(con, cfg)
    n = degraus([(a, t, p) for _, a, t, p in itens], cfg)
    por_set: dict[str, list] = {}
    for s, alvo, tem, preco in itens:
        por_set.setdefault(s, []).append((alvo, tem, preco))
    return {
        "max": n,
        "levels": niveis([(a, t, p) for _, a, t, p in itens], n, cfg),
        "by_set": {s: niveis(v, n, cfg) for s, v in por_set.items()},
    }


# --------------------------------------------------------------------------
# Payloads
# --------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sets_payload(con: sqlite3.Connection, cfg: dict | None = None) -> list[dict]:
    """As edições, com o «N impressões» do separador.

    O N é o que está NA PÁGINA — sem as escondidas (`master_set.escondidas`).
    Um separador a dizer 352 por cima de uma grelha com 340 tiles lia-se como
    erro de contagem.
    """
    cfg = cfg or config.load()
    por_set: dict[str, int] = {}
    for r in con.execute(
        "SELECT set_id, variant_kind, collector_number, public_code "
        "FROM catalog.printings"
    ):
        if not escondida(r, cfg):
            por_set[r["set_id"]] = por_set.get(r["set_id"], 0) + 1
    out = [
        {"id": s, "name": config.set_name(s),
         "order": config.set_order(s), "n_printings": n}
        for s, n in por_set.items()
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

    # O que está escondido (André, 2026-09-11: *"podes tirar as signatures da
    # coleção, nunca vou colocar nenhuma"*; os tokens desde 2026-09-14) não vai
    # para a grelha — nem para um bloco de fora. Guarda-se à parte só para o
    # VALOR: uma cópia que ele tenha continua na caixa e vale o mesmo, e o
    # total desta edição tem de bater certo com o `prices.collection_value`,
    # que lê o `copies` inteiro.
    escondidas_valor: list[tuple[int, int]] = []
    groups: dict[str, dict] = {}
    for r in rows:
        if escondida(r, cfg):
            preco = price.get(r["printing_id"])
            if preco is not None:
                escondidas_valor.append((totais.get(r["printing_id"], 0), preco))
            continue
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
            # O bloco da grelha: `master` para o que conta, e um bloco próprio
            # para cada pedaço da coleção extra. É o mesmo campo que diz se
            # entra na percentagem (ver `conta_bloco`).
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
    # TODOS os blocos têm contador próprio ("tens N de M"); só o master set
    # entra na percentagem global — a coleção extra não, e é o ponto todo de
    # ser extra (André, 2026-09-14: *"só quero % de completo para masterset"*).
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
            # "se estivesse completa" é sobre o MASTER SET: o que não entra na
            # percentagem também não entra no preço de a fechar — a coleção
            # extra é a mais, e o preço dela está nas wantlists.
            if conta_bloco(p["block"], cfg):
                value_full += p["target"] * p["price"]
    # As escondidas: valem o que ele tem delas, e não entram no «se estivesse
    # completa» — estão fora da percentagem por construção (ver `_fora`).
    for qty_total, preco in escondidas_valor:
        value_owned += qty_total * preco

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
        # As variantes que não estão na página (`master_set.escondidas`), para o
        # filtro de tipo de impressão não oferecer um chip que não filtra nada.
        "hidden_kinds": sorted(kinds_escondidas(cfg)),
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
