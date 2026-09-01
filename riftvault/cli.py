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
"""

from __future__ import annotations

import argparse
import re
import sys

from . import build as build_mod
from . import catalog, collection, config, db, decks as decks_mod
from . import faltas as faltas_mod
from . import metrics, prices, server


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


def cmd_wantlist(args) -> int:
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

    texto = faltas_mod.wantlist(alvo["by_set"], com_edicao=not args.sem_edicao)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(texto + "\n")
        print(f"{len(texto.splitlines())} linhas escritas em {args.out}  ({rotulo})")
    else:
        print(texto)
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
    p.add_argument("--deck", help="só deste deck (slug)")
    p.add_argument("--todos", action="store_true",
                   help="cenário de ter os decks todos montados ao mesmo tempo")
    p.add_argument("--sem-edicao", action="store_true", dest="sem_edicao",
                   help="não escrever a edição entre parênteses")
    p.add_argument("--out", help="escrever para ficheiro em vez do ecrã")
    p.set_defaults(func=cmd_wantlist)

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
