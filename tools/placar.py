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

DESDE 2026-09-30 A SUITE CORRE EM PARALELO, e o placar diz TRÊS números em vez
de um: quantos ficheiros passaram à primeira, quantos só passaram SOZINHOS (e
quais — são colisões entre processos, não defeitos) e quantos são vermelhos a
sério (e quais). Ver `correr` para a regra e a razão.

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
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# O tecto de trabalhadores não é o número de núcleos. Cada ficheiro é um
# processo que copia bases de dados para pastas temporárias e as abre: a partir
# de certo ponto o que limita é o disco, e apertar mais só faz subir as
# colisões — que é justamente o que se paga a repetir. Muda-se pelo ambiente
# (`RIFTVAULT_SUITE_TRABALHADORES`).
TECTO_TRABALHADORES = 8

# Para depurar: corre um de cada vez, como até 2026-09-30.
ENV_SERIE = "RIFTVAULT_SUITE_SERIE"
ENV_TRABALHADORES = "RIFTVAULT_SUITE_TRABALHADORES"

# O registo das colisões. Não vai para o Git (é desta máquina, como o placar) e
# não se trata de maneira especial: ao fim de umas semanas diz quais é que
# valia a pena arranjar.
COLISOES = "data/colisoes.log"


def trabalhadores() -> int:
    """Quantos ficheiros ao mesmo tempo. `1` é o modo série, para depurar."""
    if os.environ.get(ENV_SERIE, "").strip() not in ("", "0"):
        return 1
    escrito = os.environ.get(ENV_TRABALHADORES, "").strip()
    if escrito:
        try:
            return max(1, int(escrito))
        except ValueError:
            pass
    return max(1, min(os.cpu_count() or 1, TECTO_TRABALHADORES))


