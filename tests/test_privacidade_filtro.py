"""O FILTRO `sem-valores` (2026-09-29): nenhum euro sai para o público.

A parte PURA — a regra sobre um payload. A parte que gera o site está no
`test_privacidade.py` (os três valores contra o `build.py`).

DUAS REDES, e apanham coisas diferentes:
  A) nenhuma chave de QUANTIA sobrevive, e nenhum texto com `€`;
  B) números que SÃO preços desta coleção não aparecem em lado nenhum — é
     esta que apanha uma quantia com um nome que a regra não conhece, e foi
     ela que apanhou o `total` das linhas das Faltas.
"""

from __future__ import annotations

import unittest

from riftvault import privacidade as pv


def quantias_vivas(o, chave="", vizinhas=(), fora=None):
    """As quantias que sobreviveram ao filtro (a rede A)."""
    fora = [] if fora is None else fora
    if isinstance(o, dict):
        irmas = tuple(o)
        for k, v in o.items():
            if pv.e_dinheiro(k, v, irmas):
                fora.append((k, v))
            quantias_vivas(v, k, irmas, fora)
    elif isinstance(o, list):
        for v in o:
            quantias_vivas(v, chave, vizinhas, fora)
    elif isinstance(o, str) and "€" in o:
        fora.append((chave, o))
    return fora


def numeros(o, fora=None):
    fora = set() if fora is None else fora
    if isinstance(o, dict):
        for v in o.values():
            numeros(v, fora)
    elif isinstance(o, list):
        for v in o:
            numeros(v, fora)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        fora.add(o)
    return fora


class TestOsTresValores(unittest.TestCase):

    def test_sao_estes_e_a_omissao_e_a_mais_fechada(self):
        self.assertEqual(pv.VALORES, ("nada", "sem-valores", "tudo"))
        self.assertEqual(pv.OMISSAO, "nada")

    def test_um_valor_inventado_rebenta_com_a_lista(self):
        with self.assertRaises(pv.ValorInvalido) as e:
            pv.validar("privado")
        self.assertIn("nada", str(e.exception))
        self.assertIn("sem-valores", str(e.exception))

    def test_nada_nao_publica(self):
        self.assertFalse(pv.publica("nada"))
        self.assertTrue(pv.publica("sem-valores"))
        self.assertTrue(pv.publica("tudo"))

    def test_so_o_do_meio_esconde_valores(self):
        self.assertFalse(pv.esconde_valores("nada"))
        self.assertTrue(pv.esconde_valores("sem-valores"))
        self.assertFalse(pv.esconde_valores("tudo"))


class TestOModoTudoNaoMexe(unittest.TestCase):

    def test_devolve_o_mesmo_objecto(self):
        p = {"price": 1234, "texto": "5,00 €"}
        self.assertIs(pv.limpar(p, "tudo"), p)

    def test_e_nao_estraga_o_original_em_sem_valores(self):
        """O mesmo payload tem de poder ser escrito nos dois modos."""
        p = {"price": 1234, "sub": {"cents": 99}}
        limpo = pv.limpar(p, "sem-valores")
        self.assertIsNone(limpo["price"])
        self.assertEqual(p["price"], 1234, "mexeu no original")
        self.assertEqual(p["sub"]["cents"], 99)


