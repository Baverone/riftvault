"""Listas para a wantlist do Cardmarket — o gerador, num sítio só.

Pedido do André (2026-09-08): *"no final dá-me uma lista para o Cardmarket para
eu conseguir comprar as coisas"*. A mesma lista é precisa em dois sítios — na
aba «A subir» (só o que está a valorizar) e na aba «Master set» (tudo o que
falta) — por isso o gerador é **um** e recebe as impressões já escolhidas por
quem chama. As duas abas do frontend usam o gémeo em JavaScript (`cmLinha`), que
escreve exactamente a mesma linha; há teste que compara os dois formatos.

O FORMATO
    `N Nome (V.n) (Edição)` — a quantidade, o nome, a versão quando há mais do
    que uma, e a edição. É o que a ajuda do Cardmarket documenta
    (`4x High Tide (V.1) (Fallen Empires)`), e é o mesmo que o `faltas.wantlist`
    já usava para as listas dos decks; nesta corrida não houve rede para
    reconfirmar no site deles (ver o relatório), por isso não se inventou
    variação nenhuma.

    O NOME É O DO MERCADO ("Darius - Trifarian"), não o da RiftScribe
    ("Darius, Trifarian"): 414 das 1179 impressões diferem e sem isso não casa
    lá nada.

    A segunda forma, `N Nome [UNL-228]`, leva o número de coleção em vez da
    versão e da edição. Não é sintaxe do Cardmarket — é para ele desambiguar à
    mão qual das versões é que quer, quando o nome sozinho não chega.

O FOIL NÃO SE ESCREVE NA LINHA. Está confirmado: no Cardmarket o foil é um
filtro POR ENTRADA, ligado na interface depois de a carta entrar na lista. Por
isso devolve-se `foil` à parte — as linhas onde o mercado só tem oferta foil —
para ele saber onde o ligar. Não inventar sintaxe.
"""

from __future__ import annotations

import csv
import io
import sqlite3

# As colunas do CSV, pela ordem que o André pediu. O separador é a vírgula e o
# ficheiro leva BOM, como o `riftvault shopping --csv` que já existia.
CABECALHO_CSV = ["quantidade", "nome", "codigo", "edicao", "raridade",
                 "preco_hoje_eur", "delta_pct", "custo_eur"]


def codigo(public_code: str | None) -> str:
    """`UNL-228/219` -> `UNL-228`. É o que a carta tem impresso à frente."""
    return (public_code or "").split("/")[0]


def versoes(con: sqlite3.Connection) -> dict[str, dict]:
    """printing_id -> {v, n, foil_only}: o número de versão no Cardmarket.

    O Cardmarket distingue impressões com o mesmo nome na mesma edição por
    `(V.1)`, `(V.2)`... e a ordem é a do número de coleção. Aqui calcula-se
    esse índice a partir do nosso catálogo.

    NÃO VALIDADO contra o Cardmarket — a numeração deles é inferida, não lida.
    Se sair trocada, o sítio para corrigir é esta função.

    Agrupa-se pelo NÚMERO DE COLEÇÃO (o `group_key`), não pela carta lógica nem
    pelo nome de mercado.

    Foi o André que corrigiu isto (2026-09-01): "as signatures são normalmente
    as V.2". Agrupando por carta, a `Daughter of the Void` do OGN dava três
    versões — a base 247, a reimpressão showcase 299 e a signature 299* — e a
    signature saía V.3. Se lá é V.2, então o Cardmarket trata a 247 e a 299 como
    PRODUTOS DIFERENTES, e junta só as impressões que partilham número de
    coleção. Com este agrupamento as 36 signatures ficam todas em V.2, como ele
    descreve.

    Também resolve o problema do nome: o CardTrader escreve a arte alternativa
    de 3 cartas com vírgula e a base com hífen, e agrupar por nome partia-as em
    dois grupos de um.
    """
    rows = con.execute(
        "SELECT m.printing_id, m.market_name, m.market_set, p.group_key, "
        "       p.collector_number, p.variant, p.variant_label, p.public_code, "
        "       pl.from_foil "
        "FROM catalog.cardtrader_map m "
        "JOIN catalog.printings p ON p.printing_id = m.printing_id "
        "LEFT JOIN catalog.price_latest pl ON pl.printing_id = m.printing_id "
        "WHERE m.market_name IS NOT NULL"
    ).fetchall()

    grupos: dict[tuple, list] = {}
    for r in rows:
        grupos.setdefault(r["group_key"], []).append(r)

    out: dict[str, dict] = {}
    for _, lst in grupos.items():
        lst.sort(key=lambda r: (r["collector_number"], r["variant"]))
        # No Cardmarket as versões vivem sob UM nome de produto; usa-se o da
        # impressão base para todas.
        canonico = lst[0]["market_name"]
        for i, r in enumerate(lst, 1):
            out[r["printing_id"]] = {
                "v": i, "n": len(lst), "name": canonico,
                "set": r["market_set"],
                "label": r["variant_label"], "code": r["public_code"],
                # O mercado só tem oferta foil desta impressão. O texto da
                # wantlist não leva flag de foil — isto serve para lhe dizer
                # em que linhas tem de ligar o filtro à mão.
                "foil_only": bool(r["from_foil"]),
            }
    return out