def _correr_um(raiz: Path, f: Path) -> dict:
    """Um ficheiro, um processo. Devolve o que aconteceu, sem julgar."""
    t0 = time.monotonic()
    r = subprocess.run([sys.executable, "-X", "utf8", "-m", "unittest",
                        f"tests.{f.stem}"],
                       cwd=str(raiz), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    saida = (r.stderr or "") + (r.stdout or "")
    m = re.search(r"^Ran (\d+) test", saida, re.M)
    return {
        "ficheiro": f.name,
        # Quanto demorou. Em paralelo o chão da corrida é o ficheiro MAIS LENTO
        # — 68 ficheiros rápidos não compensam um que leve dez minutos —, por
        # isso o placar diz quais são os cinco maiores: é onde vale a pena
        # mexer se isto voltar a incomodar.
        "segundos": round(time.monotonic() - t0, 1),
        "testes": int(m.group(1)) if m else 0,
        # `Ran` em falta é um ficheiro que nem chegou a correr (um import
        # partido) — conta como vermelho na mesma, e a razão di-lo.
        "ok": r.returncode == 0 and m is not None,
        "razao": "não correu (sem «Ran N tests»)" if not m else "falhou",
        "cauda": saida[-3000:],
    }


def correr(raiz: Path, log=print) -> dict:
    """A suite, UM PROCESSO POR FICHEIRO, em PARALELO e com REPETIÇÃO SOZINHO.

    UM PROCESSO POR FICHEIRO é a regra da casa e não é superstição: a bateria
    toda num processo só tem falhas de estado partilhado que passam sozinhas
    (`test_mesma_legend`, `test_nome_do_deck`), e um teste que só falha
    acompanhado esconde-se atrás de um verde. Isso não mudou.

    O QUE MUDOU A 2026-09-30 é a ORDEM. Correr os 69 ficheiros um a seguir ao
    outro demorava **681 segundos** medidos, e uma ordem corre a suite várias
    vezes: era o maior pedaço de tempo morto do ciclo. Agora:

      1. corre-se TUDO em paralelo;
      2. cada ficheiro que fique vermelho REPETE-SE SOZINHO, um de cada vez,
         sem mais nada a correr;
      3. quem passa à segunda era COLISÃO — conta verde, e fica registado;
         quem falha as duas é vermelho a sério.

    POR QUE É QUE ISTO NÃO PERDE RIGOR. A repetição sozinha é EXACTAMENTE a
    condição que a suite antiga media — um ficheiro, um processo, nada ao lado
    —, ficheiro a ficheiro. Um vermelho a sério falha nas duas e dá vermelho
    como antes; um que só falhe acompanhado passa a APARECER (a suite antiga
    nunca os corria juntos e por isso nunca o via). Ganha-se informação; não se
    troca uma pergunta por outra mais fraca.

    E POR QUE É QUE NÃO HÁ UMA LISTA DOS «MAUS». Uma lista escrita à mão
    envelhece: o ficheiro que se arranja continua lá a ser desculpado, e o que
    passa a colidir amanhã não está. Pior — uma lista errada dá VERMELHOS
    FALSOS, e um vermelho falso é a pior coisa que uma suite faz, porque ensina
    a ignorá-la. Aqui quem decide é a própria corrida, e só os vermelhos pagam
    o preço da lentidão.
    """
    inicio = time.monotonic()
    # A impressao digital tira-se dos DOIS lados do ciclo (2026-10-01). A do
    # fim, sozinha, so apanhava «corri e depois emendei»; uma alteracao feita A
    # MEIO deixava os ficheiros ja corridos a medir bytes antigos e o placar a
    # dizer os novos — verde a descrever codigo que nunca correu inteiro. Em
    # paralelo isto conta AINDA MAIS: os 79 ficheiros arrancam quase todos ao
    # mesmo tempo, por isso uma emenda a meio apanha-os em estados diferentes.
    antes = impressao_digital(raiz)
    todos = ficheiros_de_teste(raiz)
    n_trab = trabalhadores()
    log(f"suite: {len(todos)} ficheiros, {n_trab} ao mesmo tempo"
        f"{' (MODO SÉRIE)' if n_trab == 1 else ''}", flush=True)

    # 1ª volta, em paralelo. As threads só esperam por subprocessos, por isso o
    # GIL não estorva. Escreve-se cada linha À MEDIDA que ela acaba (e não a
    # lista no fim): quem está a olhar para o ecrã tem de ver que aquilo anda.
    por_ficheiro: dict[str, dict] = {}

    def _anotar(r: dict) -> None:
        por_ficheiro[r["ficheiro"]] = r
        log(f"{'ok' if r['ok'] else 'FALHOU':7} {r['ficheiro']:36} "
            f"{r['testes']:4} testes {r.get('segundos', 0):7.1f}s", flush=True)

    if n_trab == 1:
        for f in todos:
            _anotar(_correr_um(raiz, f))
    else:
        with ThreadPoolExecutor(max_workers=n_trab) as pool:
            for fut in as_completed([pool.submit(_correr_um, raiz, f)
                                     for f in todos]):
                _anotar(fut.result())

    # 2ª volta: cada vermelho SOZINHO, um de cada vez. É a condição da suite
    # antiga, e é ela que distingue colisão de defeito.
    a_repetir = [f for f in todos if not por_ficheiro[f.name]["ok"]]
    colidiram: list[dict] = []
    maus: list[dict] = []
    if a_repetir:
        log(f"\n{len(a_repetir)} a repetir SOZINHO (um de cada vez)...", flush=True)
    for f in a_repetir:
        r = _correr_um(raiz, f)
        # A palavra final é a da corrida sozinha, incluindo a contagem: é a
        # que vale, porque é a que mede o ficheiro sem ninguém ao lado.
        por_ficheiro[f.name] = r
        if r["ok"]:
            log(f"{'colidiu':7} {f.name:36} {r['testes']:4} testes "
                f"(passa sozinho)", flush=True)
            colidiram.append({"ficheiro": f.name, "testes": r["testes"]})
        else:
            log(f"{'VERMELHO':7} {f.name:36} ({r['razao']})", flush=True)
            maus.append({"ficheiro": f.name, "razao": r["razao"],
                         "cauda": r["cauda"]})

    testes = sum(r["testes"] for r in por_ficheiro.values())
    mais_lentos = [{"ficheiro": r["ficheiro"], "segundos": r.get("segundos", 0)}
                   for r in sorted(por_ficheiro.values(),
                                   key=lambda r: -r.get("segundos", 0))[:5]]
    depois = impressao_digital(raiz)
    placar = {
        "quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "segundos": round(time.monotonic() - inicio, 1),
        # O chão de uma corrida em paralelo é o ficheiro mais lento, não a média.
        "mais_lentos": mais_lentos,
        "raiz": str(raiz),
        "head": _head(raiz),
        # A do FIM e a que a `verde()` compara com o disco — e ela que apanha
        # uma emenda feita depois da corrida. A do INICIO esta ca para se poder
        # perguntar se o codigo se manteve o mesmo do principio ao fim.
        "impressao_digital": depois,
        "impressao_no_inicio": antes,
        "mexeram_a_meio": antes != depois,
        "ficheiros": len(todos),
        "testes": testes,
        # FICHEIRO A FICHEIRO: nome -> {testes, ok, segundos}. É o que deixa
        # comparar duas corridas sem acreditar nos totais — um ficheiro a correr
        # menos testes e outro a correr mais davam a MESMA soma, e foi assim que
        # se provou que o paralelo diz o mesmo que a série (2026-10-02). Sem as
        # caudas, que são para o ecrã e ocupam 3 KB cada.
        "por_ficheiro": {n: {"testes": r["testes"], "ok": r["ok"],
                             "segundos": r.get("segundos", 0)}
                         for n, r in sorted(por_ficheiro.items())},
        # `a_falhar` são só os VERMELHOS A SÉRIO — é o campo que o portão lê, e
        # o significado não mudou: «isto não se pode integrar».
        "a_falhar": len(maus),
        "maus": maus,
        # Os três números, para quem lê.
        "verdes_a_primeira": len(todos) - len(a_repetir),
        "colidiram": colidiram,
        "modo": "série" if n_trab == 1 else "paralelo",
        "trabalhadores": n_trab,
    }
    if colidiram:
        _registar_colisoes(raiz, placar)
    log(f"\nPLACAR: {placar['ficheiros']} ficheiros, {placar['testes']} testes, "
        f"{placar['segundos']:.0f}s ({placar['modo']}, {n_trab} ao mesmo tempo)"
        f"\n  mais lentos: "
        + " · ".join(f"{r['ficheiro']} {r['segundos']:.0f}s" for r in mais_lentos)
        + f"\n  {placar['verdes_a_primeira']} verdes à primeira"
        f"\n  {len(colidiram)} só passaram sozinhos"
        + (f" ({', '.join(c['ficheiro'] for c in colidiram)})" if colidiram else "")
        + f"\n  {placar['a_falhar']} vermelhos a sério"
        + (f" ({', '.join(m['ficheiro'] for m in maus)})" if maus else ""),
        flush=True)
    if placar["mexeram_a_meio"]:
        log("AVISO: o codigo mudou DURANTE a corrida — este placar nao vale "
            f"({antes[:12]} no inicio, {depois[:12]} no fim). Volta a correr.",
            flush=True)
    for m in maus:
        log(f"\n===== {m['ficheiro']} ({m['razao']})\n{m['cauda']}")
    return placar


def _registar_colisoes(raiz: Path, placar: dict) -> None:
    """Uma linha por ficheiro que só passou sozinho, com a data.

    Sem tratamento especial nenhum — é só memória. Ao fim de umas semanas isto
    diz quais é que colidem mesmo e valia a pena arranjar, em vez de se
    adivinhar.
    """
    alvo = raiz / COLISOES
    try:
        alvo.parent.mkdir(parents=True, exist_ok=True)
        with alvo.open("a", encoding="utf-8") as fh:
            for c in placar["colidiram"]:
                fh.write(f"{placar['quando']}\t{c['ficheiro']}\t"
                         f"{c['testes']}\t{placar['trabalhadores']}\t"
                         f"{placar['head'][:8]}\n")
    except OSError:
        pass  # o registo é conveniência; nunca é motivo para a suite falhar


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
      5. o código mudou A MEIO     — a impressão do princípio não bate com a do
                                     fim, portanto parte da suite correu contra
                                     bytes que já não existem. É a que a de
                                     cima não apanha, porque no fim já está
                                     tudo coerente (2026-10-01);
      6. há testes a falhar        — o placar diz, e desde 2026-09-30 «a
                                     falhar» são os VERMELHOS A SÉRIO: os que
                                     falharam em paralelo E sozinhos. Um que
                                     passe sozinho era colisão, conta verde e
                                     fica dito (e no `data/colisoes.log`).
    """
    p = ler(raiz)
    if p is None:
        return False, (f"VERMELHO: não há placar legível em {raiz / PLACAR}. "
                       f"Corre `py -X utf8 tools/portao.py suite`.")
    if "impressao_no_inicio" not in p:
        return False, ("VERMELHO: este placar é de antes de 01/10/2026 e não "
                       "diz se o código se manteve o mesmo durante a corrida. "
                       "Volta a correr a suite.")
    if p.get("mexeram_a_meio") or p["impressao_no_inicio"] != p["impressao_digital"]:
        return False, ("VERMELHO: o código mudou A MEIO da corrida "
                       f"({str(p['impressao_no_inicio'])[:12]} no início, "
                       f"{str(p['impressao_digital'])[:12]} no fim). Parte da "
                       "suite mediu bytes que já não existem — volta a correr.")
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
    colidiram = p.get("colidiram") or []
    extra = ""
    if colidiram:
        # Dizer QUAIS, e não só quantos: um verde que esconde «três passaram à
        # segunda» é um verde em que se confia de menos.
        extra = (f", {len(colidiram)} só passaram sozinhos ("
                 + ", ".join(c.get("ficheiro", "?") for c in colidiram) + ")")
    return True, (f"VERDE: {p['ficheiros']} ficheiros, {p['testes']} testes, "
                  f"0 vermelhos{extra} (corrida de {p['quando']}, "
                  f"modo {p.get('modo', '?')}, HEAD {p['head'][:8]}).")
