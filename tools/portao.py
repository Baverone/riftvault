"""O PORTÃO: o merge só acontece a partir do PLACAR da suite (2026-09-29).

    py -X utf8 tools/portao.py suite        corre a suite e grava o placar
    py -X utf8 tools/portao.py verificar    lê o placar; sai 1 se vermelho
    py -X utf8 tools/portao.py merge <ramo> -m "<mensagem>"   [--push]

O `merge` VERIFICA PRIMEIRO e recusa-se a chamar o `git` se o placar não for
verde. Não há bandeira para o forçar, e é de propósito: uma bandeira de forçar
é a que se usa às duas da manhã. Quem quiser mesmo fazer o merge com a suite
vermelha escreve o `git merge` à mão — e aí é uma decisão, não um descuido.

Corre o `git` no diretório da RAIZ (`git -C`), nunca com um `cd` à frente.

A SUITE CORRE EM PARALELO desde 2026-09-30, e cada vermelho repete-se sozinho
antes de contar como vermelho. Para depurar um de cada vez:

    RIFTVAULT_SUITE_SERIE=1 py -X utf8 tools/portao.py suite

Ver `tools/placar.py` para o que o placar guarda, para as cinco maneiras de
estar vermelho e para a razão de não haver lista de ficheiros «maus».
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import placar as pl  # noqa: E402


def _git(raiz: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(raiz), *args],
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accao", choices=("suite", "verificar", "merge"))
    ap.add_argument("ramo", nargs="?", help="o ramo a integrar, no `merge`")
    ap.add_argument("-m", "--mensagem", help="mensagem do merge")
    ap.add_argument("--raiz", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--push", action="store_true", help="empurra depois do merge")
    a = ap.parse_args(argv)
    raiz = Path(a.raiz).resolve()

    if a.accao == "suite":
        p = pl.correr(raiz)
        alvo = pl.gravar(raiz, p)
        print(f"\nplacar gravado em {alvo}")
        ok, razao = pl.verde(raiz)
        print(razao)
        return 0 if ok else 1

    if a.accao == "verificar":
        ok, razao = pl.verde(raiz)
        print(razao)
        return 0 if ok else 1

    # merge
    if not a.ramo:
        print("falta o ramo: `portao.py merge <ramo> -m \"...\"`")
        return 2
    ok, razao = pl.verde(raiz)
    print(razao)
    if not ok:
        print("O MERGE NÃO SE FAZ. Corre a suite e emenda o que estiver "
              "vermelho — não há bandeira para forçar isto.")
        return 1

    sujo = _git(raiz, "status", "--porcelain").stdout.strip()
    # O próprio placar não conta: é o resultado da corrida, e está no
    # `.gitignore` — mas se alguém o tirar de lá, não é motivo para parar.
    sujo = "\n".join(l for l in sujo.splitlines()
                     if l.split()[-1] != pl.PLACAR)
    if sujo:
        print("VERMELHO: a árvore de trabalho tem alterações por commitar — "
              "o placar mediu o que está em disco, mas o merge integra o que "
              "está commitado:\n" + sujo)
        return 1

    msg = a.mensagem or f"Merge: {a.ramo}"
    r = _git(raiz, "merge", "--no-ff", a.ramo, "-m", msg)
    print(r.stdout or r.stderr)
    if r.returncode != 0:
        return r.returncode
    if a.push:
        r = _git(raiz, "push")
        print(r.stdout or r.stderr)
        return r.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
