"""Modo publicado: gera o site estático (só leitura) para o GitHub Pages.

É o MESMO frontend do modo edição — os ficheiros são copiados tal e qual. O que
muda é só o conteúdo dos payloads: `editable: false`, e os endpoints da API
passam a ser ficheiros .json reais nos mesmos caminhos.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import config, db, decks, faltas, metrics, venda


def build(out_dir: Path | str | None = None, log=print) -> dict:
    cfg = config.load()
    out = Path(out_dir or config.ROOT / "site")
    out.mkdir(parents=True, exist_ok=True)

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
    if image_mode == "local" and config.IMAGES_DIR.exists():
        dest = out / "img"
        dest.mkdir(exist_ok=True)
        for src in config.IMAGES_DIR.glob("*.webp"):
            shutil.copy2(src, dest / src.name)
            n_img += 1
        log(f"  img/  ({n_img} imagens copiadas)")
    else:
        log("  imagens: a apontar para o CDN da RiftScribe (static_images='remote')")

    return {"out": str(out), "sets": n_sets, "images": n_img, "image_mode": image_mode}
