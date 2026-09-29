"""O PLACAR da suite, e a impressão digital do código que ele mediu.

Porque é que isto existe (2026-09-29). Nesse dia o harness que corre estas
sessões disse «exit code 0» numa corrida cujo PLACAR, impresso pela própria
suite, dizia «1 a falhar». Quem lesse o código de saída dava o ramo por verde e
fazia o merge. A regra da casa sempre foi «lê o placar, não acredites no
harness» — mas era uma regra FALADA, e uma regra falada é uma regra que um dia
se esquece. Isto torna-a mecânica.

AS TRÊS COISAS QUE UM PLACAR TEM DE DIZER, e nenhuma se pode presumir:

  1. quantos ficheiros correram, quantos testes, quantos a falhar;
  2. QUE CÓDIGO é que ele mediu — senão um placar verde de há duas horas
     autoriza um merge de código que nunca correu;
  3. QUANDO. Só para o humano ler; quem decide é a impressão digital.

A IMPRESSÃO DIGITAL é o sha256 de tudo o que pode mudar a resposta da suite: o
pacote (`.py`, `.sql`, e o `web/`, que os testes leem como texto), os testes, e
o `riftvault_config.json` — que não é enfeite, é onde vivem regras que os
testes medem (`master_set.um_de_cada`, `selado.excluidos`, `decks.montados`).
Muda um byte de qualquer um deles e o placar deixa de valer para este código.

O `data/` NÃO entra: os testes correm contra cópias e pastas temporárias, e pôr
a coleção na impressão digital fazia um `+` num tile invalidar um placar verde.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# O placar fica na raiz do repositório e NÃO vai para o Git: é o resultado de
# uma corrida nesta máquina, não conteúdo do projecto. Um placar commitado era
# a pior versão deste problema — um verde de outra pessoa a autorizar o meu
# merge.
PLACAR = ".placar.json"

# O que pode mudar a resposta da suite.
IMPRESSAO = (
    ("riftvault", ("*.py", "*.sql")),
    ("riftvault/web", ("*.js", "*.css", "*.html")),
    ("tests", ("*.py",)),
)
IMPRESSAO_FICHEIROS = ("riftvault_config.json",)


def impressao_digital(raiz: Path) -> str:
    """O sha256 do código que a suite mede. Estável entre corridas."""
    h = hashlib.sha256()
    caminhos: list[Path] = []
    for pasta, padroes in IMPRESSAO:
        for padrao in padroes:
            caminhos += (raiz / pasta).glob(padrao)
    caminhos += [raiz / n for n in IMPRESSAO_FICHEIROS]
    for p in sorted(set(caminhos), key=lambda x: x.relative_to(raiz).as_posix()):
        if not p.is_file():
            continue
        h.update(p.relative_to(raiz).as_posix().encode())
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def _head(raiz: Path) -> str:
    try:
        r = subprocess.run(["git", "-C", str(raiz), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=30)
        return (r.stdout or "").strip() or "?"
    except (OSError, subprocess.SubprocessError):
        return "?"


def ficheiros_de_teste(raiz: Path) -> list[Path]:
    return sorted((raiz / "tests").glob("test_*.py"))


# ---------------------------------------------------------------------------
# Correr
# ---------------------------------------------------------------------------

def correr(raiz: Path, log=print) -> dict:
    """A suite, UM PROCESSO POR FICHEIRO, e o placar do que aconteceu.

    Um processo por ficheiro é a regra da casa e não é superstição: a bateria
    toda num processo só tem falhas de estado partilhado que passam sozinhas
    (`test_mesma_legend`, `test_nome_do_deck`), e um teste que só falha
    acompanhado esconde-se atrás de um verde.
    """
    todos = ficheiros_de_teste(raiz)
    maus: list[dict] = []
    testes = 0
    for f in todos:
        r = subprocess.run([sys.executable, "-X", "utf8", "-m", "unittest",
                            f"tests.{f.stem}"],
                           cwd=str(raiz), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        saida = (r.stderr or "") + (r.stdout or "")
        m = re.search(r"^Ran (\d+) test", saida, re.M)
        n = int(m.group(1)) if m else 0
        testes += n
        ok = r.returncode == 0 and m is not None
        log(f"{'ok' if ok else 'FALHOU':7} {f.name:36} {n:4} testes", flush=True)
        if not ok:
            maus.append({"ficheiro": f.name,
                         # `Ran` em falta é um ficheiro que nem chegou a correr
                         # (um import partido) — conta como vermelho na mesma.
                         "razao": "não correu (sem «Ran N tests»)" if not m else "falhou",
                         "cauda": saida[-3000:]})

    placar = {
        "quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "raiz": str(raiz),
        "head": _head(raiz),
        "impressao_digital": impressao_digital(raiz),
        "ficheiros": len(todos),
        "testes": testes,
        "a_falhar": len(maus),
        "maus": maus,
    }
    log(f"\nPLACAR: {placar['ficheiros']} ficheiros, {placar['testes']} testes, "
        f"{placar['a_falhar']} a falhar", flush=True)
    for m in maus:
        log(f"\n===== {m['ficheiro']} ({m['razao']})\n{m['cauda']}")
    return placar


def gravar(raiz: Path, placar: dict) -> Path:
    alvo = raiz / PLACAR
    alvo.write_text(json.dumps(placar, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    return alvo


# ---------------------------------------------------------------------------
# Ler — e é aqui que «ausente ou ilegível» vale VERMELHO
# ---------------------------------------------------------------------------

CAMPOS = ("quando", "head", "impressao_digital", "ficheiros", "testes", "a_falhar")


def ler(raiz: Path) -> dict | None:
    """O placar gravado, ou `None` se não houver ou não se perceber.

    Não levanta: quem chama trata o `None` como VERMELHO, que é o que ele é.
    Um placar meio escrito (a corrida morreu a meio) cai aqui e conta como
    ausente — que é melhor do que ler-lhe metade dos campos.
    """
    p = raiz / PLACAR
    try:
        dados = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(dados, dict) or any(c not in dados for c in CAMPOS):
        return None
    try:
        int(dados["ficheiros"]), int(dados["testes"]), int(dados["a_falhar"])
    except (TypeError, ValueError):
        return None
    return dados


def verde(raiz: Path) -> tuple[bool, str]:
    """Pode fazer-se o merge? A razão vem escrita, verde ou vermelha.

    As cinco maneiras de estar VERMELHO, por ordem de quem as apanha primeiro:

      1. não há placar             — ninguém correu a suite;
      2. o placar não se lê        — JSON partido, ou campos a menos;
      3. o código mudou desde ele  — a impressão digital não bate: um verde de
                                     antes da última alteração não autoriza
                                     esta. É esta que apanha o caso real de
                                     «corri a suite, depois emendei uma linha»;
      4. faltam ficheiros          — o placar mediu menos ficheiros do que os
                                     que estão em disco (um teste novo por
                                     correr, ou uma corrida interrompida);
      5. há testes a falhar        — o placar diz.
    """
    p = ler(raiz)
    if p is None:
        return False, (f"VERMELHO: não há placar legível em {raiz / PLACAR}. "
                       f"Corre `py -X utf8 tools/portao.py suite`.")
    agora = impressao_digital(raiz)
    if p["impressao_digital"] != agora:
        return False, ("VERMELHO: o código mudou depois de a suite ter corrido "
                       f"(placar {p['impressao_digital'][:12]}, agora "
                       f"{agora[:12]}). O placar é de outro código — volta a "
                       "correr a suite.")
    em_disco = len(ficheiros_de_teste(raiz))
    if int(p["ficheiros"]) != em_disco:
        return False, (f"VERMELHO: o placar mediu {p['ficheiros']} ficheiros e "
                       f"em disco estão {em_disco}. Corrida incompleta.")
    if int(p["a_falhar"]) > 0:
        nomes = ", ".join(m.get("ficheiro", "?") for m in p.get("maus", []))
        return False, (f"VERMELHO: {p['a_falhar']} ficheiro(s) a falhar"
                       + (f" ({nomes})" if nomes else "") + ".")
    return True, (f"VERDE: {p['ficheiros']} ficheiros, {p['testes']} testes, "
                  f"0 a falhar (corrida de {p['quando']}, HEAD {p['head'][:8]}).")
