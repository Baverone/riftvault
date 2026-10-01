"""A LISTA das coleções públicas (2026-09-30).

André, 2026-09-30: *"a baverone.com tem que ter tudo / depois quando se abre o
Riftbound, vai ter lá, em modo leitura, as coleções: Baverone / Miguel / Rafa"*.

As PÁGINAS de cada um já existiam (o `build.build_todos` gera `u/<slug>/` desde
2026-09-29, e já salta quem tem privacidade «nada» ou está atrás das portas
fechadas). O que não existia era o ÍNDICE que as junta — é este ficheiro.

---------------------------------------------------------------------------
QUANDO É QUE A LISTA PASSA A SER A RAIZ
---------------------------------------------------------------------------
Hoje `rift.baverone.com` **é** a coleção dele, e ele disse *"quero apenas
apresentar quando tiver tudo"* (2026-09-29). Por isso a troca é AUTOMÁTICA e
não uma chave que ele tenha de mudar:

    0 ou 1 coleção pública  ->  a raiz fica EXACTAMENTE como está hoje
    2 ou mais              ->  a raiz é a lista, e a dele vive em `u/baverone/`

Com as portas fechadas há uma pública (a dele), por isso hoje **nada muda**.
Ela aparece sozinha no dia em que ele abrir as portas e um amigo escolher
publicar — que é exactamente o dia em que uma lista passa a fazer sentido.

Uma lista com uma entrada só não é uma lista: é um clique a mais entre ele e a
coleção dele, e uma página que anuncia um serviço que ainda não tem ninguém.

---------------------------------------------------------------------------
OS FAVORITOS DELE NÃO PODEM PARTIR
---------------------------------------------------------------------------
O site é uma aplicação de uma página com rotas no `#` (`#colecao/UNL`,
`#decks/ornn`, …). Quando a raiz passa a ser a lista, um favorito antigo
continua a bater na raiz — e o `#` **nunca chega ao servidor**, por isso não
há reencaminhamento de servidor que o possa apanhar (e o GitHub Pages também
não tem regras de reencaminhamento nenhumas). Quem o vê é o browser, e é por
isso que o reencaminhamento vive na própria página da lista, em JavaScript, no
`<head>`: qualquer `#` na raiz manda para `u/<slug dele>/` com o mesmo `#`.

É deliberadamente CEGO ao nome da secção — não repete a lista `SECCOES` do
`app.js`. Uma secção nova nasce reencaminhada sozinha; e um `#` que já não
exista cai na regra de sempre do `app.js` (abre a primeira secção visível),
que é o mesmo que acontecia antes desta mudança.

**O QUE NÃO SE CONSEGUE REENCAMINHAR, e diz-se em vez de partir em silêncio:**
os ficheiros de dados (`/api/set/OGN.json` e companhia) passam a viver em
`u/baverone/api/…` e um endereço antigo para eles dá **404**. Não há maneira
de o evitar num alojamento estático sem duplicar o site inteiro na raiz. São
endereços de máquina, não de pessoa — o que se marca nos favoritos é a página,
e essa é reencaminhada.

---------------------------------------------------------------------------
O QUE CADA CARTÃO MOSTRA
---------------------------------------------------------------------------
Os números saem do `api/index.json` **já gerado** de cada pessoa — não são
calculados outra vez. Duas consequências, as duas boas: não há uma segunda
definição de «quantas cartas tem o Miguel», e o cartão não pode mostrar mais
do que a página dela já mostra, porque lê o ficheiro que já passou pelo
`privacidade.limpar`. Por cima disso o cartão volta a passar pelo mesmo filtro
(`cartao`), que é cinto e suspensórios de propósito: quem escolheu
«sem-valores» não vê euros aqui, e isso não depende de ninguém se lembrar.
"""

from __future__ import annotations

import html as _html
import json
import shutil
import unicodedata
from pathlib import Path

from . import config, multi, privacidade, utilizador

