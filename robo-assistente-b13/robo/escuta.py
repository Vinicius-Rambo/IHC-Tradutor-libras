"""
ESCUTA (ouvido contínuo do modo Libras, sem Vosk)
=================================================
No modo dedicado não existe palavra de ativação: o robô escuta o tempo todo e corta o áudio
em frases, sempre que a pessoa faz uma pausa. Não carrega nenhum modelo (só usa o volume).

    ouvir(pedaco) -> None, ou os bytes de uma frase pronta (16 bits, 16 kHz)
"""

from collections import deque

import numpy as np

from robo import config


def medir_volume(pedaco: bytes) -> float:
    amostras = np.frombuffer(pedaco[: len(pedaco) // 2 * 2], dtype=np.int16).astype(np.float32)
    return float(np.sqrt(np.mean(amostras ** 2))) if len(amostras) else 0.0


class Escuta:
    ANTES = 3   # pedacinhos guardados antes da fala, para não cortar o começo da primeira palavra

    def __init__(self):
        self.anteriores = deque(maxlen=self.ANTES)
        self._zerar()

    def _zerar(self):
        self.audio = bytearray()
        self.silencio = 0.0
        self.voz = 0.0          # segundos com voz de verdade
        self.falando = False

    def reiniciar(self):
        self.anteriores.clear()
        self._zerar()

    def ouvir(self, pedaco: bytes):
        pedaco = pedaco[: len(pedaco) // 2 * 2]
        if not pedaco:
            return None
        duracao = len(pedaco) / 2 / config.TAXA_DE_AMOSTRAGEM
        com_voz = medir_volume(pedaco) > config.LIMIAR_DE_SILENCIO

        if not self.falando:
            if not com_voz:
                self.anteriores.append(pedaco)
                return None
            self.falando = True
            for antigo in self.anteriores:
                self.audio.extend(antigo)
            self.anteriores.clear()

        self.audio.extend(pedaco)
        if com_voz:
            self.voz += duracao
            self.silencio = 0.0
        else:
            self.silencio += duracao

        segundos = len(self.audio) / 2 / config.TAXA_DE_AMOSTRAGEM
        if self.silencio >= config.SEGUNDOS_DE_SILENCIO_PARA_PARAR or segundos >= config.SEGUNDOS_MAXIMOS_DE_FALA:
            frase = bytes(self.audio) if self.voz >= getattr(config, "LIBRAS_SEGUNDOS_MINIMOS_DE_VOZ", 0.35) else None
            self._zerar()
            return frase
        return None
