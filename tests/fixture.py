"""Catálogo e coleção mínimos, construídos em disco, sem rede.

Os testes não podem tocar no `data/vault.db` do André nem falar com a
RiftScribe. Aqui monta-se um catálogo de brincar com o mesmo formato do real —
o que interessa é a forma (impressões, cartas lógicas, grupos), não o tamanho.
"""

from __future__ import annotations

import atexit
import importlib
import json
import os
import shutil
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


# --- UMA PASTA TEMPORÁRIA POR PROCESSO (2026-10-15) --------------------------
#
# Os testes escreviam configs no `%TEMP%` com NOME FIXO
# (`riftvault-voltar-1.json`, `riftvault-runas-alt-fora.json`, …). Em série
# isso não se vê; com o portão a 16 trabalhadores, e com duas baterias a correr
# ao mesmo tempo em worktrees diferentes, dois processos truncavam e
# reescreviam o MESMO ficheiro — e o `test_voltar_1` até o reescreve com outro
# conteúdo a meio de um teste. Quem o lia no instante errado lia o config do
# outro, ou um JSON a meio. Sozinho passava; a meias com outra bateria, não.
#
# A cura é a de sempre: cada processo tem a SUA pasta (`tempfile.mkdtemp`, que
# garante um nome que mais ninguém tem, mesmo entre processos que partilhem o
# `%TEMP%`), e todo o ficheiro temporário de nome escolhido pelo teste vive lá
# dentro. O nome dentro da pasta pode ser fixo à vontade: a pasta é que é
# única. Apaga-se à saída do processo (`atexit`).
#
# Porquê `mkdtemp` e não `NamedTemporaryFile`: os testes precisam de um CAMINHO
# que se escreve, se lê e se reescreve (e que se passa ao `riftvault` por uma
# variável de ambiente); no Windows um `NamedTemporaryFile` aberto não se deixa
# abrir uma segunda vez, e um com `delete=False` volta a deixar lixo. Uma pasta
# por processo dá as duas coisas: nomes legíveis e uma limpeza só.
_PASTA_DO_PROCESSO: Path | None = None


def pasta_do_processo() -> Path:
    """A pasta temporária DESTE processo — criada uma vez, apagada à saída."""
    global _PASTA_DO_PROCESSO
    if _PASTA_DO_PROCESSO is None:
        _PASTA_DO_PROCESSO = Path(tempfile.mkdtemp(prefix="riftvault-tests-"))
        atexit.register(shutil.rmtree, _PASTA_DO_PROCESSO, True)
    return _PASTA_DO_PROCESSO


def ficheiro_temporario(nome: str) -> Path:
    """Um caminho para `nome` que só ESTE processo usa.

    Não cria o ficheiro: quem chama escreve-o (ou, no `SEM_CONFIG`, conta com
    que ele não exista)."""
    return pasta_do_processo() / nome


#: O config que «não existe» — para o `riftvault` medir com os DEFAULTS.
#: Era `%TEMP%/riftvault-nao-existe.json`, um caminho PARTILHADO por mais de
#: quarenta ficheiros de teste e por todos os processos. Só valia enquanto
#: ninguém o criasse — e o `config.escrever_valor` CRIA-O quando se escreve no
#: config com ele apontado (é o que faz o «Montar» de um deck). Um teste desses
#: num processo deixava os outros todos, até na corrida seguinte, a ler um
#: config que não era o deles. Agora é por processo.
SEM_CONFIG = str(ficheiro_temporario("riftvault-nao-existe.json"))


def config_decks_sem_alt_art(caso=None) -> Path:
    """Um config temporário com a regra dos decks DE HOJE, escrita por extenso.

    Nasceu a 2026-09-16 para desligar o «o deck joga em Alt Art» (a cópia
    base deixava de servir o deck e o Defy do catálogo destes testes tem uma
    alt art). A 2026-09-17 o André voltou atrás — os decks jogam a base, só a
    Legend e o Champion jogam uma versão especial (`test_voltar_1.py`) — e a
    regra que os testes da partilha de 2026-09-11 (`test_partilha_compra`,
    `test_binders`, `test_encomendas`) descrevem passou a ser a de sempre.
    Fica a escrever os defaults do bloco `decks` para esses testes não
    dependerem do ficheiro real. Chamar ANTES do `Vault`, que é quem recarrega
    o `config`. Com `caso` (o TestCase) a variável é limpa no fim do teste,
    para o ficheiro seguinte da suite voltar a ler o config real.

    O NOME LEVA O PID, e é por isto (2026-10-02, a suite em paralelo). O nome
    era fixo (`riftvault-decks-sem-alt-art.json`) e ONZE ficheiros de teste
    chamam isto — em série dava no mesmo, porque o conteúdo é sempre o mesmo e
    só há um processo de cada vez; em paralelo são onze processos a truncar e a
    reescrever o MESMO ficheiro do `%TEMP%`, e quem o fosse ler no instante
    errado lia-o a meio (`JSONDecodeError`) ou vazio. Um vermelho falso desses
    aparece uma vez em cada tantas corridas e não se reproduz, que é a pior
    espécie. O PID dá um ficheiro por processo e não muda nada do que o teste
    mede — o conteúdo é igual ao que sempre foi.

    Desde 2026-10-15 vive na pasta do processo (`ficheiro_temporario`), que dá
    o mesmo isolamento e ainda se apaga no fim — os ficheiros com PID ficavam
    no `%TEMP%` para sempre (eram 335 nesse dia).
    """
    caminho = ficheiro_temporario("riftvault-decks-sem-alt-art.json")
    # `so_base: false` (2026-09-21): a omissão passou a ser só versões base, a
    # Legend e o Champion incluídos; os testes que chamam isto descrevem a
    # regra de 2026-09-17 e desligam-na de propósito.
    caminho.write_text(json.dumps({"decks": {
        "so_base": False,
        "so_normais_excepto": ["legend", "champion"],
        "versoes_especiais": ["a", "overnumbered", "promo"]}}), encoding="utf-8")
    os.environ["RIFTVAULT_CONFIG"] = str(caminho)
    if caso is not None:
        caso.addCleanup(lambda: os.environ.pop("RIFTVAULT_CONFIG", None))
    return caminho


