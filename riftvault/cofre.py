"""Onde está o COFRE DE CONTAS, e como se abre (2026-10-31).

Desde este dia as passwords do riftvault não moram no `auth.db`: moram no cofre
partilhado com o mtgvault — o pacote `contas`, só stdlib, que vive FORA deste
repositório (`Desktop/Claude/01-Projetos/contas`). Aqui só se responde a três
perguntas: onde está o pacote, onde está a base, e como se abre. A lógica (o
travão, a fila do scrypt, a geração) é toda do `contas.cofre`; o `auth.py`
delega lá.

O IMPORT É PREGUIÇOSO, e é de propósito: o `riftvault build` importa o
`auth.py` (pelo `abrir.py`) e não pode passar a precisar do cofre para gerar o
site. Quem precisa do cofre chama `modulo()`, e só aí o `contas` entra.

ONDE ESTÁ A BASE, por ordem:

  1. `CONTAS_DB` — o que os testes e o executor da suite usam;
  2. se o riftvault está num ensaio ou numa pasta de dados à parte
     (`RIFTVAULT_AUTH`, `RIFTVAULT_DATA` ou `RIFTVAULT_ENSAIO`), ao lado do
     `auth.db` dele — senão um teste ou um ensaio que se esquecesse do
     `CONTAS_DB` escrevia no cofre a sério, que é onde estão as passwords de
     toda a gente;
  3. o cofre a sério, `<pasta do contas>/data/contas.db`.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

#: As variáveis que dizem «isto não é o riftvault a sério» (ver o topo).
_FORA_DO_REAL = ("RIFTVAULT_AUTH", "RIFTVAULT_DATA", "RIFTVAULT_ENSAIO")


def pasta_contas() -> Path:
    """A pasta do projecto `contas` (a que tem `contas/__init__.py` dentro).

    `CONTAS_DIR` manda. Sem ela sobe-se pelos antepassados da raiz do
    repositório e fica o primeiro `A/contas` ou `A/01-Projetos/contas` que seja
    mesmo o pacote: o checkout principal (`01-Projetos/Riftbound`) encontra-o
    ao lado, e um worktree (`03-Revisoes-e-Worktrees/wt/...`) encontra-o
    subindo até à `Desktop/Claude`.
    """
    escrita = os.environ.get("CONTAS_DIR", "").strip()
    if escrita:
        p = Path(escrita)
        if not (p / "contas" / "__init__.py").is_file():
            raise RuntimeError(
                f"o CONTAS_DIR aponta para {p}, mas lá não está o pacote "
                f"`contas` (falta {p / 'contas' / '__init__.py'}).")
        return p
    from . import config
    raiz = Path(config.ROOT).resolve()
    for antepassado in (raiz, *raiz.parents):
        for candidato in (antepassado / "contas",
                          antepassado / "01-Projetos" / "contas"):
            if (candidato / "contas" / "__init__.py").is_file():
                return candidato
    raise RuntimeError(
        "não encontrei o cofre de contas (o pacote `contas`) a subir a partir "
        f"de {raiz}: define CONTAS_DIR com a pasta dele.")


def caminho_db() -> Path:
    """A base do cofre que ESTE processo usa. Ver a ordem no topo."""
    escrito = os.environ.get("CONTAS_DB", "").strip()
    if escrito:
        return Path(escrito)
    if any(os.environ.get(v, "").strip() for v in _FORA_DO_REAL):
        from . import auth
        return auth.caminho().with_name("contas.db")
    return pasta_contas() / "data" / "contas.db"


def no_caminho() -> Path:
    """Põe a pasta do `contas` no `sys.path` (no FIM: não tapa nada daqui)."""
    pasta = pasta_contas()
    if str(pasta) not in sys.path:
        sys.path.append(str(pasta))
    return pasta


def modulo():
    """O `contas.cofre`, importado à primeira chamada.

    Confirma que o `contas` que entrou é o da pasta encontrada: com a pasta no
    FIM do `sys.path`, um outro `contas` mais à frente ganhava em silêncio — e
    um cofre trocado é o pior sítio para uma surpresa.
    """
    pasta = no_caminho()
    import contas
    import contas.cofre
    origem = Path(contas.__file__).resolve().parent.parent
    if origem != pasta.resolve():
        raise RuntimeError(
            f"o pacote `contas` importado vem de {origem}, não de {pasta}. "
            "Define CONTAS_DIR, ou tira o outro do caminho.")
    return contas.cofre


def abrir() -> sqlite3.Connection:
    """Uma ligação ao cofre (cria a base se for preciso). Fecha quem abre."""
    return modulo().abrir(caminho_db())
