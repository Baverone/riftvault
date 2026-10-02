"""A leitura de uma decklist por IMAGEM (2026-10-02).

Os testes constroem a página à mão — uma grelha de cartas com o crachá `xN`
desenhado por cima, a partir das artes do catálogo de brincar. Não dependem da
imagem de prova do André, que vive fora do repositório; o que ela prova está no
`TestAImagemDeProva`, que se salta quando ela não está lá.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

#: Um caminho que não existe: o `config` cai nos `DEFAULTS`. Sem isto lia-se o
#: `riftvault_config.json` A SÉRIO, onde `multi.aberto` é `true`.
SEM_CONFIG = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import Vault  # noqa: E402

try:
    from PIL import Image, ImageDraw, ImageFont  # noqa
    import numpy  # noqa
    TEM_PIL = True
except Exception:                                      # pragma: no cover
    TEM_PIL = False

PROVA = Path(r"C:\Users\Catarina\Desktop\ai-pc\work\fixtures"
             r"\deck-rengar-pridestalker.png")

FUNDO = (232, 106, 42)      # o laranja da página de torneio
LARG, ALT = 491, 712
MARGEM, GAP = 84, 72


def _fonte(tam):
    from PIL import ImageFont
    for n in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        p = Path(r"C:\Windows\Fonts") / n
        if not p.exists():
            p = Path("/usr/share/fonts/truetype/dejavu") / n
        if p.exists():
            return ImageFont.truetype(str(p), tam)
    return ImageFont.load_default()


def pagina(artes, quantidades, *, corte=None, por_linha=6):
    """Monta uma página como a do torneio: grelha de 6, crachá `xN` em cada."""
    from PIL import Image, ImageDraw
    linhas = [artes[i:i + por_linha] for i in range(0, len(artes), por_linha)]
    extra = ALT // 3 if corte is not None else 0
    W = MARGEM * 2 + por_linha * LARG + (por_linha - 1) * GAP
    H = MARGEM * 2 + len(linhas) * (ALT + 94) + extra
    im = Image.new("RGB", (W, H), FUNDO)
    k = 0
    for li, linha in enumerate(linhas):
        y = MARGEM + li * (ALT + 94) + (extra if corte is not None and li >= corte else 0)
        for ci, arte in enumerate(linha):
            x = MARGEM + ci * (LARG + GAP)
            im.paste(arte.convert("RGB").resize((LARG, ALT), Image.LANCZOS), (x, y))
            _cracha(im, x, y, quantidades[k])
            k += 1
    return im


def _cracha(im, x, y, n):
    """O crachá: caixa escura com `xN` branco, no mesmo sítio da página real."""
    from PIL import ImageDraw
    from riftvault import imagem as mod
    d = ImageDraw.Draw(im)
    bx = (x + int(LARG * mod.CRACHA[0]) + 16, y + int(ALT * mod.CRACHA[1]) + 19,
          x + int(LARG * mod.CRACHA[2]) - 15, y + int(ALT * mod.CRACHA[3]) - 17)
    d.rounded_rectangle(bx, radius=18, fill=(38, 43, 54))
    f = _fonte(58)
    t = f"x{n}"
    cx = (bx[0] + bx[2]) // 2
    cy = (bx[1] + bx[3]) // 2
    d.text((cx, cy), t, fill=(255, 255, 255), font=f, anchor="mm")


@unittest.skipUnless(TEM_PIL, "sem Pillow/numpy")
class Base(unittest.TestCase):
    #: Um catálogo de brincar com cartas de cada tipo que importa.
    CARTAS = [("Pridestalker", "Legend"), ("Trophy Hunter", "Unit"),
              ("Inferna", "Unit"), ("Pakaa Cub", "Unit"), ("Sabotage", "Spell"),
              ("Punch First", "Spell"), ("Body Rune", "Rune"),
              ("Fury Rune", "Rune"), ("Emperor's Dais", "Battlefield"),
              ("Seat of Power", "Battlefield"), ("Star Spring", "Battlefield"),
              ("Rampage", "Spell"), ("Brittle Steel", "Spell"),
              ("Noxus Hopeful", "Unit"), ("First Mate", "Unit"),
              ("Kinkou Initiate", "Unit"), ("Nidalee", "Unit"),
              ("Darius", "Unit")]

    def setUp(self):
        os.environ["RIFTVAULT_CONFIG"] = SEM_CONFIG
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_CONFIG", None))
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import imagem
        self.mod = imagem
        self.con = self.v.connect()
        self.addCleanup(self.con.close)
        for i, (nome, tipo) in enumerate(self.CARTAS, start=1):
            self.v.add_printing(self.con, f"tst-{i:03d}-100", "TST", i, nome,
                                card_type=tipo)
        self.v.rebuild(self.con)
        self.artes = self._artes()

    def _artes(self):
        """As artes do catálogo de brincar, em disco, como no `data/images/`."""
        from PIL import Image, ImageDraw
        from riftvault import config
        pasta = Path(config.IMAGES_DIR)
        pasta.mkdir(parents=True, exist_ok=True)
        fora = {}
        rs = self.con.execute(
            "SELECT printing_id FROM catalog.printings ORDER BY printing_id"
        ).fetchall()
        for i, r in enumerate(rs):
            im = Image.new("RGB", (600, 837), (12, 12, 16))
            d = ImageDraw.Draw(im)
            # cada carta com um padrão próprio, para as assinaturas diferirem
            for j in range(14):
                cor = ((i * 37 + j * 23) % 256, (i * 91 + j * 7) % 256,
                       (i * 13 + j * 53) % 256)
                d.rectangle((20 + j * 20, 40 + ((i + j) % 9) * 50,
                             560 - j * 12, 120 + ((i + j) % 9) * 60), fill=cor)
            im.save(pasta / f"{r[0]}.webp")
            fora[r[0]] = im
        return fora


class TestOTextoSaiPelaMesmaPorta(Base):
    def test_o_que_sai_e_o_formato_que_o_colar_ja_le(self):
        from riftvault import colar, decks
        ids = list(self.artes)[:6]
        im = pagina([self.artes[i] for i in ids], [1, 2, 3, 1, 2, 3])
        r = self.mod.ler(self.con, _bytes(im))
        self.assertEqual(len(r["cartas"]), 6)
        lido = decks.parse_texto(r["texto"])
        self.assertTrue(lido["lines"], "o texto tem de ser legível pelo leitor único")
        p = colar.prever(self.con, r["texto"])
        self.assertEqual(p["nao_casaram"], [],
                         "o que a imagem lê vem do catálogo: tem de casar sempre")

    def test_o_modulo_nao_tem_gramatica_propria(self):
        """O leitor é UM só: o `imagem` produz texto, não analisa nenhum."""
        fonte = (Path(__file__).resolve().parent.parent
                 / "riftvault" / "imagem.py").read_text(encoding="utf-8")
        for proibido in ('endswith(":")', "ROLES", "re.match"):
            self.assertNotIn(proibido, fonte)

    def test_ler_nao_grava_deck_nenhum(self):
        from riftvault import config
        ids = list(self.artes)[:6]
        antes = sorted(Path(config.decks_dir(self.con)).glob("*.txt"))
        self.mod.ler(self.con, _bytes(pagina([self.artes[i] for i in ids], [1] * 6)))
        self.assertEqual(sorted(Path(config.decks_dir(self.con)).glob("*.txt")), antes)


class TestAsQuantidades(Base):
    def test_le_o_cracha_de_cada_carta(self):
        ids = list(self.artes)[:6]
        qs = [1, 2, 3, 4, 8, 9]
        r = self.mod.ler(self.con, _bytes(pagina([self.artes[i] for i in ids], qs)))
        self.assertEqual([c["qty"] for c in sorted(
            r["cartas"], key=lambda c: c["coluna"])], qs)

    def test_o_oito_nao_vira_tres(self):
        """A guarda dos BURACOS: é topológica, e por isso não depende da fonte."""
        from PIL import Image
        import numpy as np
        for d, esperado in ((0, 1), (1, 0), (3, 0), (4, 1), (8, 2), (9, 1)):
            im = Image.new("L", (170, 190), 0)
            from PIL import ImageDraw
            ImageDraw.Draw(im).text((30, 20), str(d), 255, font=_fonte(90))
            m = np.asarray(im) > 128
            self.assertEqual(self.mod._buracos(self.mod._recorta_bool(m, np), np),
                             esperado, f"o dígito {d}")


class TestSoAceitaOQueTemCerteza(Base):
    def _ambigua(self):
        """Metade de uma carta e metade de outra: as duas ficam igualmente perto.

        É assim que se prova a regra da MARGEM, que é a que o protege a sério.
        Uma intrusa qualquer (um círculo verde) está longe de tudo e seria
        apanhada por qualquer regra; esta está PERTO de duas.
        """
        from PIL import Image
        ids = list(self.artes)
        return Image.blend(self.artes[ids[6]].convert("RGB"),
                           self.artes[ids[7]].convert("RGB"), 0.5)

    def test_uma_carta_ambigua_fica_de_fora_e_e_contada(self):
        ids = list(self.artes)[:5]
        im = pagina([self.artes[i] for i in ids] + [self._ambigua()], [1] * 6)
        r = self.mod.ler(self.con, _bytes(im))
        self.assertEqual(len(r["cartas"]), 5)
        self.assertEqual(len(r["duvidas"]), 1)
        self.assertIn("não reconheci", r["duvidas"][0]["porque"])

    def test_nunca_escolhe_o_mais_parecido_em_silencio(self):
        """Uma dúvida nunca vira uma linha do texto."""
        ids = list(self.artes)[:5]
        im = pagina([self.artes[i] for i in ids] + [self._ambigua()], [1] * 6)
        r = self.mod.ler(self.con, _bytes(im))
        self.assertTrue(r["duvidas"])
        linhas = [l for l in r["texto"].splitlines() if l and not l.endswith(":")]
        self.assertEqual(len(linhas), len(r["cartas"]))
        for d in r["duvidas"]:
            # a parecida é informação para ele, não uma linha da lista
            self.assertNotIn(str(d.get("parecida") or "\0"), r["texto"])

    def test_a_margem_e_contra_outra_CARTA_nao_outra_impressao(self):
        """Duas impressões da mesma carta dão a mesma linha: não há que desempatar."""
        fonte = (Path(__file__).resolve().parent.parent
                 / "riftvault" / "imagem.py").read_text(encoding="utf-8")
        self.assertIn("card_key", fonte.split("A margem mede-se")[1][:600])


class TestOsPapeis(Base):
    def test_o_tipo_vem_do_catalogo_e_nao_da_imagem(self):
        self.assertEqual(self.mod._papel("Legend"), "legend")
        self.assertEqual(self.mod._papel("Rune"), "runes")
        self.assertEqual(self.mod._papel("Battlefield"), "battlefields")
        self.assertEqual(self.mod._papel("Unit"), "main")
        self.assertEqual(self.mod._papel("Spell"), "main")
        self.assertEqual(self.mod._papel(None), "main")

    def test_o_corte_para_o_sideboard_e_o_ESPACO_entre_linhas(self):
        ids = list(self.artes)[:18]
        im = pagina([self.artes[i] for i in ids], [1] * 18, corte=2)
        r = self.mod.ler(self.con, _bytes(im))
        self.assertTrue(r["sideboard"])
        self.assertEqual(sum(1 for c in r["cartas"] if c["sideboard"]), 6)

    def test_o_corte_ve_se_com_DUAS_linhas_so(self):
        """Não se compara com a mediana: com duas linhas ela seria o corte."""
        ids = list(self.artes)[:12]
        im = pagina([self.artes[i] for i in ids], [1] * 12, corte=1)
        r = self.mod.ler(self.con, _bytes(im))
        self.assertTrue(r["sideboard"])
        self.assertEqual(sum(1 for c in r["cartas"] if c["sideboard"]), 6)

    def test_sem_salto_fica_tudo_no_deck(self):
        ids = list(self.artes)[:12]
        im = pagina([self.artes[i] for i in ids], [1] * 12)
        r = self.mod.ler(self.con, _bytes(im))
        self.assertFalse(r["sideboard"])
        self.assertFalse(any(c["sideboard"] for c in r["cartas"]))

    def test_com_DOIS_cortes_nao_se_adivinha(self):
        import numpy as np
        self.assertEqual(self.mod._divisor([0, 800, 1900, 3000], 700, np)[0], None)
        self.assertEqual(self.mod._divisor([0, 800, 1900, 3000], 700, np)[1], 2)


class TestRecusasLegiveis(Base):
    def test_sem_imagem(self):
        with self.assertRaises(self.mod.ImagemIlegivel):
            self.mod.ler(self.con, b"")

    def test_lixo_em_vez_de_imagem(self):
        with self.assertRaises(self.mod.ImagemIlegivel):
            self.mod.ler(self.con, b"nao sou uma imagem" * 50)

    def test_uma_imagem_sem_grelha_nenhuma(self):
        from PIL import Image
        im = Image.new("RGB", (900, 700), FUNDO)
        with self.assertRaises(self.mod.ImagemIlegivel) as e:
            self.mod.ler(self.con, _bytes(im))
        self.assertIn("grelha", str(e.exception).lower())


class TestOEcra(unittest.TestCase):
    """A caixa da secção Decks: a imagem enche a MESMA caixa de texto."""

    @property
    def js(self):
        return (Path(__file__).resolve().parent.parent
                / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")

    def test_ha_um_seletor_de_imagem(self):
        self.assertIn('id="colar-img"', self.js)
        self.assertIn('accept="image/*"', self.js)

    def test_manda_para_a_rota_da_imagem(self):
        self.assertIn("api/decks/imagem", self.js)

    def test_passa_pelo_cabecalhos_como_todos_os_POST(self):
        trecho = self.js.split("async function colarImagem")[1][:900]
        self.assertIn("cabecalhos()", trecho)

    def test_o_texto_vai_para_a_MESMA_caixa_e_fica_editavel(self):
        """Não há segunda caixa: o que a imagem lê é emendável antes de gravar."""
        trecho = self.js.split("async function colarImagem")[1][:900]
        self.assertIn("colarEstado.texto = j.texto", trecho)
        self.assertEqual(self.js.count('id="colar-txt"'), 1)

    def test_diz_o_que_NAO_leu(self):
        self.assertIn("function colarImagemHTML", self.js)
        trecho = self.js.split("function colarImagemHTML")[1][:1200]
        self.assertIn("duvidas", trecho)
        self.assertIn("por ler", trecho)
        self.assertIn("champion_por_posicao", trecho)

    def test_o_limpar_tambem_limpa_a_imagem(self):
        trecho = self.js.split("$('#colar-limpar').onclick")[1][:300]
        self.assertIn("img: null", trecho)

    def test_o_css_tem_as_classes(self):
        css = (Path(__file__).resolve().parent.parent
               / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
        for c in (".colar-img", ".colar-img-res", ".colar-falhas"):
            self.assertIn(c, css)


class TestARota(unittest.TestCase):
    def test_a_rota_esta_na_lista_das_escritas(self):
        """Lê a coleção de quem a manda: sem sessão não pode responder."""
        from tests.test_contas import ESCRITAS
        self.assertIn("/api/decks/imagem", ESCRITAS)

    def test_o_tecto_do_corpo_e_por_ROTA(self):
        """Alargar para a imagem não pode alargar para as outras vinte e duas."""
        from riftvault import rotas_conta
        self.assertGreater(rotas_conta.corpo_maximo("/api/decks/imagem"),
                           rotas_conta.CORPO_MAXIMO)
        self.assertEqual(rotas_conta.corpo_maximo("/api/adjust"),
                         rotas_conta.CORPO_MAXIMO)
        self.assertEqual(rotas_conta.corpo_maximo("/api/decks/colar"),
                         rotas_conta.CORPO_MAXIMO)


# A IMAGEM DE PROVA do André (UVS Games, RQ Los Angeles, 2026-09-26) mede-se
# contra o `data/` REAL, no `_revisao\_prova_imagem.py`: 31/31 cartas, zero
# dúvidas, Legend 1 · Champion 1 · main 39 · battlefields 3 · runas 12 ·
# sideboard 10, com as duas ALT ART (OGN-007a, OGN-039a) identificadas. Aqui
# prova-se o MECANISMO, contra pastas temporárias — é a regra da casa, e os
# testes nunca tocam na coleção dele.


def _bytes(im):
    import io
    b = io.BytesIO()
    im.save(b, format="PNG")
    return b.getvalue()


if __name__ == "__main__":
    unittest.main()