# ---------------------------------------------------------------------------
# O gerador
# ---------------------------------------------------------------------------


def linha(it: dict, com_codigo: bool = False) -> str:
    """Uma linha da wantlist, a partir de um item já preparado.

    Os itens vêm da aba «A subir» ou da lista do master set; as duas trazem os
    mesmos campos de mercado (`market_name`, `market_set`, `v`, `n_versions`)
    de propósito, para não haver dois formatos.
    """
    nome = it.get("market_name") or it.get("name") or ""
    if com_codigo:
        c = codigo(it.get("code"))
        return f"{it['missing']} {nome}" + (f" [{c}]" if c else "")

    partes = [f"{it['missing']} {nome}"]
    # Só faz sentido numerar quando há mais do que uma versão.
    if it.get("v") and (it.get("n_versions") or 1) > 1:
        partes.append(f"(V.{it['v']})")
    if it.get("market_set"):
        partes.append(f"({it['market_set']})")
    return " ".join(partes)


def gerar(itens: list[dict], com_codigo: bool = False) -> dict:
    """Texto para colar, mais o que é preciso dizer por fora dele.

    `foil` são as linhas cujas impressões só têm oferta foil no mercado — o
    filtro tem de ser ligado à mão, entrada a entrada. `cents` é o total, que
    NÃO vai no texto: uma linha de total colada na wantlist seria importada
    como se fosse uma carta.
    """
    linhas = [linha(it, com_codigo) for it in itens]
    return {
        "text": "\n".join(linhas),
        "lines": len(linhas),
        "copies": sum(int(it["missing"]) for it in itens),
        "cents": sum(int(it.get("total") or 0) for it in itens),
        "foil": [l for l, it in zip(linhas, itens) if it.get("foil_only")],
    }


def csv_texto(itens: list[dict]) -> str:
    """As mesmas cartas em CSV, com cabeçalho. Colunas pedidas pelo André."""
    buf = io.StringIO(newline="")
    w = csv.writer(buf)
    w.writerow(CABECALHO_CSV)
    for it in itens:
        preco, total, pct = it.get("price"), it.get("total"), it.get("pct")
        w.writerow([
            it["missing"],
            it.get("market_name") or it.get("name") or "",
            codigo(it.get("code")),
            it.get("market_set") or it.get("set_name") or it.get("set") or "",
            it.get("rarity") or "",
            "" if preco is None else f"{preco / 100:.2f}",
            "" if pct is None else f"{pct:.1f}",
            "" if total is None else f"{total / 100:.2f}",
        ])
    return buf.getvalue()
