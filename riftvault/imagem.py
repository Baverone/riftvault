"""Ler uma decklist a partir de uma IMAGEM — a segunda porta da caixa de colar.

A primeira porta é o texto (`colar.py`, 2026-10-02). Esta lê a fotografia de
uma página de torneio e produz **o mesmo texto**; daí para a frente é o
caminho que já existe e já está testado. Não há segundo caminho de gravação.

**NÃO HÁ OCR NESTA MÁQUINA** — nem tesseract, nem easyocr, nem paddle (medido
a 2026-10-02) — e não se instala nada. Por isso a identificação não lê texto
nenhum: casa cada recorte com a ARTE do catálogo, que está toda em disco
(`data/images/`, 1180 webp). Isso identifica a IMPRESSÃO exacta — a arte
alternativa e a base são duas entradas diferentes —, o que é melhor do que ler
o nome. As quantidades são crachás `xN` grandes e brancos sobre escuro, sempre
no mesmo canto: lêem-se por template, com uma guarda topológica.

A REGRA DELE: *"só aceita o que tem a certeza"*. Tudo o que não passe a margem
fica de fora e é CONTADO; nunca se escolhe o mais parecido.
"""

from __future__ import annotations

import io
import json
import sqlite3
from pathlib import Path

from . import config, decks

# --- a geometria, em fracção da carta (medida a 2026-10-02) ----------------
# A janela da ARTE: sem a borda e sem o crachá, que é em baixo ao meio.
ART = (0.06, 0.07, 0.94, 0.52)
# O crachá da quantidade.
CRACHA = (0.385, 0.841, 0.615, 1.0)
N_HASH = 16

# Aceita-se a leitura de uma carta com pontuação até AQUI e margem para a
# segunda ACIMA de ALI. Medido na imagem de prova: a pior leitura boa deu
# p=88 com margem 105; a única dúvida deu p=45 com margem 1,9.
MAX_PONTO = 110.0
MIN_MARGEM = 25.0

# Fontes para o dígito do crachá. Nenhuma é obrigatória: usa-se a primeira que
# exista. A guarda dos BURACOS (um 8 tem dois, um 3 não tem nenhum) é que torna
# isto independente da fonte — é a confusão clássica 3/8 e é topológica.
FONTES = ("arialbd.ttf", "arial.ttf", "trebucbd.ttf", "segoeuib.ttf",
          "verdanab.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf")
BURACOS = {0: 1, 1: 0, 2: 0, 3: 0, 4: 1, 5: 0, 6: 1, 7: 0, 8: 2, 9: 1}

# A imagem de prova (a página de torneio inteira) são 19 MB.
MAX_BYTES = 40 * 1024 * 1024


class SemPillow(RuntimeError):
    """Não há Pillow/numpy — a leitura por imagem não pode correr."""


class ImagemIlegivel(ValueError):
    """Não se encontrou uma grelha de cartas na imagem."""


def _pil():
    try:
        from PIL import Image, ImageDraw, ImageFont  # noqa
        import numpy  # noqa
    except Exception as e:  # pragma: no cover - depende do ambiente
        raise SemPillow(
            "a leitura por imagem precisa do Pillow e do numpy, e não estão "
            "instalados. Cola a lista em texto, que funciona sempre.") from e
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    return Image, ImageDraw, ImageFont, np


# ---------------------------------------------------------------- assinatura

def _dhash(img, np, Image):
    g = np.asarray(img.convert("L").resize((N_HASH + 1, N_HASH), Image.LANCZOS))
    g = g.astype(np.int16)
    return (g[:, 1:] > g[:, :-1]).ravel()


def assinatura(im, np, Image):
    """Duas impressões digitais: a ARTE e a carta inteira com o crachá tapado.

    A arte sozinha não separa duas impressões com a mesma arte e molduras
    diferentes (a runa base do OGN e a promo do VEN). A carta inteira separa-as;
    o crachá tapa-se nas DUAS para a comparação ser justa.
    """
    im = im.convert("RGB")
    w, h = im.size
    arte = im.crop((int(w * ART[0]), int(h * ART[1]), int(w * ART[2]), int(h * ART[3])))
    inteira = im.copy()
    inteira.paste((128, 128, 128), (int(w * CRACHA[0]), int(h * CRACHA[1]),
                                    int(w * CRACHA[2]), int(h * CRACHA[3])))
    cor = np.asarray(arte.resize((4, 4), Image.LANCZOS)).astype(np.float32).ravel() / 255.0
    return np.concatenate([_dhash(arte, np, Image), _dhash(inteira, np, Image)]), cor


