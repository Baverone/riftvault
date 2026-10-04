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


class _Saida:
    """A porta por onde o site sai para o disco — e o CRIVO (2026-10-04).

    **Um ficheiro cujo conteúdo não mudou não se reescreve.** O `generated_at`
    muda a cada geração e era ele, sozinho, que fazia o Git ver todos os
    payloads como novos. Medido no repositório real: os dez commits do `site/`
    de 2026-10-04, de meia em meia hora das 05:37 às 10:07, tocaram
    **exactamente 28 ficheiros cada um — goncalves 14 + miguel 14 —, e em 28 de
    28 só o relógio mudava** (comparados dois pares de commits consecutivos com
    a regra do `_sem_relogio`). Era um commit, um push e uma build do Pages de
    30 em 30 minutos, 48 vezes por dia, sem uma carta mexer: a avaria de
    2026-09-10 de volta pela porta de trás, porque o `--se-mudou` só olhava
    para a coleção DELE e as dos amigos eram sempre regeneradas.

    O crivo é o do `mesmo_conteudo`, aplicado ficheiro a ficheiro em vez de ao
    site todo.

    DUAS REGRAS, e a segunda é uma decisão explícita:

      1. **ou se escreve tudo o que mudou, ou não se escreve nada.** Se nenhum
         ficheiro desta pessoa diferir, não se toca em nenhum — nem no índice.
         Senão o índice sozinho dava o mesmo commit de 30 em 30 minutos;
      2. **o `api/index.json` é SEMPRE reescrito quando algum outro mudou**,
         com relógio fresco. É ele a prova de que o site publicado é o que foi
         gerado aqui: a `riftvault-publicar` e a `riftvault-daily` leem-lhe o
         `generated_at` (pela `api/lista.json`, que diz de quem é a referência)
         e comparam-no com o que o Pages serve; e o teste delas exige, quando a
         tarefa diz que gerou o site, que o ficheiro tenha sido **escrito
         hoje**. Deixá-lo com o relógio velho dava as duas avarias de uma vez:
         a prova a comparar uma data antiga (e portanto a passar sempre) e a
         tarefa a chumbar sem motivo no `escrito_hoje`.

         Custa um ficheiro de ~20 KB por pessoa, e só em publicações que já
         iam acontecer. Ver `docs/eficiencia-site-2026-10-04.md`.

    O alinhamento com a tarefa é exacto e vale a pena escrevê-lo: o
    `site_gerado` dela é o `res["mudou"]` DELE (o `cmd_build` só imprime «Site
    gerado» nesse caso), por isso o `escrito_hoje` só pergunta pelo índice dele
    quando o `_gerar` dele correu — e aí a regra 2 garante-o fresco.
    """

    #: O índice, que a regra 2 isenta do crivo. Relativo ao `out`.
    INDICE = "api/index.json"

    #: De onde se podam os órfãos. É o que o `rmtree(out/"api")` apagava antes:
    #: uma edição que saia do catálogo tem de sair do site, e um payload órfão
    #: fazia o `--se-mudou` ver diferença a cada corrida. O resto da pasta não
    #: é nosso para apagar (o `img/` de 88 MB, um `CNAME`).
    PODA = "api"

    def __init__(self, out: Path, modo: str = "tudo"):
        self.out = Path(out)
        self.modo = modo
        self._corpos: dict[str, bytes] = {}
        self._iguais: set[str] = set()
        self._fora: list[str] = []

    # -- pôr na fila -------------------------------------------------------

    def json(self, rel: str, payload) -> None:
        """Um payload. É AQUI que a privacidade se aplica (2026-09-29).

        Uma porta só, e não quinze `json.dumps` espalhados, porque um payload
        novo que não passe por aqui é uma fuga silenciosa.
        """
        self._por(rel, json.dumps(privacidade.limpar(payload, self.modo),
                                  ensure_ascii=False,
                                  separators=(",", ":")).encode("utf-8"),
                  e_json=True)

    def texto(self, rel: str, corpo: str) -> None:
        self._por(rel, corpo.encode("utf-8"), e_json=False)

    def copia(self, rel: str, origem: Path) -> None:
        self._por(rel, Path(origem).read_bytes(), e_json=False)

    def remover(self, rel: str) -> None:
        """Um ficheiro que esta pasta já não tem de ter — se lá estiver, sai.

        Serve a mudança de arrumação: a cópia velha da casca numa pasta que
        passou a apontar à raiz. Fora da `api/` a poda dos órfãos não chega
        (ali só se apaga o que a `api/` deixou de precisar), e o que é da raiz
        não é nosso para apagar às cegas — por isso nomeia-se.
        """
        if (self.out / rel).is_file():
            self._fora.append(rel)

    def _por(self, rel: str, corpo: bytes, e_json: bool) -> None:
        self._corpos[rel] = corpo
        p = self.out / rel
        if not p.is_file():
            return
        velho = p.read_bytes()
        if e_json:
            try:
                igual = (_sem_relogio(json.loads(velho))
                         == _sem_relogio(json.loads(corpo)))
            except ValueError:
                igual = False
        else:
            igual = velho == corpo
        if igual:
            self._iguais.add(rel)

    # -- escrever ----------------------------------------------------------

    def _orfaos(self) -> list[str]:
        base = self.out / self.PODA
        if not base.is_dir():
            return []
        return sorted(p.relative_to(self.out).as_posix()
                      for p in base.rglob("*") if p.is_file()
                      and p.relative_to(self.out).as_posix() not in self._corpos)

    def fechar(self) -> dict:
        orfaos = self._orfaos()
        fora = sorted(set(self._fora) - set(self._corpos))
        mudaram = sorted(r for r in self._corpos if r not in self._iguais)
        if not mudaram and not orfaos and not fora:
            return {"escritos": [], "kb": 0.0, "orfaos": [], "fora": [],
                    "iguais": len(self._iguais), "mudou": False}
        a_escrever = set(mudaram)
        if self.INDICE in self._corpos:
            a_escrever.add(self.INDICE)          # a regra 2
        for rel in sorted(a_escrever):
            p = self.out / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(self._corpos[rel])
        for rel in orfaos + fora:
            (self.out / rel).unlink(missing_ok=True)
        return {"escritos": sorted(a_escrever),
                "kb": round(sum(len(self._corpos[r]) for r in a_escrever) / 1024, 1),
                "orfaos": orfaos, "fora": fora,
                "iguais": len(self._iguais), "mudou": True}


