"""PORTAS FECHADAS, e o sítio para partir coisas (2026-09-29).

André, 2026-09-29: *"Quero apenas apresentar quando tiver tudo"*.

Isto é o INTERRUPTOR ÚNICO dessa frase. Enquanto `multi.aberto` for `false` —
e é o que está — nada do multi-utilizador está acessível a ninguém:

  * não há registo, não há convites, e há **um** utilizador: ele;
  * o `build.py` publica **só o site dele, exactamente como está hoje**, sem
    um sinal de que isto existe (nada de «em breve», nada de link de login);
  * as páginas públicas dos outros podem gerar-se para uma pasta de prova e há
    teste que o mostra, mas **não vão para o `site/`**;
  * o túnel não se liga. Não há aqui cloudflared nenhum, nem instalado nem
    configurado — ver `docs/multi-utilizador.md` para o que falta quando for
    altura.

Está num sítio só de propósito: quando ele quiser abrir, muda-se **um valor**,
não dez condições espalhadas.

    "multi": { "aberto": false }

---------------------------------------------------------------------------
O SÍTIO PARA PARTIR COISAS (`RIFTVAULT_ENSAIO`)
---------------------------------------------------------------------------
Até aqui tudo se mede contra CÓPIAS do `data/` mas corre contra o `main` e o
8770 — que é a máquina dele, com a coleção dele. Com dados de terceiros lá
dentro isso deixa de chegar.

O ensaio é uma variável do AMBIENTE e **não uma chave do config**, e a razão é
concreta: uma chave de ensaio dentro de um ficheiro que vai para o Git está a
um merge de distância de ir para produção ligada. Uma variável de ambiente não
se commita.

    RIFTVAULT_ENSAIO=1

Com ela ligada (ver `config.py`):

  * `DATA_DIR`   passa a `data-ensaio/`  (e não ao `data/`, ver a seguir)
  * o config     passa a `riftvault_config-ensaio.json`
  * o `serve`    escuta em **127.0.0.1:8779**, nunca na 8770 nem em `0.0.0.0`

**A GARANTIA DE QUE O TÚNEL NUNCA APONTA PARA CÁ** é essa última linha, e é
por construção, não por disciplina: o túnel serve a **8770**, o ensaio recusa-
se a escutar nessa porta (`PortaDeProducao`) e só aceita a interface de
loopback — nada do ensaio está sequer na rede local. A 8779 já era a porta da
casa para servir uma cópia.

**E o ensaio recusa-se a usar o `data/` a sério** (`config` rebenta ao ser
importado). É o erro que isto existe para não deixar acontecer: correr uma
experiência com a coleção verdadeira por baixo.
"""

from __future__ import annotations

from . import config

#: a porta do modo edição a sério. O ensaio não pode escutar aqui.
PORTA_PRODUCAO = 8770
#: a porta do ensaio — a mesma que a casa já usava para servir uma cópia.
PORTA_ENSAIO = 8779


class SoEmEnsaio(RuntimeError):
    """Uma coisa que só pode existir na base de ensaio foi pedida a sério."""


class PortaDeProducao(RuntimeError):
    """O ensaio tentou escutar na porta que o túnel serve."""


def aberto(cfg: dict | None = None) -> bool:
    """As portas estão abertas? HOJE NÃO, e é o que ele mandou.

    É o único sítio onde esta pergunta se faz. Quem precisar dela — o registo,
    a autenticação, o `build.py`, a CLI — importa daqui e não escreve uma
    segunda leitura.
    """
    cfg = config.load() if cfg is None else cfg
    return bool((cfg.get("multi") or {}).get("aberto", False))


def ensaio() -> bool:
    """Estamos na base de ensaio? Vem do ambiente, nunca do config."""
    return config.ENSAIO


def exigir_ensaio(o_que: str) -> None:
    """Rebenta se `o_que` for pedido fora do ensaio.

    Para as coisas que existem só para partir: um fornecedor de autenticação
    de mentira, dados semeados, uma conta de teste. Chamar isto é mais barato
    do que confiar em que ninguém se engane.
    """
    if not ensaio():
        raise SoEmEnsaio(
            f"«{o_que}» só existe na base de ensaio. Liga `RIFTVAULT_ENSAIO=1` "
            f"(e aí os dados são o `data-ensaio/`, nunca o `data/`).")


def porta(pedida: int | None = None) -> int:
    """A porta do `serve`, já com a regra do ensaio aplicada."""
    if not ensaio():
        return PORTA_PRODUCAO if pedida is None else pedida
    if pedida in (None, PORTA_ENSAIO):
        return PORTA_ENSAIO
    if pedida == PORTA_PRODUCAO:
        raise PortaDeProducao(
            f"o ensaio não escuta na {PORTA_PRODUCAO} — é a porta que o túnel "
            f"serve, e é essa a garantia de que nada do ensaio chega lá fora. "
            f"Usa a {PORTA_ENSAIO}.")
    return pedida


def anfitriao(pedido: str | None = None) -> str:
    """O `host` do `serve`. Em ensaio é sempre o loopback.

    Nem a LAN: uma experiência não tem nada que estar ao alcance do telemóvel
    dele nem de mais ninguém.
    """
    if ensaio():
        return "127.0.0.1"
    return pedido or "0.0.0.0"


def estado(cfg: dict | None = None, con=None) -> dict:
    """O que o `riftvault multi --verificar` mostra. Não escreve nada."""
    cfg = config.load() if cfg is None else cfg
    d = {
        "aberto": aberto(cfg),
        "ensaio": ensaio(),
        "dados": str(config.DATA_DIR),
        "config": str(config.CONFIG_PATH),
        "porta": porta(),
        "anfitriao": anfitriao(),
        "tunel": False,   # não há cloudflared nesta fase, por ordem dele
    }
    if con is not None:
        from . import utilizador
        us = utilizador.todos(con)
        d["utilizadores"] = len(us)
        d["slugs"] = [u["slug"] for u in us]
    return d