#: A partir de quantas coleções públicas é que a lista toma a raiz.
#: Duas — ver o cabeçalho: com uma, a lista é um clique a mais.
MINIMO_PARA_A_RAIZ = 2

#: Os ficheiros da aplicação de uma página que ficam na raiz enquanto ela é a
#: coleção dele. Quando a lista toma a raiz, ele muda-se para `u/<slug>/` e
#: estes têm de SAIR — senão ficavam lá os payloads antigos dele, a
#: envelhecer, e um `api/index.json` velho na raiz ainda por cima fazia o
#: `--se-mudou` comparar contra o sítio errado.
#:
#: É uma lista ESCRITA e não um «apaga tudo o que não é `u/`»: na raiz podem
#: estar coisas que não são nossas para apagar (o `CNAME` do domínio, o
#: `.nojekyll`, o `img/` de 88 MB de uma corrida em `static_images: local`).
RESTOS_DA_RAIZ = ("api", "app.js", "style.css", "robots.txt")


def _chave(nome: str) -> str:
    """Ordem alfabética que não põe o «Álvaro» depois do «Zé»."""
    return unicodedata.normalize("NFKD", (nome or "").casefold())


def publicas(cfg: dict | None = None) -> list[dict]:
    """Quem tem coleção pública, o ANDRÉ SEMPRE PRIMEIRO.

    A regra é a mesma do `build.build_todos`, e é de propósito: a lista não
    pode nomear alguém cuja página não foi gerada, nem esconder uma que foi.

      * portas fechadas (`multi.aberto: false`, que é o de hoje) -> só ele;
      * privacidade «nada» (que é a OMISSÃO de quem entra de novo) -> fora, e
        **nem o nome aparece**. Não estar na lista é a forma mais completa de
        não estar publicado.

    Depois dele, por nome. A ordem dele não é alfabética nem por antiguidade:
    é a casa dele.
    """
    cfg = config.load() if cfg is None else cfg
    fechado = not multi.aberto(cfg)
    dentro = []
    for u in utilizador.todos():
        dele = u["user_id"] == utilizador.ANDRE
        if fechado and not dele:
            continue
        modo = privacidade.de(None, u["user_id"])
        if not privacidade.publica(modo):
            continue
        dentro.append({"user_id": u["user_id"], "slug": u["slug"],
                     "nome": (u["nome"] or u["slug"]).strip(),
                     "publico": modo})
    dentro.sort(key=lambda e: (e["user_id"] != utilizador.ANDRE,
                             _chave(e["nome"])))
    return dentro


def na_raiz(pub: list[dict]) -> bool:
    """A lista toma a raiz? Só com duas ou mais — ver o cabeçalho."""
    return len(pub) >= MINIMO_PARA_A_RAIZ


def caminho_de(entrada: dict, pub: list[dict]) -> str:
    """Onde vive o site desta pessoa, visto da raiz.

    Enquanto a lista não toma a raiz, a dele **é** a raiz — e é isso que faz
    o dia de hoje não mudar um byte.
    """
    if not na_raiz(pub) and entrada["user_id"] == utilizador.ANDRE:
        return ""
    return f"u/{entrada['slug']}/"


def pasta_de(out: Path, entrada: dict, pub: list[dict]) -> Path:
    """A pasta onde o site desta pessoa é gerado."""
    sub = caminho_de(entrada, pub)
    return Path(out) / sub if sub else Path(out)


# ---------------------------------------------------------------------------
# Os números de cada cartão
# ---------------------------------------------------------------------------

