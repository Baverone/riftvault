"""O botão de abrir a porta: `riftvault multi --verificar` e `--abrir`.

Ele não tem de perceber de DNS nem de OAuth para saber se isto está pronto. Faz
uma pergunta a cada coisa que tem de estar no sítio, responde em português, e
**recusa abrir enquanto faltar alguma** — não é um aviso que se possa ignorar
por distração às duas da manhã.

**ERAM TRÊS PASSOS DELE, PASSARAM A DOIS a 2026-09-30 E A UM MEDIDO a
2026-10-02.** O primeiro era criar a aplicação no Discord, e desapareceu quando
a entrada passou a ser por password. Ficavam dois — a conta na Cloudflare e os
nameservers do `baverone.com` + o túnel — marcados `[TEU]`, «só tu podes»,
como se faltassem fazer.

**ESTAVAM FEITOS, e eram verificáveis.** O varrimento de 2026-10-01 (§3) mediu
no mesmo minuto o serviço `Cloudflared` a correr e o `editar.baverone.com` a
responder 200 com nove sinais de «fora» — e a checklist mandava-o lá outra vez,
ao único passo com risco declarado («o rift.baverone.com não pode cair»). Uma
checklist que presume em vez de medir ensina a ignorar a checklist, e a seguir
ignora-se o passo que importava.

Hoje é UM passo que PERGUNTA ao endereço público (`_tunel` +
`perguntar_ao_tunel`), e a cadeia inteira prova-se de uma vez. **Sem medição a
resposta é «não sei», nunca «falta»** — é a diferença entre não medir e medir
mal. O `docs/abrir-a-porta.md` continua a ser o guia dos passos dele, e o passo
aponta-lhe quando dá vermelho.

A VERIFICAÇÃO QUE INTERESSA MAIS, E PORQUÊ
    «ELE tem password definida?» Se a porta abrir sem isso, a escrita passa a
    exigir sessão (é a regra da LAN, no `rotas_conta.py`) e ele fica do lado de
    fora da sua própria coleção. É a única que o obriga a fazer uma coisa ANTES
    de abrir — e desde 2026-09-30, à tarde, essa coisa é UM comando na consola,
    que resolve tudo de uma vez e sem browser:

        riftvault conta baverone --definir-password

    Era o `--nova-password`, que dá uma TEMPORÁRIA — e a temporária não conta
    como pronto. Havia aí um beco: a temporária trocava-se só no site, e o site
    escondia a entrada enquanto a porta estivesse fechada. Ver `cmd_conta` e o
    topo do `rotas_conta.py`.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from . import auth, config

#: Quanto tempo se espera pelo endereço público. Curto de propósito: isto é uma
#: checklist que ele corre na consola, não um teste de disponibilidade. Se o
#: túnel estiver vivo responde em ~300 ms (medido a 2026-10-01 e 02/10).
ESPERA_DO_TUNEL = 5.0

#: ASCII puro. É a regra desta casa desde 2026-08-31: um User-Agent com acentos
#: dá 403 no CardTrader, e nunca se finge ser um browser.
USER_AGENT = "riftvault/1.0 (verificacao da propria app; +github)"


def perguntar_ao_tunel(base: str, espera: float = ESPERA_DO_TUNEL) -> dict:
    """Pergunta à app, PELO ENDEREÇO PÚBLICO, se o pedido lhe chegou de fora.

    É a medição do passo dele, e **não há sinal melhor do que este**: se a
    própria app responde num pedido que saiu pela internet e diz que o viu
    chegar de fora, então a conta na Cloudflare existe, os nameservers estão
    trocados, o `cloudflared` corre e entrega neste Flask. Os quatro de uma vez,
    de ponta a ponta.

    PORQUE É QUE SE PERGUNTA AO `/api/conta.json`, e não a outra rota: é a única
    que diz `origem` e `sinais` — a leitura que o `origem.py` fez do pedido —, e
    é das poucas que passa **sem sessão vindo de fora** (`rotas_conta.
    DE_FORA_SEM_SESSAO`). Qualquer outra responde 401, e aí não se distinguia
    «o túnel está em baixo» de «o túnel está vivo e pediu-me password».

    DAQUI NÃO SE VEEM OS CABEÇALHOS que a Cloudflare acrescenta — eles são
    postos no caminho de ida. Por isso não se tenta adivinhá-los: lê-se o que o
    SERVIDOR diz que viu, que é a mesma pergunta respondida por quem tem a
    resposta.

    Nunca levanta. Devolve sempre um dicionário, e `respondeu: False` com a
    razão escrita é um resultado — é o «não sei» de quem não tem rede.
    """
    url = base.rstrip("/") + "/api/conta.json"
    try:
        pedido = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(pedido, timeout=espera) as resp:
            codigo = getattr(resp, "status", None) or resp.getcode()
            corpo = resp.read(64 * 1024)
    except urllib.error.HTTPError as e:
        # Respondeu, mas não como deve: um 502/530 da Cloudflare é o túnel em
        # baixo com o DNS a funcionar, e isso é informação, não falta de rede.
        return {"respondeu": True, "codigo": e.code, "origem": None,
                "sinais": [], "url": url}
    except Exception as e:
        return {"respondeu": False, "url": url,
                "erro": f"{type(e).__name__}: {e}"}
    try:
        dados = json.loads(corpo.decode("utf-8", "replace"))
    except Exception:
        return {"respondeu": True, "codigo": codigo, "origem": None,
                "sinais": [], "url": url,
                "erro": "respondeu, mas o que veio não é o riftvault"}
    return {"respondeu": True, "codigo": codigo, "url": url,
            "origem": dados.get("origem"),
            "sinais": list(dados.get("sinais") or [])}

#: Os dois fornecedores a sério (o `local` é de ensaio e não tem segredos).
GOOGLE_D = auth.GOOGLE
DISCORD_D = auth.DISCORD


class NaoEstaPronto(Exception):
    """O `--abrir` recusou. A mensagem diz o que falta."""


def _essencial(nome: str, ok: bool, diz: str, como: str = "") -> dict:
    return {"nome": nome, "ok": ok, "essencial": True, "diz": diz, "como": como}


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


def verificar(cfg: dict | None = None, medir=None) -> dict:
    """O estado de tudo. Não escreve nada — dá para correr à vontade.

    O `medir` é quem pergunta ao endereço público (`perguntar_ao_tunel`), e por
    omissão é **`None`: não se mede e diz-se que não se mediu**. É uma escolha, e
    aqui está a razão: esta função é chamada pelo `--abrir`, por testes e por
    quem quiser, e uma biblioteca que vá à rede nas costas de quem a chama é uma
    biblioteca que fica a ver se um `urlopen` estoura o prazo. Quem pede a
    medição é o comando que um humano corre — o `riftvault multi --verificar`
    passa o `perguntar_ao_tunel` —, e aí a resposta é medida de ponta a ponta.

    **Sem medição a resposta é «não sei», nunca «falta».** É a diferença entre
    não medir e medir mal, e era medir mal que estava aqui até 2026-10-02.
    """
    from . import multi, privacidade, utilizador

    cfg = cfg if cfg is not None else config.load()
    passos: list[dict] = []

    aberto = multi.aberto(cfg)
    ensaio = multi.ensaio()

    # 1. HÁ POR ONDE ENTRAR (2026-09-30).
    #
    # Isto já não exige um fornecedor de OAuth. A entrada por PASSWORD não
    # precisa de configurar nada — está no código e funciona —, por isso este
    # passo é sempre verde e existe para DIZER o que está ligado: a password
    # sempre, e o Discord/Google só se ele os tiver configurado um dia.
    #
    # É um passo à parte do «tu consegues entrar» de propósito: este responde a
    # «o site tem uma porta?» e o outro a «e tu tens a chave?». Pode haver porta
    # e ele não ter chave — foi o caso durante todo o dia 29/09.
    extra = [p["etiqueta"] for p in auth.disponiveis(cfg)
             if p["pronto"] and p["nome"] != "local"]
    passos.append(_essencial(
        "Há por onde entrar", True,
        "password (sempre disponível)"
        + (f" e, a mais, {' e '.join(extra)}." if extra else ".")))

    # 2. O endereço que ele dá aos amigos.
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
            "`auth.base_url` está vazio: é o endereço que aparece no que "
            "mandas a um amigo quando lhe crias a conta.",
            "Mete `auth.base_url` a «https://editar.baverone.com» — o mesmo "
            "endereço que o túnel serve."))

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

    # 8. O CAMINHO DE FORA — e isto MEDE-SE desde 2026-10-02.
    #
    # Eram DOIS passos marcados `[TEU]` («a conta na Cloudflare» e «os
    # nameservers + o túnel»), e os dois estavam FEITOS desde 29/09: o
    # varrimento de 2026-10-01 (§3) mediu o serviço a correr e o
    # `editar.baverone.com` a responder 200 com nove sinais de «fora». Uma
    # checklist que manda repetir o passo que ele já fez — e que é o ÚNICO com
    # risco declarado, «o rift.baverone.com não pode cair» — ensina a ignorar a
    # checklist, e a seguir ignora-se o passo que importava.
    #
    # PASSOU A SER UM E NÃO DOIS, de propósito: a medição prova a cadeia inteira
    # de uma vez e, quando falha, **não sabe dizer qual elo quebrou**. Partir a
    # resposta em dois era voltar a presumir metade.
    passos.append(_tunel(cfg, medir))

    faltam = [p for p in passos if p["essencial"] and not p["ok"]]
    return {
        "aberto": aberto,
        "ensaio": ensaio,
        "utilizadores": len(utilizador.todos()),
        "passos": passos,
        "faltam": faltam,
        "pode_abrir": not faltam,
    }


#: O nome do passo medido. Nomeia os TRÊS elos que a medição prova juntos, para
#: ninguém o ler como «só o túnel».
NOME_DO_TUNEL = "O caminho de fora (Cloudflare + nameservers + túnel)"

#: O que fazer quando a medição dá vermelho, ou quando não houve medição. Os
#: dois passos dele continuam escritos — o que deixou de se presumir é se
#: estão feitos.
COMO_O_TUNEL = (
    "São os PASSOS 1 e 2 do docs/abrir-a-porta.md (a conta na Cloudflare e os "
    "nameservers + o túnel). Se já os fizeste, olha primeiro ao que corre aqui: "
    "`sc query Cloudflared` tem de dizer RUNNING. ANTES de mexer nos "
    "nameservers, confirma que a Cloudflare já tem os cinco endereços "
    "(baverone.com, rift, mtg, baiak, tibia) em «DNS only» (nuvem cinzenta) — "
    "o rift.baverone.com não pode cair.")


def _medido(nome: str, ok: bool | None, diz: str, como: str = "") -> dict:
    """Um passo que se MEDE. `ok=None` quer dizer «não sei», não «falta».

    Não é essencial, e isso é deliberado: o `--abrir` recusa pelos passos que
    deixam **ele** de fora da própria coleção (ver `_ele_entra`), e abrir a
    porta com o túnel em baixo não é dessa família — os amigos não chegam lá,
    e nada se perde. Fazê-lo essencial tinha ainda um efeito pior: um `ok=None`
    por falta de rede passava a travar o `--abrir` num avião.
    """
    return {"nome": nome, "ok": ok, "essencial": False, "diz": diz, "como": como}


def _tunel(cfg: dict, medir=None) -> dict:
    """Mede se o endereço público chega a ESTA app, vindo de fora.

    Quatro respostas, e cada uma diz o que sabe:

    * **OK** — respondeu 200 e a app diz que viu o pedido chegar de FORA, com N
      sinais de intermediário. Prova a cadeia inteira;
    * **não sei** — não há endereço escrito, ou ninguém pediu a medição, ou a
      rede não deu (o `respondeu: False`, que é o caso do avião);
    * **FALTA** — respondeu, mas não como deve: um código que não é 200 (o
      DNS resolve e o túnel está em baixo), ou não era o riftvault do outro
      lado, ou a app diz que o pedido lhe chegou «de casa» — e aí o endereço
      público não está a passar por túnel nenhum, que é configuração errada.
    """
    base = str((cfg.get("auth") or {}).get("base_url") or "").strip()
    if not base.startswith("https://"):
        return _medido(
            NOME_DO_TUNEL, None,
            "não medi: não há um endereço https escrito em `auth.base_url` "
            "para onde perguntar.", COMO_O_TUNEL)
    if medir is None:
        return _medido(
            NOME_DO_TUNEL, None,
            f"não medi (ninguém pediu uma medição). O endereço é {base}.",
            "Corre `riftvault multi --verificar`, que pergunta ao endereço "
            "e responde medido.")

    r = medir(base) or {}
    if not r.get("respondeu"):
        return _medido(
            NOME_DO_TUNEL, None,
            f"não consegui perguntar a {base} — {r.get('erro') or 'sem razão'}."
            f" Sem rede isto é «não sei», não «falta»: se já fizeste os passos, "
            f"está feito.", COMO_O_TUNEL)
    codigo = r.get("codigo")
    if codigo != 200:
        return _medido(
            NOME_DO_TUNEL, False,
            f"{base} respondeu {codigo} — o endereço resolve, mas não chega a "
            f"esta app. O túnel costuma ser o que está em baixo.", COMO_O_TUNEL)
    if r.get("erro"):
        return _medido(
            NOME_DO_TUNEL, False,
            f"{base} respondeu 200, mas {r['erro']} — o endereço está a apontar "
            f"para outra coisa.", COMO_O_TUNEL)
    sinais = list(r.get("sinais") or [])
    if r.get("origem") != "fora":
        return _medido(
            NOME_DO_TUNEL, False,
            f"{base} chega a esta app, mas ela diz que o pedido veio de CASA — "
            f"o endereço público não está a passar por túnel nenhum. Isto é "
            f"configuração errada, não falta de passo.", COMO_O_TUNEL)
    return _medido(
        NOME_DO_TUNEL, True,
        f"MEDIDO: {base} responde e chega-lhe de fora "
        f"({len(sinais)} {'sinal' if len(sinais) == 1 else 'sinais'} de "
        f"intermediário). A conta na Cloudflare, os nameservers e o túnel estão "
        f"feitos — os PASSOS 1 e 2 não têm de se repetir.")


def _ele_entra(cfg: dict) -> dict:
    """ELE tem password definida? (Ou uma conta de OAuth ligada.)

    É A VERIFICAÇÃO QUE INTERESSA MAIS. Se a porta abrir sem isto, a escrita
    passa a exigir sessão (é a regra da LAN, no `rotas_conta.py`) e ele fica do
    lado de fora da sua própria coleção. É a única que o obriga a fazer uma
    coisa antes de abrir — e desde 2026-09-30 essa coisa é um comando na
    consola, sem browser e sem contas em sítios de terceiros.

    A TEMPORÁRIA NÃO CONTA COMO PRONTO, e é de propósito: com uma temporária
    ele entra mas não faz mais nada até a trocar (ver
    `rotas_conta._trava_temporaria`). Abrir a porta nesse estado era abri-la
    com ele meio fora.
    """
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
        senha = auth.estado_senha(con, 1)
        ligadas = auth.identidades_de(con, 1)
    finally:
        con.close()

    quais = [x["provedor"] for x in ligadas]
    if senha["tem"] and not senha["temporaria"]:
        return _essencial(
            "Tu consegues entrar", True,
            f"tens password definida (utilizador «{dono.get('slug')}»)"
            + (f", e a conta está ligada ao {', '.join(quais)}." if quais
               else "."))
    if senha["temporaria"]:
        return _essencial(
            "Tu consegues entrar", False,
            "a tua password é a temporária e ainda não a trocaste — com ela "
            "entras, mas não podes fazer mais nada.",
            f"Escolhe-a na consola, aqui e agora:  riftvault conta "
            f"{dono.get('slug')} --definir-password  — pergunta-a duas vezes e "
            f"não a mostra. (Pelo site também dá: com o `riftvault serve` a "
            f"correr, a caixa «Entrar» está na barra do lado, com a porta "
            f"fechada e tudo.)")
    if quais:
        return _essencial(
            "Tu consegues entrar", True,
            f"a tua conta está ligada ao {', '.join(quais)} (sem password "
            f"definida, o que também serve).")
    return _essencial(
        "Tu consegues entrar", False,
        f"a tua conta («{dono.get('slug')}») não tem password definida.",
        f"Com a porta fechada isto não te incomoda — mas depois de abrires, "
        f"escrever passa a exigir entrar, e ficavas de fora da tua própria "
        f"coleção. Corre agora:  riftvault conta {dono.get('slug')} "
        f"--definir-password  — escolhes a password na consola, num passo só, "
        f"sem browser.")


def ligar(provedor: str = "discord", porta: int = 8770,
          cfg: dict | None = None) -> dict:
    """Um endereço de uso único que liga a conta DELE a um fornecedor.

    **DEIXOU DE SER O CAMINHO PRINCIPAL a 2026-09-30.** Nasceu a 29/09 como a
    única forma de o André entrar — ele já existia (utilizador 1, slug
    `baverone`) e o registo pedia-lhe um slug que já era dele, por isso ficava
    a olhar para um formulário sem saída. Desde que se entra por password, a
    resposta a esse problema é `riftvault conta baverone --nova-password`, e
    isto fica para quem **quiser ligar um fornecedor** a uma conta que já
    existe. Só funciona com o fornecedor configurado (sem segredo, recusa).

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

