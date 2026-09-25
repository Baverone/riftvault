"""Caminhos do projeto e leitura do riftvault_config.json.

Tudo o que está no config é conhecimento do André ou palpite meu — nada disto
vem da API da RiftScribe. Ver CLAUDE.md, "Superfícies NÃO validadas".
"""

from __future__ import annotations

import json
import os
import re
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
# O «seguir jogadores» (2026-09-17): o estado (`estado.json`, vai para o Git)
# e a última página lida de cada endereço (`paginas/`, não vai). Ver `seguir.py`.
SEGUIR_DIR = Path(os.environ.get("RIFTVAULT_SEGUIR", DATA_DIR / "seguir"))
# O «Produto Selado» (2026-09-25): a lista do que EXISTE — displays, cases,
# decks, bundles, Proving Grounds —, tal como o CardTrader a dá. Vai para o
# Git (é o catálogo, não a coleção: texto, pequeno, e o site publicado precisa
# dele) e atualiza-se com `riftvault selado --sync`. Ver `selado.py`.
SELADO_PATH = Path(os.environ.get("RIFTVAULT_SELADO", DATA_DIR / "selado_catalogo.json"))

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
    #   `um_de_cada`          — O ALVO POR CATEGORIA da coleção extra: o que
    #                           está aqui pede 1 de cada, o que não está pede
    #                           o playset do tipo. Hoje as sobrenumeradas
    #                           (2026-09-15: "overnumbered e promos (SP)
    #                           voltamos a 1 de cada / se eu tiver mais
    #                           adiciono na mesma") e as promos `VEN-SP`
    #                           (2026-09-19: "as Promo passam a 1 de cada ao
    #                           inves de playset"). As artes alternativas
    #                           estiveram aqui de 2026-09-16 ("Alt Art e
    #                           Overnumbered e assim quero apenas 1 de cada")
    #                           a 2026-09-18 ("muda novamente: Alt Art para
    #                           playset, overnumbered continua 1 de cada") e
    #                           pedem o playset. As promos andaram: playset a
    #                           2026-09-14, 1 a 2026-09-15, playset a
    #                           2026-09-18 ("as promos SP podes meter 3 de
    #                           cada"), 1 outra vez a 2026-09-19. Só o ALVO; o
    #                           bloco, a percentagem e as listas de compra não
    #                           mexem. O alvo NUNCA sobe por causa dos decks
    #                           (o «max(1, procura dos decks)» de 2026-09-16
    #                           saiu a 2026-09-17).
    #   `ordem_dos_blocos`    — A ORDEM dos blocos na grelha da Coleção
    #                           (2026-09-19: "coloca as OverNumbered a seguir
    #                           ao master Set, depois as AltArt, depois as
    #                           Promos") — e, desde a tarde desse dia, também
    #                           dos quatro blocos do separador Faltas
    #                           (`faltas_edicao.blocos`). A mesma gramática,
    #                           mais o id do bloco; o que não estiver aqui vem
    #                           a seguir, pela ordem do catálogo
    #                           `metrics.BLOCOS` (hoje só as runas especiais,
    #                           vazias). Só a ordem — não mexe no que cada
    #                           bloco mostra nem no alvo.
    # `fora` é o nome antigo da primeira (2026-09-08 a 2026-09-14) e continua a
    # ser lido. Ver `metrics._fora`, `metrics.escondida`, `metrics.e_master`,
    # `metrics.e_um_de_cada` e `metrics.ordem_dos_blocos`.
    "master_set": {"fora_da_percentagem": ["a", "overnumbered", "promo"],
                   "escondidas": ["-T", "*", "-R"],
                   "um_de_cada": ["overnumbered", "promo"],
                   "ordem_dos_blocos": ["master", "overnumbered", "a", "promo"]},
    # O que os decks JOGAM.
    #   `so_base`            — SÓ VERSÕES BASE, A LEGEND E O CHAMPION INCLUÍDOS
    #                          (André, 2026-09-21, ao acabar a experiência do
    #                          pool próprio: é a última coisa que disse sobre
    #                          versões e mantém-se). Com `true` (a omissão) um
    #                          lugar de deck só se serve de `variant_kind ==
    #                          "base"` não sobrenumerada — sem alt art, sem
    #                          sobrenumeradas, sem promos, sem assinadas, sem o
    #                          recurso a «o que houver de não-assinado» — e a
    #                          regra de 2026-09-17 (a Legend/Champion numa
    #                          versão especial) NÃO se aplica, esteja o que
    #                          estiver em `so_normais_excepto`. Com `false`
    #                          qualquer versão não assinada serve um lugar
    #                          normal (a base primeiro, depois as outras que
    #                          ele tenha — `Versoes.outras_de`) e as duas
    #                          chaves a seguir voltam a ser lidas. Desliga-se
    #                          mudando esta chave sozinha.
    #   `so_normais_excepto` — (só com `so_base: false`) os PAPÉIS da lista do
    #                          deck que jogam uma versão especial (André,
    #                          2026-09-17: "os decks apenas jogaram versoes
    #                          normais, com excepcao da Legend e do Champion
    #                          que serao Alt Art ou Overnumbered ou SP, mas
    #                          nunca assinada"); os outros papéis jogam a base.
    #                          Vazio (a omissão desde 2026-09-21): os decks
    #                          jogam tudo na base — a regra de 2026-09-17 está
    #                          DESLIGADA e não volta só por `so_base` ir a
    #                          `false`; volta escrevendo aqui os papéis.
    #   `versoes_especiais`  — o que conta como «versão especial», na gramática
    #                          das listas do `master_set` (sufixo, palavra ou
    #                          nome da variante, mais `overnumbered`). A
    #                          signature (`*`) NUNCA entra — «nunca assinada»
    #                          é regra, não config — e escrevê-la aqui rebenta.
    # Só UMA cópia por papel é especial (a Legend é 1 por deck; um Champion
    # que a lista jogue mais vezes tem as restantes na base); qualquer das
    # versões especiais serve, e o que falta compra-se na mais barata. Sem
    # versão especial no catálogo, o deck joga a base e não há falta. As runas
    # em alt art continuam retiradas (a seguir). Ver `decks.Versoes` e
    # `decks.versoes_dos_decks`. (O `jogam_alt_art`/`alt_art_ignorar_tipos`
    # de 2026-09-16 deixou de existir; um config que ainda os traga não faz
    # nada.)
    #   `contar_runas`       — AS RUNAS SAEM DA CONTAGEM DOS DECKS (André,
    #                          2026-09-17, à noite: "esquece as runas, nao
    #                          facas contagem de runas nos decks, indica me so
    #                          quantas sao e eu organizo isso sozinho a mao").
    #                          Com `false` o Rune Pool continua a ler-se e a
    #                          mostrar-se com as quantidades, mas não há
    #                          tenho/faltam, alocação, disputa, falta a comprar
    #                          nem euros para as runas, e o «tenho X de N» do
    #                          deck conta só o resto. «Runa» é o
    #                          `runas_especiais.tipos`. `true` volta a contar
    #                          como até essa noite.
    #   `ordem`              — A ORDEM DOS DECKS (2026-09-21): o slug ou o
    #                          `Nome:` de cada um, pela ordem em que ele os
    #                          quer ver; o primeiro é o principal. Enquanto a
    #                          lista existir é ela que manda na prioridade, a
    #                          cada importação; o que não nomear vem a seguir;
    #                          acrescentar um deck no fim basta. Os botões de
    #                          reordenar do site e o `riftvault decks --order`
    #                          ficam desligados. Vazia: a prioridade guardada
    #                          na base, como até aqui. Ver `decks.aplicar_ordem`.
    #   `modo`               — `coleccao`, e só isso: os decks servem-se da
    #                          Coleção por prioridade (2026-09-11), e cada deck
    #                          tem ainda as suas CÓPIAS PRÓPRIAS (2026-09-21,
    #                          `proprias.py`: o local `proprio:<slug>`, com
    #                          `+`/`−` em cada carta do deck, que servem antes
    #                          da Coleção e nunca contam para ela). O valor
    #                          `pool_proprio` foi a experiência de 2026-09-21
    #                          de manhã (um pool único, partilhado, fora da
    #                          Coleção) e ACABOU nesse mesmo dia: escrevê-lo
    #                          rebenta, com a razão — não há código atrás dele.
    #   `montados`           — QUE DECKS ESTÃO MONTADOS (André, 2026-09-24:
    #                          *"vamos desmontar os decks todos com excepcao da
    #                          LeBlanc, vou colocar tudo nos binders das edicoes
    #                          e depois voltar a montar deck a deck"*). O slug
    #                          ou o `Nome:` de cada deck montado. Um deck
    #                          DESMONTADO não consome NADA da Coleção: não
    #                          aparece na grelha como uso, não entra na
    #                          alocação, não gera libertadas, não entra no
    #                          «falta encomendar aos decks» — a Coleção dá
    #                          exactamente os mesmos números que daria se ele
    #                          não existisse. A lista dele continua a ver-se, e
    #                          a página diz o que ele PRECISARIA se fosse
    #                          montado a seguir (uma simulação, que não
    #                          consome). **Sem a chave, todos montados** (é o
    #                          que valia até aqui); a lista VAZIA é «nenhum
    #                          montado» — são coisas diferentes, e o botão de
    #                          desmontar o último escreve `[]`. Ver
    #                          `decks.montados` e `decks.alternar_montado`.
    #   `coleccao_so_a_partir_de`
    #                        — A REGRA DE RARIDADE (mesmo dia: *"vou tentar ao
    #                          maximo que cartas de raridade Rara para baixo
    #                          fiquem alocadas exclusivamente a coleccao e as
    #                          repetidas exclusivamente aos decks […] apenas
    #                          miticas para acima devo ter que usar as da
    #                          coleccao"*). Da raridade escrita para CIMA
    #                          (`metrics.RARITY_ORDER`: common < uncommon <
    #                          rare < epic < showcase) um deck pode servir-se
    #                          da Coleção sem aviso; abaixo dela, devia vir das
    #                          cópias próprias do deck. **NÃO BLOQUEIA — MARCA**:
    #                          a carta leva um aviso e o deck um contador «N
    #                          cópias a sair da Coleção que não deviam».
    #                          (No Riftbound não há «mítica»: a raridade de
    #                          topo é a `epic`.) `null` ou `""` desliga o
    #                          aviso; uma raridade que o catálogo não conheça
    #                          rebenta. Ver `decks.raridades_da_colecao`.
    "decks": {"so_base": True,
              "so_normais_excepto": [],
              "versoes_especiais": ["a", "overnumbered", "promo"],
              "contar_runas": False,
              "ordem": [],
              # `None` (e não `[]`) é o default de propósito: sem a chave,
              # TODOS montados. A lista vazia quer dizer «nenhum».
              "montados": None,
              "coleccao_so_a_partir_de": "epic",
              "modo": "coleccao"},
    # O bloco das runas especiais ("1 runa especial de cada para cada set",
    # 2026-09-08) — só o BLOCO. O `alvo` que aqui vivia (1, "runas 1 de cada")
    # deixou de ser lido a 2026-09-15: as runas pedem o alvo do tipo, como
    # tudo o resto. `retiradas` (2026-09-17: "deixa as runas Alt Art, nao
    # incluas em nada") são as variantes de runa que DEIXAM DE EXISTIR para o
    # riftvault — não aparecem, não contam para nada, os decks não as pedem;
    # com isso o bloco ficou vazio no catálogo de hoje. Ver
    # `metrics.RUNA_ESPECIAL` e `metrics.retirada`.
    "runas_especiais": {"tipos": ["Rune"], "excepto": ["base"], "retiradas": ["a"]},
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
    # O separador «A mais» (2026-09-17): o que ele tem acima do alvo e o que
    # os decks libertaram. Um botão por edição, menos estas (o OGS, como na
    # tabela de preços que se apagou a 2026-09-19); a edição sem botão
    # continua em «Todas». `sem_runas`
    # (André, 2026-09-17, à noite: "no a mais nunca aparece Runas"): as runas
    # não entram em nenhum dos dois blocos — nem no excedente nem nas
    # libertadas —; ele trata delas à mão. Ver `a_mais.py`.
    "a_mais": {"sem_edicoes": ["OGS"], "sem_runas": True},
    # O separador «Encomendas» (2026-09-17: "igual à coleção, mas só de Raras
    # para cima"): a grelha da Coleção cortada à raridade da BASE a partir
    # desta, na ordem `metrics.RARITY_ORDER` (common < uncommon < rare < epic
    # < showcase). Ver `pending.grelha`.
    "encomendas": {"raridade_minima": "rare"},
    # O bloco «Runas — 12 de cada» no fim da grelha da Coleção (André,
    # 2026-09-19: "mete 12 runas de cada (nao contabilizes para nada, e so para
    # mim para contabilizar ali algumas coisas)"). É uma VISTA: conta tudo o
    # que ele fisicamente tem de cada runa, e não entra em métrica nenhuma.
    # Ver `runas_vista.py`.
    "runas_vista": {"alvo": 12},
    # A contagem de FOIL e NÃO-FOIL (André, 2026-09-22: *"para comuns e
    # incomuns, coloca contagem para Foil e Non-Foil, para todas as edicoes
    # excepto Proving Grounds"*). O âmbito, para ele mudar sem código:
    #   `raridades`     — as raridades da BASE que levam contador (hoje as
    #                     comuns e as incomuns). Uma raridade que o catálogo
    #                     não conheça rebenta; a lista vazia também.
    #   `edicoes_fora`  — as edições sem contador. «Proving Grounds» é o OGS.
    # Vale só para as impressões BASE, não sobrenumeradas — a arte alternativa
    # e a reimpressão de topo de set são outra impressão. Hoje dá 512
    # impressões e 1376 cópias. O contador é uma REPARTIÇÃO do que ele já tem
    # (`copies.qty_foil`, com o não-foil sempre derivado) e não entra em conta
    # nenhuma do site. Ver `foil.py`.
    "foil": {"raridades": ["common", "uncommon"], "edicoes_fora": ["OGS"]},
    # O separador «Venda» (André, 2026-09-25: *"permite-me marcar as cartas
    # que estou a vender no momento para apresentar a conta a pessoa. todos os
    # precos tem que ser o Trend do Cardmarket!"*).
    #   `trend_valido_dias`  — a partir de quantos dias é que um Trend guardado
    #                          se marca como velho. Não se apaga: um Trend de
    #                          há duas semanas é melhor ponto de partida do que
    #                          um campo em branco.
    #   `cardmarket_url`     — o link da carta no Cardmarket, com `{id}` = o
    #                          `cardmarket_id` do `cardtrader_map` (1178 das
    #                          1179 impressões têm um). **NÃO VALIDADO** — o
    #                          site deles responde 403 a pedidos automáticos e
    #                          não há conta para experimentar; se abrir em 404,
    #                          muda-se esta linha e todos os links mudam.
    #   `cardmarket_busca`   — o segundo link de cada linha (e o único da
    #                          impressão sem id): pesquisa pelo nome de
    #                          mercado, `{q}` já codificado.
    # A conta faz-se SÓ com o Trend que ele mete à mão; o preço do CardTrader
    # aparece ao lado, rotulado, e nunca entra no total. Ver `venda.py`.
    "venda": {"trend_valido_dias": 7,
              "cardmarket_url":
                  "https://www.cardmarket.com/en/Riftbound/Products/Singles?idProduct={id}",
              "cardmarket_busca":
                  "https://www.cardmarket.com/en/Riftbound/Products/Search?searchString={q}"},
    # As línguas cujas ofertas do CardTrader entram no preço (2026-09-15:
    # "apenas cartas versao ingles"). Era 'en' fixo no código desde o início.
    "precos": {"linguas": ["en"]},
    # Seguir jogadores no Piltover Archive (André, 2026-09-17: "o @koko_lopez e
    # um jogador muito bom, gostava de seguir os decks que ele coloca e que vai
    # atualizando" / "nao preciso que me diga quanto custaria, mas sim o que
    # falta"). `jogadores` são os handles (o `/users/<nome>` do site);
    # `intervalo_segundos` é o mínimo entre dois pedidos ao site (nunca menos
    # de 1 — é a regra de educação, `seguir.INTERVALO_MINIMO`); `max_paginas`
    # trava a listagem `/decks?q=<nome>` para um nome muito comum não puxar
    # centenas de páginas. Ver `seguir.py`.
    "seguir": {"jogadores": [], "intervalo_segundos": 1.0, "max_paginas": 10},
    # As abas que NÃO se mostram (André, 2026-09-25: "Tira a aba 'A mais',
    # 'Por Deck' e 'Pimp Deck'"). Escondidas, não apagadas: o cálculo, as rotas
    # e a CLI ficam — o «A mais» continua a ser calculado e o
    # `api/a_mais.json` a ser gerado; o que sai é o botão, no 8770 e no site
    # publicado. **Repor uma aba é tirar o nome desta lista, mais nada.** Os
    # nomes são os ids das abas — `inicio`, `colecao`, `faltas-edicao`,
    # `a-mais`, `decks`, `staples`, `pordeck`, `pimp`, `encomendas`, `venda` —
    # e aceitam-se também como ele as lê no ecrã («A mais», «Por deck», «Pimp
    # deck»). Um nome desconhecido rebenta. Ver `abas.py`.
    "abas": {"escondidas": []},
    # O separador «Produto Selado» (André, 2026-09-25: *"tudo o que e produtos
    # de coleccao do Riftbound, como displays ou boxcase, ou duel decks,
    # proving ground, etc etc, para eu saber o que ha, o que tenho e o que nao
    # tenho"*).
    #   `categorias`        — os ids das CATEGORIAS do CardTrader que contam
    #                         como produto selado. A separação selado/single é
    #                         deles, não minha: o `GET /categories` dá treze
    #                         categorias de Riftbound com nome, e a 258 são as
    #                         cartas (`prices.SINGLES_CATEGORY`). Por omissão
    #                         entram 259 Booster Boxes, 260 Boosters, 261
    #                         Bundles, 262 Starter Decks, 263 Box Sets &
    #                         Displays e 283 Complete Sets. Os ACESSÓRIOS — 264
    #                         Playmats, 265 Albums, 266 Sleeves, 267 Deck
    #                         Boxes, 268 Memorabilia — e as 284 Oversized ficam
    #                         de fora, contados no `scope.fora` da página;
    #                         metê-los é acrescentar o número aqui. Escrever a
    #                         258 rebenta.
    #   `datas_por_edicao`  — a data de saída de cada edição, por código do
    #                         CardTrader. **Vem dele** — a API não dá data
    #                         nenhuma (uma expansão são quatro campos). Um
    #                         produto com data no futuro aparece «por sair» e
    #                         NÃO conta para o que falta.
    #   `por_sair`          — as edições anunciadas sem data exacta (*"depois
    #                         Legacy (LGC) e The Reckoning (REC) em 2027"*).
    #   `ordem_das_edicoes` — a ordem no ecrã; o que não estiver aqui vem a
    #                         seguir, por código.
    #   `extra`             — produtos que a API não tem (regionais,
    #                         promocionais), à mão: `nome` (obrigatório),
    #                         `edicao`, `tipo`, `data`, `preco_eur`, `nota`. A
    #                         lista da app é a da API MAIS estes. Um `tipo` que
    #                         não exista rebenta.
    # O SELADO NÃO ENTRA NA COLEÇÃO: nem níveis, nem denominador, nem A mais,
    # nem Faltas, nem wantlists, nem decks, nem foil, nem próprias, nem Venda —
    # e o valor dele é um total próprio, nunca somado ao da Coleção. Ver
    # `selado.py`.
    "selado": {"categorias": [259, 260, 261, 262, 263, 283],
               "datas_por_edicao": {"OGN": "2025-10-31", "SFD": "2026-02-13",
                                    "UNL": "2026-05-08", "VEN": "2026-07-31",
                                    "RAD": "2026-10-23"},
               "por_sair": ["LGC", "PG2", "REC"],
               "ordem_das_edicoes": ["OGN", "OGS", "SFD", "UNL", "VEN",
                                     "RAD", "LGC", "PG2", "REC"],
               "extra": []},
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