def cartao(raiz: Path, entrada: dict) -> dict:
    """Os números do cartão, lidos do site JÁ GERADO desta pessoa.

    Sem o `api/index.json` (uma pasta por gerar) devolve-se o cartão sem
    números em vez de rebentar: a lista tem de conseguir mostrar um nome e um
    link mesmo que a geração daquela pessoa tenha falhado.
    """
    p = Path(raiz) / "api" / "index.json"
    d = {}
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            d = {}
    totals = d.get("totals") or {}
    niveis = ((d.get("levels") or {}).get("levels") or [])
    playset = niveis[-1] if niveis else {}
    c = {
        "cards": totals.get("cards"),
        "copies": totals.get("copies"),
        "printings": totals.get("printings"),
        "playset_done": playset.get("done"),
        "playset_total": playset.get("total"),
        "playset_pct": playset.get("pct"),
        "value_cents": ((d.get("value") or {}).get("cents")),
    }
    # Cinto e suspensórios: o ficheiro de onde isto saiu já vinha filtrado,
    # mas o cartão volta a passar pelo MESMO filtro. Assim «este cartão não
    # mostra euros de quem escolheu sem-valores» não depende de ninguém se
    # lembrar de nada — é a regra do `privacidade.py` outra vez.
    return privacidade.limpar(c, entrada["publico"])


def payload(out: Path, pub: list[dict] | None = None,
            cfg: dict | None = None) -> dict:
    """O que a lista sabe. Também vai para `api/lista.json`, legível à máquina."""
    cfg = config.load() if cfg is None else cfg
    pub = publicas(cfg) if pub is None else pub
    out = Path(out)
    itens = []
    for e in pub:
        itens.append({**e, "url": caminho_de(e, pub) or "./",
                      **cartao(pasta_de(out, e, pub), e)})
    return {"na_raiz": na_raiz(pub), "coleccoes": itens,
            "dele": utilizador.SLUG_ANDRE}


# ---------------------------------------------------------------------------
# A página
# ---------------------------------------------------------------------------

def _num(n) -> str:
    """1234 -> «1 234». O espaço é fino e não parte a linha."""
    if n is None:
        return "—"
    return f"{int(n):,}".replace(",", " ")


def _plural(n, um: str, muitos: str) -> str:
    """«1 carta», «2 cartas» — a coleção de quem começa tem UMA carta.

    O site já se apanhou nisto mais do que uma vez (a revisão de 2026-09-09:
    «1 versões», «1 cartas», «2 impressãoões»), e num cartão com três números
    é onde mais se vê.
    """
    return f"{_num(n)} {um if n == 1 else muitos}"


def _euros(cents) -> str | None:
    if cents is None:
        return None
    return f"{cents / 100:,.2f} €".replace(",", " ").replace(".", ",")


def _cartao_html(it: dict) -> str:
    nome = _html.escape(it["nome"])
    url = _html.escape(it["url"])
    linhas = []
    if it.get("playset_total"):
        linhas.append(
            f'<div class="l-barra"><span style="width:'
            f'{min(100, float(it.get("playset_pct") or 0)):.1f}%"></span></div>'
            f'<p class="l-num"><b>{_num(it.get("playset_done"))}</b>'
            f'<span class="l-de"> de {_num(it.get("playset_total"))}</span>'
            f' <span class="l-rot">impressões em playset</span></p>')
    if it.get("cards") is not None:
        linhas.append(f'<p class="l-sub">'
                      f'{_plural(it.get("cards"), "carta", "cartas")} · '
                      f'{_plural(it.get("copies"), "cópia", "cópias")}</p>')
    eur = _euros(it.get("value_cents"))
    if eur:
        linhas.append(f'<p class="l-sub">{eur}</p>')
    if not linhas:
        linhas.append('<p class="l-sub">coleção por gerar</p>')
    return (f'<a class="l-cartao" href="{url}">'
            f'<span class="l-ini" aria-hidden="true">'
            f'{_html.escape(nome[:1].upper() or "?")}</span>'
            f'<h2>{nome}</h2>{"".join(linhas)}'
            f'<span class="l-ir">ver a coleção →</span></a>')


