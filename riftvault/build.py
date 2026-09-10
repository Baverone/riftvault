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

from . import config, db, decks, faltas, metrics, venda

# A pasta das imagens fica de fora da comparação: em `static_images: "local"`
# são ~88 MB e não dependem da colecção — o que muda nelas é o `riftvault
# images`, não o build.
IMG_DIR = "img"


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


def build(out_dir: Path | str | None = None, log=print,
          so_se_mudou: bool = False) -> dict:
    out = Path(out_dir or config.ROOT / "site")
    if so_se_mudou and (out / "api" / "index.json").exists():
        prova = out.parent / (out.name + "-prova")
        shutil.rmtree(prova, ignore_errors=True)
        try:
            _gerar(prova, log=lambda *_: None, imagens=False)
            igual = mesmo_conteudo(out, prova)
        finally:
            shutil.rmtree(prova, ignore_errors=True)
        if igual:
            log("O site já está em dia — nada mudou desde a última geração.")
            return {"out": str(out), "sets": 0, "images": 0, "mudou": False,
                    "image_mode": ("local" if config.load().get("static_images")
                                   == "local" else "remote")}
    res = _gerar(out, log=log, imagens=True)
    res["mudou"] = True
    return res


def _gerar(out_dir: Path | str, log=print, imagens: bool = True) -> dict:
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

    for name in ("index.html", "app.js", "style.css"):
        shutil.copy2(config.WEB_DIR / name, out / name)

    image_mode = "local" if cfg.get("static_images") == "local" else "remote"

    con = db.connect()  # não readonly: garante o schema num clone fresco
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

    index = metrics.index_payload(con, editable=False, image_mode=image_mode)
    (out / "api" / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    n_sets = 0
    for s in index["sets"]:
        payload = metrics.set_payload(con, s["id"], editable=False, image_mode=image_mode)
        (api_dir / f"{s['id']}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
        n_sets += 1
        log(f"  api/set/{s['id']}.json  ({len(payload['groups'])} grupos)")
    con.close()

    # Decks: os mesmos URLs que o servidor serve em modo edição.
    con = db.connect()
    deck_dir = out / "api" / "deck"
    deck_dir.mkdir(parents=True, exist_ok=True)
    index_decks = decks.decks_index(con)
    (out / "api" / "decks.json").write_text(
        json.dumps({"editable": False, "decks": index_decks, "rules": decks.rules()},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for d in index_decks:
        (deck_dir / f"{d['id']}.json").write_text(
            json.dumps(decks.deck_payload(con, d["id"]), ensure_ascii=False,
                       separators=(",", ":")), encoding="utf-8")
    (out / "api" / "faltas.json").write_text(
        json.dumps(faltas.payload(con), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    # A lista de venda é um ficheiro à parte de propósito: o `faltas.json` já é
    # descarregado inteiro a cada visita e esta secção pode nunca ser aberta.
    lista_venda = venda.payload(con, editable=False)
    (out / "api" / "venda.json").write_text(
        json.dumps(lista_venda, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    con.close()
    log(f"  api/decks.json  ({len(index_decks)} decks) + api/faltas.json"
        f" + api/venda.json ({lista_venda['printings']} impressões)")

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
