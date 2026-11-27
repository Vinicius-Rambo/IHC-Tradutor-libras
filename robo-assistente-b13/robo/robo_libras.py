"""
ROBÔ LIBRAS (modo dedicado: fala -> texto -> glosa -> sinais)
============================================================
Versão enxuta do robô, só para traduzir. Não carrega IA, voz, câmera nem Vosk.

    tablet (microfone) --áudio--> Escuta (corta frases) --> fila --> Parakeet (texto)
                                                                      --> Libras (glosa, sinais, vídeo)
    tablet (tela)      <--legenda / mostrar_libras--

A escuta continua gravando a próxima frase enquanto a anterior ainda está sendo traduzida,
então numa aula ninguém perde o que o professor disse enquanto o Parakeet trabalha.
Usa as mesmas mensagens do robô completo (veja robo.py), então a mesma tela serve aos dois.
"""

import asyncio
import re
import time
import traceback

from robo import config
from robo.escuta import Escuta
from robo.libras import Libras


class RoboLibras:
    def __init__(self):
        from robo.transcricao import Transcritor   # import tardio: só carrega o motor escolhido
        print("Ligando o robô Libras (modo dedicado)...")
        self.escuta = Escuta()
        self.transcritor = Transcritor()
        self.libras = Libras()
        self.rosto = None
        self.fila = None
        self.trabalhador = None
        self.pausado = False
        self.processando = False
        self.avatar = getattr(config, "LIBRAS_AVATAR", "vlibras")
        print(f"Robô Libras pronto! (avatar: {self.avatar})")

    # ---------- conversa com a tela ----------
    async def conectar_rosto(self, conexao):
        self.rosto = conexao
        self.escuta.reiniciar()
        if self.fila is None:
            self.fila = asyncio.Queue()
        if self.trabalhador is None or self.trabalhador.done():
            self.trabalhador = asyncio.create_task(self._trabalhar())
        await self.enviar({"tipo": "libras_config", "avatar": self.avatar,
                           "editor": bool(getattr(config, "LIBRAS_EDITOR_LIGADO", False)),
                           "pausado": self.pausado})
        await self.enviar_estado()

    def desconectar_rosto(self, conexao):
        if self.rosto is conexao:
            self.rosto = None

    def _usar(self, conexao):
        if conexao is not None and conexao is not self.rosto:
            self.rosto = conexao   # a aba que está mandando som é a que recebe os sinais

    async def enviar(self, mensagem: dict):
        if self.rosto is None:
            return
        try:
            await self.rosto.send_json(mensagem)
        except Exception:
            pass

    async def enviar_estado(self):
        estado = "dormindo" if self.pausado else ("pensando" if self.processando or (self.fila and not self.fila.empty())
                                                  else "ouvindo")
        await self.enviar({"tipo": "estado", "estado": estado})

    # ---------- o que chega da tela ----------
    async def receber_audio(self, pedaco: bytes, conexao=None):
        self._usar(conexao)
        if self.pausado:
            return
        frase = self.escuta.ouvir(pedaco)
        if frase:
            await self.enfileirar(frase)

    async def receber_mensagem(self, mensagem: dict, conexao=None):
        self._usar(conexao)
        tipo = mensagem.get("tipo")
        if tipo == "pausar":
            self.pausado = bool(mensagem.get("ligado", True))
            self.escuta.reiniciar()
            await self.enviar_estado()
        elif tipo == "texto":   # frase digitada na tela (teste sem microfone, ou professor digitando)
            texto = str(mensagem.get("texto", "")).strip()[:400]
            if texto:
                await self.enfileirar(texto)

    async def receber_quadro(self, jpeg: bytes) -> dict:
        return {"rostos": [], "alguem": False}   # sem câmera no modo Libras

    def receber_foto(self, pedido: str, jpeg: bytes):
        pass

    # ---------- fila de frases ----------
    async def enfileirar(self, item):
        maximo = max(1, getattr(config, "LIBRAS_FILA_MAXIMA", 3))
        while self.fila.qsize() >= maximo:
            self.fila.get_nowait()
            print("[libras] fila cheia: descartei a frase mais antiga")
        self.fila.put_nowait(item)
        await self.enviar_estado()

    async def _trabalhar(self):
        while True:
            item = await self.fila.get()
            self.processando = True
            await self.enviar_estado()
            try:
                await self._processar(item)
            except Exception as erro:
                print(f"[libras] erro: {erro}")
                traceback.print_exc()
            finally:
                self.processando = False
                await self.enviar_estado()

    async def _processar(self, item):
        if isinstance(item, str):
            texto = item
        else:
            inicio = time.time()
            texto = await asyncio.to_thread(self.transcritor.transcrever, item)
            print(f"[robô] ouvi: {texto!r}")
            print(f"[tempo] entender a fala: {time.time() - inicio:.1f} s")
        if len(re.findall(r"\w", texto)) < 2:
            return
        await self.enviar({"tipo": "legenda", "quem": "pessoa", "texto": texto})   # o texto aparece já
        usa_video = self.avatar == "vlibras"
        if usa_video and self.libras.usa_video():   # gerar o vídeo leva alguns segundos
            await self.enviar({"tipo": "libras_aguarde", "frase": texto})
        inicio = time.time()
        resultado = await asyncio.to_thread(self.libras.traduzir, texto, usa_video)
        soletradas = [i["palavra"] for i in resultado["itens"] if i["modo"] == "letras"]
        print(f"[libras] '{texto}' -> {resultado['glosa']}"
              + (f"  (soletrando: {', '.join(soletradas)})" if soletradas else "")
              + ("  [vídeo do avatar]" if resultado.get("video") else "")
              + f"  [tempo] {time.time() - inicio:.1f} s")
        await self.enviar({"tipo": "mostrar_libras", **resultado})
