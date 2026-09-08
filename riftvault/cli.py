"""Linha de comandos do riftvault.

    riftvault sync [--set OGN] [--images]
    riftvault serve [--port 8770]
    riftvault build [--out site]
    riftvault add OGN-100a x1
    riftvault remove OGN-100a x1
    riftvault set OGN-100a 3
    riftvault undo
    riftvault log [-n 20]
    riftvault stats
    riftvault find "sett"
    riftvault a-subir [--cardmarket] [--todas] [--csv f.csv]
    riftvault venda [--cardmarket] [--csv f.csv]
    riftvault wantlist [--edicao OGN] --cardmarket
"""

from __future__ import annotations

import argparse
import re
import sys

from . import a_subir as a_subir_mod
from . import build as build_mod
from . import cardmarket, catalog, collection, config, db, decks as decks_mod
from . import faltas as faltas_mod
from . import metrics, pending as pending_mod, prices, server
from . import venda as venda_mod


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
    res = build_mod.build(args.out)
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
    con.close()
    return 0


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
    print(f"{res['historico_gravado']} entradas novas no histórico.")
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
        print(f"  {v['copias_sem_preco']} cópias sem preço (sem oferta no CardTrader)")
    if v["cents_de_foil"]:
        pct = 100 * v["cents_de_foil"] / v["cents"] if v["cents"] else 0
        print(f"  ATENÇÃO: {prices.eur(v['cents_de_foil'])} ({pct:.0f}% do total, "
              f"{v['copias_de_foil']} cópias) vem de cartas que o CardTrader só "
              f"lista em foil.\n  Como o riftvault não distingue acabamentos, se "
              f"as tuas forem normais o valor real é mais baixo.")

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
            print(f"  {prices.eur(r['total']):>10}  {r['qty']}x {prices.eur(r['price_cents']):>8}  "
                  f"{r['name']} [{r['variant_label']}]{foil}")
    con.close()
    return 0


def cmd_decks(args) -> int:
    con = db.connect()
    decks_mod.import_all(con)
    if args.order:
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

    print(f"{'#':<3} {'deck':<48} {'tenho':>12} {'falta':>7} {'noutro':>7}")
    for d in decks_mod.decks_index(con):
        print(f"{d['priority']:<3} {d['name'][:48]:<48} "
              f"{d['have']:>5}/{d['wanted']:<6} {d['missing']:>7} {d['shared']:>7}")
    con.close()
    return 0