#: O reencaminhamento dos favoritos. Vai no `<head>`, ANTES de a página se
#: desenhar — com ele no fim do `<body>` via-se a lista a piscar antes do
#: salto. `location.replace` e não `href`: o botão «voltar» tem de levar a
#: pessoa a onde ela estava, e não outra vez para aqui.
def _script_reencaminha(slug: str) -> str:
    return (
        "<script>\n"
        "  /* Um favorito antigo aponta para a raiz com a rota no `#`\n"
        "     (`#colecao/UNL`). O `#` nunca chega ao servidor, por isso quem\n"
        "     o pode apanhar é só o browser. Cego ao nome da secção de\n"
        "     propósito: uma rota nova é reencaminhada sozinha. */\n"
        "  (function () {\n"
        "    var h = location.hash;\n"
        "    if (h && h.length > 1) "
        f"location.replace('u/{slug}/' + h);\n"
        "  })();\n"
        "</script>")


def html(dados: dict) -> str:
    itens = dados["coleccoes"]
    cartoes = "\n      ".join(_cartao_html(it) for it in itens)
    quantos = len(itens)
    if quantos == 0:
        corpo = ('<p class="l-vazio">Ainda não há nenhuma coleção pública. '
                 'Quem quiser publicar a sua escolhe-o nas definições da '
                 'conta — a omissão é ficar privado.</p>')
    else:
        corpo = f'<div class="l-grelha">\n      {cartoes}\n    </div>'
    sub = ("1 coleção" if quantos == 1 else f"{quantos} coleções")
    return f"""<!DOCTYPE html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#07080d">
<title>riftvault — coleções de Riftbound</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23120f1d'/%3E%3Cpath d='M20 46V18h13a9 9 0 0 1 0 18h-4l10 10h-8l-9-10v-6h10a3 3 0 0 0 0-6h-6v22z' fill='%23a77bff'/%3E%3C/svg%3E">
{_script_reencaminha(dados["dele"])}
<style>
  :root {{
    --bg: #07080d; --card2: #0e1018; --card: #12151f; --card3: #171b28;
    --ink: #eef0f6; --ink2: #c8cede; --muted: #8c93a8;
    --line: rgba(255,255,255,.07); --line2: rgba(255,255,255,.13);
    --accent: #a77bff; --accent-ink: #0b0713; --accent-soft: #1d1430;
    --font: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
    --font-hd: 'Space Grotesk', 'Inter', system-ui, -apple-system, sans-serif;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--ink);
    font: 16px/1.5 var(--font);
    /* O telemóvel é o sítio onde ele usa isto. */
    padding: 32px 20px 64px; padding-bottom: calc(64px + env(safe-area-inset-bottom));
  }}
  .l-wrap {{ max-width: 980px; margin: 0 auto; }}
  .l-topo {{ display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }}
  .l-logo {{
    width: 38px; height: 38px; border-radius: 10px; flex: 0 0 auto;
    background: var(--accent-soft); color: var(--accent);
    display: grid; place-items: center;
    font: 700 20px/1 var(--font-hd);
  }}
  h1 {{ font: 700 26px/1.2 var(--font-hd); margin: 0; letter-spacing: -.01em; }}
  .l-sub-topo {{ color: var(--muted); margin: 0 0 28px 50px; font-size: 14px; }}
  .l-grelha {{
    display: grid; gap: 14px;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  }}
  .l-cartao {{
    display: block; text-decoration: none; color: inherit;
    background: var(--card); border: 1px solid var(--line);
    border-radius: 14px; padding: 18px;
  }}
  .l-cartao:hover, .l-cartao:focus-visible {{
    border-color: var(--accent); background: var(--card3);
  }}
  .l-ini {{
    display: grid; place-items: center; width: 34px; height: 34px;
    border-radius: 9px; background: var(--accent); color: var(--accent-ink);
    font: 700 16px/1 var(--font-hd); margin-bottom: 10px;
  }}
  .l-cartao h2 {{ font: 600 19px/1.25 var(--font-hd); margin: 0 0 12px; }}
  .l-barra {{
    height: 5px; border-radius: 99px; background: var(--card3);
    overflow: hidden; margin-bottom: 8px;
  }}
  .l-barra span {{ display: block; height: 100%; background: var(--accent); }}
  .l-num {{ margin: 0 0 4px; font-size: 15px; }}
  .l-num b {{ font: 600 17px/1 var(--font-hd); }}
  .l-de, .l-rot {{ color: var(--muted); font-size: 13px; }}
  .l-sub {{ margin: 0 0 2px; color: var(--ink2); font-size: 13px; }}
  .l-ir {{ display: block; margin-top: 12px; color: var(--accent); font-size: 13px; }}
  .l-vazio {{
    background: var(--card); border: 1px solid var(--line); border-radius: 14px;
    padding: 20px; color: var(--muted); max-width: 62ch;
  }}
  .l-rodape {{ margin-top: 32px; color: var(--muted); font-size: 13px; }}
  @media (max-width: 480px) {{
    body {{ padding: 20px 14px 48px; }}
    .l-grelha {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
  <div class="l-wrap">
    <div class="l-topo">
      <span class="l-logo" aria-hidden="true">R</span>
      <h1>riftvault</h1>
    </div>
    <p class="l-sub-topo">Coleções de Riftbound · {sub} · só leitura</p>
    {corpo}
    <p class="l-rodape">Cada coleção é de quem a organiza. Quem não escolheu
      publicar não aparece aqui.</p>
  </div>
</body>
</html>
"""


