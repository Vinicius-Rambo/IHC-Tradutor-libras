"""Testes da parte Python do modo dedicado. Rode na pasta do projeto:   python -m unittest tests.test_libras_tela -v
(Não precisa de microfone, de modelos nem de internet.)"""
import asyncio
import json
import os
import struct
import sys
import tempfile
import types
import unittest

from robo import config

config.LIBRAS_API_LIGADA = False
config.LIBRAS_USAR_VLIBRAS = False


def pcm(volume, segundos):
    n = int(16000 * segundos)
    return struct.pack("<%dh" % n, *([volume, -volume] * (n // 2) + [0] * (n % 2)))


class TestEscuta(unittest.TestCase):
    def test_corta_frase_depois_do_silencio(self):
        from robo.escuta import Escuta
        e, saida = Escuta(), []
        for _ in range(4):
            saida.append(e.ouvir(pcm(100, 0.25)))      # silêncio: nada
        for _ in range(4):
            saida.append(e.ouvir(pcm(5000, 0.25)))     # fala
        for _ in range(5):
            saida.append(e.ouvir(pcm(100, 0.25)))      # pausa
        frases = [s for s in saida if s]
        self.assertEqual(len(frases), 1)
        self.assertGreater(len(frases[0]) / 2 / 16000, 1.0)

    def test_barulho_curto_e_ignorado(self):
        from robo.escuta import Escuta
        e = Escuta()
        saida = [e.ouvir(pcm(5000, 0.1))] + [e.ouvir(pcm(100, 0.25)) for _ in range(5)]
        self.assertEqual([s for s in saida if s], [])


class TestLibras(unittest.TestCase):
    def setUp(self):
        from robo.libras import Libras
        self.pasta = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.pasta, "animacoes"))
        with open(os.path.join(self.pasta, "animacoes", "sinais.json"), "w") as f:
            json.dump({"bom dia": {"quadros": [{"t": 0}]}, "_aviso": "x"}, f)
        config.LIBRAS_PASTA = self.pasta
        import robo.libras as modulo
        modulo.PASTA_RAIZ = ""
        self.l = Libras()

    def test_animacao_tem_prioridade_e_junta_palavras(self):
        itens = self.l.montar(["BOM", "DIA", "ANA"])
        self.assertEqual([i["modo"] for i in itens], ["animacao", "letras"])
        self.assertEqual(itens[0]["chave"], "bom dia")

    def test_chaves_com_underline_sao_ignoradas(self):
        self.assertNotIn("aviso", self.l.animacoes)

    def test_traduzir_sem_video(self):
        r = self.l.traduzir("Bom dia, Ana!", com_video=False)
        self.assertIsNone(r["video"])
        self.assertEqual(r["glosa"].split(), ["BOM", "DIA", "ANA"])


class TestRoboLibras(unittest.TestCase):
    def test_fluxo_texto_digitado(self):
        fake = types.ModuleType("robo.transcricao")
        fake.Transcritor = lambda: types.SimpleNamespace(transcrever=lambda a: "bom dia")
        sys.modules["robo.transcricao"] = fake
        from robo.robo_libras import RoboLibras

        class Conexao:
            def __init__(self): self.msgs = []
            async def send_json(self, m): self.msgs.append(m)

        async def rodar():
            r = RoboLibras()
            c = Conexao()
            await r.conectar_rosto(c)
            await r.receber_mensagem({"tipo": "texto", "texto": "Bom dia, Ana!"}, c)
            for volume in [5000] * 4 + [100] * 5:   # fala e depois pausa, em pedaços de 0,25 s
                await r.receber_audio(pcm(volume, 0.25), c)
            await asyncio.sleep(0.5)
            r.trabalhador.cancel()
            return [m["tipo"] for m in c.msgs], c.msgs

        tipos, msgs = asyncio.run(rodar())
        self.assertEqual(tipos[0], "libras_config")
        self.assertEqual(tipos.count("mostrar_libras"), 2)
        self.assertEqual(tipos.count("legenda"), 2)
        self.assertIn("itens", [m for m in msgs if m["tipo"] == "mostrar_libras"][0])


if __name__ == "__main__":
    unittest.main()
