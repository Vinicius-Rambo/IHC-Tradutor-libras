"""
VLIBRAS API (o robô pedindo os sinais prontos a um serviço na internet)
=======================================================================
O avatar 3D do VLibras (governo federal, LAVID/UFPB) é "gerado por código": o serviço recebe o texto,
devolve a glosa e pode renderizar um VÍDEO do avatar sinalizando. O tablet só toca o vídeo (MP4), então
não precisa de WebGL: serve para tablets antigos, como o Samsung com Android 7.

  POST {base}/translate   {"text": "..."}      -> glosa
  POST {base}/video       {"gloss": "..."}     -> vídeo do avatar

ATENÇÃO: esse contrato foi descrito por um projeto de terceiros, não por documentação oficial. O nome dos
campos, o formato da resposta e a exigência de chave podem ser diferentes. Rode primeiro, na B13:

    .venv/bin/python ferramentas/testar_vlibras_api.py "bom dia"

e ajuste os LIBRAS_API_* do config.py. Se a internet cair, o robô pausa a API por um tempo e usa as
imagens da pasta libras/ (ou a soletração), sem travar a conversa.
"""

import glob
import hashlib
import os
import time

import httpx

CHAVES_DA_GLOSA = ("translation", "glosa", "gloss", "text", "result")
CHAVES_DO_VIDEO = ("url", "video", "videoUrl", "link", "path")


class ClienteVLibras:
    def __init__(self, config, pasta_cache: str, pasta_raiz: str):
        self.c = config
        self.base = getattr(config, "LIBRAS_API_URL", "https://traducao2.vlibras.gov.br").rstrip("/")
        self.video_ligado = getattr(config, "LIBRAS_API_VIDEO", True)
        self.pasta_cache = pasta_cache
        self.parado_ate = 0.0   # depois de uma falha, não tenta de novo por um tempo (sala sem internet)
        os.makedirs(pasta_cache, exist_ok=True)
        self.chave = None
        arquivo = os.path.join(pasta_raiz, getattr(config, "LIBRAS_API_ARQUIVO_DA_CHAVE", "chave_vlibras.txt"))
        if os.path.isfile(arquivo):
            self.chave = open(arquivo, encoding="utf-8").read().strip() or None

    # ---------- infraestrutura ----------
    def disponivel(self) -> bool:
        return time.time() >= self.parado_ate

    def _falhou(self, motivo):
        pausa = getattr(self.c, "LIBRAS_API_PAUSA_APOS_FALHA", 60)
        self.parado_ate = time.time() + pausa
        print(f"[vlibras-api] falhou ({motivo}); sem tentar de novo por {pausa} s")

    def _cabecalho(self) -> dict:
        cab = {"User-Agent": "RoboByte/1.0 (robo assistente de aulas, projeto escolar)"}
        if self.chave:
            cab[getattr(self.c, "LIBRAS_API_CABECALHO_DA_CHAVE", "x-api-key")] = self.chave
        return cab

    # ---------- texto -> glosa ----------
    def glosa(self, texto: str):
        """A glosa como texto ("BOM DIA ANA"), ou None se a API não respondeu."""
        if not self.disponivel():
            return None
        try:
            r = httpx.post(self.base + getattr(self.c, "LIBRAS_API_CAMINHO_TRADUCAO", "/translate"),
                           json={"text": texto}, headers=self._cabecalho(),
                           timeout=getattr(self.c, "LIBRAS_API_TEMPO_MAXIMO", 8))
            r.raise_for_status()
            return extrair_glosa(r)
        except Exception as erro:
            self._falhou(f"{type(erro).__name__}: {erro}")
            return None

    # ---------- glosa -> vídeo do avatar ----------
    def video(self, glosa: str):
        """Caminho do MP4 relativo à pasta libras ("cache/ab12.mp4"), ou None."""
        if not (self.video_ligado and glosa):
            return None
        nome = hashlib.sha1(glosa.encode("utf-8")).hexdigest()[:16] + ".mp4"
        arquivo = os.path.join(self.pasta_cache, nome)
        if os.path.isfile(arquivo):                       # a mesma frase de novo: sem internet e sem espera
            os.utime(arquivo)
            return "cache/" + nome
        if not self.disponivel():
            return None
        try:
            tempo = getattr(self.c, "LIBRAS_API_TEMPO_MAXIMO_VIDEO", 30)
            campo = getattr(self.c, "LIBRAS_API_CAMPO_VIDEO", "gloss")
            r = httpx.post(self.base + getattr(self.c, "LIBRAS_API_CAMINHO_VIDEO", "/video"),
                           json={campo: glosa}, headers=self._cabecalho(), timeout=tempo, follow_redirects=True)
            r.raise_for_status()
            dados = extrair_video(r, self.base, self._cabecalho(), tempo)
            if not dados:
                raise ValueError("a resposta não trouxe um vídeo (confira com testar_vlibras_api.py)")
            with open(arquivo, "wb") as f:
                f.write(dados)
            self._limpar_cache()
            return "cache/" + nome
        except Exception as erro:
            self._falhou(f"vídeo: {type(erro).__name__}: {erro}")
            return None

    def _limpar_cache(self):
        """O disco da B13 é pequeno: apaga os vídeos mais antigos quando passa do limite."""
        limite = getattr(self.c, "LIBRAS_CACHE_MAX_MB", 300) * 1024 * 1024
        arquivos = sorted(glob.glob(os.path.join(self.pasta_cache, "*.mp4")), key=os.path.getmtime)
        total = sum(os.path.getsize(a) for a in arquivos)
        while arquivos and total > limite:
            velho = arquivos.pop(0)
            total -= os.path.getsize(velho)
            os.remove(velho)


def extrair_glosa(resposta) -> str:
    """Aceita JSON (texto, lista ou objeto com um campo conhecido) ou texto puro."""
    try:
        dados = resposta.json()
    except Exception:
        dados = resposta.text
    if isinstance(dados, dict):
        dados = next((dados[k] for k in CHAVES_DA_GLOSA if isinstance(dados.get(k), (str, list))), None)
    if isinstance(dados, list):
        dados = " ".join(str(p) for p in dados)
    return (dados or "").strip().strip('"') or None


def extrair_video(resposta, base: str, cabecalho: dict, tempo: float):
    """O vídeo pode vir direto na resposta, ou como um endereço dentro de um JSON."""
    if resposta.headers.get("content-type", "").startswith("video/"):
        return resposta.content
    try:
        dados = resposta.json()
    except Exception:
        return None
    endereco = next((dados[k] for k in CHAVES_DO_VIDEO if isinstance(dados, dict) and isinstance(dados.get(k), str)), None)
    if not endereco:
        return None
    if endereco.startswith("/"):
        endereco = base + endereco
    segunda = httpx.get(endereco, headers=cabecalho, timeout=tempo, follow_redirects=True)
    segunda.raise_for_status()
    return segunda.content