#: ERA ` TEU  ` NO `None` ATÉ 2026-10-02, e isso era o defeito a ler em voz
#: alta: a marca dizia «isto é contigo» a um passo que estava feito. Hoje o
#: `None` é **«não sei»** — o passo mede-se, e quando a medição não corre (sem
#: rede, ou ninguém a pediu) diz-se isso em vez de se presumir.
_MARCA = {True: "  OK   ", False: "FALTA  ", None: "NÃO SEI"}


def texto(estado: dict | None = None, cfg: dict | None = None) -> str:
    est = estado if estado is not None else verificar(cfg)
    linhas = []
    porta = "ABERTA" if est["aberto"] else "FECHADA"
    linhas.append(f"A porta das contas está {porta}."
                  + (" (a correr em ENSAIO)" if est["ensaio"] else ""))
    linhas.append(f"Utilizadores: {est['utilizadores']}.")
    # A PORTA NÃO MANDA NA AUTENTICAÇÃO (2026-10-01). Dizia-se aqui só se ela
    # estava aberta ou fechada, e quem lesse isso concluía — como nós
    # concluímos — que fechada queria dizer «sem autenticação». Diz-se as duas
    # metades juntas, porque são as duas que ele precisa de ter na cabeça.
    linhas.append("De fora de casa, entrar é sempre obrigatório — mesmo para "
                  "ver, e com a porta fechada também.")
    linhas.append("Em casa, escrever " + ("exige entrar." if est["aberto"]
                                          else "não pede password."))
    linhas.append("")
    for p in est["passos"]:
        linhas.append(f"[{_MARCA[p['ok']]}] {p['nome']}: {p['diz']}")
        if p["como"] and p["ok"] is not True:
            for pedaco in _dobrar(p["como"], 72):
                linhas.append(f"            {pedaco}")
    linhas.append("")
    if est["aberto"]:
        linhas.append("Já está aberta. Para fechar: riftvault multi --fechar")
    elif est["pode_abrir"]:
        linhas.append("Está tudo pronto do lado do código.")
        # ERA «falta só o que é teu (as linhas marcadas TEU)», e desde
        # 2026-10-02 já não há nenhuma: o passo dele MEDE-SE. Uma linha
        # `NÃO SEI` é a medição que não correu, e di-lo.
        if any(p["ok"] is None for p in est["passos"]):
            linhas.append("Há linhas em NÃO SEI: é a medição que não correu, "
                          "não um passo a faltar. Depois:")
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
# rastreada.
#
# ATENÇÃO — ESTE `robots.txt` ESTÁ INERTE, e foi medido (varrimento de
# 2026-10-01): um `robots.txt` lê-se **só em `/robots.txt` do anfitrião**, por
# isso o que o `build` escreve em `u/<slug>/robots.txt` nunca é pedido por motor
# nenhum, e o `rift.baverone.com/robots.txt` responde **404** — que para um
# motor significa «podes rastrear tudo». Das duas portas que isto dizia fechar,
# só a etiqueta na página fecha alguma.
#
# NÃO SE APAGOU, de propósito: não expõe nada (não leva nomes), custa dois
# ficheiros, e volta a ser o sítio certo no dia em que o site de um amigo tiver
# anfitrião próprio (`miguel.rift.baverone.com`, o que ele pediu primeiro — ver
# `docs/multi-utilizador.md`). Um `robots.txt` **na raiz** é a hipótese que ele
# viu a 2026-10-02 e **não** escolheu.

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


