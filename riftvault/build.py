"""Modo publicado: gera o site estático (só leitura) para o GitHub Pages.

É o MESMO frontend do modo edição — os ficheiros são copiados tal e qual. O que
muda é só o conteúdo dos payloads: `editable: false`, e os endpoints da API
passam a ser ficheiros .json reais nos mesmos caminhos.

O SITE É GERADO NO PC E VAI PARA O GIT (2026-09-10)
    Até hoje quem corria isto era o GitHub Actions, e para isso descarregava o
    catálogo inteiro da RiftScribe a cada build. A 10/09, das 11:55 às 17:45,
    todas as builds morreram nesse passo — o `riftscribe.gg/api` deixou de
    responder (timeout, do Actions e do PC) — e o site ficou parado na versão da
    manhã, com o André fora de casa a olhar para ele.

    O catálogo completo já está no PC (`data/catalog.db`) e é aqui que vive a
    única coisa insubstituível, a colecção. Por isso a geração passou para cá: o
    `site/` é commitado e o workflow só o publica. Uma RiftScribe em baixo deixa
    de poder parar o site — no pior caso publica-se o catálogo de ontem.

    O `--se-mudou` (`so_se_mudou=True`) é o que impede a `riftvault-publicar` de
    gastar uma build do Pages de 30 em 30 minutos: gera para uma pasta de prova
    e compara com o que já está publicado, ignorando o `generated_at`. Se o
    conteúdo é o mesmo, não se mexe em nada. Comparar o RESULTADO em vez de
    adivinhar pelas datas dos ficheiros é de propósito — o `vault.db` é
    reescrito por qualquer clique, mesmo um que não mude número nenhum.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import (a_mais, a_subir, abrir, config, db, decks, faltas, faltas_foil,
               lista, metrics, multi, pending, principal, privacidade,
               runas_vista, selado, utilizador, venda)

# A pasta das imagens fica de fora da comparação: em `static_images: "local"`
# são ~88 MB e não dependem da colecção — o que muda nelas é o `riftvault
# images`, não o build.
IMG_DIR = "img"

#: A casca vive no `config` (dois escritores, uma definição) — ver lá.
#:
#: UMA VEZ SÓ, NA RAIZ (2026-10-04): cada `u/<slug>/index.html` aponta-lhe com
#: `../../`. Os caminhos TÊM de ser relativos — o site responde ao mesmo tempo
#: em `rift.baverone.com/` e em `baverone.github.io/riftvault/` (é por este que
#: o teste da `riftvault-publicar` pergunta), e um `/app.js` absoluto dava 404
#: no segundo.
CASCA = config.CASCA

#: Como o `index.html` se refere a cada ficheiro da casca. Tem de casar com o
#: `riftvault/web/index.html` — se deixar de casar, o `_aponta_a_casca`
#: rebenta em vez de publicar uma página sem CSS.
REFERENCIA_DA_CASCA = {"app.js": 'src="app.js"', "style.css": 'href="style.css"'}


def _aponta_a_casca(html: str, subida: str) -> str:
    """Faz o `index.html` apontar à casca que vive `subida` acima dele.

    REBENTA se a referência não estiver lá exactamente uma vez. É de propósito:
    uma página sem `style.css` não dá erro nenhum — abre em texto cru —, e
    descobria-se pela fotografia e não pelo teste. A alternativa (substituir o
    que houver e seguir) era publicar o site partido em silêncio.
    """
    for nome in CASCA:
        velha = REFERENCIA_DA_CASCA[nome]
        quantas = html.count(velha)
        if quantas != 1:
            raise ValueError(
                f"o index.html refere {velha} {quantas} vezes (esperava 1) — "
                f"a casca mudou de forma e o `build.REFERENCIA_DA_CASCA` tem "
                f"de a acompanhar, senão a página sai sem {nome}")
        html = html.replace(velha, velha.replace(f'"{nome}"',
                                                 f'"{subida}{nome}"'))
    return html


def _sem_relogio(obj):
    """O payload sem os `generated_at` — o que sobra é o CONTEÚDO.

    Sem isto duas builds seguidas nunca são iguais (o relógio anda), e o site
    era commitado e publicado de meia em meia hora sem uma carta mudar.
    """
    if isinstance(obj, dict):
        return {k: _sem_relogio(v) for k, v in obj.items() if k != "generated_at"}
    if isinstance(obj, list):
        return [_sem_relogio(v) for v in obj]
    return obj


def _ficheiros(raiz: Path) -> dict[str, Path]:
    return {p.relative_to(raiz).as_posix(): p
            for p in raiz.rglob("*") if p.is_file()
            and not p.relative_to(raiz).as_posix().startswith(IMG_DIR + "/")}


def mesmo_conteudo(a: Path, b: Path) -> bool:
    """Os dois sites dizem a mesma coisa (a menos do relógio)?"""
    fa, fb = _ficheiros(a), _ficheiros(b)
    if fa.keys() != fb.keys():
        return False
    for nome, pa in fa.items():
        pb = fb[nome]
        if nome.endswith(".json"):
            try:
                ja = _sem_relogio(json.loads(pa.read_text(encoding="utf-8")))
                jb = _sem_relogio(json.loads(pb.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                return False
            if ja != jb:
                return False
        elif pa.read_bytes() != pb.read_bytes():
            return False
    return True


def mesmo_conteudo_raiz(a: Path, b: Path) -> bool:
    """Como o `mesmo_conteudo`, mas SÓ o site da raiz — ignora o `u/<slug>/`.

    Serve uma pergunta só, e é a da checklist 17: **abrir as portas muda o
    site DELE?** Comparar as pastas inteiras respondia outra coisa (com as
    portas abertas há pastas a mais, e é suposto).
    """
    def so_raiz(raiz: Path) -> dict[str, Path]:
        return {n: p for n, p in _ficheiros(raiz).items()
                if not n.startswith("u/")}
    fa, fb = so_raiz(a), so_raiz(b)
    if fa.keys() != fb.keys():
        return False
    for nome, pa in fa.items():
        pb = fb[nome]
        if nome.endswith(".json"):
            try:
                ja = _sem_relogio(json.loads(pa.read_text(encoding="utf-8")))
                jb = _sem_relogio(json.loads(pb.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                return False
            if ja != jb:
                return False
        elif pa.read_bytes() != pb.read_bytes():
            return False
    return True


def build(out_dir: Path | str | None = None, log=print,
          so_se_mudou: bool = False, user_id: int | None = None,
          casca: str | None = None) -> dict:
    """O site de UM utilizador, com a privacidade dele respeitada.

    `publico = "nada"` não gera nada — nem a pasta. É a omissão de quem entra
    de novo, e é a leitura certa de «o que o público vê»: quem não escolheu
    publicar não publicou.
    """
    out = Path(out_dir or config.ROOT / "site")
    uid = utilizador.atual() if user_id is None else int(user_id)
    modo = privacidade.de(None, uid)
    if not privacidade.publica(modo):
        log(f"«{utilizador.registo(uid)['slug']}» tem a privacidade em "
            f"«{modo}» — não se gera site nenhum.")
        return {"out": str(out), "sets": 0, "images": 0, "mudou": False,
                "publico": modo, "gerado": False}
    if so_se_mudou and (out / "api" / "index.json").exists():
        # A pasta de prova fica NA RAIZ DO REPO e não ao lado do `out`: desde
        # 2026-09-30 o site dele pode viver em `site/u/baverone/`, e ali
        # `out.parent` era DENTRO do `site/` — uma corrida interrompida a meio
        # deixava uma `site/u/baverone-prova/` commitada e publicada.
        prova = config.ROOT / (out.name + "-prova")
        shutil.rmtree(prova, ignore_errors=True)
        try:
            # O `casca` TEM de ir na prova: sem ele a prova leva o `app.js` e o
            # `style.css` que o `out` já não tem, o `mesmo_conteudo` compara
            # conjuntos de ficheiros diferentes e diz «mudou» a TODAS as
            # corridas — a avaria de 2026-09-10 por outro caminho.
            _gerar(prova, log=lambda *_: None, imagens=False, user_id=uid,
                   modo=modo, casca=casca)
            igual = mesmo_conteudo(out, prova)
        finally:
            shutil.rmtree(prova, ignore_errors=True)
        if igual:
            log("O site já está em dia — nada mudou desde a última geração.")
            return {"out": str(out), "sets": 0, "images": 0, "mudou": False,
                    "publico": modo, "gerado": True,
                    "image_mode": ("local" if config.load().get("static_images")
                                   == "local" else "remote")}
    res = _gerar(out, log=log, imagens=True, user_id=uid, modo=modo,
                 casca=casca)
    res["mudou"] = True
    res["publico"] = modo
    res["gerado"] = True
    return res


def build_todos(out_dir: Path | str | None = None, log=print,
                cfg: dict | None = None, so_se_mudou: bool = False) -> dict:
    """O site DELE na raiz, e o de cada utilizador em `u/<slug>/`.

    **COM AS PORTAS FECHADAS (`multi.aberto: false`, que é a omissão) SÓ SAI O
    DELE**, e sai exactamente como sai hoje — mesmo que haja utilizadores no
    registo e mesmo que algum deles tenha escolhido `publico: "tudo"`. É o
    ponto 9 da ordem de 2026-09-29: *"Quero apenas apresentar quando tiver
    tudo"*. Quando ele quiser abrir, muda-se **um valor** no config.

    O mecanismo de gerar os outros EXISTE e é exercitado em teste
    (`test_privacidade.TestPortasFechadas`) — «não publica» tem de ser uma
    escolha, não uma incapacidade; senão no dia de abrir descobria-se que não
    estava feito.

    A LISTA (2026-09-30) entra aqui, e a troca é AUTOMÁTICA: com duas ou mais
    coleções públicas a raiz passa a ser o índice (`lista.py`) e a dele muda-se
    para `u/baverone/`. Com uma — que é o de hoje, com as portas fechadas — a
    raiz fica exactamente como está. Ele não tem de mudar chave nenhuma.
    """
    cfg = config.load() if cfg is None else cfg
    out = Path(out_dir or config.ROOT / "site")
    pub = lista.publicas(cfg)
    indice = lista.na_raiz(pub)
    # A CASCA fica na RAIZ quando a lista toma a raiz (2026-10-04) — uma vez
    # só, em vez de uma cópia por pessoa. A subida sai do caminho REAL de cada
    # um (`u/<slug>/` -> `../../`) e não de um `"../../"` escrito à mão: se a
    # arrumação mudar de profundidade, muda aqui sozinha.
    entrada_dele = {"user_id": utilizador.ANDRE, "slug": utilizador.SLUG_ANDRE}
    casca = lista.subida_da_casca(entrada_dele, pub) if indice else None
    dele = lista.pasta_de(out, entrada_dele, pub)
    res = build(dele, log=log, so_se_mudou=so_se_mudou,
                user_id=utilizador.ANDRE, casca=casca)
    outros, saltados = [], []
    for u in utilizador.todos():
        if u["user_id"] == utilizador.ANDRE:
            continue
        modo = privacidade.de(None, u["user_id"])
        if not multi.aberto(cfg):
            saltados.append((u["slug"], "portas fechadas"))
            continue
        if not privacidade.publica(modo):
            saltados.append((u["slug"], f"privacidade «{modo}»"))
            continue
        r = build(out / "u" / u["slug"], log=lambda *_: None,
                  user_id=u["user_id"],
                  casca=lista.subida_da_casca(u, pub))
        outros.append({"slug": u["slug"], "publico": modo, **r})
    if saltados:
        log("  não publicados: " + " · ".join(f"{s} ({p})" for s, p in saltados))
    # DESPUBLICAR TEM DE SER TÃO FÁCIL COMO PUBLICAR: quem deixou de ser
    # público perde a pasta que já lá estava, e não só a geração desta vez.
    # Saltar não é apagar — ver `lista.limpar_nao_publicadas`.
    saiu = lista.limpar_nao_publicadas(out, pub)
    if saiu:
        log("  saíram do site (já não se publicam): " + " · ".join(saiu))
    if indice:
        # A ORDEM IMPORTA: tirar os restos do site dele da raiz ANTES de lá
        # escrever a lista — o `limpar_raiz` leva a `api/` inteira, e a lista
        # escreve a sua `api/lista.json` por cima.
        restos = lista.limpar_raiz(out)
        if restos:
            log("  a raiz passa a ser a lista — saíram de lá: "
                + " · ".join(restos))
        dados = lista.escrever(out, pub=pub, cfg=cfg)
        log(f"  index.html + api/lista.json  ({len(dados['coleccoes'])} "
            f"coleções públicas; a dele em u/{utilizador.SLUG_ANDRE}/)")
        res["lista"] = dados
    res["na_raiz"] = indice
    res["publicas"] = pub
    res["outros"] = outros
    res["saltados"] = saltados
    res["aberto"] = multi.aberto(cfg)
    return res


def _gerar(out_dir: Path | str, log=print, imagens: bool = True,
           user_id: int | None = None, modo: str = "tudo",
           casca: str | None = None) -> dict:
    cfg = config.load()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # A `api/` é reescrita de raiz. Uma edição que desapareça do catálogo tem de
    # desaparecer do site; e um payload órfão fazia o `--se-mudou` ver diferença
    # a cada corrida (o ficheiro está de um lado e não do outro), o que dava uma
    # build do Pages de 30 em 30 minutos sem nada ter mudado.
    shutil.rmtree(out / "api", ignore_errors=True)

    # O GitHub Pages ignora pastas começadas por _ sem isto.
    (out / ".nojekyll").write_text("", encoding="utf-8")

    # A CASCA (2026-10-04): com `casca` posto, o `app.js` e o `style.css` não
    # se copiam para cá — vivem `casca` acima, uma vez só para toda a gente, e
    # o `index.html` sai com as referências reescritas. Sem `casca` (o site de
    # UMA pessoa, na raiz) fica tudo como sempre foi.
    for name in ("index.html", *(() if casca else CASCA)):
        shutil.copy2(config.WEB_DIR / name, out / name)
    if casca:
        pagina = out / "index.html"
        pagina.write_text(_aponta_a_casca(pagina.read_text(encoding="utf-8"),
                                          casca), encoding="utf-8")

    # «NÃO INDEXES ISTO» (2026-09-29, fatia `2-multi-contas`). A página DELE fica
    # exactamente como está — publicada e indexada, como sempre foi. A de um
    # amigo sai marcada, nas duas formas que os motores respeitam: a etiqueta na
    # página e o `robots.txt` na raiz dela.
    #
    # Os dois juntos, e não só o `robots.txt`: esse pede que não se RASTREIE, e
    # uma página já conhecida por um link pode ser indexada sem ser rastreada. O
    # `noindex` na própria página é o que fecha essa porta.
    #
    # Porque é que isto é do lado seguro do erro: uma página da coleção de um
    # amigo indexada antes de ele saber que existe **não se desfaz** — pede-se a
    # remoção, fica em cache, fica no Bing, fica no archive.org.
    if not abrir.publico_indexavel(dono=(user_id is None or user_id == 1)):
        pagina = out / "index.html"
        pagina.write_text(abrir.marcar_html(pagina.read_text(encoding="utf-8")),
                          encoding="utf-8")
        (out / "robots.txt").write_text(abrir.robots_txt(), encoding="utf-8")

    image_mode = "local" if cfg.get("static_images") == "local" else "remote"

    def escrever(caminho: Path, payload) -> None:
        """A ÚNICA porta por onde um payload sai para o disco.

        É aqui que a privacidade se aplica (2026-09-29): com `publico:
        "sem-valores"` o `privacidade.limpar` tira todas as quantias antes de
        o JSON ser escrito. Uma porta só, e não quinze `json.dumps` espalhados,
        porque um payload novo que não passe por aqui é uma fuga silenciosa —
        e há teste que recusa um `json.dumps` neste ficheiro fora daqui.
        """
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(
            json.dumps(privacidade.limpar(payload, modo), ensure_ascii=False,
                       separators=(",", ":")), encoding="utf-8")

    con = db.connect(user_id=user_id)  # não readonly: garante o schema num clone fresco
    # As listas TÊM de ser relidas antes dos payloads da Coleção: o nome do deck
    # que aparece em cada tile ("2× Ornn · 1 na Coleção") sai da tabela `decks`
    # do vault.db, e a alocação por prioridade da secção Decks sai das listas. O
    # vault.db que vem do Git tem os decks como estavam da última vez que o
    # André correu isto em casa, por isso importar só a seguir deixava a Coleção
    # uma edição de deck atrasada em relação à secção Decks do MESMO site.
    # (Desde 2026-09-10 o LOCAL de cada cópia já não vem daqui — está gravado na
    # `copy_locations` —, mas o nome de mostrar continua a vir.)
    decks.import_all(con, log=lambda *_: None)
    api_dir = out / "api" / "set"
    api_dir.mkdir(parents=True, exist_ok=True)

    index = metrics.index_payload(con, editable=False, image_mode=image_mode, cfg=cfg)
    escrever(out / "api" / "index.json", index)

    n_sets = 0
    for s in index["sets"]:
        payload = metrics.set_payload(con, s["id"], editable=False, image_mode=image_mode)
        escrever(api_dir / f"{s['id']}.json", payload)
        n_sets += 1
        log(f"  api/set/{s['id']}.json  ({len(payload['groups'])} grupos)")
    # O bloco «Runas — 12 de cada» do fim da grelha (2026-09-19): o contador
    # dele. Um ficheiro só, com a referência de CADA edição em `por_edicao`
    # (2026-10-01) — as seis runas são as mesmas, o que muda é a impressão.
    # Não conta para nada — e no site publicado é só de leitura
    # (`editable: False`, sem `+`/`−`).
    runas = runas_vista.payload(con, cfg, image_mode=image_mode, editable=False)
    escrever(out / "api" / "runas.json", runas)
    log(f"  api/runas.json  ({runas['totals']['cards']} runas, contador "
        f"{runas['totals']['contador']} · na coleção {runas['totals']['total']} — só para ver; "
        + " ".join(f"{sid} {e['totals']['total']}"
                   for sid, e in runas["por_edicao"].items()) + ")")
    con.close()

    # Decks: os mesmos URLs que o servidor serve em modo edição.
    con = db.connect(user_id=user_id)
    deck_dir = out / "api" / "deck"
    deck_dir.mkdir(parents=True, exist_ok=True)
    index_decks = decks.decks_index(con)
    escrever(out / "api" / "decks.json",
             {"editable": False, "decks": index_decks, "rules": decks.rules(),
              "ordem_fixa": decks.ordem_fixa(), "so_base": decks.so_base(),
              "raridade_colecao": decks.raridade_da_colecao(),
              # O DECK PRINCIPAL (2026-09-27): quem é. A wantlist dele
              # vai no payload de cada deck, como tudo o resto.
              "principal": principal.estado(con)})
    for d in index_decks:
        escrever(deck_dir / f"{d['id']}.json", decks.deck_payload(con, d["id"]))
    # O `api/faltas.json` (o antigo separador «Faltas», até 2026-09-15)
    # partiu-se na wantlist da Coleção e nas listas de compra dos decks. (A
    # terceira parte, a tabela de preços, saiu com o separador dela a
    # 2026-09-19 — ver o CLAUDE.md.)
    escrever(out / "api" / "wantlist.json", a_subir.master_faltas(con))
    escrever(out / "api" / "compras.json", faltas.compras(con))
    # O separador «Faltas» (2026-09-15, fim da tarde): por edição, as DUAS
    # metades — os quatro blocos de NORMAIS e, desde 2026-09-27, as FOILS à
    # parte, com a quinta wantlist.
    fe = faltas_foil.payload_completo(con)
    escrever(out / "api" / "faltas_edicao.json", fe)
    # O separador «A mais» (2026-09-17): o excedente e as libertadas dos decks.
    am = a_mais.payload(con)
    escrever(out / "api" / "a_mais.json", am)
    # As encomendas (2026-09-11): a lista do que está a caminho, só de leitura
    # no site publicado — os `+`/`−` são do modo edição.
    encomendas = {"editable": False, **pending.encomendas(con)}
    escrever(out / "api" / "encomendas.json", encomendas)
    # O separador «Encomendas» (2026-09-17): a grelha da Coleção de Rara para
    # cima, uma por edição, com o que vem a caminho. Sem controlos no site
    # publicado — o `editable: False` é o mesmo flag da Coleção.
    # A «Venda» (2026-09-25): a venda em curso, só de leitura no site
    # publicado — juntar, tirar, escrever o Trend e «marcar como vendidas» são
    # do modo edição (o `editable: False` é o mesmo flag da Coleção).
    vd = venda.payload(con, cfg, editable=False)
    escrever(out / "api" / "venda.json", vd)
    # O «Produto Selado» (2026-09-25): a lista do que há, do que ele tem e do
    # que não tem. Só de leitura no site publicado — os `+`/`−` são do modo
    # edição (o mesmo `editable: False` da Coleção).
    sl = selado.payload(con, cfg, editable=False)
    escrever(out / "api" / "selado.json", sl)
    enc_dir = out / "api" / "encomendas"
    enc_dir.mkdir(parents=True, exist_ok=True)
    n_enc = 0
    for s in index["sets"]:
        g = pending.grelha(con, s["id"], editable=False, image_mode=image_mode, cfg=cfg)
        escrever(enc_dir / f"{s['id']}.json", g)
        n_enc += g["totals"]["printings"]
    con.close()
    log(f"  api/decks.json  ({len(index_decks)} decks, "
        f"{sum(d['proprias'] for d in index_decks)} cópias próprias) + api/wantlist.json"
        f" + api/compras.json + api/faltas_edicao.json ({fe['totals']['copies']} "
        f"cópias a comprar · {fe['foil']['totals']['copies']} foils à parte, que "
        f"não são faltas) + api/a_mais.json ({am['totals']['excedente']['copies']} "
        f"cópias a mais) + api/encomendas.json "
        f"({encomendas['totals']['copies']} cópias a caminho) + api/encomendas/*.json "
        f"({n_enc} impressões de Rara para cima) + api/venda.json "
        f"({vd['totals']['lines']} linhas na venda em curso) + api/selado.json "
        f"({sl['totals']['tenho']}/{sl['totals']['ha']} produtos selados)")

    n_img = 0
    if imagens and image_mode == "local" and config.IMAGES_DIR.exists():
        dest = out / "img"
        dest.mkdir(exist_ok=True)
        for src in config.IMAGES_DIR.glob("*.webp"):
            shutil.copy2(src, dest / src.name)
            n_img += 1
        log(f"  img/  ({n_img} imagens copiadas)")
    elif imagens:
        log("  imagens: a apontar para o CDN da RiftScribe (static_images='remote')")

    return {"out": str(out), "sets": n_sets, "images": n_img, "image_mode": image_mode}
