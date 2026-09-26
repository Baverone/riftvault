"""Linha de comandos do riftvault.

    riftvault sync [--set OGN] [--images]
    riftvault serve [--port 8770]
    riftvault build [--out site] [--se-mudou]
    riftvault add OGN-100a x1
    riftvault remove OGN-100a x1
    riftvault set OGN-100a 3
    riftvault undo
    riftvault log [-n 20]
    riftvault stats
    riftvault find "sett"
    riftvault a-subir [--cardmarket] [--todas] [--csv f.csv]
    riftvault wantlist [--edicao OGN] --cardmarket
    riftvault faltas [--edicao OGN]
    riftvault local [REF N --para deck:azir] [--deck azir --propor|--marcar ...]
    riftvault encomendas [--mais REF [N] | --menos REF [N] | --chegou [REF]]
    riftvault seguir [--jogador NOME] [--so-mudados] [--sem-rede] [--json]
    riftvault proprias [SLUG] [--mais REF [N] | --menos REF [N]]
    riftvault foil [REF] [--mais [N] | --menos [N]] [--edicao OGN]
    riftvault venda [--juntar REF [N] | --tirar REF [N]] [--trend REF EUR]
                    [--limpar] [--vender --sim]
    riftvault selado [--sync] [--mais ID [N] | --menos ID [N]] [--edicao OGN]
                     [--so-faltas | --so-tenho]
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from . import abas
from . import a_mais as a_mais_mod
from . import a_subir as a_subir_mod
from . import build as build_mod
from . import cardmarket, catalog, collection, config, db, decks as decks_mod
from . import faltas as faltas_mod
from . import faltas_edicao
from . import foil as foil_mod
from . import locais as locais_mod
from . import metrics, painel, pending as pending_mod, prices
from . import proprias as proprias_mod
from . import runas_vista as runas_vista_mod
from . import seguir as seguir_mod
from . import server
from . import uso_decks


def _qty(raw: str | None) -> int:
    """Aceita '3', 'x3' ou nada (=1)."""
    if not raw:
        return 1
    m = re.fullmatch(r"[xX]?(\d+)", raw.strip())
    if not m:
        raise SystemExit(f"quantidade inválida: {raw!r} (usa 3 ou x3)")
    return int(m.group(1))


def _describe(con, printing_id: str) -> str:
    row = con.execute(
        "SELECT name, public_code, variant_label, set_id FROM catalog.printings "
        "WHERE printing_id = ?", (printing_id,)
    ).fetchone()
    if not row:
        return printing_id
    return f"{row['name']} [{row['public_code']} · {row['variant_label']}]"


# --------------------------------------------------------------------------


def cmd_sync(args) -> int:
    sets = [s.upper() for s in args.set] if args.set else None
    print("A descarregar o catálogo da RiftScribe...")
    res = catalog.sync(sets, delay=0.0 if args.fast else 1.0)
    print(f"\n{res['total']} impressões em {len(res['sets'])} edições.")

    if res["unknown_variants"]:
        print("\n" + "!" * 60)
        print("ATENÇÃO: variantes que o riftvault não sabe classificar:")
        for v in res["unknown_variants"]:
            print(f"  variant={v!r}")
        print("Foram guardadas como 'unknown'. Acrescenta-as em catalog.LANE_KINDS")
        print("e volta a correr o sync, senão os alvos ficam errados.")
        print("!" * 60)

    if args.images:
        print("\nA descarregar imagens...")
        img = catalog.sync_images(sets)
        print(f"  {img['downloaded']} novas, {img['cached']} já em cache, "
              f"{img['failed']} falhadas (de {img['total']}).")
    else:
        print("\n(imagens não descarregadas — corre `riftvault sync --images`)")

    # Sair com erro é de propósito: no GitHub Actions é isto que impede o
    # `build` de publicar um site a que falta uma edição inteira.
    if res["sets_vazias"]:
        print(f"\nerro: {', '.join(res['sets_vazias'])} vieram sem uma única "
              f"entrada da API. O catálogo dessas edições ficou como estava.",
              file=sys.stderr)
        return 1
    return 0


def cmd_images(args) -> int:
    sets = [s.upper() for s in args.set] if args.set else None
    res = catalog.sync_images(sets)
    print(f"{res['downloaded']} novas, {res['cached']} em cache, "
          f"{res['failed']} falhadas (de {res['total']}).")
    return 0


def cmd_serve(args) -> int:
    server.serve(host=args.host, port=args.port)
    return 0


def cmd_build(args) -> int:
    res = build_mod.build(args.out, so_se_mudou=getattr(args, "se_mudou", False))
    if not res["mudou"]:
        print(f"\nSite em dia em {res['out']} — nada para regenerar.")
        return 0
    print(f"\nSite gerado em {res['out']} ({res['sets']} edições, "
          f"imagens: {res['image_mode']}).")
    return 0


def cmd_add(args) -> int:
    if args.foil:
        print("(nota: o riftvault não distingue foil de normal — ver CLAUDE.md)")
    con = db.connect()
    try:
        res = collection.adjust(con, args.ref, _qty(args.qty), source="cli")
    except collection.UnknownPrinting as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    print(f"+{res['applied']}  {_describe(con, res['printing_id'])}  -> {res['qty']}")
    con.close()
    return 0


def cmd_remove(args) -> int:
    if args.foil:
        print("(nota: o riftvault não distingue foil de normal — ver CLAUDE.md)")
    con = db.connect()
    try:
        res = collection.adjust(con, args.ref, -_qty(args.qty), source="cli")
    except collection.UnknownPrinting as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    if res["applied"] == 0:
        print(f"nada a remover: {_describe(con, res['printing_id'])} já está a 0")
    else:
        print(f"{res['applied']}  {_describe(con, res['printing_id'])}  -> {res['qty']}")
    con.close()
    return 0


def cmd_set(args) -> int:
    con = db.connect()
    try:
        res = collection.set_qty(con, args.ref, int(args.qty), source="cli")
    except collection.UnknownPrinting as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    print(f"= {res['qty']}  {_describe(con, res['printing_id'])}")
    con.close()
    return 0


def cmd_undo(args) -> int:
    con = db.connect()
    res = collection.undo_last(con, source="cli")
    if not res:
        print("não havia nada para desfazer.")
        return 1
    print(f"desfeita a op #{res['undone_op']}: "
          f"{_describe(con, res['printing_id'])} -> {res['qty']}")
    con.close()
    return 0


def cmd_log(args) -> int:
    con = db.connect()
    for op in collection.history(con, args.n):
        flag = " (desfeita)" if op["undone_at"] else ""
        name = op["name"] or op["printing_id"]
        print(f"#{op['id']:<5} {op['ts']}  {op['delta']:+3d} -> {op['qty_after']:<3} "
              f"[{op['source']}] {name} · {op['variant_label'] or ''}{flag}")
    con.close()
    return 0


def cmd_stats(args) -> int:
    con = db.connect()
    if db.catalog_is_empty(con):
        print("catálogo vazio — corre `riftvault sync`.")
        return 1
    t = collection.totals(con)
    print(f"Coleção: {t['copies']} cópias · {t['printings']} impressões · "
          f"{t['cards']} cartas distintas\n")
    sets = metrics.sets_payload(con)
    # A largura acompanha o nome mais comprido — o "OGS (Proving Grounds)"
    # rebentava com uma coluna fixa.
    w = max([len(s["name"]) for s in sets] + [6])
    print(f"{'edição':<{w}} {'playsets jogáveis':>20} {'master set':>16}")
    for s in sets:
        p = metrics.set_payload(con, s["id"])["progress"]
        pl, ms = p["playset"], p["master"]
        print(f"{s['name']:<{w}} {pl['done']:>8}/{pl['total']:<11} "
              f"{ms['done']:>7}/{ms['total']:<8}")

    # A contagem por níveis do master set (André, 2026-09-08): quantas faltam
    # para ter 1 de cada, 2 de cada, o playset de cada. O último nível dá
    # exactamente a coluna "master set" acima — é a mesma conta, por degraus.
    niv = metrics.niveis_payload(con)
    if niv["max"] > 1:
        n = niv["max"]
        linhas = [(s["name"], niv["by_set"].get(s["id"], [])) for s in sets]
        linhas.append(("TOTAL", niv["levels"]))

        def celula(lv):
            pct = f"{lv['pct']:.1f}".replace(".", ",")
            return (f"{pct:>5}% · faltam {lv['missing']:>4} · "
                    f"{prices.eur(lv['cents']):>11}")

        larg = max((len(celula(lv)) for _, ls in linhas for lv in ls), default=0)
        # O último degrau é o playset inteiro de cada carta (3 numa Unit, 12
        # numa runa desde 2026-09-14), por isso diz «playset» e não «3 de cada».
        print("\nContagem por níveis do master set "
              "(cópias, não o que vem a caminho):")
        print(f"{'edição':<{w}} "
              + " ".join(f"{(f'playset ({k}/{n})' if k == n else f'{k}/{n}'):^{larg}}"
                         for k in range(1, n + 1)))
        for nome, ls in linhas:
            print(f"{nome:<{w}} " + " ".join(celula(lv).ljust(larg) for lv in ls))

    # O painel do topo da Coleção (2026-09-21): os três níveis em tenho/total
    # por bloco e por edição, sem as runas — o que ele vê nos três cartões.
    print("\nPainel da Coleção (impressões que chegaram a cada nível, sem runas):")
    print(painel.texto(painel.payload(con), sets))

    # A contagem de foil das comuns e incomuns (2026-09-22): quantas normais e
    # quantas foils. São duas contagens independentes e o total é a soma
    # (2026-09-26) — nenhuma das contas acima as soma.
    print("\nFoil e não-foil (comuns e incomuns, impressões base):")
    print(foil_mod.texto(foil_mod.resumo(con), sets, prices.valor_dos_foils(con)))

    # O que os decks têm de comprar (2026-09-11): a soma do `missing` de todos,
    # com o que dois decks disputam e a Coleção não chega a contar como falta.
    decks_mod.import_all(con, log=lambda *_: None)
    tot = decks_mod.resumo_das_faltas(con)
    if tot["copies"] or tot["ordered"]:
        print(f"\nDecks: falta comprar {tot['copies']} cópias de {tot['cards']} "
              f"cartas · {prices.eur(tot['cents'])}"
              + (f" — {tot['disputed']} disputadas com um deck de cima"
                 if tot["disputed"] else "")
              + (f" — {tot['ordered']} já a caminho (não contam na falta)"
                 if tot["ordered"] else ""))

    # As abas escondidas (2026-09-25). Só o BOTÃO sai — tudo o que está acima
    # continua a ser calculado, esteja a aba à vista ou não.
    print("\n" + abas.texto())

    if getattr(args, "usadas", False):
        _imprimir_usadas(con)
    con.close()
    return 0


def _imprimir_usadas(con) -> None:
    """As cartas que os decks usam, e quanto cada deck leva — o gémeo em
    consola do rótulo «Azir 3 · Kennen 2 (faltam 2)» da grelha da Coleção."""
    uso = decks_mod.uso_por_carta(con)
    if not uso:
        print("\nNenhum deck pede carta nenhuma.")
        return
    nomes = {r["card_key"]: r["name"] for r in con.execute(
        "SELECT card_key, name FROM catalog.cards")}
    tenho = decks_mod.owned_by_card(con)
    print(f"\nCartas usadas em decks ({len(uso)}), tens / os decks que as pedem:")
    for ck in sorted(uso, key=lambda k: nomes.get(k, k).casefold()):
        partes = []
        for u in uso[ck]:
            curto = u["deck"].split(" · ")[0]
            detalhe = [x for x in (
                f"faltam {u['missing']}" if u["missing"] else "",
                f"{u['ordered']} a caminho" if u.get("ordered") else "") if x]
            partes.append(f"{curto} {u['wanted']}"
                          + (f" ({', '.join(detalhe)})" if detalhe else ""))
        print(f"  {nomes.get(ck, ck)[:34]:<34} {tenho.get(ck, 0):>3}   "
              + " · ".join(partes))


def cmd_map(args) -> int:
    try:
        ct = prices.CardTrader()
    except prices.CardTraderError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    print("A mapear as impressões para os blueprints do CardTrader...")
    res = prices.sync_map(ct)
    print(f"\n{res['mapped']} impressões mapeadas.")
    if res.get("market_only"):
        print(f"{res['market_only']} impressões que só o CardTrader tem "
              f"({res['market_only_casadas']} casadas com uma carta nossa) — "
              f"ficam fora do catálogo, só para a aba Pimp.")
    if res["missing"]:
        print(f"\n{len(res['missing'])} sem par no CardTrader:")
        for pid, code, name in res["missing"][:20]:
            print(f"  {code or pid:<16} {name}")
    return 0


def cmd_prices(args) -> int:
    try:
        ct = prices.CardTrader()
    except prices.CardTraderError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    print("A descarregar preços do CardTrader (um pedido por edição, são grandes)...")
    res = prices.sync_prices(ct)
    v = res["valor"]
    print(f"\n{res['printings']} impressões com preço atualizado "
          f"({res['sem_preco']} sem oferta utilizável).")
    print(f"{res['historico_gravado']} entradas novas no histórico"
          f" · {res.get('oferta_gravada', 0)} no tamanho da oferta.")
    print(f"\nValor da coleção: {prices.eur(v['cents'])}")
    return 0


def cmd_value(args) -> int:
    con = db.connect()
    v = prices.collection_value(con)
    if not v["day"]:
        print("ainda não há preços — corre `riftvault map` e depois `riftvault prices`.")
        return 1
    print(f"Valor da coleção: {prices.eur(v['cents'])}   "
          f"({v['copias']} cópias, preços de {v['day']})")
    print("  critério: preço mais baixo em Near Mint/Mint, inglês, no CardTrader")
    if v["copias_sem_preco"]:
        n = v["copias_sem_preco"]
        print(f"  {n} {'cópia' if n == 1 else 'cópias'} sem preço "
              f"(sem oferta no CardTrader)")
    if v["cents_de_foil"]:
        pct = 100 * v["cents_de_foil"] / v["cents"] if v["cents"] else 0
        print(f"  ATENÇÃO: {prices.eur(v['cents_de_foil'])} ({pct:.0f}% do total, "
              f"{v['copias_de_foil']} cópias) vem de cartas que o CardTrader só "
              f"lista em foil.\n  Como o riftvault não distingue acabamentos, se "
              f"as tuas forem normais o valor real é mais baixo.")
    # O foil MARCADO (2026-09-26): com `foil.conta_para_valor` ligado as foils
    # dele contam ao PREÇO DA FOIL do CardTrader; as que não têm oferta foil
    # caem para o preço da normal, e esse FALLBACK é o que faz do total um PISO.
    f = v.get("foils")
    if f and f["copies"]:
        n, pf = f["ao_preco_da_normal"], f["preco_de_foil"]
        print(f"  os teus {f['copies']} foils contam {prices.eur(f['cents'])} "
              f"no total acima:")
        if pf["copies"]:
            print(f"    {pf['copies']} cópias em {pf['printings']} impressões "
                  f"({prices.eur(pf['cents'])}) ao PREÇO DA FOIL do CardTrader "
                  f"— sem ressalva")
        if n["copies"]:
            print(f"    {n['copies']} cópias em {n['printings']} impressões "
                  f"({prices.eur(n['cents'])}) ao preço da NORMAL, por o "
                  f"CardTrader não ter oferta foil delas — este pedaço é um "
                  f"PISO e o real é mais alto")
        if f["sem_preco"]["copies"]:
            print(f"    {f['sem_preco']['copies']} cópias sem preço no CardTrader "
                  f"— não contam")

    by = prices.value_by_set(con)
    if by:
        print("\npor edição:")
        for s in metrics.sets_payload(con):
            if by.get(s["id"]):
                print(f"  {s['name']:<24} {prices.eur(by[s['id']]):>12}")

    top = prices.top_value(con, args.n)
    if top:
        print(f"\nas {len(top)} mais valiosas:")
        for r in top:
            foil = " (preço de foil)" if r["from_foil"] else ""
            # Com cópias foil a linha não é `qty × price_cents`: elas contam ao
            # preço delas (ou ao da normal, quando não há oferta foil). Diz-se,
            # senão a multiplicação não fecha com o total ao lado.
            if r["qty_foil"]:
                pf = (prices.eur(r["price_foil_cents"]) if r["price_foil_cents"]
                      is not None else prices.eur(r["price_cents"]) + " (o da normal)")
                quanto = (f"{r['qty_normal']}x {prices.eur(r['price_cents'])} + "
                          f"{r['qty_foil']} foil x {pf}")
            else:
                quanto = f"{r['qty']}x {prices.eur(r['price_cents'])}"
            print(f"  {prices.eur(r['total']):>10}  {quanto:>28}  "
                  f"{r['name']} [{r['variant_label']}]{foil}")
    con.close()
    return 0


def cmd_decks(args) -> int:
    con = db.connect()
    imp = decks_mod.import_all(con)
    # MONTAR/DESMONTAR (2026-09-24): escreve `decks.montados` no config — o
    # estado é de lá, não da base, *"para não se perder"*.
    for slug, montar in ((getattr(args, "montar", None), True),
                         (getattr(args, "desmontar", None), False)):
        if not slug:
            continue
        try:
            est = decks_mod.alternar_montado(con, slug, montar)
        except decks_mod.DeckDesconhecido as exc:
            print(f"erro: {exc}", file=sys.stderr)
            return 1
        print(f"{slug}: {'montado' if montar else 'desmontado'}.  "
              f"montados: {', '.join(est['montados']) or '(nenhum)'}\n")
    if args.order:
        if decks_mod.ordem_fixa():
            print(f"erro: a ordem dos decks está em `decks.{decks_mod.ORDEM}` no "
                  f"riftvault_config.json — muda-se lá, não com --order", file=sys.stderr)
            return 1
        by_slug = {r["name"]: r["deck_id"] for r in decks_mod.deck_rows(con)}
        ids = []
        for slug in args.order.split(","):
            slug = slug.strip()
            if slug not in by_slug:
                print(f"erro: não há deck chamado {slug!r}", file=sys.stderr)
                return 1
            ids.append(by_slug[slug])
        # Os que não foram nomeados ficam a seguir, pela ordem que tinham.
        ids += [r["deck_id"] for r in decks_mod.deck_rows(con) if r["deck_id"] not in ids]
        decks_mod.set_order(con, ids)
        print("ordem alterada.\n")
    # Recomeçar o registo do que as listas pedem (2026-09-21): apaga o
    # `deck_need_log` e escreve o ponto de partida com os decks de HOJE — as
    # «libertadas» do A mais ficam vazias até a próxima lista mudar.
    if getattr(args, "recomecar_registo", False):
        n = uso_decks.recomecar(con)
        print(f"registo dos decks recomeçado: {n} linhas de partida "
              f"(0 -> N), libertadas a zero.\n")
    if imp["ordem"]["nao_encontrados"]:
        print(f"decks.{decks_mod.ORDEM}: sem deck para "
              f"{', '.join(repr(x) for x in imp['ordem']['nao_encontrados'])} — "
              f"ignorado.")

    # O "tenho" é o que a alocação por prioridade dá ao deck, venha das cópias
    # PRÓPRIAS dele (2026-09-21, servem primeiro), do que está sleevado nele,
    # do binder Decks/Venda ou da Coleção (2026-09-11: *"se há na coleção o
    # deck usa"*); as quatro colunas do meio somam-no. "falta" é o
    # que o deck não recebe e tem de comprar; "disputadas" é a parte dessa
    # falta que existe num deck de cima — informação, não desconto. "a caminho"
    # (2026-09-11) é o que já está encomendado para este deck: não é tenho,
    # já não é falta.
    # As runas não se contam (2026-09-17, à noite: *"indica me so quantas
    # sao"*): o «tenho» é só do resto, e a coluna «runas» diz quantas a lista
    # pede — à mão.
    print(f"{'#':<3} {'deck':<40} {'estado':<11} {'tenho':>12} {'próprias':>8} "
          f"{'deck':>5} {'binder':>7} "
          f"{'coleção':>8} {'a caminho':>9} {'falta':>6} {'disputadas':>10} "
          f"{'runas':>6} {'aviso':>6}")
    idx = decks_mod.decks_index(con)
    for d in idx:
        # Os membros de um grupo de Legend (2026-09-11, noite) levam «··» à
        # frente: partilham as cartas e o total conta-os uma vez.
        nome = ("·· " if d["grupo"]["variantes"] else "") + d["name"]
        runas = d.get("runas") or {}
        print(f"{d['priority']:<3} {nome[:40]:<40} "
              f"{('montado' if d['montado'] else 'DESMONTADO'):<11} "
              f"{d['have']:>5}/{d['wanted']:<6} {d['proprias']:>8} {d['no_deck']:>5} "
              f"{d['no_binder']:>7} {d['na_colecao']:>8} {d['ordered']:>9} "
              f"{d['missing']:>6} {d['shared']:>10} "
              f"{(runas.get('copies') or '') if not runas.get('contadas') else '':>6} "
              f"{d['aviso_colecao'] or '':>6}")
    # DESMONTADOS (2026-09-24): não consomem nada da Coleção; o que a linha
    # deles diz é a SIMULAÇÃO de os montar a seguir aos montados.
    fora = [d for d in idx if not d["montado"]]
    if fora:
        print(f"\n{len(fora)} desmontado{'s' if len(fora) > 1 else ''} "
              f"({', '.join(d['slug'] for d in fora)}): não consomem nada da Coleção "
              f"— não aparecem na grelha, não entram na falta a comprar nem no A "
              f"mais. As colunas deles são a simulação de os montar a seguir aos "
              f"montados. `riftvault decks --montar <slug>` monta.")
    est = decks_mod.montados_estado(con)
    if est["nao_encontrados"]:
        print(f"decks.{decks_mod.MONTADOS}: sem deck para "
              f"{', '.join(repr(x) for x in est['nao_encontrados'])} — ignorado.")
    # A REGRA DE RARIDADE (2026-09-24): cópias que saem da Coleção abaixo do
    # patamar — deviam vir das cópias próprias do deck. Só marca.
    minima = decks_mod.raridade_da_colecao()
    aviso = sum(d["aviso_colecao"] for d in idx)
    if minima and aviso:
        print(f"\n{aviso} cópias saem da Coleção com raridade abaixo de «{minima}» "
              f"— pela regra, essas deviam ser cópias próprias dos decks "
              f"(`decks.{decks_mod.RARIDADE_COLECAO}`). Não bloqueia nada; "
              f"`riftvault deck <slug>` diz quais.")
    if any(not (d.get("runas") or {}).get("contadas", True) for d in idx):
        print("(as runas não se contam nos decks — «tenho» é sem elas; a coluna "
              "«runas» diz quantas a lista pede, para organizares à mão)")
    grupos = [g for g in decks_mod.grupos(con) if g["variantes"]]
    for g in grupos:
        lider = next(d for d in idx if d["id"] == g["lider"])
        print(f"\n·· {g['rotulo']}: a mesma Legend — partilham as cartas, "
              f"a falta é a mesma compra ({lider['grupo']['missing']} cópias, "
              f"contadas uma vez no total).")
    tot = decks_mod.resumo_das_faltas(con)
    if tot["copies"] or tot["ordered"]:
        print(f"\nFalta comprar aos decks: {tot['copies']} cópias de "
              f"{tot['cards']} cartas · {prices.eur(tot['cents'])}"
              + (f" ({tot['disputed']} disputadas com um deck de cima)"
                 if tot["disputed"] else "")
              + (f" — {tot['ordered']} já a caminho" if tot["ordered"] else ""))
    # Lugares normais tapados por outra versão que ele tem (2026-09-17, tarde)
    # — sem esta regra eram falta.
    if tot["outras"]["copies"]:
        o = tot["outras"]
        print(f"{o['copies']} {'cópia joga' if o['copies'] == 1 else 'cópias jogam'} "
              f"noutra versão (Alt Art, sobrenumerada ou promo) porque a base não "
              f"chega — {o['cards']} {'carta' if o['cards'] == 1 else 'cartas'}; "
              f"`riftvault deck <slug>` reparte-as.")
    extra = sum(d["extra"] for d in idx)
    if extra:
        print(f"{extra} cópias estão marcadas num deck que já não as pede — "
              f"a lista mudou.")
    # As cópias próprias (2026-09-21): quantas os decks têm guardadas para si,
    # e quantas dessas não servem (outra versão, carta que a lista não pede).
    proprias = sum(d["proprias"] for d in idx)
    fora_p = sum(d["proprias_fora"] for d in idx)
    if proprias or fora_p:
        print(f"{proprias} cópias próprias dos decks a servir (não contam para a "
              f"Coleção)" + (f"; {fora_p} guardadas que não servem — "
                              f"`riftvault proprias <slug>` diz quais" if fora_p else "")
              + f" · só versões base: {'sim' if decks_mod.so_base() else 'não'}")
    con.close()
    return 0


def _codigo_curto(code) -> str:
    """`UNL-176a/219` -> `UNL-176a`: o denominador não ajuda a encontrar a carta."""
    return str(code or "?").split("/")[0]


def cmd_deck(args) -> int:
    con = db.connect()
    decks_mod.import_all(con, log=lambda *_: None)
    row = next((r for r in decks_mod.deck_rows(con) if r["name"] == args.slug), None)
    if not row:
        print(f"erro: não há deck chamado {args.slug!r}", file=sys.stderr)
        return 1
    p = decks_mod.deck_payload(con, row["deck_id"])
    L = p["legality"]
    print(f"{p['name']}   (prioridade {p['priority']}"
          + ("" if p["montado"] else ", DESMONTADO") + ")")
    if not p["montado"]:
        print(f"  desmontado: não consome nada da Coleção. O que se segue é a "
              f"SIMULAÇÃO de o montar a seguir aos que estão montados — nada "
              f"disto conta em lado nenhum. `riftvault decks --montar {p['slug']}`.")
    if p["grupo"]["variantes"]:
        print(f"  a mesma Legend que «{'», «'.join(p['grupo']['irmaos'])}»: "
              f"partilham as cartas; o grupo compra {p['grupo']['missing']} "
              f"cópias ao todo, contadas uma vez.")
    ok = lambda b: "ok" if b else "X"
    print(f"  main {L['main']['n']}/{L['main']['alvo']} {ok(L['main']['ok'])} · "
          f"runas {L['runes']['n']}/{L['runes']['alvo']} {ok(L['runes']['ok'])} · "
          f"battlefields {L['battlefields']['n']}/{L['battlefields']['alvo']} "
          f"{ok(L['battlefields']['ok'])} · domínios "
          f"{' + '.join(L['dominios']['legend'])} {ok(L['dominios']['ok'])}")
    if p["unresolved"]:
        print("  por casar no catálogo: "
              + ", ".join(u["name"] for u in p["unresolved"]))

    # De onde vêm as cartas: as três primeiras somam o que o deck tem, e cada
    # uma diz onde ele as vai encontrar. A Coleção conta desde 2026-09-11.
    lc = p["locais"]
    print(f"  próprias {lc['proprias']} · no deck {lc['no_deck']} · no binder "
          f"Decks/Venda {lc['no_binder']} (ir buscar) · na Coleção {lc['na_colecao']} · "
          f"a comprar {lc['missing']}"
          + (f" ({lc['shared']} disputadas com um deck de cima)"
             if lc.get("shared") else "")
          + (f" · a caminho {lc['ordered']}" if lc.get("ordered") else "")
          + (f"  [só versões base]" if p.get("so_base") else ""))
    # As cópias próprias que não servem este deck (2026-09-21): outra versão
    # com `so_base`, uma carta que a lista não pede, ou acima do pedido.
    if p.get("proprias_fora"):
        print(f"  {lc['proprias_fora']} cópias próprias que NÃO servem este deck: "
              + ", ".join(f"{x['qty']}x {x['name']} [{_codigo_curto(x['code'])}] ({x['motivo']})"
                          for x in p["proprias_fora"])
              + f" — tira-as com `riftvault proprias {p['slug']} --menos REF`.")
    if lc["na_colecao"] and p["montado"]:
        print(f"  para sleevar as da Coleção: `riftvault local --deck "
              f"{p['slug']} --propor`")
    if lc.get("outras"):
        print(f"  {lc['outras']} {'cópia joga' if lc['outras'] == 1 else 'cópias jogam'} "
              f"noutra versão porque a base não chega (Alt Art, sobrenumerada ou "
              f"promo — nunca assinada).")
    if lc["extra"]:
        print(f"  {lc['extra']} cópias estão marcadas neste deck e ele já não "
              f"as pede.")
    # As runas não se contam (2026-09-17, à noite): diz-se quantas a lista
    # pede, e mais nada — ele organiza-as à mão.
    ru = p.get("runas") or {}
    if ru.get("copies") and not ru.get("contadas"):
        print(f"  runas: {ru['copies']} ({ru['cards']} {'carta' if ru['cards'] == 1 else 'cartas'}) "
              f"— não se contam, organizas à mão")

    if p["missing_by_set"]:
        print("\nFalta comprar, por edição:")
        pl = lambda n, s, p_: f"{s if n == 1 else p_}"
        for m in p["missing_by_set"]:
            extra = f"  ({m['multi']} também noutra edição)" if m["multi"] else ""
            print(f"  {m['name']:<24} {m['copies']:>3} {pl(m['copies'], 'cópia ', 'cópias')}"
                  f" de {m['cards']:>2} {pl(m['cards'], 'carta ', 'cartas')}"
                  f"  {prices.eur(m['cents']):>9}{extra}")

    for s in p["sections"]:
        nao = s.get("nao_contadas", 0)
        if nao and not s["wanted"]:
            # O Rune Pool inteiro: só as quantidades (2026-09-17, à noite).
            print(f"\n{s['label']}  ({nao} — não se contam, organizas à mão)")
        else:
            print(f"\n{s['label']}  ({s['have']}/{s['wanted']})"
                  + (f"  + {nao} não contadas" if nao else ""))
        for c in s["cards"]:
            if not c.get("contado", True):
                print(f"  - {c['wanted']:>2} {c['name'][:38]:<38}")
                continue
            # De onde vem o que tem — os quatro somam o `have`; as próprias
            # do deck (2026-09-21) primeiro.
            onde = " · ".join(f"{n} {sitio}" for n, sitio in (
                (c.get("proprias", 0), "próprias"), (c["no_deck"], "no deck"),
                (c["no_binder"], "no binder Decks/Venda"),
                (c["na_colecao"], "na Coleção")) if n)
            if c["missing"] or c.get("ordered"):
                # O que falta compra-se SEMPRE (2026-09-11); se existe num deck
                # de cima, diz-se onde — é informação, não desconto. O que já
                # vem a caminho diz-se à parte: não é tenho, já não é falta.
                marca = "x" if c["missing"] else "~"
                partes = []
                if c["missing"]:
                    partes.append(f"falta{'m' if c['missing'] > 1 else ''} "
                                  f"{c['missing']} a comprar")
                if c.get("ordered"):
                    partes.append(f"{c['ordered']} a caminho")
                if onde:
                    partes.append(onde)
                extra = "  (" + "; ".join(partes) + ")"
                if c["shared"]:
                    extra += "  -> " + ", ".join(
                        f"{h['qty']}x em «{h['deck']}»" for h in c["shared"]["em"])
                # O irmão do grupo pede-a também: é a mesma compra, não uma
                # disputa (2026-09-11, noite).
                if c.get("partilhada"):
                    extra += "  partilhada com " + ", ".join(
                        f"«{h['deck']}»" for h in c["partilhada"])
            elif c["no_binder"]:
                marca = "b"
                extra = f"  ({onde})"
            else:
                marca = "."
                # Diz-se de onde vem quando vem de mais do que um sítio.
                fontes = sum(1 for n in (c.get("proprias", 0), c["no_deck"],
                                         c["no_binder"], c["na_colecao"]) if n)
                extra = (f"  ({onde})" if fontes > 1 else "")
                if args.onde:
                    extra += "  " + " · ".join(f"{x['qty']}x {x['code']}"
                                               for x in c["printings"])
            # Uma linha servida por UMA só outra versão (a base não chegou e
            # a alt art tapou tudo) diz-o na própria linha; não há nada para
            # repartir.
            versoes = c.get("versoes") or []
            if len(versoes) == 1 and c.get("outras"):
                extra += f"  em {versoes[0]['label']} ({_codigo_curto(versoes[0]['code'])})"
            print(f"  {marca} {c['wanted']:>2} {c['name'][:38]:<38} {c['have']}/{c['wanted']}{extra}")
            # «Separa as versões por Art» (André, 2026-09-17): uma carta
            # servida por mais do que uma impressão reparte-se, uma sub-linha
            # por versão. Servida por uma só, não se enche a vista.
            if len(versoes) > 1:
                for x in versoes:
                    print(f"        {x['qty']} {x['label']} ({_codigo_curto(x['code'])})")

    _montagem(p)
    con.close()
    return 0


def _por_carta(p: dict) -> list[dict]:
    """As linhas do deck somadas POR CARTA, para a vista de montagem.

    A lista mostra-se por papel (o main e o sideboard são secções diferentes)
    mas quem está a montar tem a carta na mão uma vez só: 2 Sabotage no main e
    1 no sideboard são 3 Sabotage para arranjar, não duas linhas.
    """
    out: dict[str, dict] = {}
    for s in p["sections"]:
        for c in s["cards"]:
            if not c.get("contado", True):
                continue
            e = out.get(c["card_key"])
            if e is None:
                e = out[c["card_key"]] = {"name": c["name"], "rarity": c.get("rarity"),
                                          "wanted": 0, "proprias": 0, "no_deck": 0,
                                          "no_binder": 0, "na_colecao": 0, "missing": 0,
                                          "ordered": 0, "aviso": 0, "foil_na_colecao": 0}
            for campo in ("wanted", "proprias", "no_deck", "no_binder", "na_colecao",
                          "missing", "ordered", "aviso", "foil_na_colecao"):
                e[campo] += c.get(campo) or 0
    return list(out.values())


def _montagem(p: dict) -> None:
    """O MODO DE REMONTAGEM (André, 2026-09-24): carta a carta, para ele
    montar o deck com as cartas na mão.

    *"vou colocar tudo nos binders das edicoes e depois voltar a montar deck a
    deck e assim conseguir perceber o que tenho e nao tenho"*. Uma linha por
    carta, **o que falta primeiro**: quanto precisa, quantas já tem como
    PRÓPRIAS do deck, quantas sairiam da Coleção e quantas faltam mesmo. A
    marca `!` é a regra de raridade: uma cópia abaixo do patamar a sair da
    Coleção, que ele quer que venha das próprias.
    """
    cartas = _por_carta(p)
    if not cartas:
        return
    # O que falta primeiro; depois o que sai da Coleção (é o que ele vai ter
    # de ir buscar ao binder); no fim o que já está montado.
    cartas.sort(key=lambda c: (-c["missing"], -(c.get("aviso") or 0),
                               -c["na_colecao"], c["name"]))
    minima = p.get("raridade_colecao")
    print(f"\nMontagem{'' if p['montado'] else ' (simulação — o deck está desmontado)'}: "
          f"o que precisas de ter à mão")
    print(f"  {'':2} {'precisa':>7} {'próprias':>8} {'binder':>6} {'coleção':>7} "
          f"{'falta':>5}  carta")
    for c in cartas:
        aviso = c.get("aviso") or 0
        marca = "x" if c["missing"] else ("!" if aviso else " ")
        rar = f"  [{c.get('rarity') or '?'}]" if aviso else ""
        # Quantas das que saem da Coleção são FOIL (2026-09-26): as normais
        # servem primeiro, e dizer-lho poupa-lhe uma volta ao binder.
        f = c.get("foil_na_colecao") or 0
        foil = f"  ({f} em foil)" if f else ""
        print(f"  {marca:2} {c['wanted']:>7} {c.get('proprias', 0):>8} "
              f"{c['no_binder'] + c['no_deck']:>6} {c['na_colecao']:>7} "
              f"{c['missing']:>5}  {c['name'][:34]}{rar}{foil}")
    if p.get("foil_na_colecao"):
        print(f"    {p['foil_na_colecao']} cópias de {p['foil_cartas']} cartas saem da "
              f"Coleção em FOIL — as normais servem primeiro, estas são as que "
              f"sobraram para foil (o deck joga foil ou normal, tanto faz).")
    if minima and p.get("aviso_colecao"):
        print(f"  ! {p['aviso_colecao']} cópias de {p['aviso_cartas']} cartas saem da "
              f"Coleção abaixo de «{minima}» — pela regra, essas deviam ser cópias "
              f"próprias deste deck (`riftvault proprias {p['slug']} --mais REF`).")


def cmd_shopping(args) -> int:
    con = db.connect()
    decks_mod.import_all(con, log=lambda *_: None)
    deck_id = None
    if args.deck:
        row = next((r for r in decks_mod.deck_rows(con) if r["name"] == args.deck), None)
        if not row:
            print(f"erro: não há deck chamado {args.deck!r}", file=sys.stderr)
            return 1
        deck_id = row["deck_id"]

    linhas = decks_mod.shopping_list(con, deck_id)
    total = sum(x["total_cents"] for x in linhas)
    if args.csv:
        import csv as _csv
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as fh:
            w = _csv.writer(fh)
            w.writerow(["carta", "quantidade", "preco_unitario_eur", "total_eur"])
            for x in linhas:
                w.writerow([x["name"], x["qty"],
                            "" if x["price_cents"] is None else f"{x['price_cents']/100:.2f}",
                            f"{x['total_cents']/100:.2f}"])
        print(f"{len(linhas)} linhas escritas em {args.csv}")
    else:
        for x in linhas:
            print(f"  {x['qty']:>2}x {x['name'][:40]:<40} "
                  f"{prices.eur(x['price_cents']):>9} = {prices.eur(x['total_cents']):>10}")
    print(f"\n{len(linhas)} cartas em falta · {prices.eur(total)}")
    con.close()
    return 0


def cmd_wantlist_edicao(args) -> int:
    """A wantlist das faltas do MASTER SET, por edição.

    André, 2026-09-08: *"Quero também que no fim de cada edição me dês uma
    wantlist para eu colocar no Cardmarket."* É o gémeo em consola dos dois
    blocos do fim da Coleção, e sai do mesmo sítio (`a_subir.wantlist`) — sem
    `--edicao` dá todas as edições seguidas, que é o bloco «Wantlist — tudo».

    O stdout fica COLÁVEL tal e qual: os totais, o corte por edição e o aviso
    do foil vão todos para o stderr. Uma linha de total colada na wantlist era
    importada como se fosse uma carta.
    """
    con = db.connect()
    if db.catalog_is_empty(con):
        print("catálogo vazio — corre `riftvault sync`.", file=sys.stderr)
        con.close()
        return 1

    alvo = args.edicao.upper() if args.edicao else None
    if alvo:
        conhecidas = [r["set_id"] for r in con.execute(
            "SELECT DISTINCT set_id FROM catalog.printings ORDER BY set_id")]
        if alvo not in conhecidas:
            print(f"erro: não há edição {alvo!r}. Há: {', '.join(conhecidas)}",
                  file=sys.stderr)
            con.close()
            return 1

    nivel = getattr(args, "nivel", None)
    if nivel is not None and nivel < 1:
        print("erro: --nivel tem de ser 1 ou mais.", file=sys.stderr)
        con.close()
        return 1

    p = a_subir_mod.wantlist(con, alvo, com_codigo=args.codigos, nivel=nivel)
    saida = p["text"] + ("\n" if p["text"] else "")
    if args.out:
        open(args.out, "w", encoding="utf-8").write(saida)
        print(f"{p['lines']} linhas escritas em {args.out}")
    else:
        sys.stdout.write(saida)

    for d in p["sets"]:
        w = d["wantlist"]
        print(f"# {d['name']}: {w['lines']} linhas · {w['copies']} cópias · "
              f"{prices.eur(w['cents'])}", file=sys.stderr)
    print(f"#\n# total{f' (até {nivel} de cada)' if nivel else ''}: "
          f"{p['lines']} linhas · {p['copies']} cópias · "
          f"{prices.eur(p['cents'])}"
          + (f" ({p['no_price']} sem preço no CardTrader)" if p["no_price"] else ""),
          file=sys.stderr)
    if p["foil"]:
        print(f"# {len(p['foil'])} destas só têm oferta foil no mercado. O texto da "
              f"wantlist não\n# leva marca de foil: liga o filtro Foil nestas "
              f"entradas depois de colares.", file=sys.stderr)
    con.close()
    return 0


def cmd_wantlist(args) -> int:
    # `--edicao`/`--cardmarket` trocam a pergunta: em vez do que falta aos
    # DECKS, o que falta ao master set de cada EDIÇÃO. São duas listas
    # diferentes com o mesmo formato — e o mesmo gerador.
    if args.edicao or args.cardmarket:
        return cmd_wantlist_edicao(args)

    con = db.connect()
    decks_mod.import_all(con, log=lambda *_: None)

    if args.todos:
        alvo, rotulo = faltas_mod.todos_juntos(con), "todos os decks ao mesmo tempo"
    elif args.deck:
        pd = faltas_mod.por_deck(con)
        nomes = {r["name"]: i for i, r in enumerate(decks_mod.deck_rows(con))}
        if args.deck not in nomes:
            print(f"erro: não há deck chamado {args.deck!r}", file=sys.stderr)
            return 1
        alvo = pd[nomes[args.deck]]
        rotulo = alvo["name"]
    else:
        # Sem argumentos: a soma das listas por deck, sem múltiplos.
        pd = faltas_mod.por_deck(con)
        alvo = {"by_set": [g for d in pd for g in d["by_set"]]}
        rotulo = "todos os decks, um de cada vez"

    if args.pimp:
        alvo, rotulo = faltas_mod.pimp(con), "versões alteradas dos decks"
    res = faltas_mod.wantlist(alvo["by_set"], com_edicao=not args.sem_edicao)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(res["text"] + "\n")
        print(f"{res['lines']} linhas escritas em {args.out}  ({rotulo})")
    else:
        print(res["text"])

    if res["foil"]:
        print(f"\n# {len(res['foil'])} destas só têm oferta foil no mercado.",
              file=sys.stderr)
        print("# O texto da wantlist não leva marca de foil: liga o filtro Foil",
              file=sys.stderr)
        print("# nestas entradas depois de colares.", file=sys.stderr)
        for l in res["foil"]:
            print(f"#   {l}", file=sys.stderr)
    con.close()
    return 0


def cmd_a_subir(args) -> int:
    """A aba «A subir» na consola, e a lista para o Cardmarket que sai dela.

    Sem opções mostra a tabela. Com `--cardmarket` escreve as linhas para colar
    na wantlist deles — as mesmas que os botões da página dão, pelo mesmo
    gerador (`cardmarket.linha`).

    `--todas` troca o âmbito: em vez do que está a subir, tudo o que falta do
    master set, por edição e número. É a lista de "comprar isto de uma vez".
    """
    con = db.connect()
    if db.catalog_is_empty(con):
        print("catálogo vazio — corre `riftvault sync`.", file=sys.stderr)
        return 1

    if args.todas:
        p = a_subir_mod.master_faltas(con)
        itens = [x for d in p["sets"] for x in d["items"]]
        rotulo = "tudo o que falta do master set"
        resumo = (f"{p['cards']} impressões · {p['copies']} cópias · "
                  f"{prices.eur(p['cents'])}"
                  + (f" ({p['no_price']} sem preço no CardTrader)" if p["no_price"] else ""))
        fora = p["scope"]
    else:
        p = a_subir_mod.calcular(con)
        itens = p["items"]
        rotulo = (f"a subir {p['min_pct']:.0f}% ou mais em {p['window_days']} dias, "
                  f"do que ainda te falta do master set")
        resumo = (f"{p['totals']['cards']} cartas · {p['totals']['copies']} cópias · "
                  f"{prices.eur(p['totals']['cents'])} "
                  f"({prices.eur(p['totals']['extra_cents'])} do que já subiu)")
        fora = p["scope"]
        if not p["ready"]:
            print("ainda não há histórico de preços com que comparar — corre "
                  "`riftvault prices` uns dias.", file=sys.stderr)

    if args.csv:
        open(args.csv, "w", encoding="utf-8-sig", newline="").write(
            cardmarket.csv_texto(itens))
        print(f"{len(itens)} linhas escritas em {args.csv}  ({rotulo})")
        con.close()
        return 0

    if args.cardmarket:
        res = cardmarket.gerar(itens, com_codigo=args.codigos)
        saida = res["text"] + ("\n" if res["text"] else "")
        if args.out:
            open(args.out, "w", encoding="utf-8").write(saida)
            print(f"{res['lines']} linhas escritas em {args.out}  ({rotulo})")
        else:
            sys.stdout.write(saida)
        # O total e o aviso do foil vão para o stderr, para o stdout ficar
        # colável tal e qual: uma linha de total importada como carta seria
        # uma carta a mais na wantlist dele.
        print(f"\n# {res['lines']} linhas · {res['copies']} cópias · "
              f"{prices.eur(res['cents'])}  ({rotulo})", file=sys.stderr)
        if res["foil"]:
            print(f"# {len(res['foil'])} destas só têm oferta foil no mercado. O texto "
                  f"da wantlist não\n# leva marca de foil: liga o filtro Foil nestas "
                  f"entradas depois de colares.", file=sys.stderr)
            for l in res["foil"]:
                print(f"#   {l}", file=sys.stderr)
        con.close()
        return 0

    print(f"{resumo}\n({rotulo})")
    if fora.get("excluded"):
        # Por critério: as signatures também são de raridade showcase, e um
        # número só não dizia quantas saíram por serem uma coisa ou a outra.
        nomes = fora.get("excluded_labels") or {}
        motivos = ", ".join(f"{c['n']} {nomes.get(c['criterio'], c['criterio'])}"
                            for c in fora.get("excluded_by") or ())
        extra = ("a coleção extra acompanha-se na grelha, não se compra"
                 if fora.get("so_master_set") else
                 "a exclusão é da sequência: a coleção extra entra na mesma")
        print(f"fora: {fora['excluded']} impressões ({motivos}) "
              f"— não entram nas listas de compra; {extra}.")
    print()
    for x in itens:
        pct = "" if x.get("pct") is None else f"{x['pct']:+7.1f}%"
        print(f"  {x['missing']:>2}x {cardmarket.codigo(x['code']):<12} "
              f"{(x.get('name') or '')[:32]:<32} "
              f"{prices.eur(x.get('price')):>10} {pct:>8}  "
              f"= {prices.eur(x.get('total')):>11}")
    con.close()
    return 0


def cmd_a_mais(args) -> int:
    """O separador «A mais» (2026-09-17): por edição, o que ele tem acima do
    alvo e o que os decks libertaram. Só mostra."""
    con = db.connect()
    if db.catalog_is_empty(con):
        print("catálogo vazio — corre `riftvault sync`.", file=sys.stderr)
        return 1
    decks_mod.import_all(con, log=lambda *_: None)
    p = a_mais_mod.payload(con)
    alvo = args.edicao.upper() if args.edicao else None
    sets = [s for s in p["sets"] if alvo is None or s["set"] == alvo]
    if alvo and not sets:
        print(f"{alvo}: não existe no catálogo.", file=sys.stderr)
        return 1
    for s in sets:
        e, l_ = s["excedente"], s["libertadas"]
        print(f"{s['name']} — {e['copies']} cópias a mais em {e['cards']} impressões · "
              f"{l_['copies']} libertadas dos decks em {l_['cards']} cartas"
              + ("" if s["button"] else "   (sem botão no site; em «Todas»)"))
        for x in e["items"]:
            onde = " + ".join(p_ for p_, n in (("binder", x["from_binder"]),
                                                ("Coleção", x["from_colecao"])) if n)
            print(f"    {cardmarket.codigo(x['code']):<12} {x['name'][:34]:<34} "
                  f"tens {x['have']}/{x['target']}  a mais {x['extra']}  ({onde}"
                  + (f", {x['used']} nos decks" if x["used"] else "")
                  + (", escondida" if x["hidden"] else "") + ")")
        for x in l_["items"]:
            ainda = ", ".join(f"{d['deck']} {d['qty']}" for d in x["still_wanted"])
            print(f"    {cardmarket.codigo(x['code']):<12} {x['name'][:34]:<34} "
                  f"saiu de {x['deck']} ({x['qty']}) a {x['ts'][:10]}  tens {x['have']}"
                  + (f"  ainda pedida: {ainda}" if ainda else ""))
        print()
    t, h = p["totals"], p["history"]
    print(f"a mais: {t['excedente']['copies']} cópias em {t['excedente']['cards']} impressões · "
          f"libertadas: {t['libertadas']['copies']} em {t['libertadas']['cards']} cartas.")
    # As runas ficam de fora dos dois blocos (2026-09-17, à noite: *"no a mais
    # nunca aparece Runas"*) — diz-se quantas, em vez de as apagar em silêncio.
    ru = (p.get("scope") or {}).get("runas") or {}
    if p.get("scope", {}).get("sem_runas") and (
            ru.get("excedente", {}).get("copies") or ru.get("libertadas", {}).get("copies")):
        print(f"fora, por serem runas: {ru['excedente']['copies']} cópias a mais em "
              f"{ru['excedente']['cards']} impressões · {ru['libertadas']['copies']} "
              f"libertadas em {ru['libertadas']['cards']} cartas — organizas à mão.",
              file=sys.stderr)
    print("registo dos decks: " + (f"desde {h['since'][:10]}, {h['events']} mudanças"
                                   if h["since"] else "ainda vazio — começa na próxima "
                                   "importação das listas"), file=sys.stderr)
    return 0


def cmd_runas(args) -> int:
    """O bloco «Runas — 12 de cada» do fim da Coleção (2026-09-19): o contador
    dele por runa, com o que a coleção sabe ao lado. Não conta para nada.
    `--mais`/`--menos NOME` mexem no contador — só nele — como os `+`/`−` do
    site."""
    con = db.connect()
    if db.catalog_is_empty(con):
        print("catálogo vazio — corre `riftvault sync`.", file=sys.stderr)
        return 1
    if args.mais or args.menos:
        nome = args.mais or args.menos
        delta = args.n if args.mais else -args.n
        try:
            r = runas_vista_mod.ajustar(con, nome, delta)
        except runas_vista_mod.RunaDesconhecida as exc:
            print(str(exc), file=sys.stderr)
            con.close()
            return 1
        print(f"{r['name']}: {r['qty']} (na coleção: {r['na_colecao']}) — "
              f"só o teu contador mexeu.")
        con.close()
        return 0
    p = runas_vista_mod.payload(con)
    if p["semeadas"]:
        print(f"contador semeado com o que tens na mão: "
              + ", ".join(f"{ck} {n}" for ck, n in p["semeadas"].items()), file=sys.stderr)
    for x in p["runas"]:
        extra = (f"  (sem as retiradas: {x['sem_retiradas']})"
                 if x["sem_retiradas"] != x["total"] else "")
        print(f"{x['name']:<12} {x['contador']:>3}/{x['target']}   "
              f"na coleção: {x['total']}{extra}")
        for o in x["origens"]:
            print(f"    {o['qty']:>3}  {cardmarket.codigo(o['code']):<12} {o['label']}")
    t = p["totals"]
    print(f"\ncontador: {t['contador']} de {t['alvo']} em {t['cards']} runas · "
          f"na coleção: {t['total']}"
          + (f" (sem as retiradas: {t['sem_retiradas']})"
             if t["sem_retiradas"] != t["total"] else ""))
    print(p["nota"], file=sys.stderr)
    con.close()
    return 0


def _precos_foil(r: dict) -> str:
    """« · foil 1,50 € (normal 0,11 €)» — os dois preços de uma impressão.

    Sem preço de foil no CardTrader diz-se que a cópia foil conta ao da normal:
    é o FALLBACK, e ele tem de o ver na linha em vez de o adivinhar.
    """
    if r.get("price") is None and r.get("price_foil") is None:
        return ""
    if r.get("price_foil") is not None:
        return (f" · foil {prices.eur(r['price_foil'])} "
                f"(normal {prices.eur(r['price'])})")
    return (f" · sem oferta foil no CardTrader — uma foil conta ao preço da "
            f"normal, {prices.eur(r['price'])}")


def cmd_foil(args) -> int:
    """A contagem de FOIL e NÃO-FOIL das comuns e incomuns (2026-09-22).

    Sem REF, o resumo por edição e por raridade (impressões, normais, foil,
    total). Com REF, quantas foils dessa impressão; `--mais`/`--menos [N]`
    acrescentam e tiram FOILS.

    O FOIL SOMA-SE (2026-09-26): `--mais 2` dá-lhe duas foils a mais das
    normais que já tinha, e o total da impressão SOBE. Não mexe nas cópias
    normais (`copies.qty`) e, com os dois botões dele desligados — a omissão —,
    nenhum número do site muda com isto.
    """
    con = db.connect()
    if db.catalog_is_empty(con):
        print("catálogo vazio — corre `riftvault sync`.", file=sys.stderr)
        return 1
    cfg = config.load()
    if args.mais or args.menos:
        if not args.ref:
            print("erro: `--mais`/`--menos` precisam da impressão "
                  "(`riftvault foil OGN-045 --mais 2`).", file=sys.stderr)
            con.close()
            return 1
        delta = args.mais if args.mais else -args.menos
        try:
            r = foil_mod.ajustar(con, args.ref, delta, source="cli", cfg=cfg)
        except (collection.UnknownPrinting, foil_mod.ForaDoAmbito) as exc:
            print(str(exc), file=sys.stderr)
            con.close()
            return 1
        print(f"{r['name']} [{_codigo_curto(r['code'])}]: {r['applied']:+d} foil -> "
              f"{r['normal']} normais · {r['foil']} foil = {r['total']} cópias "
              f"(as normais não mexeram){_precos_foil(r)}")
        con.close()
        return 0
    if args.ref:
        try:
            r = foil_mod.ajustar(con, args.ref, 0, source="cli", cfg=cfg)
        except (collection.UnknownPrinting, foil_mod.ForaDoAmbito) as exc:
            print(str(exc), file=sys.stderr)
            con.close()
            return 1
        print(f"{r['name']} [{_codigo_curto(r['code'])}]: {r['normal']} normais · "
              f"{r['foil']} foil = {r['total']} cópias{_precos_foil(r)}")
        con.close()
        return 0
    sets = metrics.sets_payload(con, cfg)
    if args.edicao:
        sets = [s for s in sets if s["id"] == args.edicao.upper()]
        if not sets:
            print(f"edição desconhecida: {args.edicao}", file=sys.stderr)
            con.close()
            return 1
    r = foil_mod.resumo(con, cfg, set_id=sets[0]["id"] if args.edicao else None)
    # O preço das foils diz-se onde a contagem aparece (2026-09-26, à tarde):
    # quanto valem ao preço de foil e quantas caem no fallback.
    print(foil_mod.texto(r, sets, prices.valor_dos_foils(con, cfg)))
    print(f"\nâmbito: impressões base, não sobrenumeradas, de raridade "
          f"{'/'.join(r['raridades'])} (foil.raridades/foil.edicoes_fora). "
          f"As normais e as foils são duas contagens independentes; o total "
          f"nunca se grava, é a soma.", file=sys.stderr)
    con.close()
    return 0


def cmd_selado(args) -> int:
    """PRODUTO SELADO (2026-09-25): o que HÁ, o que TEM e o que NÃO TEM.

    Sem opções, a lista por edição com os três estados. `--sync` vai ao
    CardTrader buscar o catálogo e os preços e reescreve o
    `data/selado_catalogo.json` (é um comando À MÃO — o `riftvault prices`
    diário não mexeu). `--mais/--menos ID [N]` mexem no que ele tem.

    **Nada disto toca na Coleção**: escreve-se na `sealed_copies` e mais
    nenhum módulo a lê. O valor do selado é um total próprio.
    """
    from . import selado as selado_mod

    cfg = config.load()
    if args.sync:
        print("A ir buscar o produto selado ao CardTrader (1 pedido/s)...")
        try:
            r = selado_mod.sincronizar(cfg=cfg, log=print)
        except prices.CardTraderError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"\n{r['produtos']} produtos (não-singles) e {r['precos']} preços "
              f"em {r['pedidos']} pedidos -> {r['caminho']}")
        if r["sem_preco"]:
            print(f"  {r['sem_preco']} sem oferta no CardTrader")

    con = db.connect()
    n = _qty(args.n)
    try:
        if args.mais:
            res = selado_mod.ajustar(con, args.mais, n, cfg, source="cli")
            print(f"{res['product_id']}: {res['applied']:+d} -> {res['qty']}")
        elif args.menos:
            res = selado_mod.ajustar(con, args.menos, -n, cfg, source="cli")
            print(f"{res['product_id']}: {res['applied']:+d} -> {res['qty']}")
    except (selado_mod.ProdutoDesconhecido, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        con.close()
        return 1

    p = selado_mod.payload(con, cfg, editable=True)
    if args.edicao:
        alvo = args.edicao.upper()
        p["sets"] = [g for g in p["sets"] if g["set"] == alvo]
        if not p["sets"]:
            print(f"não há produto selado em {alvo}", file=sys.stderr)
            con.close()
            return 1
    if args.so_faltas or args.so_tenho:
        # «Falta» não conta os por sair — ele não pode ter o que ainda não saiu.
        serve = ((lambda x: x["qty"] > 0) if args.so_tenho
                 else (lambda x: x["qty"] == 0 and not x["por_sair"]))
        for g in p["sets"]:
            g["items"] = [x for x in g["items"] if serve(x)]
        p["sets"] = [g for g in p["sets"] if g["items"]]
    if not p["items"]:
        print("A lista do produto selado está vazia — corre "
              "`riftvault selado --sync` para a ir buscar ao CardTrader.")
        con.close()
        return 0
    print(selado_mod.texto(p))
    print(f"\nO valor do selado ({selado_mod.eur(p['totals']['valor_cents'])}) é "
          f"à PARTE do valor da Coleção — nunca se somam.", file=sys.stderr)
    if p["catalogo_em"]:
        print(f"Catálogo de {p['catalogo_em']} (CardTrader). "
              f"`riftvault selado --sync` para actualizar.", file=sys.stderr)
    con.close()
    return 0


def cmd_venda(args) -> int:
    """A VENDA EM CURSO (2026-09-25): o que ele está a vender agora e a conta.

    Sem opções, a lista e o total. `--juntar/--tirar REF [N]` mexem nas
    linhas; `--trend REF EUR` grava o Trend do Cardmarket (o número é DELE, a
    olhar para a página deles — a app não tem preços do Cardmarket e o do
    CardTrader nunca entra na conta); `--limpar` esvazia; `--vender` baixa as
    cópias, e pede `--sim` para o fazer.
    """
    from . import venda as venda_mod

    con = db.connect()
    if db.catalog_is_empty(con):
        print("catálogo vazio — corre `riftvault sync`.", file=sys.stderr)
        return 1
    cfg = config.load()
    n = _qty(args.n)

    try:
        if args.juntar:
            r = venda_mod.juntar(con, args.juntar, n, source="cli")
            print(f"{r['printing_id']}: {r['applied']:+d} -> {r['qty']} na venda")
        elif args.tirar:
            r = venda_mod.juntar(con, args.tirar, -n, source="cli")
            print(f"{r['printing_id']}: {r['applied']:+d} -> {r['qty']} na venda")
        elif args.trend:
            ref, valor = args.trend
            cents = None if str(valor).strip() == "" else round(
                float(str(valor).replace(",", ".").replace("€", "").strip()) * 100)
            r = venda_mod.guardar_trend(con, ref, cents, source="cli")
            print(f"{r['printing_id']}: Trend do Cardmarket = "
                  + (prices.eur(r["cents"]) if r["cents"] is not None else "(apagado)"))
        elif args.limpar:
            print(f"venda limpa ({venda_mod.limpar(con)} linhas). "
                  f"Os Trends guardados ficam.")
        elif args.vender:
            res = venda_mod.vender(con, confirmar=bool(args.sim), source="cli")
            print(f"venda fechada: {res['copies']} cópias, "
                  f"{prices.eur(res['totals']['cents'])}")
            for f in res["itens"]:
                print(f"  -{f['baixadas']} {f['name']} [{_codigo_curto(f['code'])}]"
                      + (f"  (faltaram {f['em_falta']})" if f["em_falta"] else ""))
    except (collection.UnknownPrinting, venda_mod.SemLinha, venda_mod.VendaVazia,
            ValueError) as exc:
        print(str(exc), file=sys.stderr)
        con.close()
        return 1
    except venda_mod.PrecisaConfirmar as exc:
        print(f"{exc} — junta `--sim`.", file=sys.stderr)
        con.close()
        return 1

    lista = venda_mod.itens(con, cfg)
    t = venda_mod.conta(lista)
    if not lista:
        print("Não há nada na venda. `riftvault venda --juntar OGN-045 3`.")
        con.close()
        return 0
    largura = max(len(x["name"]) for x in lista)
    print(f"\n{'carta':<{largura}}  {'código':<12} {'qtd':>4}  {'Trend':>10}  {'subtotal':>10}")
    for x in lista:
        trend = prices.eur(x["trend"]) if x["trend"] is not None else "— por meter"
        marcas = []
        if x["trend_velho"]:
            marcas.append(f"Trend de há {x['trend_dias']} dias")
        if x["a_mais_do_que_tens"]:
            marcas.append(f"só tens {x['have']}")
        if x["em_decks"]:
            marcas.append("em " + ", ".join(x["em_decks"]))
        print(f"{x['name']:<{largura}}  {_codigo_curto(x['code']):<12} {x['qty']:>4}  "
              f"{trend:>10}  "
              f"{prices.eur(x['subtotal']) if x['trend'] is not None else '—':>10}"
              + (f"   ({'; '.join(marcas)})" if marcas else ""))
    print(f"\nTOTAL: {prices.eur(t['cents'])}  ({t['copies']} "
          f"{'carta' if t['copies'] == 1 else 'cartas'} em {t['lines']} "
          f"{'linha' if t['lines'] == 1 else 'linhas'})")
    if t["sem_trend"]:
        print(f"FALTAM {t['sem_trend']} {'linha' if t['sem_trend'] == 1 else 'linhas'} "
              f"sem Trend — {'vale' if t['sem_trend'] == 1 else 'valem'} ZERO no total. "
              f"O preço do CardTrader não as substitui.", file=sys.stderr)
    print("Os preços da conta são o Trend do Cardmarket, metido à mão "
          "(`riftvault venda --trend OGN-045 12,50`).", file=sys.stderr)
    con.close()
    return 0


def cmd_proprias(args) -> int:
    """As CÓPIAS PRÓPRIAS de cada deck (2026-09-21): sem deck, uma linha por
    deck (quantas tem guardadas, quantas servem, o que falta); com o SLUG,
    carta a carta — pedidas, próprias, da Coleção, faltam — e as próprias
    que não servem. `--mais`/`--menos REF [N]` metem e tiram (no `copies` E
    no local `proprio:<slug>`, de uma vez — a Coleção não mexe). REF é um
    código (`OGN-045`), um id, ou o nome da carta (grava na base em que se
    compra)."""
    con = db.connect()
    if db.catalog_is_empty(con):
        print("catálogo vazio — corre `riftvault sync`.", file=sys.stderr)
        return 1
    decks_mod.import_all(con, log=lambda *_: None)
    if args.mais or args.menos:
        if not args.slug:
            print("erro: `--mais`/`--menos` precisam do slug do deck "
                  "(`riftvault proprias azir --mais OGN-045 3`).", file=sys.stderr)
            con.close()
            return 1
        ref = args.mais or args.menos
        delta = _qty(args.n) if args.mais else -_qty(args.n)
        try:
            pid = proprias_mod.impressao_para(con, args.slug, ref)
            r = proprias_mod.ajustar(con, args.slug, pid, delta, source="cli")
        except (collection.UnknownPrinting, proprias_mod.NaoServe,
                proprias_mod.DeckDesconhecido) as exc:
            print(str(exc), file=sys.stderr)
            con.close()
            return 1
        print(f"{_describe(con, r['printing_id'])}: {r['applied']:+d} -> {r['qty']} "
              f"próprias do deck {r['deck']} ({r['total']} ao todo; a Coleção não mexeu)")
        con.close()
        return 0
    if not args.slug:
        print(f"{'#':<3} {'deck':<40} {'pede':>5} {'tenho':>6} {'próprias':>8} "
              f"{'da Coleção':>10} {'faltam':>7}  não servem")
        for d in proprias_mod.resumo(con):
            col = d["no_deck"] + d["no_binder"] + d["na_colecao"]
            print(f"{d['priority']:<3} {d['name'][:40]:<40} {d['wanted']:>5} {d['have']:>6} "
                  f"{d['proprias']:>8} {col:>10} {d['missing']:>7}  "
                  f"{d['proprias_fora'] or ''}")
        print(f"\nsó versões base: {'sim' if decks_mod.so_base() else 'não'} "
              f"(decks.so_base). `riftvault proprias <slug>` mostra um deck; "
              f"`--mais REF [N]`/`--menos` metem e tiram.")
        con.close()
        return 0
    try:
        row = proprias_mod.deck_por_slug(con, args.slug)
    except proprias_mod.DeckDesconhecido as exc:
        print(str(exc), file=sys.stderr)
        con.close()
        return 1
    p = decks_mod.deck_payload(con, row["deck_id"])
    lc = p["locais"]
    print(f"{p['name']}: próprias {lc['proprias']} · da Coleção "
          f"{lc['no_deck'] + lc['no_binder'] + lc['na_colecao']} · a comprar {lc['missing']}"
          + (f" · a caminho {lc['ordered']}" if lc.get("ordered") else "")
          + ("  [só versões base]" if p.get("so_base") else "") + "\n")
    print(f"{'carta':<38} {'pede':>4} {'próprias':>8} {'Coleção':>7} {'faltam':>6}  grava em")
    for sec in p["sections"]:
        for c in sec["cards"]:
            if not c.get("contado", True):
                continue
            if args.so_faltas and not c["missing"]:
                continue
            col = c["no_deck"] + c["no_binder"] + c["na_colecao"]
            grava = (c.get("propria_compra") or {}).get("code")
            print(f"{c['name'][:38]:<38} {c['wanted']:>4} {c.get('proprias', 0):>8} {col:>7} "
                  f"{c['missing']:>6}  {_codigo_curto(grava) if grava else '—'}")
    if p.get("proprias_fora"):
        print(f"\nPróprias que NÃO servem este deck ({lc['proprias_fora']} cópias): "
              + ", ".join(f"{x['qty']}x {x['name']} [{_codigo_curto(x['code'])}] ({x['motivo']})"
                          for x in p["proprias_fora"]))
    con.close()
    return 0


def cmd_seguir(args) -> int:
    """Seguir jogadores no Piltover Archive (2026-09-17): os decks de cada um,
    o que mudou desde a última corrida, e o que FALTA ao André para montar
    cada deck. Nunca euros — ele pediu «o que falta», não «quanto custaria»."""
    con = db.connect()
    if db.catalog_is_empty(con):
        print("catálogo vazio — corre `riftvault sync`.", file=sys.stderr)
        return 1
    cfg = config.load()
    nomes = args.jogador or seguir_mod.opcoes(cfg)["jogadores"]
    if not nomes:
        print("ninguém para seguir: escreve os handles em `seguir.jogadores` no "
              "riftvault_config.json, ou passa --jogador NOME.", file=sys.stderr)
        return 1
    buscar = seguir_mod.sem_rede if args.sem_rede else seguir_mod.cliente(cfg)
    try:
        p = seguir_mod.correr(con, buscar, cfg=cfg, jogadores=nomes, sem_rede=args.sem_rede,
                              log=lambda s: print(s, file=sys.stderr))
    except seguir_mod.SeguirError as exc:
        print(f"seguir: {exc}", file=sys.stderr)
        return 1
    finally:
        con.close()
    if args.json:
        print(json.dumps(p, ensure_ascii=False, indent=1))
        return 0
    for j in p["players"]:
        c = j["counts"]
        conta = (f"{j['found']} decks" + (f" (o perfil diz {j['public_decks']} públicos)"
                                          if j["public_decks"] is not None and j["public_decks"] != j["found"]
                                          else ""))
        mudou = " · ".join(f"{n} {k}" for k, n in c.items() if n)
        print(f"{j['display']} (@{j['player']}) — {j['url']}")
        print(f"  {conta} · {mudou or 'nada'}"
              + (f" · {len(j['gone'])} já não aparecem" if j["gone"] else "")
              + (" · listagem cortada (seguir.max_paginas)" if j["truncated"] else "")
              + (" · sem rede: o que estava guardado" if j["offline"] else ""))
        for d in j["decks"]:
            if args.so_mudados and d["estado"] not in ("novo", "actualizado"):
                continue
            print()
            data = (d["edited_at"] or "")[:10]
            print(f"== {d['title']}  [{d['estado']}" + (f" · editado a {data}" if data else "") + "]")
            print(f"   {d['url']}")
            f = d["faltas"]
            if f is None:
                print("   (sem lista guardada — corre sem --sem-rede para a ir buscar)")
                continue
            legend = f" · Legend: {d['legend']}" if d.get("legend") else ""
            if f["complete"]:
                print(f"   {f['wanted_copies']} cartas{legend} · TENS TUDO")
            else:
                print(f"   {f['wanted_copies']} cartas{legend} · faltam {f['missing_copies']} cópias "
                      f"de {f['missing_cards']} cartas"
                      + (f" · {len(f['unidentified'])} POR IDENTIFICAR ({f['unidentified_copies']} cópias) "
                         f"— a falta está incompleta" if f["unidentified"] else ""))
            for x in f["missing"]:
                print(f"     {x['missing']}x {x['catalog_name'][:40]:<40} {cardmarket.codigo(x['code'] or ''):<10}"
                      f" tens {x['have']} de {x['qty']}")
            for x in f["unidentified"]:
                print(f"     ?  {x['qty']}x {x['name'][:40]:<40} {x['code'] or '':<10} {x['motivo']}")
        for g in j["gone"]:
            print(f"\n-- já não aparece na listagem (desde {g['ausente_desde'][:10]}): {g['title']}  {g['url']}")
        print()
    return 0


def cmd_faltas(args) -> int:
    """O separador «Faltas» na consola: por edição, os quatro blocos — master
    set, alt art, sobrenumeradas, promos — com o que falta de cada
    (2026-09-15; o quarto a 2026-09-19). Só o master set entra nas listas de
    compra gerais; cada bloco tem a sua wantlist: `--cardmarket` com
    `--edicao` e `--bloco` escreve-a para colar (o stdout fica colável, o
    resto vai para o stderr, como no `riftvault wantlist`)."""
    con = db.connect()
    if db.catalog_is_empty(con):
        print("catálogo vazio — corre `riftvault sync`.", file=sys.stderr)
        return 1
    alvo = args.edicao.upper() if args.edicao else None
    if args.cardmarket:
        if not alvo or not args.bloco:
            print("erro: --cardmarket precisa de --edicao e --bloco "
                  f"({', '.join(faltas_edicao.BLOCO_IDS)}).", file=sys.stderr)
            con.close()
            return 1
        try:
            w = faltas_edicao.wantlist(con, alvo, args.bloco, com_codigo=args.codigos)
        except ValueError as e:
            print(f"erro: {e}", file=sys.stderr)
            con.close()
            return 1
        sys.stdout.write(w["text"] + ("\n" if w["text"] else ""))
        print(f"# {w['name']} — {w['label']}: {w['lines']} linhas · {w['copies']} cópias · "
              f"{prices.eur(w['cents'])}"
              + ("" if w["in_lists"] else " (só deste bloco — não está na wantlist geral)"),
              file=sys.stderr)
        if w["foil"]:
            print(f"# {len(w['foil'])} destas só têm oferta foil no mercado: liga o "
                  f"filtro Foil nessas entradas depois de colares.", file=sys.stderr)
        con.close()
        return 0
    p = faltas_edicao.payload(con)
    sets = [s for s in p["sets"] if alvo is None or s["set"] == alvo]
    if alvo and not sets:
        print(f"{alvo}: não existe no catálogo.", file=sys.stderr)
        return 1
    if args.bloco and args.bloco not in faltas_edicao.BLOCO_IDS:
        print(f"erro: bloco desconhecido {args.bloco!r}. Há: "
              f"{', '.join(faltas_edicao.BLOCO_IDS)}.", file=sys.stderr)
        return 1
    for s in sets:
        print(f"{s['name']} — faltam {s['copies']} cópias de {s['cards']} impressões · "
              f"{prices.eur(s['cents'])}"
              + (f" · {s['pending_copies']} a caminho" if s["pending_copies"] else ""))
        for g in s["blocks"]:
            if args.bloco and g["id"] != args.bloco:
                continue
            print(f"  {g['label']} — {g['target_label']} — faltam {g['copies']} cópias de "
                  f"{g['cards']} · {prices.eur(g['cents'])}"
                  + (f" · {g['pending_copies']} a caminho" if g["pending_copies"] else "")
                  + ("" if g["in_lists"] else "   (wantlist própria — não entra nas compras gerais)"))
            for x in g["items"]:
                caminho = f"  ({x['pending']} a caminho)" if x["pending"] else ""
                print(f"    {cardmarket.codigo(x['code']):<12} "
                      f"{x['name'][:34]:<34} tens {x['have']}/{x['target']}  "
                      f"faltam {x['missing']}  {prices.eur(x['total']):>10}{caminho}")
        print()
    t, tl = p["totals"], p["totals_lists"]
    fora = ", ".join(f"{n} {b}" for b, n in sorted(p["scope"]["fora"].items()))
    nas_listas = ", ".join(b["label"] for b in p["blocks"] if b["in_lists"])
    print(f"faltam ao todo: {t['copies']} cópias de {t['cards']} impressões · "
          f"{prices.eur(t['cents'])} · {t['pending_copies']} a caminho (não contam).")
    print(f"a comprar ({nas_listas} — a wantlist geral): {tl['copies']} cópias "
          f"de {tl['cards']} impressões · {prices.eur(tl['cents'])}."
          + (f" Fora do separador: {fora}." if fora else "")
          + (" Os outros blocos têm wantlist própria (--cardmarket --edicao X "
             "--bloco B) e não entram na geral (listas_de_compra.so_master_set)."
             if p["so_master_set"] else ""))
    con.close()
    return 0


def cmd_pending(args) -> int:
    con = db.connect()
    if args.chegou is not None:
        feitas = pending_mod.arrive(con, args.chegou or None)
        if not feitas:
            print("não havia nada por chegar.")
            return 1
        for f in feitas:
            print(f"+{f['qty']}  {_describe(con, f['printing_id'])}  -> {f['total']}")
        print(f"\n{len(feitas)} linhas deram entrada na coleção.")
        con.close()
        return 0

    linhas = pending_mod.listar(con)
    if not linhas:
        print("nada a caminho.")
        return 0
    t = pending_mod.totals(con)
    print(f"A caminho: {t['copies']} cópias em {t['lines']} linhas"
          + (f" · {prices.eur(t['cents'])}" if t["cents"] else "") + "\n")
    for r in linhas:
        so = "  [fora do catálogo]" if r["market_only"] else ""
        preco = f"  {prices.eur((r['unit_cents'] or 0) * r['qty']):>9}" if r["unit_cents"] else ""
        print(f"  #{r['id']:<4} {r['qty']}x {str(r['code']):<16} {str(r['name'])[:26]:<26} "
              f"{r['label']:<11}{preco}{so}")
    con.close()
    return 0


def cmd_encomendas(args) -> int:
    """As encomendas (André, 2026-09-11): o que está a caminho, para que deck
    vai, e o que ainda falta encomendar.

    `--mais REF [N]` / `--menos REF [N]` são os `+`/`−` do separador
    «Encomendas» na consola — a REF é um código de impressão (`OGN-045`, como
    o tile do site) ou o nome da carta (aí vai para a normal mais barata).
    `--chegou [REF]` dá entrada do que está a caminho dessa impressão (por
    código, como o «Chegou» do tile), dessa carta (por nome), ou de tudo.
    """
    con = db.connect()
    if db.catalog_is_empty(con):
        print("catálogo vazio — corre `riftvault sync`.", file=sys.stderr)
        return 1
    decks_mod.import_all(con, log=lambda *_: None)

    def carta_ou_impressao(ref: str) -> tuple[str | None, str | None]:
        """Devolve (card_key, printing_id): um dos dois, conforme a REF."""
        try:
            return None, collection.resolve_printing(con, ref)
        except collection.UnknownPrinting:
            pass
        ck = decks_mod.resolve(con, ref, "main")
        if ck is None:
            raise SystemExit(f"erro: não encontrei nem impressão nem carta {ref!r}")
        return ck, None

    if args.mais or args.menos:
        ref = args.mais or args.menos
        ck, pid = carta_ou_impressao(ref)
        n = _qty(args.qty)
        try:
            if args.mais:
                res = pending_mod.encomendar(con, ck, pid, n, source="cli")
                print(f"+{n}  {_describe(con, res['printing_id'])}  "
                      f"-> {res['open_printing']} a caminho desta impressão")
            else:
                res = pending_mod.anular(con, ck, pid, n, source="cli")
                print(f"-{res['removed']}  {_describe(con, res['printing_id'])}  "
                      f"-> {res['open_printing']} a caminho desta impressão")
        except pending_mod.SemEncomenda as exc:
            print(f"erro: {exc}", file=sys.stderr)
            return 1
        con.close()
        return 0

    if args.chegou is not None:
        ck = pid = None
        if args.chegou:
            ck, pid = carta_ou_impressao(args.chegou)
        # Por código é só essa impressão (o «Chegou» do tile, 2026-09-17);
        # por nome é a carta inteira, seja de que impressão for.
        feitas = pending_mod.arrive(con, None, source="cli", card_key=ck, printing_id=pid)
        if not feitas:
            print("não havia nada por chegar.")
            return 1
        for f in feitas:
            print(f"+{f['qty']}  {_describe(con, f['printing_id'])}  -> {f['total']}")
        print(f"\n{len(feitas)} linhas deram entrada na coleção.")
        con.close()
        return 0

    e = pending_mod.encomendas(con)
    t = e["totals"]
    if not t["copies"]:
        print("Nada a caminho.")
    else:
        print(f"A caminho: {t['copies']} cópias · {t['printings']} impressões · "
              f"{prices.eur(t['cents'])} ao preço de hoje"
              + (f" ({t['sem_preco']} sem preço)" if t["sem_preco"] else "")
              + (f" · pagaste {prices.eur(t['paid'])}" if t["paid"] else ""))
        for g in e["a_caminho"]:
            print(f"\n{g['name']}  — {g['copies']} cópias · {prices.eur(g['cents'])}")
            for it in g["items"]:
                para = " · ".join(f"{x['qty']}x {_deck_curto(x['deck'])}"
                                  for x in it["para"]) or "nenhum deck a pede"
                if it["sem_deck"] and it["para"]:
                    para += f" · {it['sem_deck']} para a Coleção"
                print(f"  {it['qty']}x {str(it['code']).split('/')[0]:<12} "
                      f"{str(it['name'])[:30]:<30} {prices.eur(it['price']):>9}"
                      f"  -> {para}")

    f = e["falta_totals"]
    if f["copies"]:
        print(f"\nFalta encomendar: {f['copies']} cópias de {f['cards']} cartas · "
              f"{prices.eur(f['cents'])}")
        for g in e["falta"]:
            print(f"  {g['name']:<24} {g['copies']:>3} cópias de {g['cards']:>2} cartas"
                  f"  {prices.eur(g['cents']):>9}")
            # A linha de cada carta, com o deck (ou o grupo de Legend) para quem
            # é — é esta lista que ele leva para a encomenda.
            for it in sorted(g["items"], key=lambda x: str(x["code"])):
                print(f"    {it['qty']}x {str(it['code']).split('/')[0]:<12} "
                      f"{str(it['name'])[:30]:<30} {prices.eur(it['price']):>9}"
                      f"  -> {_deck_curto(it['deck'])}")
    else:
        print("\nNão falta encomendar nada aos decks.")
    con.close()
    return 0


def _deck_curto(rotulo: str) -> str:
    """O rótulo de um deck só pela Legend («Leblanc, Deceiver»); num grupo de
    Legend (`A ·· B`, 2026-09-11) encurta cada membro e deixa o «··», que é o
    que diz que a encomenda serve os dois."""
    return decks_mod.GRUPO_SEP.join(
        m.split(" · ")[0] for m in rotulo.split(decks_mod.GRUPO_SEP))


def cmd_local(args) -> int:
    """Onde está cada cópia: Coleção, um deck, ou o binder Decks/Venda.

    André, 2026-09-10: *"a coleção fica em Binders de coleção; as cartas dos
    decks ficam em decks, e haverá um Binder que será apenas e exclusivamente
    para Decks/Venda"*.

    Sem argumentos mostra o resumo. As marcações em lote (`--propor` /
    `--marcar`) são dois passos de propósito: o `--propor` calcula e **não
    grava**, e o `--marcar` grava **só** as linhas que ele escrever. É a lição
    do mtgvault de 2026-09-09 — a lista que o vault calcula nunca é a lista que
    se grava.
    """
    con = db.connect()
    decks_mod.import_all(con, log=lambda *_: None)
    nomes = locais_mod.nomes_dos_decks(con)

    if args.undo:
        res = locais_mod.undo_last(con, source="cli")
        if not res:
            print("não havia movimentos de local para desfazer.")
            return 1
        print(f"desfeito o movimento #{res['undone_op']}: {res['qty']}x "
              f"{_describe(con, res['printing_id'])} voltou a "
              f"{locais_mod.rotulo(res['para'], nomes)}")
        con.close()
        return 0

    if args.desfazer_deck:
        slug = args.desfazer_deck
        if slug not in locais_mod.slugs(con):
            print(f"erro: não há deck chamado {slug!r}", file=sys.stderr)
            return 1
        res = locais_mod.desfazer_deck(con, slug, source="cli")
        print(f"Deck «{slug}» desfeito: {res['copies']} cópias de "
              f"{res['printings']} impressões passaram ao binder Decks/Venda.")
        print("Ficam disponíveis para outro deck. Nada voltou à Coleção — "
              "isso é decisão tua (`riftvault local <ref> N --para colecao`).")
        con.close()
        return 0

    if args.propor:
        if not args.deck:
            print("erro: --propor precisa de --deck <slug>.", file=sys.stderr)
            return 1
        p = locais_mod.propor_deck(con, args.deck)
        if p.get("erro"):
            print(f"erro: {p['erro']}", file=sys.stderr)
            return 1
        if not p["items"]:
            print(f"O deck «{args.deck}» não precisa de nada que esteja na Coleção.")
            con.close()
            return 0
        print(f"PROPOSTA para o deck «{args.deck}» — {p['copies']} cópias que "
              f"estão na Coleção e o deck pede.")
        exemplo = ",".join("{}:{}".format(x["printing_id"], x["qty"])
                           for x in p["items"][:3])
        print("Nada disto foi gravado. Confirma o que quiseres com:")
        print(f'  riftvault local --deck {args.deck} --marcar "{exemplo}"\n')
        for x in p["items"]:
            print(f"  {x['qty']}x {x['printing_id']:<22} {x['code']:<16} "
                  f"{x['name'][:30]:<30} (tens {x['na_colecao']} na Coleção)")
        con.close()
        return 0

    if args.marcar:
        if not args.deck and not args.para:
            print("erro: --marcar precisa de --deck <slug> ou --para <local>.",
                  file=sys.stderr)
            return 1
        destino = args.para or locais_mod.deck_local(args.deck)
        linhas = []
        for pedaco in args.marcar.split(","):
            pedaco = pedaco.strip()
            if not pedaco:
                continue
            ref, _, q = pedaco.partition(":")
            linhas.append({"printing_id": ref.strip(), "qty": int(q or 1)})
        try:
            res = locais_mod.marcar(con, linhas, destino,
                                    de=args.de or locais_mod.COLECAO, source="cli")
        except (locais_mod.LocalInvalido, locais_mod.SemCopias) as exc:
            print(f"erro: {exc}", file=sys.stderr)
            return 1
        for x in res["movidas"]:
            print(f"  {x['qty']}x {_describe(con, x['printing_id'])} -> "
                  f"{locais_mod.rotulo(x['para'], nomes)}")
        for x in res["falhadas"]:
            print(f"  X {x['printing_id']}: {x['erro']}", file=sys.stderr)
        print(f"\n{res['copies']} cópias marcadas. Rasto em "
              f"data/{locais_mod.LOG_NAME}.")
        con.close()
        return 0 if not res["falhadas"] else 1

    if args.ref:
        if not args.para:
            print("erro: falta --para <colecao|binder|deck:slug>.", file=sys.stderr)
            return 1
        try:
            res = locais_mod.mover(con, args.ref, _qty(args.qty),
                                   args.de or locais_mod.COLECAO, args.para,
                                   source="cli")
        except (locais_mod.LocalInvalido, locais_mod.SemCopias) as exc:
            print(f"erro: {exc}", file=sys.stderr)
            return 1
        except collection.UnknownPrinting as exc:
            print(f"erro: {exc}", file=sys.stderr)
            return 1
        print(f"{res['qty']}x {_describe(con, res['printing_id'])}: "
              f"{locais_mod.rotulo(res['de'], nomes)} -> "
              f"{locais_mod.rotulo(res['para'], nomes)}")
        con.close()
        return 0

    linhas = locais_mod.resumo(con)
    total = sum(x["copies"] for x in linhas)
    print(f"Onde estão as {total} cópias:\n")
    for x in linhas:
        print(f"  {x['copies']:>5} cópias  {x['printings']:>4} impressões  "
              f"{x['label']}")
    if len(linhas) <= 1:
        print("\n(ainda não marcaste nada: por omissão está tudo na Coleção)")
    print(f"\nMarcar: riftvault local --deck <slug> --propor  e depois --marcar")
    con.close()
    return 0


def cmd_find(args) -> int:
    con = db.connect()
    rows = con.execute(
        "SELECT p.printing_id, p.public_code, p.name, p.variant_label, p.set_id, "
        "       COALESCE(c.qty,0) AS qty "
        "FROM catalog.printings p LEFT JOIN copies c ON c.printing_id = p.printing_id "
        "WHERE lower(p.name) LIKE ? OR lower(p.printing_id) LIKE ? "
        "ORDER BY p.set_id, p.api_sort LIMIT ?",
        (f"%{args.query.lower()}%", f"%{args.query.lower()}%", args.n),
    ).fetchall()
    for r in rows:
        print(f"{r['printing_id']:<22} {r['public_code']:<16} "
              f"{r['variant_label']:<12} qty={r['qty']:<3} {r['name']}")
    if not rows:
        print("nada encontrado.")
    con.close()
    return 0


# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="riftvault", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("sync", help="descarrega o catálogo da RiftScribe")
    p.add_argument("--set", action="append", help="só esta edição (repetível)")
    p.add_argument("--images", action="store_true", help="descarrega também as imagens")
    p.add_argument("--fast", action="store_true", help="sem pausa entre pedidos")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("images", help="descarrega as imagens em falta")
    p.add_argument("--set", action="append")
    p.set_defaults(func=cmd_images)

    p = sub.add_parser("serve", help="modo edição: servidor local")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8770)
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("build", help="modo publicado: gera o site estático")
    p.add_argument("--out", default=None)
    p.add_argument("--se-mudou", dest="se_mudou", action="store_true",
                   help="só reescreve o site se o conteúdo mudou mesmo "
                        "(ignora o relógio) — é o que a tarefa de 30 em 30 min usa")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("add", help="soma cópias a uma impressão")
    p.add_argument("ref", help="OGN-100a, ogn-100a-298, OGN-301*, UNL-T03")
    p.add_argument("qty", nargs="?", default="1", help="3 ou x3 (default 1)")
    p.add_argument("--foil", action="store_true", help="aceite e ignorado")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("remove", help="tira cópias a uma impressão")
    p.add_argument("ref")
    p.add_argument("qty", nargs="?", default="1")
    p.add_argument("--foil", action="store_true", help="aceite e ignorado")
    p.set_defaults(func=cmd_remove)

    p = sub.add_parser("set", help="fixa a quantidade de uma impressão")
    p.add_argument("ref")
    p.add_argument("qty")
    p.set_defaults(func=cmd_set)

    p = sub.add_parser("undo", help="desfaz a última operação")
    p.set_defaults(func=cmd_undo)

    p = sub.add_parser("log", help="histórico de alterações")
    p.add_argument("-n", type=int, default=20)
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("stats", help="resumo das duas métricas por edição")
    p.add_argument("--usadas", action="store_true",
                   help="lista as cartas da coleção que os decks usam, e quais")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("decks", help="lista os decks e a alocação por prioridade")
    p.add_argument("--order", help="nova ordem por slug, ex: azir,ornn "
                                   "(o primeiro passa a principal; recusa quando "
                                   "há `decks.ordem` no config — é lá que se muda)")
    p.add_argument("--recomecar-registo", action="store_true",
                   help="apaga o registo do que as listas pedem (deck_need_log) e "
                        "recomeça-o com os decks de hoje — as «libertadas» do A mais "
                        "ficam a zero")
    p.add_argument("--montar", metavar="SLUG",
                   help="marca o deck como MONTADO (escreve `decks.montados` no "
                        "riftvault_config.json): volta a servir-se da Coleção")
    p.add_argument("--desmontar", metavar="SLUG",
                   help="marca o deck como DESMONTADO: deixa de consumir o que quer "
                        "que seja da Coleção — a lista continua a ver-se")
    p.set_defaults(func=cmd_decks)

    p = sub.add_parser("deck", help="detalhe de um deck: o que tenho e o que falta")
    p.add_argument("slug", help="nome do ficheiro sem .txt, ex: azir")
    p.add_argument("--onde", action="store_true",
                   help="mostra também que impressões usar nas que tenho")
    p.set_defaults(func=cmd_deck)

    p = sub.add_parser("shopping", help="lista de compras do que falta")
    p.add_argument("--deck", help="só deste deck (por omissão, todos)")
    p.add_argument("--csv", help="escreve para um ficheiro CSV")
    p.set_defaults(func=cmd_shopping)

    p = sub.add_parser("map", help="mapeia as impressões para o CardTrader")
    p.set_defaults(func=cmd_map)

    p = sub.add_parser("prices", help="descarrega os preços do CardTrader")
    p.set_defaults(func=cmd_prices)

    p = sub.add_parser("value", help="valor da coleção")
    p.add_argument("-n", type=int, default=15, help="quantas mostrar no top")
    p.set_defaults(func=cmd_value)

    p = sub.add_parser("wantlist", help="lista de texto para a wantlist do Cardmarket")
    p.add_argument("--edicao", help="as faltas do master set desta edição (OGN, SFD, …) "
                                    "em vez das listas dos decks")
    p.add_argument("--cardmarket", action="store_true",
                   help="as faltas do master set de TODAS as edições, na ordem "
                        "dos separadores")
    p.add_argument("--codigos", action="store_true",
                   help="com --edicao/--cardmarket: 'N Nome [OGN-007]' em vez da "
                        "versão e da edição, para desambiguar variantes à mão")
    p.add_argument("--nivel", type=int,
                   help="com --edicao/--cardmarket: só até N de cada (1 = uma de "
                        "cada, 2 = duas); sem isto, o playset da sequência")
    p.add_argument("--deck", help="só deste deck (slug)")
    p.add_argument("--todos", action="store_true",
                   help="cenário de ter os decks todos montados ao mesmo tempo")
    p.add_argument("--pimp", action="store_true",
                   help="versões alteradas das cartas dos decks, em vez das faltas")
    p.add_argument("--sem-edicao", action="store_true", dest="sem_edicao",
                   help="não escrever a edição entre parênteses")
    p.add_argument("--out", help="escrever para ficheiro em vez do ecrã")
    p.set_defaults(func=cmd_wantlist)

    p = sub.add_parser("a-subir", help="o que falta do master set e está a subir")
    p.add_argument("--cardmarket", action="store_true",
                   help="escreve as linhas para colar na wantlist do Cardmarket")
    p.add_argument("--codigos", action="store_true",
                   help="com --cardmarket: 'N Nome [UNL-228]' em vez da versão "
                        "e da edição, para desambiguar variantes à mão")
    # O argparse trata o help como uma string de formato: '%' tem de vir dobrado.
    p.add_argument("--csv", help="escreve um CSV com quantidade, nome, código, "
                                 "edição, raridade, preço, Δ%% e custo")
    p.add_argument("--todas", action="store_true",
                   help="tudo o que falta do master set, não só o que sobe")
    p.add_argument("--out", help="com --cardmarket: escrever para ficheiro")
    p.set_defaults(func=cmd_a_subir)

    p = sub.add_parser("faltas", help="o separador Faltas: por edição, o que falta "
                                      "ao master set, às alt art, às sobrenumeradas "
                                      "e às promos — cada bloco com a sua wantlist")
    p.add_argument("--edicao", help="só esta edição (OGN, SFD, …)")
    p.add_argument("--bloco", help="só este bloco (master, alt_art, overnumbered, special)")
    p.add_argument("--cardmarket", action="store_true",
                   help="com --edicao e --bloco: a wantlist desse bloco, para colar")
    p.add_argument("--codigos", action="store_true",
                   help="com --cardmarket: 'N Nome [OGN-007]' em vez da versão")
    p.set_defaults(func=cmd_faltas)

    p = sub.add_parser("a-mais", help="o separador A mais: por edição, o excedente "
                                      "acima do alvo e as cartas libertadas dos decks")
    p.add_argument("--edicao", help="só esta edição (OGN, SFD, …)")
    p.set_defaults(func=cmd_a_mais)

    p = sub.add_parser("runas", help="o bloco Runas do fim da Coleção: o teu contador "
                                     "por runa, com o que a coleção sabe ao lado — não conta")
    p.add_argument("--mais", metavar="RUNA", help="soma ao contador desta runa (só a ele)")
    p.add_argument("--menos", metavar="RUNA", help="tira do contador desta runa (nunca abaixo de 0)")
    p.add_argument("--n", type=int, default=1, help="quantas (omissão 1)")
    p.set_defaults(func=cmd_runas)

    p = sub.add_parser("foil", help="quantas das comuns e incomuns são foil: o "
                                    "resumo por edição, ou os + e - de uma impressão")
    p.add_argument("ref", nargs="?", help="OGN-045, ogn-045-298 (sem ela, o resumo)")
    p.add_argument("--mais", nargs="?", type=int, const=1, metavar="N",
                   help="marca mais N cópias como foil (omissão 1)")
    p.add_argument("--menos", nargs="?", type=int, const=1, metavar="N",
                   help="desmarca N (nunca abaixo de 0)")
    p.add_argument("--edicao", help="só esta edição (OGN, SFD, …)")
    p.set_defaults(func=cmd_foil)

    p = sub.add_parser("venda", help="a venda em curso e a conta para quem compra "
                                     "(preços: o Trend do Cardmarket, metido à mão)")
    p.add_argument("--juntar", metavar="REF", help="mete cópias desta impressão na venda")
    p.add_argument("--tirar", metavar="REF", help="tira cópias da venda")
    p.add_argument("n", nargs="?", help="quantas (3 ou x3; omissão 1)")
    p.add_argument("--trend", nargs=2, metavar=("REF", "EUR"),
                   help="grava o Trend do Cardmarket desta impressão (EUR vazio apaga)")
    p.add_argument("--limpar", action="store_true", help="esvazia a venda (os Trends ficam)")
    p.add_argument("--vender", action="store_true",
                   help="marca como vendidas: BAIXA as cópias (pede --sim)")
    p.add_argument("--sim", action="store_true", help="confirma o --vender")
    p.set_defaults(func=cmd_venda)

    p = sub.add_parser("selado", help="produto selado (displays, cases, decks, bundles, "
                                      "Proving Grounds): o que há, o que tens e o que não tens")
    p.add_argument("--sync", action="store_true",
                   help="vai ao CardTrader buscar a lista e os preços (1 pedido/s)")
    p.add_argument("--mais", metavar="ID", help="mais unidades deste produto (ct-330791)")
    p.add_argument("--menos", metavar="ID", help="menos unidades deste produto")
    p.add_argument("n", nargs="?", help="quantas (3 ou x3; omissão 1)")
    p.add_argument("--edicao", help="só esta edição (OGN, VEN, RAD, …)")
    p.add_argument("--so-faltas", action="store_true",
                   help="só o que não tens (sem os que ainda não saíram)")
    p.add_argument("--so-tenho", action="store_true", help="só o que tens")
    p.set_defaults(func=cmd_selado)

    p = sub.add_parser("proprias", help="as cópias PRÓPRIAS de cada deck (não contam "
                                        "para a Coleção): por deck, ou um deck carta a carta; + e -")
    p.add_argument("slug", nargs="?", help="o deck (nome do ficheiro em decks/, sem .txt)")
    p.add_argument("--mais", metavar="REF", help="mete cópias desta impressão nas próprias do deck")
    p.add_argument("--menos", metavar="REF", help="tira cópias desta impressão das próprias do deck")
    p.add_argument("n", nargs="?", help="quantas (3 ou x3; omissão 1)")
    p.add_argument("--so-faltas", dest="so_faltas", action="store_true",
                   help="só as cartas que faltam ao deck")
    p.set_defaults(func=cmd_proprias)

    p = sub.add_parser("seguir", help="os decks dos jogadores seguidos no Piltover "
                                      "Archive e o que falta para os montar")
    p.add_argument("--jogador", action="append", metavar="NOME",
                   help="só este handle (repetível); sem ele, os de seguir.jogadores")
    p.add_argument("--so-mudados", dest="so_mudados", action="store_true",
                   help="só os decks novos ou actualizados nesta corrida")
    p.add_argument("--sem-rede", dest="sem_rede", action="store_true",
                   help="não vai ao site: mostra o que ficou guardado da última corrida")
    p.add_argument("--json", action="store_true", help="o payload em JSON, em vez do texto")
    p.set_defaults(func=cmd_seguir)

    p = sub.add_parser("pending", help="encomendas a caminho")
    p.add_argument("--chegou", nargs="?", type=int, const=0, default=None,
                   metavar="ID",
                   help="dá entrada na coleção: sem ID, tudo o que está aberto")
    p.set_defaults(func=cmd_pending)

    p = sub.add_parser("encomendas", help="o que está a caminho, para que deck "
                                          "vai, e o que falta encomendar")
    p.add_argument("--mais", metavar="REF",
                   help="mais N a caminho: código (OGN-045) ou nome da carta")
    p.add_argument("--menos", metavar="REF", help="menos N a caminho")
    p.add_argument("qty", nargs="?", default="1", help="com --mais/--menos: 3 ou x3")
    p.add_argument("--chegou", nargs="?", const="", default=None, metavar="REF",
                   help="dá entrada na coleção: desta carta, ou de tudo sem REF")
    p.set_defaults(func=cmd_encomendas)

    p = sub.add_parser("local", help="onde está cada cópia: Coleção, deck, "
                                     "binder Decks/Venda")
    p.add_argument("ref", nargs="?", help="OGN-100a, ogn-100a-298, UNL-T03")
    p.add_argument("qty", nargs="?", default="1", help="3 ou x3 (default 1)")
    p.add_argument("--para", help="destino: colecao | binder | deck:<slug>")
    p.add_argument("--de", help="origem (por omissão: colecao)")
    p.add_argument("--deck", help="o deck a que se referem --propor/--marcar")
    p.add_argument("--propor", action="store_true",
                   help="com --deck: lista o que este deck usaria da Coleção. "
                        "NÃO grava nada.")
    p.add_argument("--marcar", metavar="LINHAS",
                   help="grava SÓ estas linhas: 'pid:qty,pid:qty'")
    p.add_argument("--desfazer-deck", dest="desfazer_deck", metavar="SLUG",
                   help="passa tudo o que está neste deck para o binder Decks/Venda")
    p.add_argument("--undo", action="store_true",
                   help="desfaz o último movimento de local")
    p.set_defaults(func=cmd_local)

    p = sub.add_parser("find", help="procura impressões por nome ou código")
    p.add_argument("query")
    p.add_argument("-n", type=int, default=30)
    p.set_defaults(func=cmd_find)

    # A consola do Windows abre em cp1252 e rebenta com os acentos e com os
    # blocos do QR. Forçar UTF-8 na saída resolve os dois de uma vez.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    args = ap.parse_args(argv)
    config.ensure_dirs()
    return args.func(args)