def cmd_deck(args) -> int:
    con = db.connect()
    decks_mod.import_all(con, log=lambda *_: None)
    row = next((r for r in decks_mod.deck_rows(con) if r["name"] == args.slug), None)
    if not row:
        print(f"erro: não há deck chamado {args.slug!r}", file=sys.stderr)
        return 1
    p = decks_mod.deck_payload(con, row["deck_id"])
    L = p["legality"]
    print(f"{p['name']}   (prioridade {p['priority']})")
    ok = lambda b: "ok" if b else "X"
    print(f"  main {L['main']['n']}/{L['main']['alvo']} {ok(L['main']['ok'])} · "
          f"runas {L['runes']['n']}/{L['runes']['alvo']} {ok(L['runes']['ok'])} · "
          f"battlefields {L['battlefields']['n']}/{L['battlefields']['alvo']} "
          f"{ok(L['battlefields']['ok'])} · domínios "
          f"{' + '.join(L['dominios']['legend'])} {ok(L['dominios']['ok'])}")
    if p["unresolved"]:
        print("  por casar no catálogo: "
              + ", ".join(u["name"] for u in p["unresolved"]))

    if p["missing_by_set"]:
        print("\nFalta comprar, por edição:")
        pl = lambda n, s, p_: f"{s if n == 1 else p_}"
        for m in p["missing_by_set"]:
            extra = f"  ({m['multi']} também noutra edição)" if m["multi"] else ""
            print(f"  {m['name']:<24} {m['copies']:>3} {pl(m['copies'], 'cópia ', 'cópias')}"
                  f" de {m['cards']:>2} {pl(m['cards'], 'carta ', 'cartas')}"
                  f"  {prices.eur(m['cents']):>9}{extra}")

    for s in p["sections"]:
        print(f"\n{s['label']}  ({s['have']}/{s['wanted']})")
        for c in s["cards"]:
            if c["shared"]:
                onde = ", ".join(f"{h['qty']}x em «{h['deck']}»" for h in c["shared"]["em"])
                marca, extra = "~", f"  -> {onde}"
            elif c["missing"]:
                # "não tenho" só quando é mesmo zero; com 1 de 2 é "falta 1".
                marca = "x"
                extra = ("  (não tenho)" if c["have"] == 0
                         else f"  (falta{'m' if c['missing'] > 1 else ''} {c['missing']})")
            else:
                marca = "."
                extra = ("  " + " · ".join(f"{x['qty']}x {x['code']}" for x in c["printings"])
                         if args.onde else "")
            print(f"  {marca} {c['wanted']:>2} {c['name'][:38]:<38} {c['have']}/{c['wanted']}{extra}")
    con.close()
    return 0


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

    p = a_subir_mod.wantlist(con, alvo, com_codigo=args.codigos)
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
    print(f"#\n# total: {p['lines']} linhas · {p['copies']} cópias · "
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
        motivos = ", ".join(f"{c['n']} {c['criterio']}"
                            for c in fora.get("excluded_by") or ())
        print(f"fora: {fora['excluded']} impressões ({motivos}) "
              f"— continuam a contar na percentagem de master set. "
              f"A exclusão é da sequência: as runas especiais e as artes "
              f"alternativas entram na mesma, 1 de cada.")
    print()
    for x in itens:
        pct = "" if x.get("pct") is None else f"{x['pct']:+7.1f}%"
        print(f"  {x['missing']:>2}x {cardmarket.codigo(x['code']):<12} "
              f"{(x.get('name') or '')[:32]:<32} "
              f"{prices.eur(x.get('price')):>10} {pct:>8}  "
              f"= {prices.eur(x.get('total')):>11}")
    con.close()
    return 0


def cmd_venda(args) -> int:
    """O que ele tem a mais da sequência: o que está num deck e o que sobra.

    Não mexe em nada — é uma sugestão. A lista sai pelo mesmo gerador das de
    compra (`cardmarket.linha`), com a quantidade a ser o excedente.
    """
    con = db.connect()
    if db.catalog_is_empty(con):
        print("catálogo vazio — corre `riftvault sync`.", file=sys.stderr)
        return 1

    v = venda_mod.listar(con)
    itens = v["items"]

    if args.csv:
        open(args.csv, "w", encoding="utf-8-sig", newline="").write(
            cardmarket.csv_texto(itens))
        print(f"{len(itens)} linhas escritas em {args.csv}  (candidatas a venda)")
        con.close()
        return 0

    if args.cardmarket:
        res = cardmarket.gerar(itens, com_codigo=args.codigos)
        saida = res["text"] + ("\n" if res["text"] else "")
        if args.out:
            open(args.out, "w", encoding="utf-8").write(saida)
            print(f"{res['lines']} linhas escritas em {args.out}")
        else:
            sys.stdout.write(saida)
        # Como nas listas de compra: o total fora do texto, para o stdout ficar
        # colável tal e qual.
        print(f"\n# {res['lines']} linhas · {res['copies']} cópias · "
              f"{prices.eur(res['cents'])}  (candidatas a venda)", file=sys.stderr)
        con.close()
        return 0

    print(f"A mais da sequência do master set e na caixa: {v['printings']} impressões · "
          f"{v['copies']} cópias · {prices.eur(v['cents'])}"
          + (f" ({v['no_price']} sem oferta no CardTrader)" if v["no_price"] else ""))
    if v["in_decks"]:
        print(f"Em uso nos decks (não entram na lista): {v['in_decks']} impressões, "
              f"{v['in_decks_copies']} cópias.")
    print("Nada disto mexe na coleção — é sugestão.\n")
    for x in itens:
        onde = ", ".join(f"{d['qty']}x {d['deck'].split(' · ')[0]}"
                         for d in x["in_decks"]) or "candidata a venda"
        print(f"  {x['qty']:>2}x {cardmarket.codigo(x['code']):<12} "
              f"{x['name'][:30]:<30} {prices.eur(x['price']):>10} "
              f"= {prices.eur(x['total']):>10}  {onde}")
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
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("decks", help="lista os decks e a alocação por prioridade")
    p.add_argument("--order", help="nova ordem por slug, ex: azir,ornn "
                                   "(o primeiro passa a principal)")
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

    p = sub.add_parser("venda", help="o que tens a mais da sequência e sobra dos decks")
    p.add_argument("--cardmarket", action="store_true",
                   help="escreve as linhas no formato do Cardmarket")
    p.add_argument("--codigos", action="store_true",
                   help="com --cardmarket: 'N Nome [UNL-228a]'")
    p.add_argument("--csv", help="escreve um CSV com as mesmas colunas das listas de compra")
    p.add_argument("--out", help="com --cardmarket: escrever para ficheiro")
    p.set_defaults(func=cmd_venda)

    p = sub.add_parser("pending", help="encomendas a caminho")
    p.add_argument("--chegou", nargs="?", type=int, const=0, default=None,
                   metavar="ID",
                   help="dá entrada na coleção: sem ID, tudo o que está aberto")
    p.set_defaults(func=cmd_pending)

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