def _nada_escrito() -> dict:
    """O `crivo` de um `build` que não chegou a gerar.

    Dois casos: privacidade «nada», e o `--se-mudou` a dizer que está em dia.
    Vai nos dois para quem lê o resultado não ter de perguntar se a chave
    existe — um `KeyError` num caminho destes aparecia meses depois, no dia em
    que alguém passasse o `so_se_mudou` aos amigos também. É uma função e não
    uma constante porque o resultado leva listas lá dentro: devolver sempre o
    MESMO dicionário punha dois `build` a partilhá-las.
    """
    return {"escritos": [], "kb": 0.0, "orfaos": [], "fora": [],
            "iguais": 0, "mudou": False}


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
                "publico": modo, "gerado": False, "crivo": _nada_escrito()}
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
                    "publico": modo, "gerado": True, "crivo": _nada_escrito(),
                    "image_mode": ("local" if config.load().get("static_images")
                                   == "local" else "remote")}
    res = _gerar(out, log=log, imagens=True, user_id=uid, modo=modo,
                 casca=casca)
    # `mudou` é «escreveu-se alguma coisa», e desde 2026-10-04 é o CRIVO que
    # responde. Era `True` sempre que o `_gerar` corresse, e com o crivo isso
    # passou a poder ser falso: sem `--se-mudou`, uma geração em que nada
    # difere não escreve um ficheiro.
    #
    # O ERRO CAI PARA O LADO SEGURO: o `cmd_build` só imprime «Site gerado»
    # quando isto é `True`, e é dessa linha que a `riftvault-publicar` tira o
    # `site_gerado` que liga o `escrito_hoje(api/index.json)`. Um `False` a
    # mais salta a verificação; um `True` a mais chumbava a tarefa.
    res["mudou"] = bool(res["crivo"]["mudou"])
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
    # O CRIVO: nada se escreve até ao `fechar()`, e lá só sai o que mudou. A
    # `api/` já não se apaga de raiz — os órfãos podam-se ao fim, que dá a
    # mesma garantia (uma edição que saia do catálogo sai do site) sem obrigar
    # a reescrever os outros vinte payloads que não mudaram (medido na pasta
    # gerada: 23 ficheiros por pessoa, 21 deles `.json`). Ver o `_Saida`.
    saida = _Saida(out, modo=modo)

    # O GitHub Pages ignora pastas começadas por _ sem isto.
    saida.texto(".nojekyll", "")

    # A CASCA (2026-10-04): com `casca` posto, o `app.js` e o `style.css` não
    # se copiam para cá — vivem `casca` acima, uma vez só para toda a gente, e
    # o `index.html` sai com as referências reescritas. Sem `casca` (o site de
    # UMA pessoa, na raiz) fica tudo como sempre foi.
    for name in (() if casca else CASCA):
        saida.copia(name, config.WEB_DIR / name)
    pagina = (config.WEB_DIR / "index.html").read_text(encoding="utf-8")
    if casca:
        pagina = _aponta_a_casca(pagina, casca)
        # A CÓPIA VELHA TEM DE SAIR, senão a poupança é mentira: o `site/`
        # commitado foi gerado quando cada pasta levava a sua casca, e a poda
        # dos órfãos só mexe na `api/`. Sem isto ficavam lá 900,7 KB de
        # `app.js`/`style.css` que ninguém volta a pedir — nem a página, que
        # aponta `../../`, nem o build, que já não os escreve.
        for name in CASCA:
            saida.remover(name)

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
        pagina = abrir.marcar_html(pagina)
        saida.texto("robots.txt", abrir.robots_txt())
    saida.texto("index.html", pagina)

    image_mode = "local" if cfg.get("static_images") == "local" else "remote"

    # A porta dos payloads é o `saida.json` — ver o `_Saida`, que é onde a
    # privacidade se aplica e onde o crivo decide. Este atalho fica só para
    # não reescrever as trinta chamadas de baixo.
    def escrever(rel: str, payload) -> None:
        saida.json(rel, payload)

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

    index = metrics.index_payload(con, editable=False, image_mode=image_mode, cfg=cfg)
    escrever(_Saida.INDICE, index)

    n_sets = 0
    for s in index["sets"]:
        payload = metrics.set_payload(con, s["id"], editable=False, image_mode=image_mode)
        escrever(f"api/set/{s['id']}.json", payload)
        n_sets += 1
        log(f"  api/set/{s['id']}.json  ({len(payload['groups'])} grupos)")
    # O bloco «Runas — 12 de cada» do fim da grelha (2026-09-19): o contador
    # dele. Um ficheiro só, com a referência de CADA edição em `por_edicao`
    # (2026-10-01) — as seis runas são as mesmas, o que muda é a impressão.
    # Não conta para nada — e no site publicado é só de leitura
    # (`editable: False`, sem `+`/`−`).
    runas = runas_vista.payload(con, cfg, image_mode=image_mode, editable=False)
    escrever("api/runas.json", runas)
    log(f"  api/runas.json  ({runas['totals']['cards']} runas, contador "
        f"{runas['totals']['contador']} · na coleção {runas['totals']['total']} — só para ver; "
        + " ".join(f"{sid} {e['totals']['total']}"
                   for sid, e in runas["por_edicao"].items()) + ")")
    con.close()

    # Decks: os mesmos URLs que o servidor serve em modo edição.
    con = db.connect(user_id=user_id)
    index_decks = decks.decks_index(con)
    escrever("api/decks.json",
             {"editable": False, "decks": index_decks, "rules": decks.rules(),
              "ordem_fixa": decks.ordem_fixa(), "so_base": decks.so_base(),
              "raridade_colecao": decks.raridade_da_colecao(),
              # O DECK PRINCIPAL (2026-09-27): quem é. A wantlist dele
              # vai no payload de cada deck, como tudo o resto.
              "principal": principal.estado(con)})
    for d in index_decks:
        escrever(f"api/deck/{d['id']}.json", decks.deck_payload(con, d["id"]))
    # O `api/faltas.json` (o antigo separador «Faltas», até 2026-09-15)
    # partiu-se na wantlist da Coleção e nas listas de compra dos decks. (A
    # terceira parte, a tabela de preços, saiu com o separador dela a
    # 2026-09-19 — ver o CLAUDE.md.)
    escrever("api/wantlist.json", a_subir.master_faltas(con))
    escrever("api/compras.json", faltas.compras(con))
    # O separador «Faltas» (2026-09-15, fim da tarde): por edição, as DUAS
    # metades — os quatro blocos de NORMAIS e, desde 2026-09-27, as FOILS à
    # parte, com a quinta wantlist.
    fe = faltas_foil.payload_completo(con)
    escrever("api/faltas_edicao.json", fe)
    # O separador «A mais» (2026-09-17): o excedente e as libertadas dos decks.
    am = a_mais.payload(con)
    escrever("api/a_mais.json", am)
    # As encomendas (2026-09-11): a lista do que está a caminho, só de leitura
    # no site publicado — os `+`/`−` são do modo edição.
    encomendas = {"editable": False, **pending.encomendas(con)}
    escrever("api/encomendas.json", encomendas)
    # O separador «Encomendas» (2026-09-17): a grelha da Coleção de Rara para
    # cima, uma por edição, com o que vem a caminho. Sem controlos no site
    # publicado — o `editable: False` é o mesmo flag da Coleção.
    # A «Venda» (2026-09-25): a venda em curso, só de leitura no site
    # publicado — juntar, tirar, escrever o Trend e «marcar como vendidas» são
    # do modo edição (o `editable: False` é o mesmo flag da Coleção).
    vd = venda.payload(con, cfg, editable=False)
    escrever("api/venda.json", vd)
    # O «Produto Selado» (2026-09-25): a lista do que há, do que ele tem e do
    # que não tem. Só de leitura no site publicado — os `+`/`−` são do modo
    # edição (o mesmo `editable: False` da Coleção).
    sl = selado.payload(con, cfg, editable=False)
    escrever("api/selado.json", sl)
    n_enc = 0
    for s in index["sets"]:
        g = pending.grelha(con, s["id"], editable=False, image_mode=image_mode, cfg=cfg)
        escrever(f"api/encomendas/{s['id']}.json", g)
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

    # O CRIVO decide aqui, com tudo na mão: ou se escreve o que mudou (mais o
    # índice, pela regra 2), ou não se escreve ficheiro nenhum.
    crivo = saida.fechar()
    if crivo["mudou"]:
        log(f"  escritos {len(crivo['escritos'])} ficheiros ({crivo['kb']} KB); "
            f"{crivo['iguais']} ficaram como estavam"
            + (f"; {len(crivo['orfaos'])} órfãos podados" if crivo["orfaos"] else "")
            + (f"; saíram as cópias velhas da casca ({', '.join(crivo['fora'])})"
               if crivo["fora"] else ""))
    else:
        log(f"  nada a escrever — os {crivo['iguais']} ficheiros desta coleção "
            f"dizem o mesmo que já está em disco")

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

    return {"out": str(out), "sets": n_sets, "images": n_img,
            "image_mode": image_mode, "crivo": crivo}