def _pasta_das_artes() -> Path:
    return Path(config.IMAGES_DIR)


def _ficheiro_do_cache() -> Path:
    # dentro do cache das imagens, que já está no `.gitignore` e é refazível
    return _pasta_das_artes() / ".assinaturas.npz"


def indice(con: sqlite3.Connection, *, usar_cache: bool = True):
    """As assinaturas das 1180 artes, com cache em disco.

    As `landscape` (os battlefields) entram DUAS vezes, rodadas 90 e 270: na
    página de torneio aparecem de lado, e uma landscape rodada cabe exactamente
    na mesma caixa de uma portrait.
    """
    Image, _, _, np = _pil()
    pasta = _pasta_das_artes()
    artes = sorted(pasta.glob("*.webp")) if pasta.is_dir() else []
    if not artes:
        raise ImagemIlegivel(
            f"não há artes em {pasta}. Corre `riftvault images` para as "
            "descarregar — sem elas não há com que comparar.")

    marca = f"{len(artes)}:{max(f.stat().st_mtime_ns for f in artes)}:{N_HASH}"
    cache = _ficheiro_do_cache()
    if usar_cache and cache.exists():
        try:
            z = np.load(cache, allow_pickle=False)
            if str(z["marca"]) == marca:
                return list(z["ids"]), z["D"], z["C"]
        except Exception:
            pass

    orient = dict(con.execute("SELECT printing_id, orientation FROM catalog.printings"))
    ids, D, C = [], [], []
    for f in artes:
        im = Image.open(f)
        voltas = (90, 270) if orient.get(f.stem) == "landscape" else (0,)
        for v in voltas:
            d, c = assinatura(im.rotate(v, expand=True) if v else im, np, Image)
            ids.append(f.stem)
            D.append(d)
            C.append(c)
    D, C = np.array(D), np.array(C)
    try:
        np.savez_compressed(cache, ids=np.array(ids), D=D, C=C, marca=np.array(marca))
    except Exception:
        pass
    return ids, D, C


# -------------------------------------------------------------------- grelha