def limpar_raiz(out: Path) -> list[str]:
    """Tira da raiz os restos do site DELE, quando ele se muda para `u/`.

    Devolve o que apagou, para o `build` o poder dizer. Ver `RESTOS_DA_RAIZ`.
    """
    out = Path(out)
    fora = []
    for nome in RESTOS_DA_RAIZ:
        alvo = out / nome
        if alvo.is_dir():
            shutil.rmtree(alvo, ignore_errors=True)
            fora.append(nome + "/")
        elif alvo.exists():
            alvo.unlink()
            fora.append(nome)
    return fora


def limpar_nao_publicadas(out: Path, pub: list[dict]) -> list[str]:
    """Tira de `u/` as pastas de quem JÁ NÃO se publica. Devolve os slugs.

    Isto é mais do que arrumação — é a metade que faltava à privacidade. Uma
    pessoa que tenha escolhido «tudo» e mude para «nada» deixava de ter página
    GERADA, mas a que já lá estava **ficava publicada para sempre**: o
    `build.py` salta-a, e saltar não é apagar. Despublicar tem de ser tão fácil
    como publicar.

    Vale também para ELE: quando a lista deixa de tomar a raiz (um amigo ficou
    privado e voltou a haver uma coleção só), o `u/baverone/` fica para trás
    com uma cópia a envelhecer — e é para lá que os favoritos foram
    reencaminhados enquanto a lista existiu.

    Só mexe DENTRO do `u/`, e só em pastas: o resto da raiz não é nosso.
    """
    out = Path(out)
    base = out / "u"
    if not base.is_dir():
        return []
    ficam = {e["slug"] for e in pub if caminho_de(e, pub)}
    fora = []
    for p in sorted(base.iterdir()):
        if p.is_dir() and p.name not in ficam:
            shutil.rmtree(p, ignore_errors=True)
            fora.append(p.name)
    return fora


def escrever(out: Path, pub: list[dict] | None = None,
             cfg: dict | None = None) -> dict:
    """Escreve a lista na raiz: o `index.html` e o `api/lista.json`."""
    out = Path(out)
    dados = payload(out, pub=pub, cfg=cfg)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html(dados), encoding="utf-8")
    (out / "api").mkdir(parents=True, exist_ok=True)
    (out / "api" / "lista.json").write_text(
        json.dumps(dados, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    return dados