def escrever_lista(seccao: str, chave: str, valores: list[str]) -> list[str]:
    """Escreve `<seccao>.<chave>` no `riftvault_config.json`, **sem reformatar
    o resto do ficheiro**, e relê o config.

    É a porta para o único botão que escreve no config: o «montar/desmontar»
    de um deck (`decks.montados`, 2026-09-24) — *"o estado é do config, não só
    da base, para não se perder"*. O ficheiro é escrito À MÃO pelo André, com
    objectos numa linha (`{ "name": "OGN", "order": 1 }`) e dezenas de `_notas`
    pelo meio; um `json.dumps(indent=2)` do ficheiro inteiro reformatava-o todo
    a cada clique. Por isso troca-se **só o valor desta chave**, como texto:
    procura-se o bloco da secção a contar chavetas e, lá dentro, a linha da
    chave; se ela ainda não existir, entra logo a seguir ao `{` da secção.

    Devolve a lista escrita. Sem ficheiro nenhum (os testes que apontam o
    `RIFTVAULT_CONFIG` para um caminho que não existe) cria um com a secção.
    """
    texto = json.dumps(list(valores), ensure_ascii=False)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(
            json.dumps({seccao: {chave: list(valores)}}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        reload()
        return list(valores)

    bruto = CONFIG_PATH.read_text(encoding="utf-8")
    ini, fim = _bloco_do_config(bruto, seccao)
    if ini is None:
        # A secção não existe no ficheiro: acrescenta-se inteira, no fim.
        raw = json.loads(bruto)
        raw[seccao] = {**(raw.get(seccao) or {}), chave: list(valores)}
        CONFIG_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        reload()
        return list(valores)

    bloco = bruto[ini:fim]
    alvo = re.search(r'"' + re.escape(chave) + r'"\s*:\s*\[[^\]]*\]', bloco)
    if alvo:
        novo = bloco[:alvo.start()] + f'"{chave}": {texto}' + bloco[alvo.end():]
    else:
        # Entra logo a seguir ao `{` da secção, com a indentação da linha
        # seguinte (ou quatro espaços, que é a do ficheiro dele).
        abre = bloco.index("{") + 1
        seg = re.match(r'\n(\s*)', bloco[abre:])
        indent = seg.group(1) if seg else "    "
        novo = bloco[:abre] + f'\n{indent}"{chave}": {texto},' + bloco[abre:]
    CONFIG_PATH.write_text(bruto[:ini] + novo + bruto[fim:], encoding="utf-8")
    reload()
    return list(valores)


def _bloco_do_config(bruto: str, seccao: str) -> tuple[int | None, int | None]:
    """(início, fim) do texto `"<seccao>": { … }` no ficheiro, a contar
    chavetas — o bloco tem objectos lá dentro e um `.index("}")` cortava no
    primeiro deles."""
    m = re.search(r'"' + re.escape(seccao) + r'"\s*:\s*\{', bruto)
    if not m:
        return None, None
    nivel, i = 0, m.end() - 1
    while i < len(bruto):
        if bruto[i] == "{":
            nivel += 1
        elif bruto[i] == "}":
            nivel -= 1
            if nivel == 0:
                return m.start(), i + 1
        i += 1
    return None, None


def set_name(set_id: str) -> str:
    return (load().get("sets", {}).get(set_id) or {}).get("name") or set_id


def set_order(set_id: str) -> int:
    # Edições que ainda não estão no config vão para o fim, por ordem alfabética.
    return (load().get("sets", {}).get(set_id) or {}).get("order") or 999


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    DECKS_DIR.mkdir(parents=True, exist_ok=True)