class TestARedeA(unittest.TestCase):
    """Nenhuma chave de quantia, nenhum euro."""

    def test_as_chaves_de_quantia_perdem_o_valor(self):
        p = {"price": 1234, "price_foil": 500, "cents": 10, "valor_cents": 7,
             "preco_cents": 3, "preco_cm_cents": 2, "value": 1,
             "cents_de_foil": 9, "qty_valor": 4}
        limpo = pv.limpar(p, "sem-valores")
        self.assertEqual(set(limpo), set(p), "não se tiram chaves, tiram-se valores")
        for k in p:
            self.assertIsNone(limpo[k], k)

    def test_as_contagens_ficam(self):
        p = {"copies": 3195, "printings": 1041, "cards": 920, "done": 910,
             "missing": 18, "pct": 98.1, "target": 3, "have": 2, "qty": 5}
        self.assertEqual(pv.limpar(p, "sem-valores"), p)

    def test_o_denominador_dos_niveis_fica(self):
        """`total` aqui é o denominador («910 de 928»), não uma quantia."""
        p = {"k": 1, "done": 910, "total": 928, "missing": 18,
             "cents": 4834, "pct": 98.1}
        limpo = pv.limpar(p, "sem-valores")
        self.assertEqual(limpo["total"], 928)
        self.assertEqual(limpo["done"], 910)
        self.assertIsNone(limpo["cents"])

    def test_o_total_de_uma_linha_com_preco_e_quantia(self):
        """E aqui `total` é `price` × `missing`, em cêntimos. O gatilho é ter
        um `price` ao lado — medido no site real: 820 ocorrências assim, e as
        84 em que é contagem não têm nenhum."""
        p = {"code": "OGN-045", "missing": 2, "price": 5027, "total": 10054}
        limpo = pv.limpar(p, "sem-valores")
        self.assertIsNone(limpo["total"])
        self.assertIsNone(limpo["price"])
        self.assertEqual(limpo["missing"], 2)
        self.assertEqual(limpo["code"], "OGN-045")

    def test_um_booleano_com_nome_de_preco_fica(self):
        """`price_is_foil` e `foil_only` respondem sim/não e não dizem quanto
        custa nada."""
        p = {"price_is_foil": True, "foil_only": False, "has_prices": True}
        self.assertEqual(pv.limpar(p, "sem-valores"), p)

    def test_uma_data_com_nome_de_preco_fica(self):
        p = {"preco_dia": "2026-09-29", "preco_fonte": "cardtrader"}
        self.assertEqual(pv.limpar(p, "sem-valores"), p)

    def test_uma_lista_de_quantias(self):
        p = {"precos": [100, 200, 300], "copias": [1, 2, 3]}
        limpo = pv.limpar(p, "sem-valores")
        self.assertEqual(limpo["precos"], [None, None, None])
        self.assertEqual(limpo["copias"], [1, 2, 3])

    def test_o_texto_com_euro_sai(self):
        """O recibo da Venda é um texto gerado com o total lá dentro. Não se
        emenda um texto — tira-se."""
        p = {"texto": "\nTOTAL: 330,50 €  (6 cartas, 3 linhas)\n"}
        self.assertIsNone(pv.limpar(p, "sem-valores")["texto"])

    def test_um_nome_de_carta_nao_e_tocado(self):
        p = {"name": "Baited Hook", "market_name": "Baited Hook", "code": "OGN-242"}
        self.assertEqual(pv.limpar(p, "sem-valores"), p)

    def test_em_profundidade(self):
        p = {"sets": [{"blocks": [{"items": [
            {"price": 999, "total": 1998, "missing": 2}]}]}]}
        self.assertEqual(quantias_vivas(pv.limpar(p, "sem-valores")), [])


class TestARedeB(unittest.TestCase):
    """Números que SÃO preços não aparecem — com sentinelas inconfundíveis.

    Um preço pequeno em cêntimos COLIDE com uma contagem (medido: o 3195 é ao
    mesmo tempo o número de cópias da coleção e o preço de uma carta). Aqui os
    preços são escolhidos para não colidirem com nada.
    """

    SENTINELAS = (777701, 777702, 777703)

    def test_nenhuma_sentinela_sobrevive(self):
        p = {"value": self.SENTINELAS[0],
             "grupos": [{"price": self.SENTINELAS[1], "missing": 3,
                         "total": self.SENTINELAS[2], "have": 1}],
             "totals": {"copies": 42, "cards": 7}}
        limpo = pv.limpar(p, "sem-valores")
        vivos = numeros(limpo) & set(self.SENTINELAS)
        self.assertEqual(vivos, set(), f"vazaram preços: {sorted(vivos)}")
        self.assertEqual(limpo["totals"], {"copies": 42, "cards": 7})

    def test_a_rede_b_apanharia_uma_chave_nova(self):
        """A prova pela negativa: uma quantia com um nome que a regra não
        conhece PASSA a rede A e é apanhada pela rede B. É para isso que as
        duas existem."""
        p = {"soma_da_caixa": self.SENTINELAS[0]}
        limpo = pv.limpar(p, "sem-valores")
        self.assertEqual(quantias_vivas(limpo), [], "a rede A não a apanha")
        self.assertIn(self.SENTINELAS[0], numeros(limpo), "a rede B tem de a ver")


if __name__ == "__main__":
    unittest.main(verbosity=2)
