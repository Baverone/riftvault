"""O botão de abrir a porta: `riftvault multi --verificar` e `--abrir`.

Ele não tem de perceber de DNS nem de OAuth para saber se isto está pronto. Faz
uma pergunta a cada coisa que tem de estar no sítio, responde em português, e
**recusa abrir enquanto faltar alguma** — não é um aviso que se possa ignorar
por distração às duas da manhã.

Os três passos que só ele pode dar (a aplicação no Discord ou no Google, a conta
na Cloudflare, e os nameservers do `baverone.com`) não se conseguem verificar
daqui: um exige as credenciais dele, os outros exigem rede e uma conta. Por isso
aparecem na lista como **passos dele**, com o que fazer, e o `docs/abrir-a-porta.md`
é o guia. O que se verifica daqui é tudo o que é código, config e ficheiros.

A VERIFICAÇÃO QUE INTERESSA MAIS, E PORQUÊ
    «A conta DELE está ligada a um fornecedor?» Se a porta abrir sem isso, a
    escrita passa a exigir sessão (é a regra da LAN, no `rotas_conta.py`) e ele
    fica do lado de fora da sua própria coleção até conseguir entrar. Por isso é
    essencial, e é a única que obriga a uma ida ao browser ANTES de abrir.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import auth, config

#: Os dois fornecedores a sério (o `local` é de ensaio e não tem segredos).
GOOGLE_D = auth.GOOGLE
DISCORD_D = auth.DISCORD


class NaoEstaPronto(Exception):
    """O `--abrir` recusou. A mensagem diz o que falta."""


def _essencial(nome: str, ok: bool, diz: str, como: str = "") -> dict:
    return {"nome": nome, "ok": ok, "essencial": True, "diz": diz, "como": como}


def _dele(nome: str, diz: str, como: str = "") -> dict:
    """Um passo dele: não se verifica daqui, e não trava o `--abrir` sozinho."""
    return {"nome": nome, "ok": None, "essencial": False, "diz": diz, "como": como}


def _texto_do_config() -> str:
    try:
        return config.CONFIG_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


def _versionado(caminho: Path) -> bool:
    """Este ficheiro vai para o Git? (Sem correr `git`: lê o `.gitignore`.)

    Só se responde ao que interessa aqui — as duas pastas/ficheiros novos — e
    procura-se a linha literal. É grosseiro de propósito: um `git check-ignore`
    obrigava a um subprocesso a cada verificação, e um falso «não está
    ignorado» é o lado seguro do erro (avisa a mais, nunca a menos).
    """
    try:
        linhas = {l.strip() for l in
                  (config.ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()}
    except OSError:
        return True
    try:
        rel = caminho.resolve().relative_to(config.ROOT.resolve()).as_posix()
    except ValueError:
        return False  # fora do repositório: não vai para o Git
    for linha in linhas:
        if not linha or linha.startswith("#"):
            continue
        # `data/users/` e `data/users` são a mesma regra; e uma pasta ignorada
        # ignora o que está lá dentro.
        padrao = linha.rstrip("/")
        if rel == padrao or rel.startswith(padrao + "/"):
            return False
    return True


def verificar(cfg: dict | None = None) -> dict:
    """O estado de tudo. Não escreve nada — dá para correr à vontade."""
    from . import multi, privacidade, utilizador

    cfg = cfg if cfg is not None else config.load()
    passos: list[dict] = []

    aberto = multi.aberto(cfg)
    ensaio = multi.ensaio()

    # 1. O fornecedor de identidade.
    disponiveis = auth.disponiveis(cfg)
    prontos = [p for p in disponiveis if p["pronto"] and p["nome"] != "local"]
    if prontos:
        passos.append(_essencial(
            "Entrar sem password",
            True,
            f"pronto: {', '.join(p['etiqueta'] for p in prontos)}."))
    else:
        falta = "; ".join(
            f"{p['etiqueta']} (falta {' e '.join(p['falta'])})"
            for p in disponiveis if p["nome"] != "local")
        passos.append(_essencial(
            "Entrar sem password", False,
            f"nenhum fornecedor configurado — {falta}.",
            "É o PASSO 1 do docs/abrir-a-porta.md: cria a aplicação no Discord "
            "(cinco minutos). O client_id vai para `auth.discord.client_id` do "
            "riftvault_config.json; o client_secret vai para o AMBIENTE, com "
            "`setx RIFTVAULT_DISCORD_SECRET \"o-segredo\"` numa consola nova — "
            "esse ficheiro está commitado num repositório público."))

    # 2. O endereço de volta.
    base = str((cfg.get("auth") or {}).get("base_url") or "").strip()
    if base.startswith("https://"):
        passos.append(_essencial("Endereço da app de edição", True, f"{base}."))
    elif base:
        passos.append(_essencial(
            "Endereço da app de edição", False,
            f"«{base}» não é https — de fora de casa tem de ser.",
            "Mete `auth.base_url` a «https://editar.baverone.com»."))
    else:
        passos.append(_essencial(
            "Endereço da app de edição", False,
            "`auth.base_url` está vazio: sem ele a volta do Discord não sabe "
            "para onde vir.",
            "Mete `auth.base_url` a «https://editar.baverone.com» — o mesmo "
            "endereço que escreveste no Discord."))

    # 3. O SEGREDO NÃO PODE ESTAR NUM FICHEIRO QUE VÁ PARA O GIT.
    #
    # Medido: `git ls-files riftvault_config.json` devolve-o — está COMMITADO, e
    # o repositório é público e empurrado de 30 em 30 minutos. Um `client_secret`
    # colado lá ia para o GitHub no push seguinte e não se despublica; teria de
    # ser revogado no Discord. Por isso o segredo vive no AMBIENTE, que é a regra
    # que o `.gitignore` já escreve para o CARDTRADER_TOKEN.
    no_ficheiro = [p for p in (GOOGLE_D, DISCORD_D)
                   if p.segredo_no_config(cfg)]
    if no_ficheiro and _versionado(config.CONFIG_PATH):
        quais = " e ".join(p.etiqueta for p in no_ficheiro)
        vars_ = " e ".join(p.var_segredo() for p in no_ficheiro)
        passos.append(_essencial(
            "O segredo não está no Git", False,
            f"o client_secret do {quais} está no {config.CONFIG_PATH.name}, "
            f"que VAI PARA O GITHUB (repositório público, push a cada 30 min).",
            f"Tira-o de lá e põe-no no ambiente: `setx {vars_} \"o-segredo\"` "
            f"numa consola nova. Se já fizeste push com ele lá dentro, faz "
            f"Reset Secret no Discord — um segredo publicado não se despublica."))
    elif no_ficheiro:
        passos.append(_essencial(
            "O segredo não está no Git", True,
            f"está no {config.CONFIG_PATH.name}, mas esse ficheiro não vai "
            f"para o Git."))
    else:
        passos.append(_essencial(
            "O segredo não está no Git", True,
            "o segredo vem do ambiente, como o CARDTRADER_TOKEN."
            if any(p.segredo(cfg) for p in (GOOGLE_D, DISCORD_D))
            else "ainda não há segredos para proteger."))

    # 4. As credenciais e as coleções dos amigos ficam fora do Git.
    fora = [p for p in (auth.caminho(), config.DATA_DIR / "users")
            if _versionado(p)]
    if fora:
        passos.append(_essencial(
            "Dados de terceiros fora do Git", False,
            "vão para o Git: " + ", ".join(p.name for p in fora) + ".",
            "Acrescenta-os ao .gitignore. O data/vault.db está num repositório "
            "PÚBLICO e é empurrado de 30 em 30 minutos; a coleção de um amigo "
            "lá dentro ficava publicada para sempre."))
    else:
        passos.append(_essencial(
            "Dados de terceiros fora do Git", True,
            "o auth.db e a pasta data/users/ estão no .gitignore."))

    # 5. A coleção de um amigo nasce privada.
    fechado = privacidade.OMISSAO == "nada"
    passos.append(_essencial(
        "Uma coleção nova nasce privada", fechado,
        f"o valor por omissão é «{privacidade.OMISSAO}»."
        + ("" if fechado else " Devia ser «nada»: uma página publicada indexa-se "
                              "e na prática não se despublica."),
        "" if fechado else "Põe o `privacidade.OMISSAO` em «nada»."))

    # 6. Ele consegue entrar. É a que evita o pior: abrir a porta com ele fora.
    passos.append(_ele_entra(cfg))

    # 7. Não se abre a porta em cima da base de ensaio.
    passos.append(_essencial(
        "Não estás em ensaio", not ensaio,
        "a correr contra os dados a sério." if not ensaio
        else "o RIFTVAULT_ENSAIO está ligado — isto é a base de brincar.",
        "" if not ensaio else "Fecha este terminal e abre outro sem o "
                              "RIFTVAULT_ENSAIO."))

    # 8. Os três passos dele que não se verificam daqui.
    passos.append(_dele(
        "A aplicação no Discord (ou Google)",
        "só tu podes criá-la — precisa da tua conta.",
        "PASSO 1 do docs/abrir-a-porta.md. Depois de colares as credenciais, "
        "este comando passa a dizer «pronto» na primeira linha."))
    passos.append(_dele(
        "A conta na Cloudflare",
        "só tu podes criá-la.",
        "PASSO 2 do docs/abrir-a-porta.md."))
    passos.append(_dele(
        "Os nameservers do baverone.com + o túnel",
        "só tu podes mudá-los, e é o passo com risco.",
        "PASSO 3 do docs/abrir-a-porta.md. ANTES de trocar, confirma que a "
        "Cloudflare já tem os cinco endereços (baverone.com, rift, mtg, baiak, "
        "tibia) e põe-nos em «DNS only» (nuvem cinzenta). O rift.baverone.com "
        "não pode cair."))

    faltam = [p for p in passos if p["essencial"] and not p["ok"]]
    return {
        "aberto": aberto,
        "ensaio": ensaio,
        "utilizadores": len(utilizador.todos()),
        "passos": passos,
        "faltam": faltam,
        "pode_abrir": not faltam,
    }


def _ele_entra(cfg: dict) -> dict:
    """A conta do dono está ligada a um fornecedor?"""
    from . import utilizador
    try:
        dono = utilizador.registo(1)
    except Exception:
        return _essencial(
            "Tu consegues entrar", False,
            "não encontrei o utilizador 1 (tu) no registo.",
            "Corre `riftvault stats` uma vez para a migração acontecer.")

    con = auth.abrir()
    try:
        ligadas = auth.identidades_de(con, 1)
    finally:
        con.close()

    if ligadas:
        quais = ", ".join(x["provedor"] for x in ligadas)
        return _essencial("Tu consegues entrar", True,
                          f"a tua conta está ligada ao {quais}.")
    return _essencial(
        "Tu consegues entrar", False,
        f"a tua conta ({dono.get('slug')}) ainda não está ligada a nenhum "
        f"fornecedor.",
        "Com a porta fechada isto não te incomoda — mas depois de abrires, "
        "escrever passa a exigir entrar, e ficavas de fora da tua própria "
        "coleção. Com o `riftvault serve` a correr, corre `riftvault multi "
        "--ligar` noutro terminal: ele dá-te um endereço para abrires no "
        "browser, entras com o Discord uma vez, e fica ligado. Depois volta a "
        "correr este comando.")


def ligar(provedor: str = "discord", porta: int = 8770,
          cfg: dict | None = None) -> dict:
    """Um endereço de uso único que liga a conta DELE a um fornecedor.

    É o caminho do primeiro utilizador, e existe porque o André **já existe**:
    é o utilizador 1, com o slug `baverone`. Na primeira entrada o riftvault não
    o reconhecia (não há identidade ligada) e oferecia-lhe o REGISTO — que lhe
    pedia um slug que ele não podia escolher, porque o dele já é dele. Ficava a
    olhar para um formulário sem saída.

    O código vem da CONSOLA de propósito: quem tem a consola do PC é o dono do
    PC, e isso prova mais do que qualquer verificação de endereço — o túnel da
    Cloudflare faz a internet inteira chegar ao Flask como `127.0.0.1`.

    E funciona com a porta FECHADA, que é o ponto: ele liga a conta antes de
    abrir, e por isso nunca se abre a porta com ele do lado de fora.
    """
    from . import utilizador

    cfg = cfg if cfg is not None else config.load()
    p = auth.provedor(provedor)
    p.exigir_configurado(cfg)
    dono = utilizador.registo(1)
    con = auth.abrir()
    try:
        token = auth.criar_convite(con, 1)
    finally:
        con.close()
    base = str((cfg.get("auth") or {}).get("base_url") or "").rstrip("/")
    local = f"http://localhost:{porta}"
    return {
        "provedor": p.nome,
        "etiqueta": p.etiqueta,
        "slug": dono.get("slug"),
        "minutos": auth.CONVITE_MINUTOS,
        # O de casa primeiro: é onde ele está quando corre isto.
        "url": f"{local}/entrar/{p.nome}?ligar={token}",
        "url_publico": (f"{base}/entrar/{p.nome}?ligar={token}"
                        if base else None),
    }


# --------------------------------------------------------------------------
# Texto
# --------------------------------------------------------------------------

_MARCA = {True: "  OK  ", False: "FALTA ", None: " TEU  "}


def texto(estado: dict | None = None, cfg: dict | None = None) -> str:
    est = estado if estado is not None else verificar(cfg)
    linhas = []
    porta = "ABERTA" if est["aberto"] else "FECHADA"
    linhas.append(f"A porta das contas está {porta}."
                  + (" (a correr em ENSAIO)" if est["ensaio"] else ""))
    linhas.append(f"Utilizadores: {est['utilizadores']}.")
    linhas.append("")
    for p in est["passos"]:
        linhas.append(f"[{_MARCA[p['ok']]}] {p['nome']}: {p['diz']}")
        if p["como"] and p["ok"] is not True:
            for pedaco in _dobrar(p["como"], 72):
                linhas.append(f"           {pedaco}")
    linhas.append("")
    if est["aberto"]:
        linhas.append("Já está aberta. Para fechar: riftvault multi --fechar")
    elif est["pode_abrir"]:
        linhas.append("Está tudo pronto do lado do código.")
        linhas.append("Falta só o que é teu (as linhas marcadas TEU), e depois:")
        linhas.append("    riftvault multi --abrir")
    else:
        n = len(est["faltam"])
        linhas.append(f"NÃO dá para abrir: falta{'' if n == 1 else 'm'} {n} "
                      f"coisa{'' if n == 1 else 's'} — "
                      + ", ".join(p["nome"] for p in est["faltam"]) + ".")
        linhas.append("O guia dos teus passos está em docs/abrir-a-porta.md.")
    return "\n".join(linhas)


def _dobrar(texto_: str, largura: int) -> list[str]:
    import textwrap
    return textwrap.wrap(texto_, largura) or [""]


# --------------------------------------------------------------------------
# «NÃO INDEXES ISTO» — nas páginas geradas de outros utilizadores
# --------------------------------------------------------------------------
#
# Uma página da coleção de um amigo indexada no Google antes de ele saber que
# existe é um erro que NÃO SE DESFAZ: pede-se a remoção, fica em cache, fica no
# Bing, fica no archive.org. Por isso enquanto o André não disser o contrário
# tudo o que não é a página DELE sai marcado, nas duas formas que os motores
# respeitam — a etiqueta na página e o ficheiro na raiz.
#
# O `noindex` na própria página é o que conta: um `robots.txt` só pede que não
# se RASTREIE, e uma página já conhecida por um link pode ser indexada sem ser
# rastreada. Os dois juntos fecham as duas portas.

META = ('<meta name="robots" content="noindex, nofollow, noarchive">\n'
        '  <meta name="googlebot" content="noindex, nofollow">')

ROBOTS = """# Enquanto as contas do riftvault não estiverem abertas ao público,
# nada daqui se indexa. Ver docs/abrir-a-porta.md.
User-agent: *
Disallow: /
"""


def marcar_html(html: str) -> str:
    """Põe a etiqueta de «não indexes» no `<head>`. Idempotente."""
    if 'name="robots"' in html:
        return html
    if "</head>" in html:
        return html.replace("</head>", f"  {META}\n</head>", 1)
    # Sem `<head>` (não acontece no nosso index.html, mas não se devolve uma
    # página sem a marca em silêncio).
    return f"{META}\n{html}"


def robots_txt() -> str:
    return ROBOTS


def publico_indexavel(modo: str, dono: bool, aberto: bool) -> bool:
    """Esta página pode ser indexada?

    Só a do DONO, só com a coleção mesmo pública, e só com a porta aberta. É a
    única combinação em que ele já decidiu tudo o que havia para decidir.
    """
    return bool(dono and aberto and modo == "tudo")


# --------------------------------------------------------------------------
# Abrir e fechar
# --------------------------------------------------------------------------


def abrir(forcar: bool = False, cfg: dict | None = None) -> dict:
    """Muda `multi.aberto` para `true`. Recusa se faltar alguma coisa."""
    est = verificar(cfg)
    if est["aberto"]:
        return {"aberto": True, "mudou": False, "estado": est}
    if est["faltam"] and not forcar:
        nomes = ", ".join(p["nome"] for p in est["faltam"])
        raise NaoEstaPronto(
            f"não abri: falta {nomes}. Corre `riftvault multi --verificar` para "
            f"ver o que fazer, ou `--abrir --forcar` se souberes o que estás a "
            f"fazer.")
    config.escrever_valor("multi", "aberto", True)
    return {"aberto": True, "mudou": True, "estado": verificar()}


def fechar(cfg: dict | None = None) -> dict:
    """Volta a fechar. Ninguém perde nada — só deixa de se entrar."""
    from . import multi
    if not multi.aberto(cfg if cfg is not None else config.load()):
        return {"aberto": False, "mudou": False}
    config.escrever_valor("multi", "aberto", False)
    return {"aberto": False, "mudou": True}