class Vault:
    """Um riftvault descartável: pastas próprias e módulos reconfigurados.

    O `config` guarda os caminhos em constantes de módulo lidas na importação,
    por isso não chega pôr as variáveis de ambiente — é preciso reimportá-lo.
    """

    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="riftvault-test-"))
        self.data = self.root / "data"
        self.decks_dir = self.root / "decks"
        self.data.mkdir()
        self.decks_dir.mkdir()

        os.environ["RIFTVAULT_DATA"] = str(self.data)
        os.environ["RIFTVAULT_DECKS"] = str(self.decks_dir)
        os.environ["RIFTVAULT_DB"] = str(self.data / "vault.db")
        os.environ["RIFTVAULT_CATALOG"] = str(self.data / "catalog.db")
        os.environ["RIFTVAULT_PRICES"] = str(self.data / "prices.db")

        from riftvault import config
        importlib.reload(config)
        config.load.cache_clear()
        self.config = config

    def close(self):
        for var in ("RIFTVAULT_DATA", "RIFTVAULT_DECKS", "RIFTVAULT_DB",
                    "RIFTVAULT_CATALOG", "RIFTVAULT_PRICES"):
            os.environ.pop(var, None)
        from riftvault import config
        importlib.reload(config)
        config.load.cache_clear()
        shutil.rmtree(self.root, ignore_errors=True)

    # -- construção do catálogo ------------------------------------------

    def connect(self):
        from riftvault import db
        return db.connect()

    def add_printing(self, con, printing_id, set_id, cn, name, *, variant="",
                     kind="base", card_type="Unit", api_sort=None, rarity="common",
                     domains=("Order",), size=None, lane="main", codigo=None,
                     base_rarity=None):
        # `size` é o TAMANHO NOMINAL da edição, e vai para o denominador do
        # código impresso (`TST-300/298`), como a API o dá. Só quem testa as
        # sobrenumeradas precisa dele — ver `metrics.e_overnumbered`; sem ele o
        # código sai sem denominador, como sempre saiu.
        #
        # O `codigo` escreve-se à mão quando a série não segue a numeração da
        # edição: as promos são `VEN-SP4/006` (a 4 de 6), não `VEN-004sp4`.
        if codigo is None:
            codigo = f"{set_id}-{cn:03d}{variant}" + (f"/{size:03d}" if size else "")
        # A `lane` é o prefixo alfabético do variante (ARMADILHA 1 do CLAUDE.md):
        # é ela que impede o `VEN-SP4` e o `VEN-004` de caírem no mesmo grupo por
        # partilharem o número. Por omissão `main`, que é o caso de quase tudo.
        # `domains=None` deixa a coluna a NULL, que é o que o schema permite.
        con.execute(
            "INSERT INTO catalog.printings (printing_id, set_id, collector_number, "
            "variant, lane, group_key, variant_kind, variant_label, card_key, "
            "public_code, name, rarity, base_rarity, type, orientation, is_banned, "
            "is_token, api_sort, domains_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,0,?,?)",
            (printing_id, set_id, cn, variant, lane, f"{set_id}|{cn}|{lane}", kind,
             kind, name.strip().casefold(), codigo, name,
             # A raridade IMPRESSA e a da BASE são a mesma na esmagadora
             # maioria; separam-se nas seis runas de arte alternativa do OGN
             # (base `common`, impressa `showcase`), como no catálogo real.
             rarity, base_rarity or rarity, card_type, "portrait",
             api_sort if api_sort is not None else cn,
             None if domains is None else json.dumps(list(domains))))

    def rebuild(self, con):
        """Deriva `cards` e os aliases, como o `sync` faz no fim."""
        from riftvault import catalog
        catalog.rebuild_cards(con)
        catalog.rebuild_aliases(con)

    def write_deck(self, slug: str, texto: str):
        (self.decks_dir / f"{slug}.txt").write_text(texto, encoding="utf-8")


def catalogo_simples(v: Vault):
    """Duas Units e um Legend numa edição, com a coleção já lá dentro."""
    con = v.connect()
    v.add_printing(con, "tst-001-100", "TST", 1, "Defy")
    v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer")
    v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                   card_type="Legend")
    v.rebuild(con)
    from riftvault import collection
    collection.adjust(con, "tst-001-100", 3, source="test")
    collection.adjust(con, "tst-002-100", 3, source="test")
    collection.adjust(con, "tst-003-100", 1, source="test")
    con.close()