def _grelha(im, np):
    """As caixas das cartas. Devolve (colunas, linhas, largura, altura).

    As cartas estão numa grelha regular sobre um fundo liso; cada uma tem a
    borda escura. Procura-se a borda, não o conteúdo — o conteúdo varia.
    """
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    H, W, _ = a.shape
    # A borda de uma carta é quase preta (soma ~65). O fundo mais escuro da
    # página de prova (laranja carregado) soma ~300, por isso 180 separa os dois
    # com folga dos dois lados. Com 260 o intervalo entre colunas contava como
    # carta e a grelha inteira virava uma coluna só.
    escuro = a.sum(axis=2) < 180

    def runs(v, lim, minimo):
        out, s = [], None
        for i, x in enumerate(v):
            if x > lim and s is None:
                s = i
            elif x <= lim and s is not None:
                if i - s >= minimo:
                    out.append((s, i))
                s = None
        if s is not None and len(v) - s >= minimo:
            out.append((s, len(v)))
        return out

    cols = runs(escuro.sum(axis=0), H * 0.03, int(W * 0.04))
    if len(cols) < 2:
        raise ImagemIlegivel("não se vê uma grelha de cartas nesta imagem.")
    larg = int(np.median([e - s for s, e in cols]))
    cols = [s for s, e in cols if abs((e - s) - larg) <= max(4, larg * 0.08)]
    if len(cols) < 2:
        raise ImagemIlegivel("as colunas de cartas não são regulares.")

    # A altura vem do rácio de uma carta, que é fixo.
    alt = int(round(larg * 712 / 491))

    # O FUNDO, medido linha a linha nos INTERVALOS entre colunas, que são fundo
    # por construção. A página tem um gradiente, por isso um limiar fixo de cor
    # não serve; este é o único sítio onde se pode perguntar «que cor é o fundo
    # a esta altura» sem adivinhar.
    gaps = [x for i in range(len(cols) - 1)
            for x in range(cols[i] + larg + 4, min(cols[i + 1] - 4, W))]
    if len(gaps) < 20:
        raise ImagemIlegivel("as colunas de cartas estão encostadas umas às outras.")
    fundo_cor = np.median(a[:, gaps, :], axis=1)                     # (H, 3)
    dif = np.abs(a - fundo_cor[:, None, :]).sum(axis=2) > 60         # não é fundo

    tiras = np.stack([dif[:, cx + larg // 4:cx + 3 * larg // 4].mean(axis=1)
                      for cx in cols], axis=1)                       # (H, ncols)
    dentro = tiras > 0.5
    n = dentro.sum(axis=1)
    cru, s = [], None
    for y in range(H):
        if n[y] >= 1 and s is None:
            s = y
        elif n[y] < 1 and s is not None:
            cru.append([s, y])
            s = None
    if s is not None:
        cru.append([s, H])
    # Uma carta é um bloco contínuo: um intervalo curto lá dentro é a caixa de
    # texto clara a passar perto da cor do fundo, não o fim da linha. Sem isto
    # a última linha da imagem de prova partia-se em três (os cortes eram de 3 e
    # 7 px). O limite fica bem abaixo do intervalo ENTRE linhas, que nesta
    # página é de 94 px — com 0,2 da altura juntavam-se duas linhas numa.
    juntos = []
    for r in cru:
        if juntos and r[0] - juntos[-1][1] < alt * 0.06:
            juntos[-1][1] = r[1]
        else:
            juntos.append(r)
    linhas = [(s, e) for s, e in juntos if e - s > alt * 0.75]
    if not linhas:
        raise ImagemIlegivel("não se vê nenhuma linha de cartas.")
    # a faixa do cabeçalho tem outra altura; as cartas são todas iguais
    modal = int(np.median([e - s for s, e in linhas]))
    linhas = [(s, e) for s, e in linhas if abs((e - s) - modal) <= max(6, modal * 0.08)]
    if not linhas:
        raise ImagemIlegivel("as linhas de cartas não são regulares.")

    tops, ocup = [], []
    for s, e in linhas:
        top = min(max(0, s), H - alt)
        tops.append(top)
        ocup.append([ci for ci in range(len(cols))
                     if dif[top:top + alt, cols[ci]:cols[ci] + larg].mean() > 0.5])
    return cols, tops, ocup, larg, alt


def _divisor(tops, np):
    """Onde a grelha se parte — a linha «Sideboard».

    Não se lê a palavra (não há OCR): lê-se o SALTO. Um intervalo entre linhas
    maior do que o normal é um cabeçalho pelo meio. Com mais do que um salto
    não se adivinha: fica tudo no deck e diz-se.
    """
    if len(tops) < 2:
        return None, 0
    passos = [tops[i + 1] - tops[i] for i in range(len(tops) - 1)]
    normal = float(np.median(passos))
    saltos = [i for i, p in enumerate(passos) if p > normal * 1.12]
    if len(saltos) != 1:
        return None, len(saltos)
    return saltos[0] + 1, 1


# ----------------------------------------------------------- o crachá «xN»

def _modelos(ImageFont, ImageDraw, Image, np):
    for nome in FONTES:
        p = Path(r"C:\Windows\Fonts") / nome
        if not p.exists():
            p = Path("/usr/share/fonts/truetype/dejavu") / nome
        if not p.exists():
            continue
        try:
            f = ImageFont.truetype(str(p), 90)
        except Exception:
            continue
        ms = {}
        for d in range(10):
            img = Image.new("L", (170, 190), 0)
            ImageDraw.Draw(img).text((30, 20), str(d), 255, font=f)
            g = _recorta(np.asarray(img) > 128, np, Image)
            if g is not None:
                ms[d] = g
        if len(ms) == 10:
            return nome, ms
    return None, None


def _recorta(mask, np, Image, gw=20, gh=28):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    r = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    img = Image.fromarray((r * 255).astype(np.uint8)).resize((gw, gh), Image.LANCZOS)
    return np.asarray(img).astype(np.float32) / 255.0


def _buracos(mask, np):
    """Quantos buracos tem o glifo — 8 tem dois, 0/4/6/9 um, os outros nenhum.

    É o que torna a leitura independente da fonte: a confusão clássica 3/8
    deixa de ser possível, porque é topológica e não de forma.
    """
    h, w = mask.shape
    fundo = ~mask
    visto = np.zeros_like(fundo)
    pilha = [(y, x) for y in range(h) for x in (0, w - 1) if fundo[y, x]]
    pilha += [(y, x) for x in range(w) for y in (0, h - 1) if fundo[y, x]]
    while pilha:
        y, x = pilha.pop()
        if visto[y, x] or not fundo[y, x]:
            continue
        visto[y, x] = True
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and fundo[ny, nx] and not visto[ny, nx]:
                pilha.append((ny, nx))
    dentro = fundo & ~visto
    # conta as componentes do que ficou
    marca = np.zeros_like(dentro, dtype=np.int32)
    n = 0
    for y in range(h):
        for x in range(w):
            if dentro[y, x] and marca[y, x] == 0:
                n += 1
                p = [(y, x)]
                tam = 0
                while p:
                    cy, cx = p.pop()
                    if marca[cy, cx] or not dentro[cy, cx]:
                        continue
                    marca[cy, cx] = n
                    tam += 1
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and dentro[ny, nx] and not marca[ny, nx]:
                            p.append((ny, nx))
                if tam < max(4, dentro.size // 400):   # ruído de antialiasing
                    n -= 1
    return n


def quantidade(carta, modelos, np, Image):
    """O número do crachá, ou None se não houver certeza."""
    if not modelos:
        return None
    w, h = carta.size
    b = carta.crop((int(w * CRACHA[0]), int(h * CRACHA[1]),
                    int(w * CRACHA[2]), int(h * CRACHA[3])))
    rgb = np.asarray(b.convert("RGB")).astype(np.int16)

    # Primeiro a CAIXA do crachá, que é um rectângulo escuro cheio. Sem isto o
    # branco apanhava também a caixa de texto creme da própria carta (e o fundo
    # laranja da página), e os glifos vinham todos colados num só.
    escuro = rgb.max(axis=2) < 90
    cx_ = [i for i, v in enumerate(escuro.sum(axis=0)) if v > escuro.shape[0] * 0.5]
    cy_ = [i for i, v in enumerate(escuro.sum(axis=1)) if v > escuro.shape[1] * 0.5]
    if len(cx_) < 20 or len(cy_) < 20:
        return None
    b = b.crop((cx_[0], cy_[0], cx_[-1] + 1, cy_[-1] + 1))
    rgb = np.asarray(b.convert("RGB")).astype(np.int16)

    # O texto do crachá é BRANCO puro; dentro da caixa escura mais nada o é.
    m = (rgb[:, :, 0] > 190) & (rgb[:, :, 1] > 190) & (rgb[:, :, 2] > 190)
    col = m.sum(axis=0)
    runs, s = [], None
    for i, v in enumerate(col):
        if v > 0 and s is None:
            s = i
        elif v == 0 and s is not None:
            runs.append((s, i))
            s = None
    if s is not None:
        runs.append((s, len(col)))
    # o que toca a borda do recorte é o FUNDO à volta do crachá, não um glifo
    runs = [(a, c) for a, c in runs if a > 0 and c < len(col) and c - a >= 4]
    if len(runs) < 2:
        return None
    valor = 0
    for a, c in runs[1:]:                     # o primeiro glifo é o «x»
        sub = m[:, a:c]
        g = _recorta(sub, np, Image)
        if g is None:
            return None
        nb = _buracos(_recorta_bool(sub, np), np)
        cands = [d for d in range(10) if BURACOS[d] == nb]
        if not cands:
            return None
        pont = sorted((float(np.abs(modelos[d] - g).sum()), d) for d in cands)
        if len(pont) > 1 and pont[1][0] - pont[0][0] < 12.0:
            return None                        # dois dígitos empatados: não se adivinha
        valor = valor * 10 + pont[0][1]
    return valor or None


def _recorta_bool(mask, np):
    ys, xs = np.nonzero(mask)
    return mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


# ----------------------------------------------------------------- a leitura

def _papel(tipo: str | None) -> str:
    if tipo == "Legend":
        return "legend"
    if tipo == "Rune":
        return "runes"
    if tipo == "Battlefield":
        return "battlefields"
    return "main"


def ler(con: sqlite3.Connection, dados: bytes) -> dict:
    """Lê a imagem e devolve o TEXTO da decklist, mais o que não conseguiu ler.

    Não escreve nada e não grava deck nenhum: é o `colar.prever`/`colar.gravar`
    que faz isso, com o texto que sai daqui — a MESMA porta do copy-paste.
    """
    Image, ImageDraw, ImageFont, np = _pil()
    if not dados:
        raise ImagemIlegivel("não veio imagem nenhuma.")
    if len(dados) > MAX_BYTES:
        raise ImagemIlegivel(
            f"a imagem tem {len(dados)//1024} KB e o limite é "
            f"{MAX_BYTES//1024//1024} MB.")
    try:
        im = Image.open(io.BytesIO(dados))
        im.load()
        im = im.convert("RGB")
    except Exception as e:
        raise ImagemIlegivel(f"não se conseguiu abrir a imagem: {e}") from e

    cols, tops, ocup, larg, alt = _grelha(im, np)
    corte, n_saltos = _divisor(tops, np)
    ids, D, C = indice(con)
    _fonte, modelos = _modelos(ImageFont, ImageDraw, Image, np)

    info = {}
    for r in con.execute(
            "SELECT printing_id, public_code, name, type, card_key "
            "FROM catalog.printings"):
        info[r[0]] = {"public_code": r[1], "name": r[2], "type": r[3], "card_key": r[4]}

    cartas, duvidas = [], []
    for li, top in enumerate(tops):
        for ci in ocup[li]:
            cx = cols[ci]
            carta = im.crop((cx, top, cx + larg, top + alt))
            d, c = assinatura(carta, np, Image)
            pont = (D != d).sum(axis=1) + np.abs(C - c).sum(axis=1) * 2.0
            ordem = np.argsort(pont)
            melhor = int(ordem[0])
            # A margem mede-se contra a melhor CARTA diferente, não contra a
            # melhor impressão diferente. A lista que sai daqui é por NOME, e
            # duas impressões da mesma carta (a runa base do OGN e a promo do
            # VEN, com a mesma arte) dão a mesma linha — não há nada a
            # desempatar. Contra outra carta a dúvida é a sério.
            ck = info.get(ids[melhor], {}).get("card_key")
            seg = next((int(i) for i in ordem[1:]
                        if info.get(ids[i], {}).get("card_key") != ck), None)
            margem = float(pont[seg] - pont[melhor]) if seg is not None else 999.0
            qtd = quantidade(carta, modelos, np, Image)
            onde = {"linha": li + 1, "coluna": ci + 1}
            if pont[melhor] > MAX_PONTO or margem < MIN_MARGEM:
                duvidas.append({**onde, "porque": "não reconheci a carta com certeza",
                                "parecida": info.get(ids[melhor], {}).get("public_code"),
                                "qty": qtd})
                continue
            if qtd is None:
                duvidas.append({**onde, "porque": "não li a quantidade",
                                "parecida": info.get(ids[melhor], {}).get("public_code"),
                                "qty": None})
                continue
            meta = info.get(ids[melhor], {})
            cartas.append({
                **onde, "printing_id": ids[melhor], "qty": qtd,
                "code": meta.get("public_code"), "name": meta.get("name"),
                "type": meta.get("type"), "card_key": meta.get("card_key"),
                "papel": _papel(meta.get("type")),
                "sideboard": corte is not None and li >= corte,
                "ponto": round(float(pont[melhor]), 1), "margem": round(margem, 1),
            })

    if not cartas:
        raise ImagemIlegivel(
            "não se reconheceu nenhuma carta. Esta leitura foi feita para as "
            "páginas de classificações com a grelha de cartas; se a imagem for "
            "outra coisa, cola a lista em texto.")

    # o CHAMPION: a página põe-no logo a seguir aos battlefields. O catálogo não
    # sabe qual é (não há marca de champion nas `tags`), por isso isto é um
    # PALPITE de disposição — vai dito, e a caixa do texto é editável.
    champion = None
    mains = [c for c in cartas if c["papel"] == "main" and not c["sideboard"]]
    if mains and any(c["papel"] == "battlefields" for c in cartas):
        primeiro = min(mains, key=lambda c: (c["linha"], c["coluna"]))
        bf = max((c["linha"], c["coluna"]) for c in cartas if c["papel"] == "battlefields")
        if (primeiro["linha"], primeiro["coluna"]) > bf and primeiro["qty"] == 1:
            champion = primeiro
            champion["papel"] = "champion"

    return {
        "texto": texto_da_leitura(cartas),
        "cartas": cartas,
        "duvidas": duvidas,
        "champion_por_posicao": bool(champion),
        "sideboard": corte is not None,
        "saltos": n_saltos,
        "grelha": {"colunas": len(cols), "linhas": len(tops),
                   "cartas": sum(len(o) for o in ocup)},
        "fonte_dos_digitos": _fonte,
    }


ORDEM = ["legend", "champion", "main", "battlefields", "runes", "sideboard"]
TITULO = {"legend": "Legend", "champion": "Champion", "main": "MainDeck",
          "battlefields": "Battlefields", "runes": "Rune Pool",
          "sideboard": "Sideboard"}


def texto_da_leitura(cartas: list[dict]) -> str:
    """O texto no formato de sempre — o que o `decks.parse_texto` já lê."""
    blocos: dict[str, list[str]] = {}
    for c in cartas:
        papel = "sideboard" if c["sideboard"] else c["papel"]
        blocos.setdefault(papel, []).append(f"{c['qty']} {c['name']}")
    saida = []
    for papel in ORDEM:
        if blocos.get(papel):
            saida.append(f"{TITULO[papel]}:")
            saida.extend(blocos[papel])
            saida.append("")
    return "\n".join(saida).strip() + "\n"
