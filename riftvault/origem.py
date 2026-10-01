"""DE ONDE VEM ESTE PEDIDO: de casa, ou da internet? (2026-10-01)

Isto nasceu de dois defeitos que duas revisões independentes encontraram no
mesmo sítio, e os dois tinham a mesma raiz: **a app decidia se era preciso
autenticação a partir da PORTA DAS CONTAS** (`multi.aberto`), e não a partir de
quem estava a bater. Com o túnel vivo, «fechar a porta» desligava a
autenticação para a internet inteira.

A PERGUNTA CERTA, E PORQUE É QUE ELA MUDOU
    Até aqui estava escrito — aqui, no `rotas_conta.py` e no
    `docs/contas-e-autenticacao.md` — que **não há atalho por endereço**, porque
    «o túnel faz todo o tráfego da internet chegar ao Flask como `127.0.0.1`».
    Isso continua a ser VERDADE e foi medido outra vez a 2026-10-01: o
    `cloudflared` corre como serviço nesta máquina e fala com o `localhost:8770`.

    O que estava errado era a CONCLUSÃO. De «o loopback não prova que é ele»
    tirou-se «não se pode distinguir nada», e daí «então a porta decide». Mas há
    coisas que o loopback NÃO explica, e são elas que decidem:

      * um pedido do telemóvel dele chega de **192.168.1.x** — e isso o túnel
        não consegue produzir, porque o par TCP não se escolhe;
      * um pedido que passou pela Cloudflare traz **cabeçalhos que só um
        intermediário põe** (`CF-Connecting-IP` e companhia);
      * um pedido que passou pelo túnel pede o **anfitrião público**
        (`editar.baverone.com`), que é o nome por onde a Cloudflare o encaminha.

    Ou seja: não se pergunta «isto vem de fora?» (que é falsificável para
    ambos os lados), pergunta-se **«isto é inequivocamente de casa?»**.

E A REGRA É UM «E», NUNCA UM «OU»
    `de_casa` exige as TRÊS coisas ao mesmo tempo. É isso que faz o erro cair
    sempre para o lado seguro:

      * **forjar** qualquer um dos três só pode TIRAR a confiança, nunca dá-la —
        quem estiver na rede de casa e mandar um `CF-Connecting-IP` inventado
        consegue uma coisa só: passar a precisar de password;
      * para um pedido da internet ser tratado como de casa, teria de chegar com
        endereço privado **e** sem um único cabeçalho de intermediário **e** sem
        pedir o anfitrião público. Tem de vencer os três.

    Nenhum dos três é, sozinho, uma prova. Juntos são o mais perto disso que há
    sem mudar o túnel, e cada um tapa o buraco dos outros: se amanhã ele trocar
    a Cloudflare por outro túnel que não ponha cabeçalhos, fica o anfitrião; se
    o túnel reescrever o anfitrião, ficam os cabeçalhos — medido, a Cloudflare
    põe-nos e **não** reescreve o nome (ver `docs/origem-do-pedido.md`).

O QUE ISTO **NÃO** É
    Não é identidade. Isto nunca diz QUEM é alguém — só se o pedido pode ou não
    ser tratado como o de uma pessoa que está na casa. Quem decide quem é
    alguém continua a ser a sessão, e mais nada. Por isso também não substitui
    o guarda da escrita: de casa com a porta aberta, escrever continua a exigir
    sessão e CSRF.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

#: CABEÇALHOS QUE SÓ UM INTERMEDIÁRIO PÕE.
#:
#: Um browser não manda nenhum destes: são postos por quem está no meio
#: (a Cloudflare, o `cloudflared`, um nginx, um ngrok). A presença de UM basta
#: para o pedido deixar de ser «de casa».
#:
#: A lista é larga de propósito, e não é só Cloudflare: o dia em que ele trocar
#: de túnel não pode ser o dia em que isto deixa de funcionar em silêncio.
#: Medido a 2026-10-01 contra o túnel a sério — ver `docs/origem-do-pedido.md`.
CABECALHOS_DE_INTERMEDIARIO = (
    # Cloudflare
    "CF-Connecting-IP", "CF-Connecting-IPv6", "CF-Ray", "CF-IPCountry",
    "CF-Visitor", "CF-Worker", "CF-Warp-Tag-Id", "CDN-Loop",
    # convenções de qualquer proxy
    "X-Forwarded-For", "X-Forwarded-Proto", "X-Forwarded-Host",
    "X-Forwarded-Port", "X-Forwarded-Scheme", "Forwarded",
    "X-Real-IP", "True-Client-IP", "X-Client-IP", "X-Original-Forwarded-For",
    "Via",
)


#: AS GAMAS DA CASA, ESCRITAS UMA A UMA — e **não** o `is_private` do Python.
#:
#: A primeira versão fazia `ip.is_loopback or ip.is_private or ip.is_link_local`,
#: e a bateria apanhou-a logo: para o Python, `203.0.113.9` **é privado**. Ele
#: marca assim as gamas reservadas para documentação (`192.0.2.0/24`,
#: `198.51.100.0/24`, `203.0.113.0/24`) e a `240.0.0.0/4`, que não são a rede de
#: casa de ninguém.
#:
#: E o pior não é a lista estar errada — é **mudar sozinha**: o que o Python
#: entende por «privado» já mudou entre versões (a `100.64.0.0/10` do CGNAT das
#: operadoras era privada e no 3.14 não é). Uma decisão de segurança não pode
#: depender disso em silêncio. Por isso escreve-se a lista: loopback, as três do
#: RFC 1918, a de auto-configuração, e as equivalentes em IPv6.
GAMAS_DE_CASA = tuple(ipaddress.ip_network(r) for r in (
    "127.0.0.0/8",      # loopback (é por aqui que o túnel entra, ver o topo)
    "10.0.0.0/8",       # RFC 1918
    "172.16.0.0/12",    # RFC 1918
    "192.168.0.0/16",   # RFC 1918 — a rede dele (ver «O IP da LAN muda sozinho»)
    "169.254.0.0/16",   # sem DHCP
    "::1/128",          # loopback, IPv6
    "fc00::/7",         # unique local, IPv6
    "fe80::/10",        # link local, IPv6
))


def endereco_de_casa(endereco: str | None) -> bool:
    """Este endereço é da casa? (loopback ou a rede local.)

    Loopback NÃO prova que é ele — é por aí que o túnel entra —, mas prova que
    não é um pedido directo da internet, e isso é o que esta função responde.
    O `::ffff:127.0.0.1` conta: é o mesmo endereço escrito à maneira do IPv6.
    """
    if not endereco:
        return False  # sem endereço não se presume casa
    texto = endereco.strip()
    if texto.startswith("[") and texto.endswith("]"):
        texto = texto[1:-1]
    texto = texto.split("%")[0]  # o `%eth0` do IPv6 com âmbito
    try:
        ip = ipaddress.ip_address(texto)
    except ValueError:
        return False
    mapeado = getattr(ip, "ipv4_mapped", None)
    if mapeado is not None:
        ip = mapeado
    return any(ip in rede for rede in GAMAS_DE_CASA
               if ip.version == rede.version)


def anfitriao_publico(cfg: dict | None) -> str:
    """O nome por onde se chega aqui de fora, se ele o tiver escrito.

    Sai do `auth.base_url` — é o endereço que ele dá a um amigo e o mesmo que o
    túnel serve. Sem ele escrito, esta pista não existe e ficam as outras duas.
    """
    base = str(((cfg or {}).get("auth") or {}).get("base_url") or "").strip()
    if not base:
        return ""
    try:
        return (urlsplit(base).hostname or "").lower()
    except ValueError:
        return ""


def classificar(endereco: str | None, cabecalhos, anfitriao: str,
                publico: str) -> dict:
    """A regra, sem Flask: dá para a testar com strings.

    `cabecalhos` é qualquer coisa com `.get(nome)` — o `request.headers` serve, e
    um `dict` também.
    """
    sinais: list[str] = []

    if not endereco_de_casa(endereco):
        sinais.append(f"o pedido vem de {endereco or '?'}")

    for nome in CABECALHOS_DE_INTERMEDIARIO:
        if cabecalhos.get(nome):
            sinais.append(f"trazia o cabeçalho {nome}")

    nome_pedido = (anfitriao or "").split(":")[0].strip().lower()
    if publico and nome_pedido == publico:
        sinais.append(f"pediu {publico}, que é o endereço público")

    return {"de_casa": not sinais, "sinais": sinais}


def do_pedido(request, cfg: dict | None = None) -> dict:
    """O mesmo, a partir do `request` do Flask."""
    return classificar(request.remote_addr, request.headers,
                       request.host or "", anfitriao_publico(cfg))


def porque(sinais) -> str:
    """Uma frase para o diagnóstico. Nunca leva VALORES de cabeçalhos."""
    lista = list(sinais or [])
    if not lista:
        return "este pedido é de casa (rede local, sem intermediário no meio)."
    return "este pedido vem de fora: " + "; ".join(lista) + "."