def publico_indexavel(dono: bool) -> bool:
    """Esta página pode ser indexada? **Só a DELE.**

    A regra é uma linha, e a primeira versão estava errada de uma maneira que
    vale a pena registar: exigia também `aberto=True`, e com a porta fechada
    (que é o estado de hoje) isso metia `noindex` no **site dele** — que está
    publicado e indexado desde o início. Uma correcção de segurança que
    despublicava o site do próprio dono.

    O que ele pediu é o contrário disso: o site DELE fica *exactamente* como
    está, e é o de um amigo que não se indexa *"até ele dizer o contrário"*.
    Por isso a única coisa que conta é de quem é a página.

    Quando ele quiser deixar indexar a de um amigo, é aqui — uma função, uma
    linha. Não se inventou uma chave de config para uma decisão que ele ainda
    não tomou.
    """
    return bool(dono)


def lista_indexavel() -> bool:
    """A página da LISTA (a raiz, quando há duas ou mais) pode ser indexada?

    **NÃO**, e é decisão dele de 2026-10-02, com as quatro hipóteses à frente:
    *"a lista deixa de ser indexada, como já acontece com as páginas de cada
    um; quem tiver o link abre tudo igual"*. Não quis tirar os euros da lista
    nem fechar o site todo com um `robots.txt` na raiz.

    O que o varrimento de 2026-10-01 mediu, e que isto fecha: a raiz publicada
    nomeia os amigos **e o valor da coleção de cada um** (*«Gonçalves — 433
    cartas · 686,57 €»*), e era a única página do site sem a marca — a de cada
    um deles já a tinha, a dele não a tem de propósito (é a dele). A página que
    os nomeia é mais exposta do que as que ela aponta: basta-lhe um link para
    aparecer numa pesquisa pelo nome de uma pessoa.

    Uma função à parte do `publico_indexavel` porque a pergunta é outra: ali é
    «de quem é esta página», aqui não é de ninguém — é o índice que nomeia
    todos. Mas vive no MESMO ficheiro, ao lado dela, para quem procurar «o que
    é que se indexa» encontrar as duas respostas no mesmo sítio. A marca é a
    mesma (`marcar_html`), para não haver duas maneiras de dizer a mesma coisa.
    """
    return False


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
    """Volta a fechar: as contas dos amigos deixam de valer.

    **A DOCSTRING ANTIGA DIZIA «Ninguém perde nada — só deixa de se entrar», E
    ERA FALSO DE UMA MANEIRA PERIGOSA** (corrigido a 2026-10-01). Até aqui
    fechar DESLIGAVA A AUTENTICAÇÃO: o `rotas_conta._antes` deixava passar
    qualquer escrita sem sessão e sem CSRF, e com o túnel vivo isso era escrita
    anónima na coleção dele a partir da internet. Uma frase que descrevia a
    porta como inofensiva, num sítio que a punha a abaixo.

    O que fechar faz HOJE, e é tudo:

      * o OAuth não anda e não se registam contas (`auth.exigir_porta_aberta`);
      * o site publicado continua a ser só o dele;
      * **em casa** volta a escrever-se sem password, que é o que ele quer.

    O que fechar **nunca** fez, e convém não repetir a asneira ao contrário:
    não impede quem já tem conta de entrar. A entrada por password não passa
    pela porta desde 2026-09-30 — medido a 01/10, com a porta fechada um amigo
    entra e usa a coleção DELE (a dele, não a do André: é o `get_con` a abrir o
    ficheiro do dono da sessão).

    O que fechar **NÃO** faz, e é a correcção: não mexe no que se exige a quem
    vem de FORA. Quem chega pelo túnel precisa de sessão para tudo, com a porta
    aberta ou fechada. Quem decide isso é a ORIGEM do pedido (`origem.py`), não
    esta chave.

    Nada se apaga: as contas, as passwords e as coleções ficam todas, e abrir
    outra vez repõe o que era.
    """
    from . import multi
    if not multi.aberto(cfg if cfg is not None else config.load()):
        return {"aberto": False, "mudou": False}
    config.escrever_valor("multi", "aberto", False)
    return {"aberto": False, "mudou": True}
