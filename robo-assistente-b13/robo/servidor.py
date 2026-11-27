"""
SERVIDOR (a ponte entre o computador e o tablet)
================================================
- Entrega a tela de Libras (pasta "libras_tela") e os arquivos de libras/ (sinais, vídeos, animações 3D).
- Mantém uma conexão aberta (WebSocket) por onde passam:
    tablet -> B13: o áudio do microfone, toques, frases digitadas
    B13 -> tablet: o estado do robô, a frase ouvida e os sinais a mostrar
- Modo dedicado (config.LIBRAS_MODO_DEDICADO): só o robô de Libras, leve. Senão, o robô completo.

Para ligar o robô:   python -m robo.servidor
"""

import json
import os
import re

import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from robo import config

app = FastAPI()
robo = None  # criado lá embaixo, quando o servidor liga
DEDICADO = getattr(config, "LIBRAS_MODO_DEDICADO", False)


@app.middleware("http")
async def sem_memoria_no_navegador(pedido, proximo):
    """Faz o Chrome do tablet sempre buscar a versão nova da página."""
    resposta = await proximo(pedido)
    resposta.headers["Cache-Control"] = "no-store"
    return resposta


@app.websocket("/ws")
async def conexao_com_o_rosto(conexao: WebSocket):
    await conexao.accept()
    print("[servidor] a tela (tablet) conectou")
    await robo.conectar_rosto(conexao)
    try:
        while True:
            mensagem = await conexao.receive()
            if mensagem["type"] == "websocket.disconnect":
                break
            if mensagem.get("bytes"):
                await robo.receber_audio(mensagem["bytes"], conexao)
            elif mensagem.get("text"):
                await robo.receber_mensagem(json.loads(mensagem["text"]), conexao)
    except WebSocketDisconnect:
        pass
    finally:
        robo.desconectar_rosto(conexao)
        print("[servidor] a tela desconectou")


# Câmera (só o robô completo usa)
@app.post("/visao/quadro")
async def quadro_da_camera(pedido: Request):
    return await robo.receber_quadro(await pedido.body())


@app.post("/visao/foto/{numero}")
async def foto_da_camera(numero: str, pedido: Request):
    robo.receber_foto(numero, await pedido.body())
    return {"ok": True}


# ---------- editor de sinais: grava em libras/animacoes/*_usuario.json ----------
PASTA_ANIMACOES = os.path.join("libras", "animacoes")
ARQUIVOS_DO_EDITOR = {"sinal": "sinais_usuario.json", "alfabeto": "alfabeto_usuario.json"}


def _chave(texto: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFD", str(texto).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(re.findall(r"[a-z0-9]+", t))


@app.post("/api/sinal")
async def gravar_sinal(pedido: Request):
    """Corpo: {"tipo": "sinal"|"alfabeto", "palavra": "bom dia", "dados": {"quadros": [...]}}.
    Só vale a partir da própria B13 (o tablet chega pelo cabo, como localhost)."""
    if not getattr(config, "LIBRAS_EDITOR_LIGADO", False):
        raise HTTPException(403, "editor desligado no config.py")
    if pedido.client is None or pedido.client.host not in ("127.0.0.1", "::1"):
        raise HTTPException(403, "só a partir da própria B13")
    corpo = await pedido.json()
    arquivo = ARQUIVOS_DO_EDITOR.get(corpo.get("tipo"))
    chave = _chave(corpo.get("palavra", ""))
    dados = corpo.get("dados")
    if not arquivo or not chave or not isinstance(dados, dict) or not isinstance(dados.get("quadros"), list):
        raise HTTPException(400, "pedido inválido")
    if corpo["tipo"] == "alfabeto":
        chave = chave.upper()[:1]
    caminho = os.path.join(PASTA_ANIMACOES, arquivo)
    atual = {}
    if os.path.isfile(caminho):
        with open(caminho, encoding="utf-8") as f:
            atual = json.load(f)
    atual[chave] = dados
    with open(caminho + ".tmp", "w", encoding="utf-8") as f:
        json.dump(atual, f, ensure_ascii=False, indent=1)
    os.replace(caminho + ".tmp", caminho)   # troca inteira: nunca deixa o arquivo pela metade
    if getattr(robo, "libras", None) is not None:
        robo.libras.carregar_animacoes(forcar=True)
    print(f"[editor] gravei '{chave}' em {arquivo}")
    return {"ok": True, "palavra": chave}


# Imagens, vídeos e animações dos sinais (tem que vir antes da página)
os.makedirs(os.path.join("libras", "sinais"), exist_ok=True)
os.makedirs(os.path.join("libras", "alfabeto"), exist_ok=True)
os.makedirs(PASTA_ANIMACOES, exist_ok=True)
app.mount("/libras", StaticFiles(directory="libras"), name="libras")

# A tela de Libras. No modo dedicado ela é a página principal.
if DEDICADO:
    app.mount("/", StaticFiles(directory="libras_tela", html=True), name="libras_tela")
else:
    app.mount("/libras-tela", StaticFiles(directory="libras_tela", html=True), name="libras_tela")
    app.mount("/", StaticFiles(directory="rosto", html=True), name="rosto")


if __name__ == "__main__":
    if DEDICADO:
        from robo.robo_libras import RoboLibras
        robo = RoboLibras()
    else:
        from robo.robo import Robo
        robo = Robo()
    pagina = "" if DEDICADO else "/libras-tela/"
    print()
    print("=" * 60)
    print(f"  {config.NOME_DO_ROBO} está no ar! ({'modo Libras dedicado' if DEDICADO else 'robô completo'})")
    print(f"  No tablet (ligado no cabo USB), abra: http://localhost:{config.PORTA}{pagina}")
    print("  Para desligar: aperte Ctrl+C nesta janela")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=config.PORTA, log_level="warning")
